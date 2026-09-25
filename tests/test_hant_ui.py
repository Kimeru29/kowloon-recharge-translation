from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.hant_inventory import inventory_hant_text
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells
from tools.hant_ui import (
    HANT_ENGLISH_LINES,
    HANT_POINTER_TABLE_OFFSET,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_WRAPPED_LINES,
    patch_hant_tutorial,
)
from tools.startup_ui import NAME_PROMPT_POINTER_TABLE_OFFSET, NAME_PROMPT_TEXTS
from tools.localization import encode_ps2_english

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


def _segment_file_offset(info, va: int) -> int:
    return info.file_offset + (va - info.segment_vaddr)


class HantTutorialTests(unittest.TestCase):
    def test_repoints_tutorial_descriptor_to_wrapped_translation_table(self) -> None:
        result, info = patch_hant_tutorial(RAW)
        self.assertGreater(len(result), len(RAW))
        self.assertEqual(0x902F00, info.segment_vaddr)

        for index in (2, 3):
            target_va = struct.unpack_from("<I", result, NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = _segment_file_offset(info, target_va)
            expected = encode_ps2_english(NAME_PROMPT_TEXTS[index], collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        table_va = struct.unpack_from("<I", result, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
        self.assertGreaterEqual(table_va, info.segment_vaddr)
        self.assertLess(table_va, info.segment_vaddr + info.payload_size)
        table_file = _segment_file_offset(info, table_va)

        self.assertEqual(16, len(HANT_WRAPPED_LINES))
        for index, english in enumerate(HANT_WRAPPED_LINES):
            self.assertLessEqual(measured_hant_cells(english), HANT_LAYOUT_PROFILE.max_cells)
            target_va = struct.unpack_from("<I", result, table_file + index * 4)[0]
            self.assertGreaterEqual(target_va, info.segment_vaddr)
            self.assertLess(target_va, info.segment_vaddr + info.payload_size)
            target_file = _segment_file_offset(info, target_va)
            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            self.assertEqual(expected, result[target_file:target_file + len(expected)])

        eof_va = struct.unpack_from("<I", result, table_file + len(HANT_WRAPPED_LINES) * 4)[0]
        self.assertEqual(0x795FBC, eof_va)

        # The pristine 17-entry tutorial table becomes immutable provenance;
        # only the descriptor is redirected to the wrapped table.
        self.assertEqual(
            RAW[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
            result[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4],
        )

    def test_wrapping_preserves_established_tutorial_wording_and_punctuation(self) -> None:
        expected = " ".join((
            HANT_ENGLISH_LINES[0].strip(),
            *(HANT_ENGLISH_LINES[index].strip() for index in (2, 3, 4)),
            HANT_ENGLISH_LINES[7].strip(),
            *(HANT_ENGLISH_LINES[index].strip() for index in (9, 10, 12, 13, 14)),
        ))
        self.assertEqual(expected, " ".join(HANT_WRAPPED_LINES))

    def test_unresolved_hant_candidates_remain_pristine(self) -> None:
        result, _info = patch_hant_tutorial(RAW)
        candidates = [
            entry for entry in inventory_hant_text(RAW, None)
            if entry.owner == "executable_hant_candidate"
        ]
        self.assertGreaterEqual(len(candidates), 10)

        for entry in candidates:
            with self.subTest(key=entry.key):
                encoded = entry.source_text.encode("cp932") + b"\x00"
                self.assertEqual(
                    RAW[entry.source_offset:entry.source_offset + len(encoded)],
                    result[entry.source_offset:entry.source_offset + len(encoded)],
                )
                for pointer_offset in entry.pointer_offsets:
                    self.assertEqual(
                        RAW[pointer_offset:pointer_offset + 4],
                        result[pointer_offset:pointer_offset + 4],
                    )

    def test_fail_closes_if_hant_source_pointer_or_descriptor_is_not_pristine(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x5C8B10] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T source"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_POINTER_TABLE_OFFSET + 3 * 4] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T pointer"):
            patch_hant_tutorial(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[HANT_TUTORIAL_DESCRIPTOR_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T tutorial descriptor"):
            patch_hant_tutorial(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
