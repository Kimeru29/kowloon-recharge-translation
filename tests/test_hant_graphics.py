from __future__ import annotations

from hashlib import sha256
import unittest

from tests.test_tmx import make_container
from tools.hant_graphics import (
    HANT_CAPTIONS,
    CaptionSpec,
    port_indexed_caption_atlas,
    repaint_caption_indices,
)
from tools.tmx import _decode_indices, find_tmx_entry, replace_tmx_indexed


class HantGraphicsTests(unittest.TestCase):
    def test_caption_manifest_is_semantic_and_bounded_to_gp020_atlas(self) -> None:
        self.assertEqual(
            {
                "help": "HELP",
                "config": "CONFIG",
                "reset_defaults": "RESET DEFAULTS",
                "delete": "DELETE",
                "page": "PAGE",
                "mail": "MAIL",
                "dictionary": "DICTIONARY",
                "enemy": "ENEMY",
                "memo": "MEMO",
            },
            {spec.key: spec.english for spec in HANT_CAPTIONS},
        )
        self.assertTrue(all(spec.provenance == "semantic" for spec in HANT_CAPTIONS))
        for spec in HANT_CAPTIONS:
            left, top, right, bottom = spec.rect
            self.assertGreaterEqual(left, 0)
            self.assertGreaterEqual(top, 0)
            self.assertLessEqual(right, 512)
            self.assertLessEqual(bottom, 512)
            self.assertLess(left, right)
            self.assertLess(top, bottom)
            self.assertEqual(64, len(spec.source_sha256))

    def test_repaint_clears_only_green_family_pixels_inside_rect_and_draws_english(self) -> None:
        width, height = 32, 12
        palette = [(255, 255, 255, 0), (19, 204, 58, 255), (220, 10, 20, 255)]
        indices = bytearray([0] * (width * height))

        # Simulate baked Japanese pixels plus unrelated red chrome in the same box.
        rect = (2, 2, 30, 10)
        for x in range(3, 20):
            indices[4 * width + x] = 1
        indices[5 * width + 2] = 2
        indices[5 * width + 21] = 2
        before = bytes(indices)
        region = bytes(
            indices[y * width + x]
            for y in range(rect[1], rect[3])
            for x in range(rect[0], rect[2])
        )
        spec = CaptionSpec(
            key="help",
            english="HELP",
            rect=rect,
            scale_x=1,
            scale_y=1,
            source_sha256=sha256(region).hexdigest(),
        )

        out = repaint_caption_indices(before, width, height, palette, (spec,))

        self.assertNotEqual(before, out)
        self.assertEqual(2, out[5 * width + 2])
        self.assertEqual(2, out[5 * width + 21])
        for y in range(height):
            for x in range(width):
                if rect[0] <= x < rect[2] and rect[1] <= y < rect[3]:
                    continue
                self.assertEqual(before[y * width + x], out[y * width + x])
        self.assertGreater(sum(1 for value in out if value == 1), 0)

    def test_repaint_fails_closed_when_source_caption_region_drifted(self) -> None:
        width, height = 16, 8
        palette = [(255, 255, 255, 0), (19, 204, 58, 255)]
        indices = bytes([0] * (width * height))
        spec = CaptionSpec(
            key="help",
            english="HELP",
            rect=(1, 1, 15, 7),
            scale_x=1,
            scale_y=1,
            source_sha256="0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "caption preimage mismatch: help"):
            repaint_caption_indices(indices, width, height, palette, (spec,))

    def test_ports_indexed_caption_atlas_without_changing_container_layout(self) -> None:
        width, height = 32, 8
        blob = make_container(width=width, height=height)
        blob = blob.replace(b"GRP999/GP999_00.TMX", b"GRP020/GP020_03.TMX")
        palette = [(255, 255, 255, 0)] * 256
        palette[1] = (19, 204, 58, 255)
        palette[2] = (200, 20, 30, 255)
        indices = bytearray([0] * (width * height))
        rect = (2, 0, 30, 8)
        for x in range(2, 14):
            indices[4 * width + x] = 1
        indices[5 * width + 2] = 2
        source = replace_tmx_indexed(blob, "GRP020/GP020_03.TMX", palette, bytes(indices))
        region = bytes(
            indices[y * width + x]
            for y in range(rect[1], rect[3])
            for x in range(rect[0], rect[2])
        )
        spec = CaptionSpec(
            key="help",
            english="HELP",
            rect=rect,
            scale_x=1,
            scale_y=1,
            source_sha256=sha256(region).hexdigest(),
        )

        out = port_indexed_caption_atlas(source, "GRP020/GP020_03.TMX", (spec,))

        self.assertEqual(len(source), len(out))
        self.assertEqual(source[-4:], out[-4:])
        self.assertEqual(
            find_tmx_entry(source, "GRP020/GP020_03.TMX"),
            find_tmx_entry(out, "GRP020/GP020_03.TMX"),
        )
        source_indices = _decode_indices(source, find_tmx_entry(source, "GRP020/GP020_03.TMX"))
        target_indices = _decode_indices(out, find_tmx_entry(out, "GRP020/GP020_03.TMX"))
        for y in range(height):
            for x in range(width):
                if rect[0] <= x < rect[2] and rect[1] <= y < rect[3]:
                    continue
                self.assertEqual(source_indices[y * width + x], target_indices[y * width + x])


if __name__ == "__main__":
    unittest.main()
