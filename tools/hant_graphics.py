from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256

from tools.tmx import _decode_indices, _decode_palette, find_tmx_entry, replace_tmx_indexed


HANT_GP020_TMX = "GRP020/GP020_03.TMX"
_GREEN_RGB = (19, 204, 58)


@dataclass(frozen=True)
class CaptionSpec:
    key: str
    english: str
    rect: tuple[int, int, int, int]
    scale_x: int
    scale_y: int
    source_sha256: str
    provenance: str = "semantic"


# GP020_03 is the baked H.A.N.T. UI atlas proven by the six-tile constructor
# (group 0x14, indices 0x10..0x15). The currently owned PS4 extraction does not
# contain a recoverable localized GP020 bundle, so these captions are deliberately
# semantic English repaints, not remaster-derived artwork. Rectangle hashes pin
# every edit to the pristine PS2 atlas and fail closed if the source asset drifts.
HANT_CAPTIONS: tuple[CaptionSpec, ...] = (
    CaptionSpec("help", "HELP", (26, 74, 103, 94), 2, 2, "c77bd886cb1251876dc54d21aee19ee417533c7037bfb43b682eb5c6304e6fbf"),
    CaptionSpec("config", "CONFIG", (112, 74, 204, 94), 2, 2, "84acb5cf7b4aa24bf3f98d9a3afefc8219eba2ffc770b83993506adaae179b67"),
    CaptionSpec("reset_defaults", "RESET DEFAULTS", (55, 105, 171, 124), 1, 2, "3def11ddf128bf986164329f28ede5b47d62b1cc583bf0f3aa89e0a2c9ed1965"),
    CaptionSpec("delete", "DELETE", (55, 129, 116, 148), 1, 2, "1f89ff3dd55d59512107c005f704b433c0ea5b2d9b8700dc1aa9981b1763fb11"),
    CaptionSpec("page", "PAGE", (447, 38, 498, 56), 1, 2, "c7e3665e8b32c19a75667cab5a991a816fa69879181ace56d0433d05fb3a9b75"),
    CaptionSpec("mail", "MAIL", (397, 216, 480, 238), 2, 2, "0c508bed04b43954a3caab0e0c01f25719906c245c52e37fb74632302c28c056"),
    CaptionSpec("dictionary", "DICTIONARY", (395, 299, 482, 323), 1, 2, "2e2aff7930c182de4b10c7a4ed636e29680baa082b9034d97e00ef0a0b398af0"),
    CaptionSpec("enemy", "ENEMY", (402, 382, 478, 407), 2, 2, "f50bf2e5bc9d66fde996a83726f4979f530f3a4a0488295f099c48054a601e23"),
    CaptionSpec("memo", "MEMO", (395, 473, 482, 501), 2, 2, "59f7d98b5fcf7b5e8cee37f6eb3bcd5cd5c271a8af93ba59071de2ab9966dda7"),
)


# Compact 5x7 uppercase bitmap font. Keeping this local makes the asset build
# deterministic and avoids introducing a system-font dependency for nine labels.
_FONT_5X7: dict[str, tuple[str, ...]] = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
}


def _region_bytes(indices: bytes | bytearray, width: int, rect: tuple[int, int, int, int]) -> bytes:
    left, top, right, bottom = rect
    return bytes(indices[y * width + x] for y in range(top, bottom) for x in range(left, right))


def _validate_specs(width: int, height: int, specs: Sequence[CaptionSpec]) -> None:
    for spec in specs:
        left, top, right, bottom = spec.rect
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError(f"caption rectangle outside atlas: {spec.key} {spec.rect}")
        if spec.scale_x <= 0 or spec.scale_y <= 0:
            raise ValueError(f"caption scale must be positive: {spec.key}")
        if len(spec.source_sha256) != 64:
            raise ValueError(f"caption preimage hash is invalid: {spec.key}")
        unsupported = sorted(set(spec.english) - set(_FONT_5X7) - {" "})
        if unsupported:
            raise ValueError(f"unsupported caption glyphs for {spec.key}: {unsupported!r}")


def _text_width(text: str, scale_x: int) -> int:
    if not text:
        return 0
    advances = [4 * scale_x if char == " " else 6 * scale_x for char in text]
    return sum(advances) - scale_x


def _draw_caption(
    indices: bytearray,
    width: int,
    spec: CaptionSpec,
    green_index: int,
) -> None:
    left, top, right, bottom = spec.rect
    text_width = _text_width(spec.english, spec.scale_x)
    text_height = 7 * spec.scale_y
    if text_width > right - left or text_height > bottom - top:
        raise ValueError(
            f"caption does not fit {spec.key}: text={text_width}x{text_height} rect={right-left}x{bottom-top}"
        )

    x_cursor = left + ((right - left) - text_width) // 2
    y_origin = top + ((bottom - top) - text_height) // 2
    for char in spec.english:
        if char == " ":
            x_cursor += 4 * spec.scale_x
            continue
        glyph = _FONT_5X7[char]
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit != "1":
                    continue
                x0 = x_cursor + gx * spec.scale_x
                y0 = y_origin + gy * spec.scale_y
                for dy in range(spec.scale_y):
                    base = (y0 + dy) * width
                    for dx in range(spec.scale_x):
                        indices[base + x0 + dx] = green_index
        x_cursor += 6 * spec.scale_x


def repaint_caption_indices(
    indices: bytes,
    width: int,
    height: int,
    palette: Sequence[tuple[int, int, int, int]],
    specs: Sequence[CaptionSpec],
) -> bytes:
    """Replace only baked green caption pixels, preserving every other atlas pixel."""

    if len(indices) != width * height:
        raise ValueError(f"indexed atlas size mismatch: {len(indices)} != {width * height}")
    _validate_specs(width, height, specs)

    for spec in specs:
        actual = sha256(_region_bytes(indices, width, spec.rect)).hexdigest()
        if actual != spec.source_sha256:
            raise ValueError(
                f"caption preimage mismatch: {spec.key}; expected {spec.source_sha256}, got {actual}"
            )

    green_indices = [
        index
        for index, color in enumerate(palette)
        if tuple(color[:3]) == _GREEN_RGB and color[3] > 0
    ]
    if not green_indices:
        raise ValueError("GP020 caption palette has no H.A.N.T green entries")
    green_index = max(green_indices, key=lambda index: palette[index][3])

    transparent_counts: Counter[int] = Counter()
    for spec in specs:
        left, top, right, bottom = spec.rect
        for y in range(top, bottom):
            for x in range(left, right):
                value = indices[y * width + x]
                if palette[value][3] == 0:
                    transparent_counts[value] += 1
    if not transparent_counts:
        raise ValueError("GP020 caption regions have no transparent background index")
    transparent_index = transparent_counts.most_common(1)[0][0]

    out = bytearray(indices)
    green_set = set(green_indices)
    for spec in specs:
        left, top, right, bottom = spec.rect
        for y in range(top, bottom):
            base = y * width
            for x in range(left, right):
                offset = base + x
                if out[offset] in green_set:
                    out[offset] = transparent_index
        _draw_caption(out, width, spec, green_index)
    return bytes(out)


def port_indexed_caption_atlas(
    source_bin: bytes,
    tmx_name: str,
    specs: Sequence[CaptionSpec],
) -> bytes:
    """Patch one indexed TMX caption atlas without changing its container layout."""

    entry = find_tmx_entry(source_bin, tmx_name)
    palette = _decode_palette(source_bin, entry)
    indices = _decode_indices(source_bin, entry)
    localized = repaint_caption_indices(indices, entry.width, entry.height, palette, specs)
    out = replace_tmx_indexed(source_bin, tmx_name, palette, localized)
    if len(out) != len(source_bin):
        raise AssertionError(f"{tmx_name}: localized container size changed")
    if find_tmx_entry(out, tmx_name) != entry:
        raise AssertionError(f"{tmx_name}: TMX metadata changed")
    return out


def port_hant_gp020_graphics(source_bin: bytes) -> bytes:
    """Apply the semantic-English baked-caption pass to pristine B_GP020.BIN."""

    entry = find_tmx_entry(source_bin, HANT_GP020_TMX)
    if (entry.width, entry.height, entry.image_psm) != (512, 512, 0x13):
        raise ValueError(
            "unexpected GP020_03 layout: "
            f"{entry.width}x{entry.height} psm={entry.image_psm:#x}"
        )
    return port_indexed_caption_atlas(source_bin, HANT_GP020_TMX, HANT_CAPTIONS)
