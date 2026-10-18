"""Run the complete native EE glyph geometry builder against the real ELF."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.r67_native_geometry import (
    BUILDER_END,
    BUILDER_START,
    SOURCE_ELF,
    render,
)


class NativeGlyphGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = SOURCE_ELF.read_bytes()

    def test_real_elf_pins_builder_getter_and_accumulator_words(self):
        bias = 0xFFF80
        for address, word in {
            BUILDER_START: 0x27BDFF30,
            0x18D044: 0x0C068064,
            0x18E010: 0x46190018,
            0x18E014: 0x4601D81C,
            0x18E1EC: 0x03E00008,
        }.items():
            self.assertEqual(struct.unpack_from("<I", self.raw, address - bias)[0], word)
        font = 0x5D77D0 - bias
        self.assertEqual(self.raw[font + 4:font + 6], bytes((16, 18)))
        self.assertEqual(struct.unpack_from("<HH", self.raw, font + 6), (256, 256))
        self.assertLess(BUILDER_START, BUILDER_END)

    def test_27_native_glyphs_reach_expected_last_quad_edge(self):
        result = render(self.raw, "A" * 27)
        self.assertEqual(len(result.nodes), 28)  # glyphs plus linked terminator
        self.assertAlmostEqual(result.bounds.right, 241.0)
        self.assertEqual(result.native_private[0x04], result.nodes[0].address)
        self.assertEqual(result.nodes[-1].control, 0xFFFFFF0F)

    def test_newline_uses_native_nine_pixel_line_pitch(self):
        result = render(self.raw, "A\nA")
        self.assertAlmostEqual(result.nodes[0].quads[0].top, 16.0)
        self.assertAlmostEqual(result.nodes[2].quads[0].top, 25.0)

    def test_native_space_controls_advance_full_and_half_widths(self):
        full = render(self.raw, [0xFFFFFF0B])
        half = render(self.raw, [0xFFFFFF0A])
        self.assertAlmostEqual(full.cursor_x, 42.0)
        self.assertAlmostEqual(half.cursor_x, 34.0)

    def test_nonzero_letter_spacing_comes_from_native_cursor_path(self):
        result = render(self.raw, "AA", letter_spacing=2.0)
        self.assertAlmostEqual(result.cursor_x, 46.0)
        self.assertAlmostEqual(result.nodes[1].quads[0].left, 36.0)


if __name__ == "__main__":
    unittest.main()
