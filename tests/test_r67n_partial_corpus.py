from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tests.test_r67n_partial import ORIGINAL, SAME, dc_for, region, script
from tools.r67n_partial_corpus import main


DEFAULT_PATHS = {
    "MS/MS00_01.MTX", "MS/MS01_00.MTX", "MS/MS01_03.MTX", "MS/MS06_03.MTX", "MS/MS13_02.MTX",
    *(f"FD/FD00_{index:02d}.MTX" for index in range(24)), "FD/FD00_29.MTX",
}
PAYLOAD_PATH = Path("MS/MS01_00.MTX")


class PartialCorpusTests(unittest.TestCase):
    def setUp(self) -> None:
        workspace = TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.root = Path(workspace.name)
        self.ps2 = self.root / "ps2"
        self.ps4 = self.root / "ps4"

    def _write_inputs(self) -> None:
        for root in (self.ps2, self.ps4):
            for family in ("MS", "FD"):
                (root / family / "EN").mkdir(parents=True)
        ps4 = script(region(b"r", SAME, b"wc"))
        dc = json.dumps(dc_for(ps4, [(SAME, "Go on")]))
        for item in sorted(DEFAULT_PATHS | {"FD/FD00_24.MTX", "MS/MS99_99.MTX"}):
            path = Path(item)
            ps2 = ps4 if path == PAYLOAD_PATH or item not in DEFAULT_PATHS else script(
                region(b"r", ORIGINAL, b"wc")
            )
            (self.ps2 / path).write_bytes(ps2)
            (self.ps4 / path).write_bytes(ps4)
            (self.ps4 / path.parent / "EN" / f"{path.stem}DC.json").write_text(dc, encoding="utf-8")

    def _args(self, destination: Path) -> list[str]:
        return ["--ps2-adv", str(self.ps2), "--ps4-adv", str(self.ps4),
                "--output-dir", str(destination)]

    def _run(self, destination: Path) -> dict:
        with redirect_stdout(StringIO()):
            self.assertEqual(0, main(self._args(destination)))
        return json.loads((destination / "report.json").read_bytes())

    def test_default_scope_reports_exact_requested_mtx_files(self) -> None:
        self._write_inputs()
        out = self.root / "report"
        report = self._run(out)

        self.assertEqual(30, report["files_examined"])
        self.assertEqual({f"ADV/{path}" for path in DEFAULT_PATHS},
                         {row["path"] for row in report["results"]})
        self.assertEqual(29, report["unresolved_english_entries"])
        self.assertEqual([out / "overlay" / PAYLOAD_PATH], list(out.rglob("*.MTX")))

    def test_rejects_existing_destination_before_reading_sources(self) -> None:
        out = self.root / "already-exists"
        out.mkdir()
        report = out / "report.json"
        report.write_bytes(b"preserve")

        errors = StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as ex:
            main(self._args(out))

        self.assertEqual(2, ex.exception.code)
        self.assertIn("Output directory already exists", errors.getvalue())
        self.assertEqual(b"preserve", report.read_bytes())

    def test_repeated_sweep_has_identical_payload_and_per_entry_hashes(self) -> None:
        self._write_inputs()
        first, second = self.root / "first", self.root / "second"
        expected_line = "Ｇｏ　ｏｎ".encode("cp932")
        expected = script(region(b"r", expected_line, b"wc"))

        reports = [self._run(destination) for destination in (first, second)]
        self.assertEqual(reports[0]["results"], reports[1]["results"])
        for report, destination in zip(reports, (first, second), strict=True):
            row = next(item for item in report["results"] if item["proven_groups"])
            self.assertEqual(expected, (destination / "overlay" / PAYLOAD_PATH).read_bytes())
            self.assertEqual(sha256(expected).hexdigest(), row["output_sha256"])
            self.assertEqual(
                [{"entry_id": 5, "output_start": 5, "output_end": 15,
                  "sha256": sha256(expected_line).hexdigest()}],
                row["spans"][0]["entries"],
            )


if __name__ == "__main__":
    unittest.main()
