from __future__ import annotations

from pathlib import Path

from tools.graphics_layout import RegionTransfer, repack_rgba_regions, validate_alpha_repack
from tools.graphics_port import port_png_into_container, port_png_into_standalone_tmx, port_rgba_into_container
from tools.tmx import _decode_indices, _decode_palette, decode_tmx_rgba, find_tmx_entry, replace_tmx_indexed


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
_TITLE_BACKING_TMX = "GRP088/GP088_08.TMX"
_TITLE_SIZE = (512, 512)
_TITLE_BACKING_SIZE = (512, 64)

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

# GP088_08 has two independently meaningful rows in the pristine asset:
# - x=1..470 / y=1..22: unrelated long footer/title chrome;
# - x=1..70 / y=25..46: the 70px menu-label backing, followed by a 6px gap
#   and a small green trailing marker at x=77..82 on y=29..35.
# r8 proved this is the live backing. Its runtime screenshot is consistent with
# the strip being presented at roughly half logical width. The longest
# localized label, ``Load Game``, is nine 16px glyphs = 144 logical pixels.
# A 300px texture strip presents at about 150 logical pixels on this path. Keep
# the existing six-texture-pixel gap separately and move the trailing marker.
_TITLE_BACKING_BLACK_INDEX = 1
_TITLE_BACKING_TRANSPARENT_INDEX = 15
_TITLE_BACKING_SOURCE_X = (1, 71)       # [start,end)
_TITLE_BACKING_TARGET_X = (1, 301)      # 300 texture px ~= 150 logical px
_TITLE_BACKING_Y = (25, 47)
_TITLE_BACKING_MARKER_SOURCE_X = (77, 83)
_TITLE_BACKING_MARKER_TARGET_X = (307, 313)
_TITLE_BACKING_MARKER_Y = (29, 36)


def _extend_title_label_backing_indices(
    indices: bytes,
    width: int,
    height: int,
    palette: list[tuple[int, int, int, int]],
) -> bytes:
    """Extend only the proven GP088_08 menu-label backing for English width.

    The function is intentionally fail-closed on the pristine bar/gap geometry.
    It preserves the unrelated 470px strip and copies the existing trailing
    green marker verbatim to the new right edge rather than redrawing it.
    """

    if (width, height) != _TITLE_BACKING_SIZE or len(indices) != width * height:
        raise ValueError(
            f"GP088_08 title backing preimage has unexpected dimensions "
            f"{width}x{height} / {len(indices)} bytes"
        )
    if len(palette) <= _TITLE_BACKING_TRANSPARENT_INDEX:
        raise ValueError("GP088_08 title backing preimage has incomplete palette")
    black = _TITLE_BACKING_BLACK_INDEX
    transparent = _TITLE_BACKING_TRANSPARENT_INDEX
    if palette[black][3] == 0 or palette[transparent][3] != 0:
        raise ValueError("GP088_08 title backing preimage palette roles drifted")

    source = bytes(indices)
    out = bytearray(source)
    sx0, sx1 = _TITLE_BACKING_SOURCE_X
    tx0, tx1 = _TITLE_BACKING_TARGET_X
    mx0, mx1 = _TITLE_BACKING_MARKER_SOURCE_X
    nx0, nx1 = _TITLE_BACKING_MARKER_TARGET_X
    y0, y1 = _TITLE_BACKING_Y
    my0, my1 = _TITLE_BACKING_MARKER_Y

    for y in range(y0, y1):
        row = y * width
        if source[row + sx0:row + sx1] != bytes([black]) * (sx1 - sx0):
            raise ValueError(f"GP088_08 title backing preimage bar drifted at row {y}")
        if source[row + sx1:row + mx0] != bytes([transparent]) * (mx0 - sx1):
            raise ValueError(f"GP088_08 title backing preimage gap drifted at row {y}")

    # Save the exact marker before the old location is covered by the wider bar.
    marker_rows = {
        y: source[y * width + mx0:y * width + mx1]
        for y in range(my0, my1)
    }
    if not any(any(value != transparent for value in row) for row in marker_rows.values()):
        raise ValueError("GP088_08 title backing preimage trailing marker is missing")

    for y in range(y0, y1):
        row = y * width
        out[row + tx0:row + tx1] = bytes([black]) * (tx1 - tx0)
        out[row + tx1:row + nx0] = bytes([transparent]) * (nx0 - tx1)
    for y, marker in marker_rows.items():
        row = y * width
        out[row + nx0:row + nx1] = marker

    return bytes(out)


def _extend_title_label_backing(source_bin: bytes) -> bytes:
    entry = find_tmx_entry(source_bin, _TITLE_BACKING_TMX)
    palette = _decode_palette(source_bin, entry)
    indices = _decode_indices(source_bin, entry)
    localized = _extend_title_label_backing_indices(indices, entry.width, entry.height, palette)
    return replace_tmx_indexed(source_bin, _TITLE_BACKING_TMX, palette, localized)


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
    regions rather than synthesizing missing artwork. GP088_08 independently
    owns the 70px Japanese menu-label backing. Runtime r8 proves the title path
    presents that texture at about half logical width, so r9 extends only that
    dark strip to 300 texture pixels and preserves its trailing marker.
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
    out = _extend_title_label_backing(out)
    if len(out) != len(source_bin):
        raise AssertionError("Localized B_GP088 container changed size")
    return out
