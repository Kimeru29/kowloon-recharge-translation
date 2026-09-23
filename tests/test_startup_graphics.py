from __future__ import annotations

from pathlib import Path
import struct
import tempfile
import unittest

from tests.test_tmx import make_container
from tools.startup_graphics import port_name_entry_graphics, port_quote_graphic, port_title_startup_graphics
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
        def entry(name: str) -> bytes:
            encoded_name = name.encode("ascii") + b"\x00"
            prefix = bytearray(0x100)
            prefix[:len(encoded_name)] = encoded_name
            width = height = 512
            chunk_size = 0x40 + 256 * 4 + width * height
            tmx = bytearray(chunk_size)
            struct.pack_into("<II", tmx, 0, 2, chunk_size)
            tmx[8:12] = b"TMX0"
            tmx[16] = 1
            tmx[17] = 0
            struct.pack_into("<HH", tmx, 18, width, height)
            tmx[22] = 0x13
            # transparent, source-title, and flattened-overlay colors
            palette = 0x40
            tmx[palette + 0:palette + 4] = bytes((0, 0, 0, 0))
            tmx[palette + 4:palette + 8] = bytes((200, 50, 10, 0x80))
            tmx[palette + 8:palette + 12] = bytes((20, 80, 200, 0x80))
            return bytes(prefix + tmx)

        blob = entry("GRP088/GP088_03.TMX") + entry("GRP088/GP088_12.TMX")
        source_indices = bytearray(512 * 512)
        for y in range(20, 390):
            for x in range(310, 320):
                source_indices[y * 512 + x] = 1
            for x in range(375, 385):
                source_indices[y * 512 + x] = 1
        palette = [(0, 0, 0, 0)] * 256
        palette[1] = (200, 50, 10, 255)
        palette[2] = (20, 80, 200, 255)
        blob = replace_tmx_indexed(
            blob, "GRP088/GP088_03.TMX", palette, bytes(source_indices)
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
            blob, "GRP088/GP088_12.TMX", palette, bytes(target_indices)
        )
        return blob

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
