"""Port official PS4 Emotion Wheel lettering into the approved PS2 Group 1 atlas."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

from tools.tmx import _decode_indices, _decode_palette, find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_GROUP_SHA256 = "895f3d1864a653b3eb76a06eae8b8ea65b9f31cfe156fe922eb72d9eeb967942"
OFFICIAL_BUNDLE_SHA256 = "78ac1bcdbe7e6838be3c0d3ae49d76c290bfd3205ad55e97bc647697b3d6260b"
OFFICIAL_TEXTURE_SHA256 = {
    "02": "490072a4f90b21ae3137f9eaa8a003eb3d7a7c8ee73377402d118d6a44125fb6",
    "03": "3b13dadf29209f3d64ffc1fd1da5c97e154b1cd90a08d0825ed613d3182fb190",
    "08": "42494369fbe7fc0686ebef4dd4782392a4f3c3881dd625c99836f1527c26eb98",
    "10": "e00101e7b784db568f47f65f2123d4c2cd97e60be4c52abcc73d35d033ec3615",
}
JAPANESE_TEXTURE_SHA256 = {
    "02": "0ee399cf25917db5669dabe7af1bbd90484dd3114eb797afd5b800005d78c263",
    "03": "99f753f350a9a3c3e04b9bd273607aec863e2204061b9d9dca677baadbd22683",
    "08": "ee33eb96e057cdaa3e085b07ab1b29c402cb67c7b8fed29c800f56d4c7f5451d",
    "10": "b520345691a18f7a92a808bc9df73eace249fcdad80d085ced16d72ae592dfce",
}
LABELS = ("JOY", "LOVE", "AMITY", "HOT", "COLD", "ANGER", "SOMBER", "GRIEF")
TARGET_TEXTURES = {
    "02": "GRP001/GP001_02.TMX",
    "03": "GRP001/GP001_03.TMX",
    "08": "GRP001/GP001_08.TMX",
    "10": "GRP001/GP001_10.TMX",
}

# UV rectangles from the approved ELF, in the 256x256 atlas coordinate space.
PAIRED_02 = (
    (40, 0, 80, 72),   # LOVE / JOY
    (0, 0, 40, 72),    # COLD / ANGER
    (80, 0, 152, 40),  # AMITY / HOT
)
PAIRED_10 = (
    (160, 160, 232, 200),  # default GRIEF / SOMBER
    (40, 0, 80, 72), (80, 40, 152, 80), (0, 0, 40, 72),
    (80, 0, 152, 40), (80, 160, 120, 232), (152, 80, 224, 120),
    (120, 160, 160, 232), (152, 120, 224, 160), (0, 72, 40, 144),
    (80, 80, 152, 120), (40, 72, 80, 144), (80, 120, 152, 160),
    (40, 144, 80, 216), (152, 40, 224, 80), (0, 144, 40, 216),
    (152, 0, 224, 40),
)
PAIRED_OCCURRENCE_COUNT = len(PAIRED_02) + len(PAIRED_10)
GOLD_RECTS = {
    "JOY": (136, 32, 168, 64), "LOVE": (136, 0, 168, 32),
    "AMITY": (136, 64, 168, 96), "HOT": (136, 96, 168, 128),
    "COLD": (0, 224, 32, 256), "ANGER": (32, 224, 64, 256),
    "SOMBER": (224, 224, 256, 256), "GRIEF": (192, 224, 224, 256),
}
GLOW_RECTS = {
    "JOY": (0, 0, 64, 64), "LOVE": (64, 0, 128, 64),
    "AMITY": (128, 0, 192, 64), "HOT": (192, 0, 256, 64),
    "COLD": (0, 64, 64, 128), "ANGER": (64, 64, 128, 128),
    "SOMBER": (128, 64, 192, 128), "GRIEF": (192, 64, 256, 128),
}

_BUNDLE_CANDIDATES = (
    Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/BLBRD/b_gp001_en"),
    Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/BLBRD/b_gp001_en"),
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _find_texture_source() -> tuple[Path, Path, str]:
    local_en = ROOT / "local/r67-15l-investigation/gp001_en"
    local_jp = ROOT / "local/r67-15l-investigation/gp001_jp"
    has_recovered_bundle = False
    for bundle in _BUNDLE_CANDIDATES:
        if bundle.is_file() and _sha(bundle.read_bytes()) == OFFICIAL_BUNDLE_SHA256:
            has_recovered_bundle = True
            break
    if local_en.is_dir() and local_jp.is_dir():
        kind = "verified_bundle_and_local_textures" if has_recovered_bundle else "pinned_local_source_recovery"
        return local_en, local_jp, kind
    raise FileNotFoundError("official PS4 bundle and pinned local extraction are unavailable")


def _load_images() -> tuple[dict[str, Image.Image], dict[str, Image.Image], str]:
    english_root, japanese_root, source_kind = _find_texture_source()
    english: dict[str, Image.Image] = {}
    japanese: dict[str, Image.Image] = {}
    for atlas in TARGET_TEXTURES:
        en_path = english_root / f"GP001_{atlas}.png"
        jp_path = japanese_root / f"GP001_{atlas}.png"
        if not en_path.is_file() or not jp_path.is_file():
            raise FileNotFoundError(f"official wheel texture pair is missing for GP001_{atlas}")
        en_bytes, jp_bytes = en_path.read_bytes(), jp_path.read_bytes()
        if _sha(en_bytes) != OFFICIAL_TEXTURE_SHA256[atlas]:
            raise ValueError(f"official GP001_{atlas} source hash mismatch")
        if _sha(jp_bytes) != JAPANESE_TEXTURE_SHA256[atlas]:
            raise ValueError(f"Japanese GP001_{atlas} comparison source hash mismatch")
        with Image.open(en_path) as image:
            english[atlas] = image.convert("RGBA")
        with Image.open(jp_path) as image:
            japanese[atlas] = image.convert("RGBA")
    return english, japanese, source_kind


def _nearest_index(color: tuple[int, int, int, int], palette: list[tuple[int, int, int, int]]) -> int:
    red, green, blue, alpha = color
    return min(range(len(palette)), key=lambda i: (
        3 * (palette[i][0] - red) ** 2 + 4 * (palette[i][1] - green) ** 2
        + 2 * (palette[i][2] - blue) ** 2 + 2 * (palette[i][3] - alpha) ** 2
    ))


def _resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return image.resize(size, Image.Resampling.LANCZOS)


def _paired_label_mask(english: Image.Image, japanese: Image.Image,
                       size: tuple[int, int]) -> Image.Image:
    """Cover both visible texture deltas and Japanese-only glyph support."""
    delta = ImageChops.difference(english, japanese).convert("RGB").convert("L")
    delta = delta.point(lambda value: 255 if value >= 20 else 0)
    japanese_only = ImageChops.subtract(japanese.getchannel("A"), english.getchannel("A"))
    support = japanese_only.point(lambda value: 255 if value > 0 else 0)
    matte = ImageChops.lighter(delta, support).filter(ImageFilter.MaxFilter(5))
    matte = _resize(matte, size)
    resized_support = _resize(support, size).point(lambda value: 255 if value > 0 else 0)
    return ImageChops.lighter(matte, resized_support)


def _patch_rect(
    output: bytearray,
    old: bytes,
    entry,
    source: Image.Image,
    rect: tuple[int, int, int, int],
    mask: Image.Image | None,
    clear_to_transparent: bool = False,
) -> int:
    left, top, right, bottom = rect
    palette = _decode_palette(old, entry)
    indices = _decode_indices(old, entry)
    transparent_index = next((index for index, color in enumerate(palette) if color[3] == 0), None)
    if clear_to_transparent and transparent_index is None:
        raise ValueError(f"{entry.name}: cannot clear a single-label tile without transparent palette color")
    if clear_to_transparent:
        for y in range(top, bottom):
            start = entry.pixel_offset + y * entry.width + left
            output[start:start + right - left] = bytes([transparent_index]) * (right - left)
    changed = 0
    for y in range(top, bottom):
        for x in range(left, right):
            alpha = 255 if mask is None else mask.getpixel((x, y))
            rgba = source.getpixel((x, y))
            alpha = (alpha * rgba[3] + 127) // 255
            if alpha == 0:
                continue
            position = y * entry.width + x
            previous_index = transparent_index if clear_to_transparent else indices[position]
            previous = palette[previous_index]
            mixed = tuple((previous[channel] * (255 - alpha) + rgba[channel] * alpha + 127) // 255
                          for channel in range(4))
            new_index = _nearest_index(mixed, palette)
            if new_index != previous_index:
                output[entry.pixel_offset + position] = new_index
                changed += 1
    if clear_to_transparent:
        changed = sum(output[entry.pixel_offset + y * entry.width + x] != indices[y * entry.width + x]
                      for y in range(top, bottom) for x in range(left, right))
    return changed


def apply(old: bytes) -> tuple[bytes, dict]:
    """Apply official wheel lettering; preserve the source palette and all unowned bytes."""
    if not isinstance(old, bytes):
        raise TypeError("old Group 1 container must be bytes")
    source_hash = _sha(old)
    if source_hash != SOURCE_GROUP_SHA256:
        raise ValueError(f"unrecognized Group 1 source container hash: {source_hash}")
    english, japanese, source_kind = _load_images()
    output = bytearray(old)
    changed_by_texture: dict[str, int] = {}
    ownership_evidence: dict[str, list[dict]] = {"02": [], "03": [], "08": [], "10": []}

    entries = {atlas: find_tmx_entry(old, name) for atlas, name in TARGET_TEXTURES.items()}
    scaled_en: dict[str, Image.Image] = {}
    for atlas, entry in entries.items():
        if (entry.width, entry.height, entry.image_psm) != (256, 128 if atlas == "02" else 256, 0x13):
            raise ValueError(f"GP001_{atlas}: unexpected dimensions or PS2 pixel format")
        scaled_en[atlas] = _resize(english[atlas], (entry.width, entry.height))

    for atlas, crops in (("02", PAIRED_02), ("10", PAIRED_10)):
        entry = entries[atlas]
        mask = _paired_label_mask(english[atlas], japanese[atlas], (entry.width, entry.height))
        changed = 0
        for rect in crops:
            modified = _patch_rect(output, old, entry, scaled_en[atlas], rect, mask)
            changed += modified
            left, top, right, bottom = rect
            coverage = sum(mask.getpixel((x, y)) > 0
                           for y in range(top, bottom) for x in range(left, right))
            ownership_evidence[atlas].append({"uv_pixels": list(rect),
                                              "masked_texels": coverage,
                                              "changed_indices": modified})
        changed_by_texture[entry.name] = changed

    for atlas, rects, label_type in (("03", GOLD_RECTS.values(), "gold"),
                                     ("08", GLOW_RECTS.values(), "glow")):
        entry = entries[atlas]
        changed = 0
        for rect in rects:
            modified = _patch_rect(output, old, entry, scaled_en[atlas], rect, None,
                                   clear_to_transparent=True)
            changed += modified
            left, top, right, bottom = rect
            alpha = scaled_en[atlas].getchannel("A").crop(rect)
            alpha_coverage = sum(alpha.histogram()[1:])
            ownership_evidence[atlas].append({"uv_pixels": list(rect),
                                              "masked_texels": alpha_coverage,
                                              "changed_indices": modified})
        changed_by_texture[entry.name] = changed

    localized = bytes(output)
    if len(localized) != len(old):
        raise AssertionError("Group 1 container length changed")
    allowed = set()
    for entry in entries.values():
        allowed.update(range(entry.pixel_offset, entry.pixel_offset + entry.pixel_bytes))
    modified = {index for index, (before, after) in enumerate(zip(old, localized)) if before != after}
    if not modified or not modified <= allowed:
        raise AssertionError("patch changed bytes outside the four owned indexed texture payloads")
    report = {
        "status": "PASS_OFFICIAL_EMOTION_WHEEL_ART",
        "source_container_sha256": source_hash,
        "official_bundle_sha256": OFFICIAL_BUNDLE_SHA256,
        "official_texture_sha256": OFFICIAL_TEXTURE_SHA256,
        "official_source_kind": source_kind,
        "labels": sorted(LABELS),
        "texture_count": len(entries),
        "variant_count": 4,
        "variants": {
            "paired_plaques": {"occurrences": len(PAIRED_02) + 1, "label_drawings": (len(PAIRED_02) + 1) * 2,
                                "mask": "English/Japanese texture delta union Japanese-only alpha support, dilated 5px before downsample"},
            "paired_selected": {"occurrences": len(PAIRED_10) - 1, "label_drawings": (len(PAIRED_10) - 1) * 2,
                                "mask": "English/Japanese texture delta union Japanese-only alpha support, dilated 5px before downsample"},
            "gold_singles": {"occurrences": len(GOLD_RECTS), "label_drawings": len(GOLD_RECTS),
                              "mask": "clear each owned tile to transparent palette color, then composite official English source alpha"},
            "glowing_singles": {"occurrences": len(GLOW_RECTS), "label_drawings": len(GLOW_RECTS),
                                 "mask": "clear each owned tile to transparent palette color, then composite official English source alpha"},
        },
        "paired_plaque_occurrences": PAIRED_OCCURRENCE_COUNT,
        "label_drawing_occurrences": 56,
        "texture_changes": changed_by_texture,
        "ownership_evidence": ownership_evidence,
        "palette_bytes_changed": 0,
        "native_program_bytes_changed": 0,
        "candidate_container_sha256": _sha(localized),
    }
    return localized, report
