from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.import_exact_ksf import import_exact_ksf_corpus


class KsfCorpusImportTests(unittest.TestCase):
    def test_imports_only_exact_mapped_ksf_and_reports_field_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"
            output = root / "out"

            source = "見る".encode("cp932")
            raw = b"\x00\x01" + source + (b"\x00" * (20 - len(source))) + b"\x02END"
            for base in (ps2, ps4):
                path = base / "DG" / "A.KSF"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            dc = ps4 / "DG" / "EN" / "A.KSFDC.json"
            dc.parent.mkdir(parents=True, exist_ok=True)
            dc.write_text(json.dumps({"keys": [2], "values": ["Look"]}), encoding="utf-8")

            report = import_exact_ksf_corpus(ps2, ps4, output)

            self.assertEqual(1, report["eligible_exact_mapped_files"])
            self.assertEqual(1, report["fit_entries"])
            self.assertEqual(0, report["overflow_entries"])
            self.assertEqual(0, report["ambiguous_entries"])
            self.assertEqual(b"Look", (output / "DG" / "A.KSF").read_bytes()[2:6])


if __name__ == "__main__":
    unittest.main()
