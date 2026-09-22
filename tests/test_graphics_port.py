from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from tools.graphics_port import port_png_into_container, port_png_into_standalone_tmx
from tools.tmx import decode_tmx_rgba, find_tmx_entry, parse_standalone_tmx
from tests.test_tmx import make_container


try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


@unittest.skipIf(Image is None, "Pillow is an optional graphics-build dependency")
class GraphicsPortTests(unittest.TestCase):
    def test_ports_png_into_standalone_tmx_without_changing_layout(self) -> None:
        container = make_container(width=4, height=2)
        standalone = container[0x100:-4]
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "localized.png"
            Image.new("RGBA", (8, 4), (90, 80, 70, 255)).save(png)
            out = port_png_into_standalone_tmx(standalone, png, name="TR028.TMX")

        self.assertEqual(len(standalone), len(out))
        entry = parse_standalone_tmx(out, "TR028.TMX")
        pixels = decode_tmx_rgba(out, entry)
        self.assertEqual({(90, 80, 70, 255)}, {tuple(pixels[i:i+4]) for i in range(0, len(pixels), 4)})

    def test_downscales_png_and_preserves_container_layout(self) -> None:
        blob = make_container(width=4, height=2)
        with tempfile.TemporaryDirectory() as tmp:
            png = Path(tmp) / "localized.png"
            image = Image.new("RGBA", (8, 4), (12, 34, 56, 255))
            image.save(png)
            out = port_png_into_container(blob, "GRP999/GP999_00.TMX", png)
        self.assertEqual(len(blob), len(out))
        entry = find_tmx_entry(out, "GRP999/GP999_00.TMX")
        pixels = decode_tmx_rgba(out, entry)
        self.assertEqual({(12, 34, 56, 255)}, {tuple(pixels[i:i+4]) for i in range(0, len(pixels), 4)})
        self.assertEqual(b"TAIL", out[-4:])


if __name__ == "__main__":
    unittest.main()
