from __future__ import annotations

import unittest

from tools.regression import RegressionError, compare_manifests, validate_invariants


BASELINE = {
    "schema_version": 1,
    "invariants": {
        "serial": "SLPM-66511",
        "save_directory": "BISLPM-66511Save",
    },
    "entries": [
        {
            "id": "mtx:DG/DG00_00.MTX:27",
            "asset": "DG/DG00_00.MTX",
            "source_sha256": "aaa",
            "provenance": "official-ps4",
            "text": "Old man's voice",
        }
    ],
}


class RegressionTests(unittest.TestCase):
    def test_additive_entries_are_allowed(self) -> None:
        current = {
            **BASELINE,
            "entries": BASELINE["entries"]
            + [
                {
                    "id": "mtx:DG/DG00_00.MTX:40",
                    "asset": "DG/DG00_00.MTX",
                    "source_sha256": "aaa",
                    "provenance": "official-ps4",
                    "text": "Hey, over here.",
                }
            ],
        }

        result = compare_manifests(BASELINE, current)

        self.assertEqual(["mtx:DG/DG00_00.MTX:40"], result.added)
        self.assertEqual([], result.changed)
        self.assertEqual([], result.removed)

    def test_removed_accepted_entry_fails(self) -> None:
        current = {**BASELINE, "entries": []}

        with self.assertRaisesRegex(RegressionError, "removed"):
            compare_manifests(BASELINE, current)

    def test_source_preimage_drift_fails(self) -> None:
        changed = dict(BASELINE["entries"][0])
        changed["source_sha256"] = "bbb"
        current = {**BASELINE, "entries": [changed]}

        with self.assertRaisesRegex(RegressionError, "changed"):
            compare_manifests(BASELINE, current)

    def test_save_and_serial_identity_are_fixed(self) -> None:
        validate_invariants(BASELINE["invariants"])

        with self.assertRaisesRegex(RegressionError, "serial"):
            validate_invariants({"serial": "WRONG", "save_directory": "BISLPM-66511Save"})
        with self.assertRaisesRegex(RegressionError, "save_directory"):
            validate_invariants({"serial": "SLPM-66511", "save_directory": "WRONG"})

    def test_duplicate_stable_ids_are_rejected(self) -> None:
        current = {**BASELINE, "entries": BASELINE["entries"] * 2}

        with self.assertRaisesRegex(RegressionError, "duplicate"):
            compare_manifests(BASELINE, current)


if __name__ == "__main__":
    unittest.main()
