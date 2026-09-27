from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest

from tests.test_tmx import make_container
from tools.startup_graphics import _extend_title_label_backing_indices, port_name_entry_graphics, port_quote_graphic, port_title_startup_graphics
from tools.tmx import decode_tmx_rgba, find_tmx_entry, parse_standalone_tmx, replace_tmx_indexed

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


@unittest.skipIf(Image is None, "Pillow is an optional graphics-build dependency")
class StartupGraphicsTests(unittest.TestCase):
    def test_ports_quote_png_into_same_size_standalone_tmx(self) -> None:
        standalone = make_container(width=4, height=2)[0x100:-4]
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "TR028.png"
            Image.new("RGBA", (8, 4), (11, 22, 33, 255)).save(png)
            out = port_quote_graphic(standalone, png, name="TR028.TMX")

        self.assertEqual(len(standalone), len(out))
        entry = parse_standalone_tmx(out, "TR028.TMX")
        rgba = decode_tmx_rgba(out, entry)
        self.assertEqual({(11, 22, 33, 255)}, {tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)})


    @staticmethod
    def _make_gp088_title_container(*, valid_packed_layout: bool = True) -> bytes:
        def entry(name: str, *, width: int = 512, height: int = 512) -> bytes:
            encoded_name = name.encode("ascii") + b"\x00"
            prefix = bytearray(0x100)
            prefix[:len(encoded_name)] = encoded_name
            chunk_size = 0x40 + 256 * 4 + width * height
            tmx = bytearray(chunk_size)
            struct.pack_into("<II", tmx, 0, 2, chunk_size)
            tmx[8:12] = b"TMX0"
            tmx[16] = 1
            tmx[17] = 0
            struct.pack_into("<HH", tmx, 18, width, height)
            tmx[22] = 0x13
            return bytes(prefix + tmx)

        blob = (
            entry("GRP088/GP088_03.TMX")
            + entry("GRP088/GP088_08.TMX", width=512, height=64)
            + entry("GRP088/GP088_12.TMX")
        )

        title_palette = [(0, 0, 0, 0)] * 256
        title_palette[1] = (200, 50, 10, 255)
        title_palette[2] = (20, 80, 200, 255)
        source_indices = bytearray(512 * 512)
        for y in range(20, 390):
            for x in range(310, 320):
                source_indices[y * 512 + x] = 1
            for x in range(375, 385):
                source_indices[y * 512 + x] = 1
        blob = replace_tmx_indexed(
            blob, "GRP088/GP088_03.TMX", title_palette, bytes(source_indices)
        )

        backing_palette = [(0, 0, 0, 0)] * 256
        backing_palette[0] = (0, 0, 0, 202)
        backing_palette[1] = (0, 0, 0, 126)
        backing_palette[2] = (18, 204, 58, 255)
        backing_palette[15] = (255, 255, 255, 0)
        backing_indices = bytearray([15] * (512 * 64))
        for y in range(1, 23):
            backing_indices[y * 512 + 1:y * 512 + 471] = bytes([0]) * 470
        for y in range(25, 47):
            backing_indices[y * 512 + 1:y * 512 + 71] = bytes([1]) * 70
        for y in range(29, 36):
            backing_indices[y * 512 + 77:y * 512 + 83] = bytes([2]) * 6
        blob = replace_tmx_indexed(
            blob, "GRP088/GP088_08.TMX", backing_palette, bytes(backing_indices)
        )

        target_indices = bytearray(512 * 512)
        if valid_packed_layout:
            for y in range(20, 390):
                for x in range(310, 320):
                    target_indices[(y + 14) * 512 + (x - 223)] = 1
                for x in range(375, 385):
                    target_indices[(y + 14) * 512 + (x - 87)] = 1
            # Simulate the original flattened re:charge banner crossing both titles.
            for y in range(245, 325):
                for x in range(50, 160):
                    target_indices[y * 512 + x] = 2
                for x in range(250, 360):
                    target_indices[y * 512 + x] = 2
        blob = replace_tmx_indexed(
            blob, "GRP088/GP088_12.TMX", title_palette, bytes(target_indices)
        )
        return blob


    def test_extends_gp088_08_title_label_backing_to_longest_english_label(self) -> None:
        width, height = 512, 64
        transparent, black, marker = 15, 1, 2
        indices = bytearray([transparent] * (width * height))

        # Exact pristine GP088_08 geometry: a 470x22 footer strip and an
        # independent 70x22 menu-label backing. r8 extended this to 150 texture
        # pixels, but its runtime screenshot is consistent with the title path
        # presenting this strip at about half logical width.
        # Nine 16px English glyphs need 144 logical pixels, so use a 300px texture
        # strip (about 150 logical pixels on this path), keep the existing 6px
        # texture gap, and move the trailing marker with it.
        for y in range(1, 23):
            indices[y * width + 1:y * width + 471] = bytes([0]) * 470
        for y in range(25, 47):
            indices[y * width + 1:y * width + 71] = bytes([black]) * 70
        for y in range(29, 36):
            indices[y * width + 77:y * width + 83] = bytes([marker]) * 6

        palette = [(0, 0, 0, 0)] * 256
        palette[0] = (0, 0, 0, 202)
        palette[black] = (0, 0, 0, 126)
        palette[marker] = (18, 204, 58, 255)
        palette[transparent] = (255, 255, 255, 0)

        result = _extend_title_label_backing_indices(bytes(indices), width, height, palette)

        # Footer/header strip is unrelated and remains byte-identical.
        self.assertEqual(indices[1 * width:23 * width], result[1 * width:23 * width])
        for y in range(25, 47):
            self.assertEqual(bytes([black]) * 300, result[y * width + 1:y * width + 301])
            self.assertEqual(bytes([transparent]) * 6, result[y * width + 301:y * width + 307])
        for y in range(29, 36):
            self.assertEqual(bytes([marker]) * 6, result[y * width + 307:y * width + 313])
        self.assertTrue(all(value == transparent for y in range(25, 47) for value in result[y * width + 313:(y + 1) * width]))

    def test_title_backing_extension_fails_closed_on_pristine_bar_drift(self) -> None:
        width, height = 512, 64
        palette = [(0, 0, 0, 0)] * 256
        palette[1] = (0, 0, 0, 126)
        palette[15] = (255, 255, 255, 0)
        indices = bytes([15] * (width * height))
        with self.assertRaisesRegex(ValueError, "GP088_08.*backing preimage"):
            _extend_title_label_backing_indices(indices, width, height, palette)

    def test_ports_direct_and_repacked_title_logos_into_same_size_container(self) -> None:
        container = self._make_gp088_title_container()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            localized = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            for y in range(20, 390):
                for x in range(310, 320):
                    localized.putpixel((x, y), (9, 8, 7, 255))
                for x in range(375, 385):
                    localized.putpixel((x, y), (9, 8, 7, 255))
            localized.save(root / "GP088_03.png")
            out = port_title_startup_graphics(container, root)

        self.assertEqual(len(container), len(out))
        packed = find_tmx_entry(out, "GRP088/GP088_12.TMX")
        rgba = decode_tmx_rgba(out, packed)

        def pixel(x: int, y: int) -> tuple[int, int, int, int]:
            off = (y * 512 + x) * 4
            return tuple(rgba[off:off + 4])

        self.assertEqual((9, 8, 7, 255), pixel(90, 40))
        self.assertEqual((9, 8, 7, 255), pixel(290, 40))
        self.assertEqual((0, 0, 0, 0), pixel(55, 260))
        self.assertEqual((0, 0, 0, 0), pixel(255, 260))

    def test_rejects_unproven_packed_title_layout(self) -> None:
        container = self._make_gp088_title_container(valid_packed_layout=False)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(root / "GP088_03.png")
            with self.assertRaisesRegex(ValueError, "alpha-layout proof"):
                port_title_startup_graphics(container, root)

    def test_ports_both_name_entry_pngs_into_same_size_container(self) -> None:
        # Build a synthetic two-entry container using the real container parser's
        # naming convention. The second entry is appended after the first.
        first = make_container(width=4, height=2)
        first_blob = first[:-4]
        first_blob = first_blob.replace(b"GRP999/GP999_00.TMX", b"GRP019/GP019_00.TMX")
        second = make_container(width=4, height=2)[:-4]
        second = second.replace(b"GRP999/GP999_00.TMX", b"GRP019/GP019_01.TMX")
        container = first_blob + second

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            Image.new("RGBA", (8, 4), (1, 2, 3, 255)).save(root / "GP019_00.png")
            Image.new("RGBA", (8, 4), (4, 5, 6, 255)).save(root / "GP019_01.png")
            out = port_name_entry_graphics(container, root)

        self.assertEqual(len(container), len(out))
        for name, expected in (
            ("GRP019/GP019_00.TMX", (1, 2, 3, 255)),
            ("GRP019/GP019_01.TMX", (4, 5, 6, 255)),
        ):
            entry = find_tmx_entry(out, name)
            rgba = decode_tmx_rgba(out, entry)
            self.assertEqual({expected}, {tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)})


if __name__ == "__main__":
    unittest.main()
