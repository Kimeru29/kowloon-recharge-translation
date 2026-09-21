from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.iso9660_patch import IsoRecord
from tools.translation_overlay import collect_overlay, plan_replacements


class TranslationOverlayTests(unittest.TestCase):
    def test_later_root_overrides_same_path_and_records_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            exact = base / "exact"
            accepted = base / "accepted"
            (exact / "DG").mkdir(parents=True)
            (accepted / "DG").mkdir(parents=True)
            (exact / "DG" / "A.MTX").write_bytes(b"exact")
            (accepted / "DG" / "A.MTX").write_bytes(b"accepted")
            (exact / "DG" / "B.KSF").write_bytes(b"ksf")

            manifest = collect_overlay(
                [("exact", exact), ("accepted", accepted)]
            )

            by_path = {entry.path: entry for entry in manifest.entries}
            self.assertEqual({"DG/A.MTX", "DG/B.KSF"}, set(by_path))
            self.assertEqual(b"accepted", by_path["DG/A.MTX"].source_path.read_bytes())
            self.assertEqual("accepted", by_path["DG/A.MTX"].provenance)
            self.assertEqual(1, len(manifest.collisions))
            self.assertEqual("DG/A.MTX", manifest.collisions[0].path)
            self.assertEqual("exact", manifest.collisions[0].replaced_provenance)
            self.assertEqual("accepted", manifest.collisions[0].replacement_provenance)

    def test_rejects_paths_outside_adv_overlay_shape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.txt").write_text("x")

            with self.assertRaisesRegex(ValueError, "MTX or KSF"):
                collect_overlay([("bad", root)])


class ReplacementPlanningTests(unittest.TestCase):
    def test_keeps_fitting_file_in_place_and_relocates_growth_at_append_cursor(self) -> None:
        records = {
            "ADV/DG/A.MTX": IsoRecord("ADV/DG/A.MTX", 100, 3000, 0, 10),
            "ADV/DG/B.KSF": IsoRecord("ADV/DG/B.KSF", 200, 4096, 0, 20),
        }

        plan = plan_replacements(
            records,
            {
                "DG/A.MTX": 3500,  # still two sectors, fits existing allocation
                "DG/B.KSF": 5000,  # grows 2 -> 3 sectors, must relocate
            },
            append_start=1000,
        )

        a = plan.by_path["DG/A.MTX"]
        b = plan.by_path["DG/B.KSF"]
        self.assertFalse(a.relocated)
        self.assertEqual(100, a.output_extent)
        self.assertTrue(b.relocated)
        self.assertEqual(1000, b.output_extent)
        self.assertEqual(3, b.output_sectors)
        self.assertEqual(3, plan.appended_sectors)

    def test_rejects_overlay_file_missing_from_embedded_iso(self) -> None:
        with self.assertRaisesRegex(ValueError, "not found"):
            plan_replacements({}, {"DG/MISSING.MTX": 10}, append_start=100)


if __name__ == "__main__":
    unittest.main()
