from __future__ import annotations

import unittest

from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells, wrap_hant_text


class HantLayoutTests(unittest.TestCase):
    def test_profile_matches_traced_hant_renderer_geometry(self) -> None:
        self.assertEqual(28, HANT_LAYOUT_PROFILE.max_cells)
        self.assertEqual(12.0, HANT_LAYOUT_PROFILE.glyph_advance)
        self.assertEqual(16.0, HANT_LAYOUT_PROFILE.line_spacing)
        self.assertEqual(5, HANT_LAYOUT_PROFILE.controller_gap_cells)
        self.assertEqual(16, HANT_LAYOUT_PROFILE.max_rows)
        self.assertLess(HANT_LAYOUT_PROFILE.max_cells, 0x40 // 2)

    def test_wraps_at_words_without_changing_official_wording(self) -> None:
        text = "The H.A.N.T is a mini info device designed to support exploration."
        lines = wrap_hant_text(text, max_cells=HANT_LAYOUT_PROFILE.max_cells)

        self.assertEqual(
            (
                "The H.A.N.T is a mini info",
                "device designed to support",
                "exploration.",
            ),
            lines,
        )
        self.assertEqual(" ".join(lines), text)

    def test_controller_placeholder_reserves_display_width(self) -> None:
        text = "Press the      button to bring up the command thumbnails."
        lines = wrap_hant_text(
            text,
            max_cells=HANT_LAYOUT_PROFILE.max_cells,
            reserved_spans=((10, 15),),
        )

        self.assertEqual(
            (
                "Press the      button to",
                "bring up the command",
                "thumbnails.",
            ),
            lines,
        )
        self.assertIn(" " * HANT_LAYOUT_PROFILE.controller_gap_cells, lines[0])
        self.assertLessEqual(measured_hant_cells(lines[0], ((10, 15),)), HANT_LAYOUT_PROFILE.max_cells)

    def test_rejects_single_unbreakable_token_wider_than_line(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot fit"):
            wrap_hant_text("X" * 29, max_cells=HANT_LAYOUT_PROFILE.max_cells)

    def test_wrapping_is_deterministic(self) -> None:
        text = "The H.A.N.T is a mini info device designed to support exploration."
        self.assertEqual(
            wrap_hant_text(text, max_cells=HANT_LAYOUT_PROFILE.max_cells),
            wrap_hant_text(text, max_cells=HANT_LAYOUT_PROFILE.max_cells),
        )


if __name__ == "__main__":
    unittest.main()
