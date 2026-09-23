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
    validate_memory_card_sources,
)

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class MemoryCardUiTests(unittest.TestCase):
    def test_proven_startup_memory_card_messages_relocate_to_translation_segment(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        for index, (_source_offset, _source, english) in MEMORY_CARD_MESSAGES.items():
            target_va = struct.unpack_from("<I", result, MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = info.file_offset + (target_va - info.segment_vaddr)
            expected = encode_memory_card_english(english) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

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
