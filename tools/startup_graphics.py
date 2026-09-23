from __future__ import annotations

from pathlib import Path

from tools.graphics_layout import RegionTransfer, repack_rgba_regions, validate_alpha_repack
from tools.graphics_port import port_png_into_container, port_png_into_standalone_tmx, port_rgba_into_container
from tools.tmx import decode_tmx_rgba, find_tmx_entry


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


_TITLE_DIRECT_TMX = "GRP088/GP088_03.TMX"
_TITLE_PACKED_TMX = "GRP088/GP088_12.TMX"
_TITLE_SIZE = (512, 512)

# GP088_12 is a PS2-only packed atlas assembled from the same two vertical title
# variants present in GP088_03.  The original re:charge banners are flattened on
# top of the Japanese glyphs, so that crossing band is excluded from the source
# relationship proof and the localized atlas is rebuilt transparently instead.
_TITLE_PACKED_TRANSFERS = (
    RegionTransfer((300, 0, 355, 410), (-223, 14)),
    RegionTransfer((365, 0, 425, 410), (-87, 14)),
)
_TITLE_PACKED_IGNORE_RECTS = ((0, 245, 512, 325),)
_TITLE_PACKED_MIN_DICE = 0.82


def _prove_packed_title_layout(source_bin: bytes) -> tuple[bytes, bytes]:
    direct = find_tmx_entry(source_bin, _TITLE_DIRECT_TMX)
    packed = find_tmx_entry(source_bin, _TITLE_PACKED_TMX)
    if (direct.width, direct.height) != _TITLE_SIZE or (packed.width, packed.height) != _TITLE_SIZE:
        raise ValueError(
            f"Unexpected GP088 title dimensions: direct={(direct.width, direct.height)} "
            f"packed={(packed.width, packed.height)}"
        )
    direct_rgba = decode_tmx_rgba(source_bin, direct)
    packed_rgba = decode_tmx_rgba(source_bin, packed)
    validate_alpha_repack(
        direct_rgba,
        packed_rgba,
        _TITLE_SIZE,
        _TITLE_SIZE,
        _TITLE_PACKED_TRANSFERS,
        ignore_rects=_TITLE_PACKED_IGNORE_RECTS,
        margin=4,
        min_dice=_TITLE_PACKED_MIN_DICE,
    )
    return direct_rgba, packed_rgba


def port_title_startup_graphics(source_bin: bytes, png_dir: Path) -> bytes:
    """Port the official-English GP088 startup/title renderer class.

    GP088_03 has a direct localized counterpart. GP088_12 is a PS2-only packed
    derivative of GP088_03, proven by alpha-layout overlap at two renderer
    transforms. The official English remaster omits the flattened re:charge
    banners, so the packed target is rebuilt from only the localized title
    regions rather than synthesizing missing artwork.
    """

    _prove_packed_title_layout(source_bin)

    png = png_dir / "GP088_03.png"
    if not png.is_file():
        raise ValueError(f"Missing localized title PNG: {png}")
    out = port_png_into_container(source_bin, _TITLE_DIRECT_TMX, png)

    localized_direct = find_tmx_entry(out, _TITLE_DIRECT_TMX)
    localized_rgba = decode_tmx_rgba(out, localized_direct)
    packed_rgba = repack_rgba_regions(
        localized_rgba,
        _TITLE_SIZE,
        _TITLE_SIZE,
        _TITLE_PACKED_TRANSFERS,
    )
    out = port_rgba_into_container(
        out,
        _TITLE_PACKED_TMX,
        packed_rgba,
        source_size=_TITLE_SIZE,
    )
    if len(out) != len(source_bin):
        raise AssertionError("Localized B_GP088 container changed size")
    return out
