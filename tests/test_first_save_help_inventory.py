"""The first-save UI must account for every H.A.N.T. Help body."""
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from tools.first_save_help_inventory import inventory
from tools.inspect_english_bytes import parse as parse_english

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / "startup-flow-v10/fixtures/elf/SLPM_665.11"
ENGLISH = Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")


class FirstSaveHelpInventoryTests(unittest.TestCase):
    @unittest.skipUnless(ORIGINAL.exists() and ENGLISH.exists(), "Owned pristine ELF and remaster corpus unavailable")
    def test_all_55_topic_bodies_are_accounted_for(self):
        source = ORIGINAL.read_bytes()
        original_hash = hashlib.sha256(source).hexdigest()
        result = inventory(source, parse_english(ENGLISH))
        self.assertEqual(55, result["total_topics"])
        self.assertEqual(0, result["empty_pages"])
        self.assertEqual(55, result["meaningful_pages"])
        self.assertEqual(5, result["already_translated_pages"])
        self.assertEqual(50, result["outstanding_pages"])
        self.assertEqual(15, len(result["shared_one_line_placeholder_pages"]))
        self.assertEqual(759, result["meaningful_source_rows"])
        self.assertEqual(737, result["exact_official_rows"])
        self.assertEqual(original_hash, hashlib.sha256(ORIGINAL.read_bytes()).hexdigest())
        for needed in ("jumping", "wire_gun", "save_load", "basic_attack"):
            page = next(page for page in result["pages"] if page["key"] == needed)
            self.assertFalse(page["existing_r66_english"])
            self.assertGreater(page["icon_records"], 0)
            self.assertGreater(page["japanese_rows"], 0)


if __name__ == "__main__":
    unittest.main()
