from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.corpus import estimate_mtx_text_coverage, extract_japanese_literal_runs


def mtx_with_runs(*runs: str) -> bytes:
    body = b"r".join(run.encode("cp932") for run in runs) + b"wc_"
    return struct.pack("<2H", 1, 0) + body


class MtxTextCoverageTests(unittest.TestCase):
    def test_extracts_non_ascii_japanese_runs_without_treating_ascii_controls_as_text(self) -> None:
        raw = mtx_with_runs("猫犬", "専用")

        self.assertEqual({"猫犬", "専用"}, extract_japanese_literal_runs(raw))

    def test_estimates_novel_ps2_only_text_separately_from_reused_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"

            self._write(ps2 / "DG" / "MAPPED.MTX", mtx_with_runs("猫犬"))
            self._write(ps4 / "DG" / "MAPPED.MTX", mtx_with_runs("猫犬"))
            dc = ps4 / "DG" / "EN" / "MAPPEDDC.json"
            dc.parent.mkdir(parents=True, exist_ok=True)
            dc.write_text(json.dumps({"keys": [4], "values": ["Cats"]}), encoding="utf-8")

            self._write(ps2 / "FI" / "ONLY.MTX", mtx_with_runs("猫犬", "専用"))

            self._write(ps2 / "DG" / "UNMAPPED.MTX", mtx_with_runs("未訳"))
            self._write(ps4 / "DG" / "UNMAPPED.MTX", mtx_with_runs("未訳"))

            coverage = estimate_mtx_text_coverage(ps2, ps4)

            self.assertEqual(3, coverage["all_unique_runs"])
            self.assertEqual(1, coverage["mapped_common_unique_runs"])
            self.assertEqual(2, coverage["ps2_only_unique_runs"])
            self.assertEqual(1, coverage["ps2_only_reused_in_mapped_common"])
            self.assertEqual(1, coverage["ps2_only_novel_runs"])
            self.assertEqual(1, coverage["common_unmapped_unique_runs"])

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


if __name__ == "__main__":
    unittest.main()
