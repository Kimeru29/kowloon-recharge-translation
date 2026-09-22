from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.adv_layout import patch_adv_horizontal_layout

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class AdvHorizontalLayoutTests(unittest.TestCase):
    def test_transposes_line_and_glyph_axes_without_touching_font_renderer(self) -> None:
        result = patch_adv_horizontal_layout(RAW)

        # VA 0x24F9E0: X now reads byte-position field +0x465 rather than line +0x463.
        self.assertEqual(0x80430465, struct.unpack_from("<I", result, 0x14FA60)[0])
        # VA 0x24F9E8: normalize the byte position to a two-byte glyph index.
        self.assertEqual(0x00031843, struct.unpack_from("<I", result, 0x14FA68)[0])
        # VA 0x24FA24: Y now reads the line field +0x463.
        self.assertEqual(0x80440463, struct.unpack_from("<I", result, 0x14FAA4)[0])
        # VA 0x24FA28: line number is already a glyph-row index; do not halve it.
        self.assertEqual(0x0080182D, struct.unpack_from("<I", result, 0x14FAA8)[0])

        changed = [i for i, (a, b) in enumerate(zip(RAW, result)) if a != b]
        allowed = set()
        for offset in (0x14FA60, 0x14FA68, 0x14FAA4, 0x14FAA8):
            allowed.update(range(offset, offset + 4))
        self.assertTrue(changed)
        self.assertTrue(set(changed) <= allowed)
        self.assertEqual(len(RAW), len(result))

    def test_fail_closes_if_renderer_instructions_do_not_match_proven_build(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x14FA60] ^= 1
        with self.assertRaisesRegex(ValueError, "ADV layout preimage"):
            patch_adv_horizontal_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
