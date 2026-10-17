"""Focused regression tests for the r67.15g western tablet layout correction."""
from __future__ import annotations

import json
import struct
import unicodedata
import unittest
from pathlib import Path

from tools.r67_14t_stone_tablet_fit import read_string, tablet_registry
from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q_MANIFEST
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO

try:
    from tools.r67_15g_tablet_layout import (
        CENTERING_WIDTH_CELLS,
        PERMITTED_EXISTING_RANGES,
        ROW_OWNERS,
        apply,
    )
except ModuleNotFoundError:
    CENTERING_WIDTH_CELLS = 21
    PERMITTED_EXISTING_RANGES = ()
    ROW_OWNERS = (0x590FB8, 0x590FBC, 0x590FC0)
    apply = None

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-15f-item-panel-layout.elf"


@unittest.skipUnless(SOURCE.is_file(), "Requires the parent-approved 15f ELF")
class WesternTabletLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_bytes()

    def test_western_inscription_has_no_quote_ornaments_and_is_centered(self):
        self.assertIsNotNone(apply, "the tablet layout component must be implemented")
        old_rows = tuple(unicodedata.normalize(
            "NFKC", read_string(self.source, struct.unpack_from("<I", self.source, owner)[0]).decode("cp932")
        ) for owner in ROW_OWNERS)
        self.assertIn('"', old_rows[0])
        self.assertTrue(old_rows[2].endswith('"'))
        self.assertEqual(tuple(len(row) - len(row.lstrip()) for row in old_rows), (1, 2, 1))
        result, report = apply(self.source)
        expected = (
            "    The bowed one",
            "  walks west, finds",
            "  the mercy of God.",
        )
        actual = tuple(unicodedata.normalize(
            "NFKC", read_string(result, struct.unpack_from("<I", result, owner)[0]).decode("cp932")
        ) for owner in ROW_OWNERS)
        self.assertEqual(actual, expected)
        self.assertTrue(all('"' not in row for row in actual))
        cells = tuple(len(row) for row in actual)
        self.assertEqual(cells, (17, 19, 19))
        for row in actual:
            left = len(row) - len(row.lstrip())
            right = CENTERING_WIDTH_CELLS - len(row)
            self.assertEqual(left, right)
        self.assertTrue(report["old_14t_ui_lock_passed_after_in_memory_reconstruction"])

    def test_only_western_row_pointers_and_segment_size_change_in_existing_elf(self):
        result, report = apply(self.source)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.source, result))
            if before != after
        }
        permitted = set(range(0x64, 0x68))
        for start, end in PERMITTED_EXISTING_RANGES:
            permitted.update(range(start, end))
        self.assertLessEqual(changed, permitted)
        self.assertEqual(set(report["modified_existing_offsets"]), {hex(i) for i in changed})
        self.assertEqual(report["modified_tablet_row_owners"], [hex(i) for i in ROW_OWNERS])

    def test_all_other_tablet_records_and_unrelated_owners_remain_identical(self):
        result, _ = apply(self.source)
        for record in tablet_registry(self.source):
            if record != 0x590FB0:
                self.assertEqual(result[record:record + 24], self.source[record:record + 24])
        self.assertEqual(result[0x590F30:0x590F54], self.source[0x590F30:0x590F54])
        self.assertEqual(result[0x58A250:0x58A268], self.source[0x58A250:0x58A268])

    def test_original_q_lock_and_scoped_14t_ui_exception_are_reported(self):
        result, report = apply(self.source)
        q_lock = json.loads(Q_MANIFEST.read_text())
        self.assertTrue(verify_approved(result, q_lock)["approved_regions"])
        self.assertTrue(report["old_14t_ui_lock_passed_after_in_memory_reconstruction"])
        self.assertFalse(report["runtime_verified"])

    def test_changed_owner_preimage_is_rejected(self):
        changed = bytearray(self.source)
        changed[ROW_OWNERS[0]] ^= 1
        with self.assertRaisesRegex(ValueError, "preimage"):
            apply(bytes(changed))

    def test_accepts_a_sequentially_extended_elf_and_appends_after_it(self):
        extended = bytearray(self.source + b"prior-component")
        while len(extended) & 3:
            extended.append(0)
        struct.pack_into("<I", extended, 0x64, len(extended) - ELF_SEGMENT_FO)
        result, report = apply(bytes(extended))
        self.assertEqual(report["source_elf_size"], len(extended))
        self.assertEqual(int(report["appended_extent"]["start"], 16), len(extended))
        self.assertGreater(len(result), len(extended))
        self.assertEqual(struct.unpack_from("<I", result, 0x64)[0], len(result) - ELF_SEGMENT_FO)


if __name__ == "__main__":
    unittest.main()
