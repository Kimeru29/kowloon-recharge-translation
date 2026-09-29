from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.hant_inventory import inventory_hant_text

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class HantInventoryTests(unittest.TestCase):
    def test_known_tutorial_table_classifies_text_and_control_slots(self) -> None:
        entries = inventory_hant_text(RAW, None)
        tutorial = {entry.key: entry for entry in entries if entry.owner == "hant_tutorial"}

        self.assertEqual(17, len(tutorial))
        unresolved_indices = {0, 2, 3, 4, 7, 8, 9, 10, 12, 13, 14}
        control_indices = {1, 5, 6, 11, 15, 16}
        self.assertEqual(
            unresolved_indices,
            {int(key.rsplit("_", 1)[1]) for key, entry in tutorial.items() if entry.classification == "unresolved"},
        )
        self.assertEqual(
            control_indices,
            {int(key.rsplit("_", 1)[1]) for key, entry in tutorial.items() if entry.classification == "control"},
        )
        self.assertTrue(all(entry.official_english is None for entry in tutorial.values()))

    def test_pointer_backed_hant_occurrences_outside_tutorial_are_surfaced(self) -> None:
        entries = inventory_hant_text(RAW, None)
        candidates = {entry.source_offset: entry for entry in entries if entry.owner == "executable_hant_candidate"}

        self.assertIn(0x5876E0, candidates)
        self.assertEqual("Ｈ．Ａ．Ｎ．Ｔの機能", candidates[0x5876E0].source_text)
        self.assertEqual((0x587840,), candidates[0x5876E0].pointer_offsets)
        self.assertEqual("unresolved", candidates[0x5876E0].classification)
        self.assertGreaterEqual(len(candidates), 10)

    def test_help_body_inventory_models_all_55_mode4_topic_leaves(self) -> None:
        import tools.hant_inventory as hant_inventory

        inventory = getattr(hant_inventory, "inventory_hant_help_bodies", None)
        self.assertIsNotNone(inventory, "expected bounded H.A.N.T. Help body inventory")
        entries = inventory(RAW)

        self.assertEqual(55, len(entries))
        self.assertEqual((20, 20, 15), tuple(
            sum(entry.category_index == category for entry in entries)
            for category in range(3)
        ))
        by_tuple = {(entry.mode, entry.category_index, entry.topic_index): entry for entry in entries}

        hant_functions = by_tuple[(4, 2, 0)]
        self.assertEqual(0x5CBAB0, hant_functions.text_descriptor_offset)
        self.assertEqual(0x5C8C70, hant_functions.text_table_offset)
        self.assertEqual(16, hant_functions.row_count)
        self.assertEqual(0x5CBA60, hant_functions.metadata_descriptor_offset)
        self.assertEqual(0x5C8AA0, hant_functions.metadata_offset)
        self.assertEqual(3, hant_functions.metadata_record_count)

        command_thumbnails = by_tuple[(4, 2, 1)]
        self.assertEqual(0x5CBAB4, command_thumbnails.text_descriptor_offset)
        self.assertEqual(0x5C9180, command_thumbnails.text_table_offset)
        self.assertEqual(55, command_thumbnails.row_count)
        self.assertEqual(2, command_thumbnails.metadata_record_count)

        shop = by_tuple[(4, 2, 5)]
        self.assertEqual(0x5CBAC4, shop.text_descriptor_offset)
        self.assertEqual(0x5C9B80, shop.text_table_offset)
        self.assertEqual(7, shop.row_count)
        self.assertEqual(0x5CBA74, shop.metadata_descriptor_offset)
        self.assertEqual(0x698968, shop.metadata_offset)
        self.assertEqual(0, shop.metadata_record_count)

        self.assertEqual(55, len({entry.text_descriptor_offset for entry in entries}))
        self.assertEqual(55, len({(entry.category_index, entry.topic_index) for entry in entries}))

    def test_official_rows_classify_exact_and_documented_semantic_matches(self) -> None:
        rows = (
            ("Ｈ．Ａ．Ｎ．Ｔは、", "The H.A.N.T is", 0x100),
            ("次に、　方向ボタンで", "Next, use the directional buttons", 0x200),
        )
        entries = inventory_hant_text(RAW, rows)
        by_key = {entry.key: entry for entry in entries}

        self.assertEqual("official_exact", by_key["hant_tutorial_02"].classification)
        self.assertEqual("The H.A.N.T is", by_key["hant_tutorial_02"].official_english)
        self.assertEqual("official_semantic", by_key["hant_tutorial_12"].classification)
        self.assertEqual("Next, use the directional buttons", by_key["hant_tutorial_12"].official_english)
        self.assertIn("方向ボタン", by_key["hant_tutorial_12"].evidence)

    def test_inventory_keys_are_unique_and_unresolved_entries_have_no_english(self) -> None:
        entries = inventory_hant_text(RAW, None)

        self.assertEqual(len(entries), len({entry.key for entry in entries}))
        self.assertTrue(all(entry.official_english is None for entry in entries if entry.classification == "unresolved"))
        translated = [entry for entry in entries if entry.classification in {"official_exact", "official_semantic"}]
        self.assertTrue(all(entry.classification != "control" for entry in translated))

    def test_committed_manifest_contains_only_proven_tutorial_subset(self) -> None:
        path = Path(__file__).parents[1] / "translations" / "hant_ui.json"
        rows = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(17, len(rows))
        self.assertTrue(all(row["key"].startswith("hant_tutorial_") for row in rows))
        self.assertTrue(all(row["owner"] == "hant_tutorial" for row in rows))
        self.assertTrue(all(row["official_english"] is None for row in rows))
        self.assertEqual(
            {"key", "source_offset", "pointer_offsets", "source_text", "official_english", "classification", "owner", "evidence"},
            set(rows[0]),
        )


if __name__ == "__main__":
    unittest.main()
