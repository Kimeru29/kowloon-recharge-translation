from __future__ import annotations

from pathlib import Path

from tools.graphics_port import port_png_into_container, port_png_into_standalone_tmx


_NAME_ENTRY_TMX = (
    "GRP019/GP019_00.TMX",
    "GRP019/GP019_01.TMX",
)


def port_quote_graphic(source_tmx: bytes, png: Path, *, name: str) -> bytes:
    """Port one official localized quote image into a same-size PS2 TMX."""

    out = port_png_into_standalone_tmx(source_tmx, png, name=name)
    if len(out) != len(source_tmx):
        raise AssertionError(f"{name}: localized standalone TMX changed size")
    return out


def port_name_entry_graphics(source_bin: bytes, png_dir: Path) -> bytes:
    """Port the official localized GP019 name-entry graphics into PS2 B_GP019."""

    out = source_bin
    for name in _NAME_ENTRY_TMX:
        png = png_dir / (Path(name).stem + ".png")
        if not png.is_file():
            raise ValueError(f"Missing localized name-entry PNG: {png}")
        out = port_png_into_container(out, name, png)
    if len(out) != len(source_bin):
        raise AssertionError("Localized B_GP019 container changed size")
    return out
