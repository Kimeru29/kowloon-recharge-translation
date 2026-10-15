"""Regression checks for the tightly bounded 15f GP004_14 label artwork."""
from __future__ import annotations

import hashlib
import importlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from tools.inspect_english_bytes import parse
from tools.tmx import _decode_indices, _decode_palette, find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-15a-analysis/ps4-GP004_05_en.png"
GROUP4 = ROOT / "local/r67-15d-group4-clean.BIN"
ELF = ROOT / "local/r67-15d-gold-chains-compound.elf"
SOURCE_ELF = ROOT / "local/r67-15e-compound-bubble.elf"
CORPUS_CANDIDATES = (
    Path("/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes"),
    Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"),
    Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"),
)
FONT = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
EXPECTED_GROUP4_SHA = "23dfe4cf48ec3c3ecd2f583fdc2a1fea336442b369cba02264dd9f2f8e7650da"
EXPECTED_SOURCE_SHA = "3d35b93c25f6c611411e4fa75f62c45977a78caa124a05a5985e66b0ac6d3e6b"
EXPECTED_RGBA_SHA = "07ccdd23ee525bdd2f2b6efb009b00be33d64fabe252e8b5c4902eec7eb5062d"
EXPECTED_CORPUS_SHA = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
EXPECTED_FONT_SHA = "525979822591a3447cfc49d943d6f7683508e25543407871c0ed8fed05fd2bd9"
EXPECTED_APPROVED_LABEL_INDICES_SHA = "88684df8fb711eca6f8bfa12ccb9acc9bec09d8661270fee13ebcd36eb683474"
EXPECTED_FULL_ART_SHA = "9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a"
TARGET = "GRP004/GP004_14.TMX"
SPECS = (
    ("Shots", (190, 310, 241, 335), (0, 0, 24, 16), 0x17, "a4dadbf71138071434cf10d02e7fb87c5ee6826e9c6b208331038595388e2ecd"),
    ("ATK", (245, 310, 311, 335), (88, 16, 128, 32), 0x18, "a5a2a6ea7350063ba1d2c35cc07bf357e4469d2164ac6b77994f62cd4fb2d072"),
    ("Range", (321, 310, 383, 340), (64, 0, 104, 16), 0x19, "69a8527ea0be1d1cf2c5373a7d8df3055e6124299518d67617a142d3939ca640"),
    ("AP", (197, 344, 231, 372), (56, 16, 88, 32), 0x1A, "bd78cc05b3775b0771bb96f5f25a67609ca9c6ab46b748fc5542276b59820044"),
    ("Durability", (233, 344, 319, 375), (0, 16, 56, 32), 0x1B, "a2a1883ac089f73106c3b4bb807b04a1712a7150406b2781cfb0498fd04308c1"),
    ("Absorption", (321, 344, 409, 375), (0, 32, 40, 48), 0x1C, "beb13aec7525fdc4846928a36965a848daf9b0c8e67e5d9f4f2262319023eb17"),
    ("Recovery", (197, 381, 284, 409), (40, 32, 80, 48), 0x1D, "fd9d15eabbb3cfe2c1438940f44eefc475b4c6aaa8ba1f64dc82ed5b2323a3c2"),
    ("Increase", (291, 381, 375, 408), (24, 0, 64, 16), 0x1E, "ca5d2ba66a83a883bd0c4118c2c7c1d73d1992046afa140fabe751554d9e5605"),
)
ATTRIBUTE_SPECS = (
    ("Strength", "身体", (40, 80, 72, 96), 0x51, 0x29F76),
    ("Mind", "知性", (80, 32, 112, 48), 0x52, 0x29F94),
    ("Vitality", "生命", (40, 64, 80, 80), 0x53, 0x29FAE),
    ("Spirit", "精神", (0, 64, 40, 80), 0x54, 0x29FCC),
    ("Insight", "洞察", (40, 48, 80, 64), 0x55, 0x29FE8),
    ("Instinct", "直感", (0, 48, 40, 64), 0x56, 0x2A005),
    ("Agility", "敏捷", (0, 80, 40, 96), 0x57, 0x2A023),
)
EXPECTED_CORPUS_ROWS = {
    0x29F76: ("身体", "[Strength]"),
    0x29F94: ("知性", "[Mind]"),
    0x29FAE: ("生命", "[Vitality]"),
    0x29FCC: ("精神", "[Spirit]"),
    0x29FE8: ("洞察", "[Insight]"),
    0x2A005: ("直感", "[Instinct]"),
    0x2A023: ("敏捷", "[Agility]"),
}
COMPOSED_RECT = (0, 98, 40, 114)
EXPECTED_NATIVE_ELF_SHA = "d1dc87b0762465f4aa653e05e07af73cc593d4e716ee2575790edc617a54972e"


class R6715FItemPanelArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.art = importlib.import_module("tools.r67_15f_item_panel_art")
        except ModuleNotFoundError:
            cls.art = None

    def test_module_exposes_the_approved_art_transform_contract(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        self.assertTrue(callable(self.art.apply))
        self.assertEqual(self.art.TARGET_TMX, TARGET)
        self.assertTrue({s[0] for s in SPECS} <= set(self.art.PERMITTED_ART_RANGES))

    @unittest.skipUnless(SOURCE.exists() and GROUP4.exists() and any(p.exists() for p in CORPUS_CANDIDATES),
                         "Pinned art/corpus fixtures unavailable")
    def test_transform_matches_independent_masks_and_changes_only_eight_tiles(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        original = GROUP4.read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), EXPECTED_GROUP4_SHA)
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(), EXPECTED_SOURCE_SHA)
        source = Image.open(SOURCE).convert("RGBA")
        self.assertEqual(hashlib.sha256(source.tobytes()).hexdigest(), EXPECTED_RGBA_SHA)
        output, report = self.art.apply(original)
        self.assertEqual(hashlib.sha256(output).hexdigest(), EXPECTED_FULL_ART_SHA,
                         "pinned full art output changed across runtime environments")
        self.assertEqual(len(output), len(original))
        self.assertIsInstance(report, dict)

        old_entry = find_tmx_entry(original, TARGET)
        new_entry = find_tmx_entry(output, TARGET)
        self.assertEqual(new_entry, old_entry)
        self.assertEqual(original[old_entry.palette_offset:old_entry.palette_offset + old_entry.palette_bytes],
                         output[new_entry.palette_offset:new_entry.palette_offset + new_entry.palette_bytes])
        palette = _decode_palette(original, old_entry)
        after_indices = _decode_indices(output, new_entry)
        for label, crop, rect, _kind, mask_sha in SPECS:
            mask = _source_mask(source, crop)
            self.assertEqual(hashlib.sha256(mask).hexdigest(), mask_sha, label)
            fitted = _fit_mask(mask, crop, rect)
            left, top, right, bottom = rect
            expected_tile = bytes(
                _nearest_palette(fitted[y - top][x - left], palette)
                for y in range(top, bottom) for x in range(left, right)
            )
            actual_tile = bytes(after_indices[y * 128 + x]
                                for y in range(top, bottom) for x in range(left, right))
            self.assertEqual(actual_tile, expected_tile, f"{label} differs from independent oracle")
        approved_tiles = b"".join(
            bytes(after_indices[y * 128 + x]
                  for y in range(rect[1], rect[3]) for x in range(rect[0], rect[2]))
            for _label, _crop, rect, _kind, _sha in SPECS
        )
        self.assertEqual(hashlib.sha256(approved_tiles).hexdigest(),
                         EXPECTED_APPROVED_LABEL_INDICES_SHA,
                         "previously accepted eight labels changed")
        allowed = {offset for name_ranges in self.art.PERMITTED_ART_RANGES.values()
                   for start, end in name_ranges for offset in range(start, end)}
        changed = {i for i, (a, b) in enumerate(zip(original, output)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertTrue({s[0] for s in SPECS} <= set(self.art.PERMITTED_ART_RANGES))
        for label, _crop, rect, _kind, _hash in SPECS:
            left, top, right, bottom = rect
            ranges = self.art.PERMITTED_ART_RANGES[label]
            expected_ranges = tuple((old_entry.pixel_offset + 64*y + left // 2,
                                     old_entry.pixel_offset + 64*y + right // 2)
                                    for y in range(top, bottom))
            self.assertEqual(tuple(ranges), expected_ranges, label)

    @unittest.skipUnless(GROUP4.exists(), "Pinned GP004 fixture unavailable")
    def test_unpinned_input_fails_closed(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        altered = bytearray(GROUP4.read_bytes())
        altered[0] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA|pinned|source"):
            self.art.apply(bytes(altered))

    @unittest.skipUnless(GROUP4.exists() and ELF.exists() and any(p.exists() for p in CORPUS_CANDIDATES),
                         "Pinned native/corpus fixtures unavailable")
    def test_native_uv_consumers_map_to_the_eight_named_tiles_and_ammo_owner_survives(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        import struct

        elf = ELF.read_bytes()
        container = GROUP4.read_bytes()
        for _label, _crop, (left, top, right, bottom), kind, _mask_hash in SPECS:
            record = 0x4546F0 + 0x30 * (kind - 0x17)
            file_offset = record - 0xFFF80
            _flags, texture, *floats = struct.unpack_from("<HH11f", elf, file_offset)
            self.assertEqual(texture, 14)
            u0, v0, u1, v1 = floats[4:8]
            self.assertEqual((round(u0 * 128), round(v0 * 128), round(u1 * 128), round(v1 * 128)),
                             (left, top, right, bottom))
        self.assertIn(b"50/50\0", elf[0x6936C8:0x6936C8 + 32])
        changed, _ = self.art.apply(container)
        self.assertEqual(elf[0x6936C8:0x6936C8 + 32], ELF.read_bytes()[0x6936C8:0x6936C8 + 32])
        self.assertEqual(len(changed), len(container))

    @unittest.skipUnless(SOURCE.exists() and GROUP4.exists() and FONT.exists()
                         and any(p.exists() for p in CORPUS_CANDIDATES),
                         "Pinned attribution fixtures unavailable")
    def test_official_corpus_rows_and_generated_full_terms_match_the_native_attribute_tiles(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        self.assertEqual(self.art.EXPECTED_CORPUS_SHA256, EXPECTED_CORPUS_SHA)
        self.assertEqual(hashlib.sha256(FONT.read_bytes()).hexdigest(), EXPECTED_FONT_SHA)
        self.assertEqual({row: (japanese, f"[{english}]")
                          for english, japanese, _rect, _sprite, row in ATTRIBUTE_SPECS},
                         EXPECTED_CORPUS_ROWS)
        corpus_path = next((path for path in CORPUS_CANDIDATES if path.exists()), None)
        self.assertIsNotNone(corpus_path, "Restore pinned English.bytes before 15f art validation")
        self.assertEqual(hashlib.sha256(corpus_path.read_bytes()).hexdigest(), EXPECTED_CORPUS_SHA)
        corpus_rows = {offset: (key.strip("【】"), value)
                       for key, value, offset in parse(corpus_path)}
        self.assertEqual({row: corpus_rows[row] for row in EXPECTED_CORPUS_ROWS},
                         EXPECTED_CORPUS_ROWS)

        original = GROUP4.read_bytes()
        output, report = self.art.apply(original)
        entry = find_tmx_entry(output, TARGET)
        indices = _decode_indices(output, entry)
        palette = _decode_palette(output, entry)
        for english, _japanese, rect, _sprite, _row in ATTRIBUTE_SPECS:
            fitted = _raster_full_term(english, rect, 8)
            expected = bytes(_nearest_palette(fitted.getpixel((x, y)), palette)
                             for y in range(rect[3] - rect[1])
                             for x in range(rect[2] - rect[0]))
            left, top, right, bottom = rect
            actual = bytes(indices[y * 128 + x]
                           for y in range(top, bottom) for x in range(left, right))
            self.assertEqual(actual, expected, english)
            left, top, right, bottom = rect
            expected_ranges = tuple((entry.pixel_offset + 64 * y + left // 2,
                                     entry.pixel_offset + 64 * y + right // 2)
                                    for y in range(top, bottom))
            self.assertEqual(tuple(self.art.PERMITTED_ART_RANGES[english]), expected_ranges, english)
        self.assertEqual(report["attribute_art_source"], "locally rasterized pinned Arial; not copied official word art")
        self.assertEqual(report["official_corpus_sha256"], EXPECTED_CORPUS_SHA)
        composed = _raster_composed_instinct_spirit(COMPOSED_RECT)
        left, top, right, bottom = COMPOSED_RECT
        expected = bytes(_nearest_palette(composed.getpixel((x, y)), palette)
                         for y in range(bottom - top) for x in range(right - left))
        actual = bytes(indices[y * 128 + x]
                       for y in range(top, bottom) for x in range(left, right))
        self.assertEqual(actual, expected, "composed Instinct / Spirit tile differs")
        self.assertEqual(report["combined_sprite_0xB5"], {
            "label": "Instinct / Spirit", "localization": "composed from two corpus-proven terms",
            "exact_official_combined_phrase": False, "copied_official_word_art": False,
        })

    @unittest.skipUnless(SOURCE_ELF.exists(), "Pinned 15e executable unavailable")
    def test_attribute_uvs_match_plan_and_combined_b5_resource_chain_selects_gp004_14(self):
        import struct
        from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN

        elf = SOURCE_ELF.read_bytes()
        self.assertEqual(hashlib.sha256(elf).hexdigest(), EXPECTED_NATIVE_ELF_SHA)
        for _english, _japanese, rect, sprite, _row in ATTRIBUTE_SPECS:
            record = 0x4546F0 + 0x30 * (sprite - 0x17) - 0xFFF80
            _flags, texture, *floats = struct.unpack_from("<HH11f", elf, record)
            self.assertEqual(texture, 14, hex(sprite))
            self.assertEqual(tuple(round(value * 128) for value in floats[4:8]), rect, hex(sprite))

        bias = 0xFFF80
        self.assertEqual(struct.unpack_from("<I", elf, 0x485250 - bias)[0], 0x4811A0)
        self.assertEqual(elf[0x481748 - bias:0x481750 - bias], bytes.fromhex("007f450001000000"))
        record_va, count = struct.unpack_from("<II", elf, 0x481748 - bias)
        self.assertEqual((record_va, count), (0x457F00, 1))
        _flags, texture, width, height, *_rest = struct.unpack_from("<HH11f", elf, record_va - bias)
        floats = struct.unpack_from("<HH11f", elf, record_va - bias)[2:]
        self.assertEqual((texture, width, height), (14, 40.0, 16.0))
        self.assertEqual(tuple(round(value * 128) for value in floats[4:8]), COMPOSED_RECT)

        md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
        start = 0x111520
        decoded = {ins.address: (ins.mnemonic, ins.op_str)
                   for ins in md.disasm(elf[start - bias:start - bias + 0x70], start)}
        self.assertEqual(decoded[0x111530], ("addiu", "$s2, $zero, 0xb5"))
        self.assertEqual(decoded[0x111564], ("addiu", "$a0, $zero, 4"))
        self.assertEqual(decoded[0x111568], ("move", "$a1, $s2"))
        self.assertEqual(decoded[0x111574], ("jal", "0x107d60"))

    def test_missing_official_corpus_fails_closed(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing-English.bytes"
            with patch.object(self.art, "_CORPUS_CANDIDATES", (missing,)):
                with self.assertRaisesRegex(FileNotFoundError, "Pinned official English.bytes corpus"):
                    self.art._validate_corpus_and_font()

    def test_mismatched_official_corpus_fails_closed(self):
        self.assertIsNotNone(self.art, "15f item-panel art module has not been implemented")
        with tempfile.TemporaryDirectory() as temp_dir:
            altered = Path(temp_dir) / "English.bytes"
            altered.write_bytes(b"not the pinned official corpus")
            with patch.object(self.art, "_CORPUS_CANDIDATES", (altered,)):
                with self.assertRaisesRegex(ValueError, "corpus SHA does not match"):
                    self.art._validate_corpus_and_font()


def _source_mask(source, window):
    left, top, right, bottom = window
    pixels = source.crop(window).load()
    result = bytearray((right - left) * (bottom - top))
    for y in range(bottom - top):
        for x in range(right - left):
            red, green, blue, alpha = pixels[x, y]
            if min(red, green, blue) >= 128 and max(red, green, blue) - min(red, green, blue) <= 32:
                result[y * (right - left) + x] = (min(red, green, blue) * alpha + 127) // 255
    return bytes(result)


def _fit_mask(mask, window, rect):
    from PIL import Image

    source_width = window[2] - window[0]
    source_height = window[3] - window[1]
    image = Image.frombytes("L", (source_width, source_height), mask)
    bbox = image.getbbox()
    self_width = rect[2] - rect[0]
    self_height = rect[3] - rect[1]
    if bbox is None:
        raise AssertionError("expected nonempty label extraction")
    image = image.crop(bbox)
    scale = min((self_width - 2) / image.width, 14 / image.height)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    image = image.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("L", (self_width, self_height), 0)
    canvas.paste(image, ((self_width - size[0]) // 2, (self_height - size[1]) // 2))
    return [canvas.crop((0, y, self_width, y + 1)).tobytes() for y in range(self_height)]


def _nearest_palette(coverage, palette):
    return min(range(len(palette)), key=lambda index: (abs(palette[index][3] - coverage), index))


def _raster_full_term(text, rect, size):
    width, height = rect[2] - rect[0], rect[3] - rect[1]
    font = ImageFont.truetype(str(FONT), size=size, layout_engine=ImageFont.Layout.BASIC)
    bbox = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), text, font=font)
    if bbox[2] - bbox[0] > width - 2 or bbox[3] - bbox[1] > height - 2:
        raise AssertionError(f"{text} does not fit its native tile with one-pixel padding")
    mask = Image.new("L", (width, height), 0)
    x = (width - (bbox[2] - bbox[0])) // 2 - bbox[0]
    y = (height - (bbox[3] - bbox[1])) // 2 - bbox[1]
    ImageDraw.Draw(mask).text((x, y), text, font=font, fill=255)
    return mask


def _raster_composed_instinct_spirit(rect):
    width, height = rect[2] - rect[0], rect[3] - rect[1]
    font = ImageFont.truetype(str(FONT), size=7, layout_engine=ImageFont.Layout.BASIC)
    lines = ("Instinct", "Spirit")
    bounds = [ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), line, font=font)
              for line in lines]
    line_heights = [box[3] - box[1] for box in bounds]
    total_height = sum(line_heights) + 1
    if total_height > height - 2 or any(box[2] - box[0] > width - 2 for box in bounds):
        raise AssertionError("Composed full terms do not fit the native tile with one-pixel padding")
    mask = Image.new("L", (width, height), 0)
    y = (height - total_height) // 2
    for line, box, line_height in zip(lines, bounds, line_heights):
        x = (width - (box[2] - box[0])) // 2 - box[0]
        ImageDraw.Draw(mask).text((x, y - box[1]), line, font=font, fill=255)
        y += line_height + 1
    return mask


if __name__ == "__main__":
    unittest.main()
