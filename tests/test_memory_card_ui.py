from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.hant_ui import patch_hant_tutorial
from tools.memory_card_ui import (
    MEMORY_CARD_MESSAGES,
    MEMORY_CARD_POINTER_TABLE_OFFSET,
    encode_memory_card_english,
    relocated_memory_card_entries,
    validate_memory_card_sources,
)

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class MemoryCardUiTests(unittest.TestCase):
    def test_generic_entries_preserve_pointer_table_order_and_boot_aliases(self) -> None:
        entries = relocated_memory_card_entries(RAW)
        self.assertEqual(
            tuple(sorted(MEMORY_CARD_MESSAGES)),
            tuple(int(entry.key.removeprefix("memory_card_")) for entry in entries),
        )
        slot1 = next(entry for entry in entries if entry.key == "memory_card_1")
        self.assertEqual(
            (MEMORY_CARD_POINTER_TABLE_OFFSET + 4, 0x4077F0, 0x4078D0),
            slot1.pointer_offsets,
        )
        self.assertTrue(slot1.encoded.endswith(b"\x00"))

    def test_proven_startup_memory_card_messages_relocate_to_translation_segment(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        for index, (_source_offset, _source, english) in MEMORY_CARD_MESSAGES.items():
            target_va = struct.unpack_from("<I", result, MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = info.file_offset + (target_va - info.segment_vaddr)
            expected = encode_memory_card_english(english) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

    def test_boot_slot1_message_wraps_before_slot_number_for_stone_panel(self) -> None:
        english = MEMORY_CARD_MESSAGES[1][2]
        self.assertEqual("\n\n\nChecking memory card\n       slot 1", english)

        result, info = patch_hant_tutorial(RAW)
        target_va = struct.unpack_from("<I", result, MEMORY_CARD_POINTER_TABLE_OFFSET + 4)[0]
        target_file = info.file_offset + (target_va - info.segment_vaddr)
        expected = encode_memory_card_english(english) + b"\x00"
        self.assertEqual(expected, result[target_file:target_file + len(expected)])

    def test_boot_memory_card_handlers_follow_relocated_slot1_message(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        primary = struct.unpack_from(
            "<I", result, MEMORY_CARD_POINTER_TABLE_OFFSET + 4
        )[0]
        self.assertGreaterEqual(primary, info.segment_vaddr)

        # H_BootMcardChk and H_EmptyMcardChk each embed a handler-local alias
        # of table entry 1.  Runtime uses these aliases during the pre-title
        # stone-panel check, so they must follow the relocated English string.
        for alias_offset in (0x4077F0, 0x4078D0):
            self.assertEqual(primary, struct.unpack_from("<I", result, alias_offset)[0])

    def test_fail_closes_on_boot_memory_card_handler_alias_drift(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x4077F0] ^= 1
        with self.assertRaisesRegex(ValueError, "Memory-card.*alias"):
            validate_memory_card_sources(bytes(tampered))

    def test_unproven_recharge_clear_data_entries_remain_pristine(self) -> None:
        result, _info = patch_hant_tutorial(RAW)
        for index in (11, 19, 20, 21, 22, 23, 24, 25):
            off = MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4
            self.assertEqual(RAW[off:off + 4], result[off:off + 4])

    def test_fail_closes_on_memory_card_source_or_pointer_drift(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x406B50] ^= 1
        with self.assertRaisesRegex(ValueError, "Memory-card source"):
            validate_memory_card_sources(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[MEMORY_CARD_POINTER_TABLE_OFFSET + 4] ^= 1
        with self.assertRaisesRegex(ValueError, "Memory-card pointer"):
            validate_memory_card_sources(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
