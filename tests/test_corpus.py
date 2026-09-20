from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.corpus import scan_corpus


class CorpusScannerTests(unittest.TestCase):
    def test_classifies_source_relationship_separately_from_localization_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"

            self._write(ps2 / "DG" / "EXACT.MTX", b"same")
            self._write(ps4 / "DG" / "EXACT.MTX", b"same")
            self._dc(ps4 / "DG" / "EN" / "EXACTDC.json", [10, 20], ["One", "Two"])

            self._write(ps2 / "DG" / "UNMAPPED.MTX", b"same2")
            self._write(ps4 / "DG" / "UNMAPPED.MTX", b"same2")

            self._write(ps2 / "DG" / "STRUCT.MTX", b"ps2-struct")
            self._write(ps4 / "DG" / "STRUCT.MTX", b"ps4-struct")
            self._dc(ps4 / "DG" / "EN" / "STRUCTDC.json", [1], ["S"])

            self._write(ps2 / "FI" / "ONLY.MTX", b"ps2-only")

            manifest = scan_corpus(ps2, ps4)
            by_path = {item["path"]: item for item in manifest["assets"] if item["kind"] == "MTX"}

            self.assertEqual("exact", by_path["DG/EXACT.MTX"]["relation"])
            self.assertEqual("mapped", by_path["DG/EXACT.MTX"]["localization"])
            self.assertEqual(2, by_path["DG/EXACT.MTX"]["english_entries"])

            self.assertEqual("exact", by_path["DG/UNMAPPED.MTX"]["relation"])
            self.assertEqual("unmapped", by_path["DG/UNMAPPED.MTX"]["localization"])

            self.assertEqual("structural", by_path["DG/STRUCT.MTX"]["relation"])
            self.assertEqual("ps2-only", by_path["FI/ONLY.MTX"]["relation"])
            self.assertEqual("not-applicable", by_path["FI/ONLY.MTX"]["localization"])

    def test_detects_shared_changed_ps4_binary_as_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"
            for name, ps2_bytes in (("FD00_01.MTX", b"one"), ("FD00_02.MTX", b"two")):
                self._write(ps2 / "FD" / name, ps2_bytes)
                self._write(ps4 / "FD" / name, b"shared-remaster-template")
                self._dc(ps4 / "FD" / "EN" / f"{Path(name).stem}DC.json", [1], ["x"])

            manifest = scan_corpus(ps2, ps4)
            relations = {item["relation"] for item in manifest["assets"]}

            self.assertEqual({"template"}, relations)
            self.assertEqual(2, manifest["summary"]["MTX"]["template"])

    def test_scans_ksf_dc_naming_convention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"
            self._write(ps2 / "DG" / "A.KSF", b"same")
            self._write(ps4 / "DG" / "A.KSF", b"same")
            self._dc(ps4 / "DG" / "EN" / "A.KSFDC.json", [7], ["Choice"])

            manifest = scan_corpus(ps2, ps4)
            item = manifest["assets"][0]

            self.assertEqual("KSF", item["kind"])
            self.assertEqual("mapped", item["localization"])
            self.assertEqual(1, item["english_entries"])

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    @staticmethod
    def _dc(path: Path, keys: list[int], values: list[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"keys": keys, "values": values}), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
