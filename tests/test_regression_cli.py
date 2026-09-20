from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.check_regression import check_regression_files


MANIFEST = {
    "schema_version": 1,
    "invariants": {"serial": "SLPM-66511", "save_directory": "BISLPM-66511Save"},
    "entries": [
        {
            "id": "artifact:test",
            "asset": "test.bin",
            "source_sha256": "source",
            "output_sha256": "output",
            "provenance": "manual",
        }
    ],
}


class RegressionFileCheckTests(unittest.TestCase):
    def test_reads_json_manifests_and_reports_clean_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root / "baseline.json"
            current = root / "current.json"
            baseline.write_text(json.dumps(MANIFEST), encoding="utf-8")
            current.write_text(json.dumps(MANIFEST), encoding="utf-8")

            result = check_regression_files(baseline, current)

            self.assertEqual([], result.added)
            self.assertEqual([], result.changed)
            self.assertEqual([], result.removed)


if __name__ == "__main__":
    unittest.main()
