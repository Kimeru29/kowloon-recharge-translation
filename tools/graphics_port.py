from __future__ import annotations

import argparse
from pathlib import Path

from tools.tmx import (
    find_tmx_entry,
    parse_standalone_tmx,
    replace_standalone_tmx_indexed,
    replace_tmx_indexed,
)


def _require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - optional runtime dependency
        raise RuntimeError(
            "Pillow is required for PNG graphics import; run with `uv run --with pillow ...`"
        ) from exc
    return Image


def _quantize_image_for_tmx(image, width: int, height: int, palette_entries: int):
    Image = _require_pillow()
    image = image.convert("RGBA")
    if image.size != (width, height):
        image = image.resize((width, height), Image.Resampling.LANCZOS)
    quantized = image.quantize(
        colors=palette_entries,
        method=Image.Quantize.FASTOCTREE,
        dither=Image.Dither.NONE,
    )
    indices = bytes(quantized.get_flattened_data())
    raw_palette = bytes(quantized.getpalette(rawmode="RGBA"))
    colors: list[tuple[int, int, int, int]] = []
    for i in range(0, len(raw_palette), 4):
        if len(colors) == palette_entries:
            break
        colors.append(tuple(raw_palette[i:i + 4]))
    colors.extend([(0, 0, 0, 0)] * (palette_entries - len(colors)))
    if len(colors) != palette_entries or len(indices) != width * height:
        raise AssertionError("Quantizer produced an invalid fixed-size indexed image")
    return colors, indices


def quantize_png_for_tmx(png: Path, width: int, height: int, palette_entries: int):
    """Downscale an RGBA PNG and return a fixed-size PS2 palette + indices.

    Pillow is imported lazily so the repository's normal test/tooling surface
    remains dependency-free. Alpha participates in FASTOCTREE quantization.
    """

    Image = _require_pillow()
    return _quantize_image_for_tmx(Image.open(png), width, height, palette_entries)


def quantize_rgba_for_tmx(
    rgba: bytes,
    source_size: tuple[int, int],
    width: int,
    height: int,
    palette_entries: int,
):
    """Quantize raw RGBA pixels using the same deterministic path as PNG imports."""

    source_width, source_height = source_size
    expected = source_width * source_height * 4
    if source_width <= 0 or source_height <= 0 or len(rgba) != expected:
        raise ValueError(
            f"RGBA payload/size mismatch: size={source_size} bytes={len(rgba)} expected={expected}"
        )
    Image = _require_pillow()
    image = Image.frombytes("RGBA", source_size, rgba)
    return _quantize_image_for_tmx(image, width, height, palette_entries)


def port_png_into_container(blob: bytes, name: str, png: Path) -> bytes:
    entry = find_tmx_entry(blob, name)
    palette, indices = quantize_png_for_tmx(
        png,
        entry.width,
        entry.height,
        entry.palette_entries,
    )
    return replace_tmx_indexed(blob, name, palette, indices)


def port_rgba_into_container(
    blob: bytes,
    name: str,
    rgba: bytes,
    *,
    source_size: tuple[int, int],
) -> bytes:
    entry = find_tmx_entry(blob, name)
    palette, indices = quantize_rgba_for_tmx(
        rgba,
        source_size,
        entry.width,
        entry.height,
        entry.palette_entries,
    )
    return replace_tmx_indexed(blob, name, palette, indices)


def port_png_into_standalone_tmx(blob: bytes, png: Path, *, name: str = "standalone.TMX") -> bytes:
    entry = parse_standalone_tmx(blob, name)
    palette, indices = quantize_png_for_tmx(
        png,
        entry.width,
        entry.height,
        entry.palette_entries,
    )
    return replace_standalone_tmx_indexed(blob, palette, indices, name=name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Port localized PNGs into same-size PS2 TMX container entries")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--replace",
        nargs=2,
        action="append",
        metavar=("TMX_NAME", "PNG"),
        required=True,
    )
    args = parser.parse_args()

    blob = args.source.read_bytes()
    for name, png in args.replace:
        blob = port_png_into_container(blob, name, Path(png))
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(blob)
    if args.destination.stat().st_size != args.source.stat().st_size:
        raise AssertionError("Localized B_GP container size changed")
    print(f"output={args.destination}")
    print(f"size={args.destination.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
