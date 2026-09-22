from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.hant_ui import HANT_ENGLISH_LINES, HANT_POINTER_TABLE_OFFSET, patch_hant_tutorial
from tools.localization import encode_ps2_english

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class HantTutorialTests(unittest.TestCase):
    def test_repoints_all_visible_hant_lines_into_translation_segment(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        self.assertGreater(len(result), len(RAW))
        self.assertEqual(0x902F00, info.segment_vaddr)

        for index, english in HANT_ENGLISH_LINES.items():
            target_va = struct.unpack_from("<I", result, HANT_POINTER_TABLE_OFFSET + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = info.file_offset + (target_va - info.segment_vaddr)
            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        # Empty separators and EOF are control/data sentinels and stay on their
        # pristine targets rather than being reinterpreted as translatable text.
        for index in (1, 5, 6, 11, 15, 16):
            off = HANT_POINTER_TABLE_OFFSET + index * 4
            self.assertEqual(RAW[off:off + 4], result[off:off + 4])

    def test_fail_closes_if_hant_source_text_or_pointer_is_not_pristine(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x5C8B10] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T source"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_POINTER_TABLE_OFFSET + 3 * 4] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T pointer"):
            patch_hant_tutorial(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
