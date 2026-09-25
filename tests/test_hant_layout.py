from __future__ import annotations

import unittest

from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells, wrap_hant_text


class HantLayoutTests(unittest.TestCase):
    def test_profile_matches_traced_hant_renderer_geometry(self) -> None:
        self.assertEqual(21, HANT_LAYOUT_PROFILE.max_cells)
        self.assertEqual(20.0, HANT_LAYOUT_PROFILE.glyph_advance)
        self.assertEqual(21.0, HANT_LAYOUT_PROFILE.line_spacing)
        self.assertEqual(5, HANT_LAYOUT_PROFILE.controller_gap_cells)

    def test_wraps_at_words_without_changing_official_wording(self) -> None:
        text = "The H.A.N.T is a mini info device designed to support exploration."
        lines = wrap_hant_text(text, max_cells=32)

        self.assertTrue(all(len(line) <= 32 for line in lines))
        self.assertEqual(" ".join(lines), text)

    def test_controller_placeholder_reserves_display_width(self) -> None:
        text = "Press the      button to bring up the command thumbnails."
        lines = wrap_hant_text(
            text,
            max_cells=32,
            reserved_spans=((10, 15),),
        )

        self.assertTrue(all(measured_hant_cells(line) <= 32 for line in lines))

    def test_rejects_single_unbreakable_token_wider_than_line(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot fit"):
            wrap_hant_text("X" * 33, max_cells=32)

    def test_wrapping_is_deterministic(self) -> None:
        text = "The H.A.N.T is a mini info device designed to support exploration."
        self.assertEqual(
            wrap_hant_text(text, max_cells=32),
            wrap_hant_text(text, max_cells=32),
        )


if __name__ == "__main__":
    unittest.main()
