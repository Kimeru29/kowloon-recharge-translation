"""Copy the eight proven English stats labels into their GP004_14 tiles."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from tools.inspect_english_bytes import parse
from tools.tmx import _decode_indices, _decode_palette, find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IMAGE = ROOT / "local/r67-15a-analysis/ps4-GP004_05_en.png"
_CORPUS_CANDIDATES = (
    Path("/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes"),
    Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"),
    Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"),
)
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
TARGET_TMX = "GRP004/GP004_14.TMX"
EXPECTED_GROUP4_SHA256 = "23dfe4cf48ec3c3ecd2f583fdc2a1fea336442b369cba02264dd9f2f8e7650da"
EXPECTED_SOURCE_SHA256 = "3d35b93c25f6c611411e4fa75f62c45977a78caa124a05a5985e66b0ac6d3e6b"
EXPECTED_SOURCE_RGBA_SHA256 = "07ccdd23ee525bdd2f2b6efb009b00be33d64fabe252e8b5c4902eec7eb5062d"
EXPECTED_TMX_SHA256 = "d344ae4cd1d7616b018014656cda58c620e94be722635d754b29f7d2714f97f6"
EXPECTED_PALETTE_SHA256 = "d3ebd91a23673e0304fa91fc0461fc648d0ab3f4cb011749560dde4e89c60682"
EXPECTED_CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
EXPECTED_FONT_SHA256 = "525979822591a3447cfc49d943d6f7683508e25543407871c0ed8fed05fd2bd9"
PIXEL_OFFSET = 0x88980

# label, source window, destination rect, native resource type, extraction-mask SHA256
_LABELS = (
    ("Shots", (190, 310, 241, 335), (0, 0, 24, 16), 0x17, "a4dadbf71138071434cf10d02e7fb87c5ee6826e9c6b208331038595388e2ecd"),
    ("ATK", (245, 310, 311, 335), (88, 16, 128, 32), 0x18, "a5a2a6ea7350063ba1d2c35cc07bf357e4469d2164ac6b77994f62cd4fb2d072"),
    ("Range", (321, 310, 383, 340), (64, 0, 104, 16), 0x19, "69a8527ea0be1d1cf2c5373a7d8df3055e6124299518d67617a142d3939ca640"),
    ("AP", (197, 344, 231, 372), (56, 16, 88, 32), 0x1A, "bd78cc05b3775b0771bb96f5f25a67609ca9c6ab46b748fc5542276b59820044"),
    ("Durability", (233, 344, 319, 375), (0, 16, 56, 32), 0x1B, "a2a1883ac089f73106c3b4bb807b04a1712a7150406b2781cfb0498fd04308c1"),
    ("Absorption", (321, 344, 409, 375), (0, 32, 40, 48), 0x1C, "beb13aec7525fdc4846928a36965a848daf9b0c8e67e5d9f4f2262319023eb17"),
    ("Recovery", (197, 381, 284, 409), (40, 32, 80, 48), 0x1D, "fd9d15eabbb3cfe2c1438940f44eefc475b4c6aaa8ba1f64dc82ed5b2323a3c2"),
    ("Increase", (291, 381, 375, 408), (24, 0, 64, 16), 0x1E, "ca5d2ba66a83a883bd0c4118c2c7c1d73d1992046afa140fabe751554d9e5605"),
)

# label, Japanese corpus key, destination tile, native resource ID, corpus row
_ATTRIBUTES = (
    ("Strength", "身体", (40, 80, 72, 96), 0x51, 0x29F76),
    ("Mind", "知性", (80, 32, 112, 48), 0x52, 0x29F94),
    ("Vitality", "生命", (40, 64, 80, 80), 0x53, 0x29FAE),
    ("Spirit", "精神", (0, 64, 40, 80), 0x54, 0x29FCC),
    ("Insight", "洞察", (40, 48, 80, 64), 0x55, 0x29FE8),
    ("Instinct", "直感", (0, 48, 40, 64), 0x56, 0x2A005),
    ("Agility", "敏捷", (0, 80, 40, 96), 0x57, 0x2A023),
)
_COMPOSED_ATTRIBUTE = ("Instinct / Spirit", ("Instinct", "Spirit"), (0, 98, 40, 114), 0xB5)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_mask(source: Image.Image, window: tuple[int, int, int, int]) -> Image.Image:
    crop = source.crop(window).convert("RGBA")
    mask = bytearray(crop.width * crop.height)
    for position, (red, green, blue, alpha) in enumerate(crop.get_flattened_data()):
        low, high = min(red, green, blue), max(red, green, blue)
        if low >= 128 and high - low <= 32:
            mask[position] = (low * alpha + 127) // 255
    return Image.frombytes("L", crop.size, bytes(mask))


def _fit_mask(mask: Image.Image, rect: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = rect
    width, height = right - left, bottom - top
    bounds = mask.getbbox()
    if bounds is None:
        raise ValueError("Pinned English source label has no foreground")
    cropped = mask.crop(bounds)
    scale = min((width - 2) / cropped.width, 14 / cropped.height)
    fitted_size = (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale)))
    fitted = cropped.resize(fitted_size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", (width, height), 0)
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return canvas


def _nearest_alpha_index(coverage: int, palette: list[tuple[int, int, int, int]]) -> int:
    return min(range(len(palette)), key=lambda index: (abs(palette[index][3] - coverage), index))


def _raster_attribute(text: str, rect: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = rect
    width, height = right - left, bottom - top
    font = ImageFont.truetype(str(FONT), size=8, layout_engine=ImageFont.Layout.BASIC)
    draw = ImageDraw.Draw(Image.new("L", (1, 1)))
    bounds = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = bounds[2] - bounds[0], bounds[3] - bounds[1]
    if text_width > width - 2 or text_height > height - 2:
        raise ValueError(f"Full attribute term {text!r} does not fit its native tile")
    mask = Image.new("L", (width, height), 0)
    x = (width - text_width) // 2 - bounds[0]
    y = (height - text_height) // 2 - bounds[1]
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)
    return mask


def _raster_composed_attribute(lines: tuple[str, str], rect: tuple[int, int, int, int]) -> Image.Image:
    left, top, right, bottom = rect
    width, height = right - left, bottom - top
    font = ImageFont.truetype(str(FONT), size=7, layout_engine=ImageFont.Layout.BASIC)
    scratch = ImageDraw.Draw(Image.new("L", (1, 1)))
    bounds = [scratch.textbbox((0, 0), line, font=font) for line in lines]
    line_heights = [box[3] - box[1] for box in bounds]
    total_height = sum(line_heights) + 1
    if total_height > height - 2 or any(box[2] - box[0] > width - 2 for box in bounds):
        raise ValueError("Composed full attribute terms do not fit their native tile")
    mask = Image.new("L", (width, height), 0)
    y = (height - total_height) // 2
    draw = ImageDraw.Draw(mask)
    for line, box, line_height in zip(lines, bounds, line_heights):
        x = (width - (box[2] - box[0])) // 2 - box[0]
        draw.text((x, y - box[1]), line, font=font, fill=255)
        y += line_height + 1
    return mask


def _validate_corpus_and_font() -> None:
    if _sha(FONT.read_bytes()) != EXPECTED_FONT_SHA256:
        raise ValueError("Local raster font SHA does not match the pinned Arial face")
    corpus_path = next((path for path in _CORPUS_CANDIDATES if path.exists()), None)
    if corpus_path is None:
        raise FileNotFoundError(
            "Pinned official English.bytes corpus is required to build 15f artwork"
        )
    if _sha(corpus_path.read_bytes()) != EXPECTED_CORPUS_SHA256:
        raise ValueError("Official English corpus SHA does not match the pinned source")
    by_offset = {offset: (key, value) for key, value, offset in parse(corpus_path)}
    for english, japanese, _rect, _sprite, offset in _ATTRIBUTES:
        if by_offset.get(offset) != (f"【{japanese}】", f"[{english}]"):
            raise ValueError(f"Official attribute corpus row changed at {offset:#x}")


def _put_index(pixels: bytearray, width: int, x: int, y: int, value: int) -> None:
    offset = y * width + x
    byte_offset = PIXEL_OFFSET + offset // 2
    if offset & 1:
        pixels[byte_offset] = (pixels[byte_offset] & 0x0F) | (value << 4)
    else:
        pixels[byte_offset] = (pixels[byte_offset] & 0xF0) | value


def apply(old: bytes) -> tuple[bytes, dict]:
    """Return GP004 with the eight approved labels and seven attributes changed."""
    if not isinstance(old, bytes):
        raise TypeError("GP004 input must be immutable bytes")
    if _sha(old) != EXPECTED_GROUP4_SHA256:
        raise ValueError("GP004 source SHA does not match the pinned 15d/15e input")
    _validate_corpus_and_font()
    source_bytes = SOURCE_IMAGE.read_bytes()
    if _sha(source_bytes) != EXPECTED_SOURCE_SHA256:
        raise ValueError("English source artwork SHA does not match the pinned input")
    source = Image.open(SOURCE_IMAGE).convert("RGBA")
    if _sha(source.tobytes()) != EXPECTED_SOURCE_RGBA_SHA256:
        raise ValueError("Decoded English source artwork differs from its pinned pixels")

    entry = find_tmx_entry(old, TARGET_TMX)
    chunk = old[entry.base_offset:entry.base_offset + entry.chunk_size]
    if _sha(chunk) != EXPECTED_TMX_SHA256:
        raise ValueError("GP004_14 source TMX SHA does not match the pinned input")
    if (entry.width, entry.height, entry.image_psm, entry.pixel_offset) != (128, 128, 0x14, PIXEL_OFFSET):
        raise ValueError("GP004_14 dimensions, format, or pixel offset changed")
    palette_bytes = old[entry.palette_offset:entry.palette_offset + entry.palette_bytes]
    if _sha(palette_bytes) != EXPECTED_PALETTE_SHA256:
        raise ValueError("GP004_14 palette differs from the pinned white/alpha palette")

    palette = _decode_palette(old, entry)
    indices = _decode_indices(old, entry)
    output = bytearray(old)
    tile_ranges: dict[str, tuple[tuple[int, int], ...]] = {}
    labels_report = []
    for label, source_rect, rect, resource_type, expected_mask_sha in _LABELS:
        mask = _source_mask(source, source_rect)
        if _sha(mask.tobytes()) != expected_mask_sha:
            raise ValueError(f"{label} extraction mask differs from its pinned fingerprint")
        fitted = _fit_mask(mask, rect)
        left, top, right, bottom = rect
        for y in range(top, bottom):
            for x in range(left, right):
                _put_index(output, entry.width, x, y,
                           _nearest_alpha_index(fitted.getpixel((x - left, y - top)), palette))
        tile_ranges[label] = tuple(
            (PIXEL_OFFSET + 64 * y + left // 2, PIXEL_OFFSET + 64 * y + right // 2)
            for y in range(top, bottom)
        )
        labels_report.append({"label": label, "resource_type": resource_type,
                              "source_mask_sha256": expected_mask_sha,
                              "destination": rect})

    attribute_ranges: dict[str, tuple[tuple[int, int], ...]] = {}
    attributes_report = []
    for english, japanese, rect, sprite_id, corpus_offset in _ATTRIBUTES:
        raster = _raster_attribute(english, rect)
        left, top, right, bottom = rect
        for y in range(top, bottom):
            for x in range(left, right):
                _put_index(output, entry.width, x, y,
                           _nearest_alpha_index(raster.getpixel((x - left, y - top)), palette))
        attribute_ranges[english] = tuple(
            (PIXEL_OFFSET + 64 * y + left // 2, PIXEL_OFFSET + 64 * y + right // 2)
            for y in range(top, bottom)
        )
        attributes_report.append({"label": english, "native_japanese": japanese,
                                  "sprite_id": sprite_id, "corpus_row": hex(corpus_offset),
                                  "destination": rect})

    combined_label, combined_lines, combined_rect, combined_sprite = _COMPOSED_ATTRIBUTE
    combined_mask = _raster_composed_attribute(combined_lines, combined_rect)
    combined_left, combined_top, combined_right, combined_bottom = combined_rect
    for y in range(combined_top, combined_bottom):
        for x in range(combined_left, combined_right):
            _put_index(output, entry.width, x, y,
                       _nearest_alpha_index(combined_mask.getpixel((x - combined_left,
                                                                    y - combined_top)), palette))
    attribute_ranges[combined_label] = tuple(
        (PIXEL_OFFSET + 64 * y + combined_left // 2,
         PIXEL_OFFSET + 64 * y + combined_right // 2)
        for y in range(combined_top, combined_bottom)
    )

    new = bytes(output)
    changed = [index for index, (before, after) in enumerate(zip(old, new)) if before != after]
    allowed = {offset for ranges in tile_ranges.values() for start, end in ranges
               for offset in range(start, end)}
    attribute_allowed = {offset for ranges in attribute_ranges.values() for start, end in ranges
                         for offset in range(start, end)}
    allowed |= attribute_allowed
    if not changed or not set(changed) <= allowed:
        raise AssertionError("15f art output changed bytes outside the fifteen declared tiles")
    report = {
        "status": "PASS_BOUNDED_GP004_14_LABEL_TILES",
        "target_tmx": TARGET_TMX,
        "source_group4_sha256": EXPECTED_GROUP4_SHA256,
        "source_art_sha256": EXPECTED_SOURCE_SHA256,
        "palette_sha256": EXPECTED_PALETTE_SHA256,
        "changed_container_bytes": len(changed),
        "labels": labels_report,
        "attributes": attributes_report,
        "official_corpus_sha256": EXPECTED_CORPUS_SHA256,
        "official_corpus_rows_runtime_verified": True,
        "attribute_art_source": "locally rasterized pinned Arial; not copied official word art",
        "combined_sprite_0xB5": {
            "label": combined_label,
            "localization": "composed from two corpus-proven terms",
            "exact_official_combined_phrase": False,
            "copied_official_word_art": False,
        },
    }
    return new, report


PERMITTED_ART_RANGES = {
    label: tuple((PIXEL_OFFSET + 64 * y + left // 2,
                  PIXEL_OFFSET + 64 * y + right // 2)
                 for y in range(top, bottom))
    for label, _source_rect, (left, top, right, bottom), _resource_type, _mask_sha in _LABELS
}
PERMITTED_ART_RANGES.update({
    label: tuple((PIXEL_OFFSET + 64 * y + left // 2,
                  PIXEL_OFFSET + 64 * y + right // 2)
                 for y in range(top, bottom))
    for label, _japanese, (left, top, right, bottom), _sprite, _row in _ATTRIBUTES
})
_composed_label, _composed_lines, (left, top, right, bottom), _composed_sprite = _COMPOSED_ATTRIBUTE
PERMITTED_ART_RANGES[_composed_label] = tuple(
    (PIXEL_OFFSET + 64 * y + left // 2, PIXEL_OFFSET + 64 * y + right // 2)
    for y in range(top, bottom)
)
