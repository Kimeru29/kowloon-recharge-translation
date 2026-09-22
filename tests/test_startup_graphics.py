from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tests.test_tmx import make_container
from tools.startup_graphics import port_name_entry_graphics, port_quote_graphic
from tools.tmx import decode_tmx_rgba, find_tmx_entry, parse_standalone_tmx

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
