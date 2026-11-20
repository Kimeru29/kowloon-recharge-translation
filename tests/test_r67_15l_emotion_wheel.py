from __future__ import annotations

import hashlib
import json
import mmap
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageChops, ImageFilter
from tools import r67_15l_emotion_wheel as wheel
from tools import r67_15l_iso_release as release
from tools.iso9660_patch import find_record, index_iso
from tools.tmx import _decode_indices, find_tmx_entry, iter_tmx_entries

ROOT = Path(__file__).resolve().parents[1]


def _approved_group1() -> bytes:
    with release.SOURCE_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        cvm = find_record(outer, release.DATA_CVM_NAME)
        cvm_base = cvm.extent * release.SECTOR_BYTES + release.DATA_CVM_HEADER_BYTES
        _, nested = index_iso(image, cvm_base)
        record = find_record(nested, "BLBRD/B_GP001.BIN")
        start = cvm_base + record.extent * release.SECTOR_BYTES
        return bytes(image[start:start + record.size])


class EmotionWheelArtTests(unittest.TestCase):
    def test_contract_pins_official_sources_and_all_eight_labels(self):
        self.assertEqual(wheel.apply.__annotations__["return"], "tuple[bytes, dict]")
        self.assertEqual(set(wheel.LABELS), {
            "JOY", "LOVE", "AMITY", "HOT", "COLD", "ANGER", "SOMBER", "GRIEF"
        })
        self.assertEqual(set(wheel.TARGET_TEXTURES), {"02", "03", "08", "10"})
        self.assertEqual(wheel.OFFICIAL_BUNDLE_SHA256,
                         "78ac1bcdbe7e6838be3c0d3ae49d76c290bfd3205ad55e97bc647697b3d6260b")

    def test_apply_changes_only_owned_texel_payloads_and_preserves_metadata_palette(self):
        old = _approved_group1()
        self.assertEqual(hashlib.sha256(old).hexdigest(), wheel.SOURCE_GROUP_SHA256)
        new, report = wheel.apply(old)

        self.assertEqual(len(new), len(old))
        self.assertNotEqual(new, old)
        self.assertEqual(report["status"], "PASS_OFFICIAL_EMOTION_WHEEL_ART")
        self.assertEqual(report["labels"], sorted(wheel.LABELS))
        self.assertEqual(report["texture_count"], 4)
        self.assertEqual(report["official_bundle_sha256"], wheel.OFFICIAL_BUNDLE_SHA256)
        self.assertEqual(report["source_container_sha256"], wheel.SOURCE_GROUP_SHA256)

        allowed = set()
        for name in wheel.TARGET_TEXTURES.values():
            before = find_tmx_entry(old, name)
            after = find_tmx_entry(new, name)
            self.assertEqual(after, before)
            self.assertEqual(old[before.palette_offset:before.palette_offset + before.palette_bytes],
                             new[after.palette_offset:after.palette_offset + after.palette_bytes])
            allowed.update(range(before.pixel_offset, before.pixel_offset + before.pixel_bytes))

        changed = {index for index, (left, right) in enumerate(zip(old, new)) if left != right}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed, "container/header/palette or unrelated TMX bytes changed")
        self.assertEqual(len(iter_tmx_entries(new)), len(iter_tmx_entries(old)))

    def test_report_covers_every_native_variant_and_texture_label_occurrence(self):
        localized, report = wheel.apply(_approved_group1())
        self.assertEqual(report["variant_count"], 4)
        self.assertEqual(set(report["variants"]), {"paired_plaques", "gold_singles", "glowing_singles", "paired_selected"})
        self.assertEqual(report["paired_plaque_occurrences"], 20)
        self.assertEqual(report["label_drawing_occurrences"], 56)
        self.assertEqual(len(report["ownership_evidence"]["02"]), 3)
        self.assertEqual(len(report["ownership_evidence"]["10"]), 17)
        self.assertEqual(len(report["ownership_evidence"]["03"]), 8)
        self.assertEqual(len(report["ownership_evidence"]["08"]), 8)
        for atlas in ("02", "10"):
            self.assertTrue(all(row["masked_texels"] > 0
                                for row in report["ownership_evidence"][atlas]))
        for atlas in ("03", "08"):
            self.assertTrue(all(row["masked_texels"] > 0
                                for row in report["ownership_evidence"][atlas]))
        for texture in wheel.TARGET_TEXTURES.values():
            self.assertTrue(report["texture_changes"][texture])

    def test_translation_inventory_matches_transformer_uv_owners(self):
        manifest = json.loads((ROOT / "translations/r67_15l_emotion_wheel.json").read_text())
        self.assertEqual(manifest["coverage"]["paired_plaque_occurrences"], wheel.PAIRED_OCCURRENCE_COUNT)
        self.assertEqual(manifest["coverage"]["total_label_drawings"], 56)
        self.assertEqual(len(manifest["owners"]["paired_plaque_variants"]["uv_pixels"]), 16)
        self.assertEqual(manifest["owners"]["gold_single_labels"]["uv_pixels_by_label"],
                         {label: list(rect) for label, rect in wheel.GOLD_RECTS.items()})
        self.assertEqual(manifest["owners"]["glow_single_labels"]["uv_pixels_by_label"],
                         {label: list(rect) for label, rect in wheel.GLOW_RECTS.items()})

    def test_wrong_container_fails_closed(self):
        wrong = bytearray(_approved_group1())
        wrong[0] ^= 1
        with self.assertRaisesRegex(ValueError, "source|hash|container"):
            wheel.apply(bytes(wrong))

    def test_local_pinned_extraction_is_used_when_recovered_bundle_is_absent(self):
        absent = tuple(ROOT / "missing" / f"bundle-{index}" for index, _ in enumerate(wheel._BUNDLE_CANDIDATES))
        with patch.object(wheel, "_BUNDLE_CANDIDATES", absent):
            _, _, source_kind = wheel._load_images()
        self.assertEqual(source_kind, "pinned_local_source_recovery")

    def test_changed_texels_are_contained_by_native_uvs_and_official_masks(self):
        old = _approved_group1()
        new, _ = wheel.apply(old)
        english, japanese, _ = wheel._load_images()
        crops = {"02": wheel.PAIRED_02, "10": wheel.PAIRED_10,
                 "03": tuple(wheel.GOLD_RECTS.values()), "08": tuple(wheel.GLOW_RECTS.values())}
        for atlas, rects in crops.items():
            entry = find_tmx_entry(old, wheel.TARGET_TEXTURES[atlas])
            if atlas in ("02", "10"):
                matte = wheel._paired_label_mask(english[atlas], japanese[atlas],
                                                  (entry.width, entry.height))
            before, after = _decode_indices(old, entry), _decode_indices(new, entry)
            owned = set()
            for left, top, right, bottom in rects:
                owned.update(y * entry.width + x for y in range(top, bottom) for x in range(left, right)
                             if atlas not in ("02", "10") or matte.getpixel((x, y)) > 0)
            changed = {position for position, (before_index, after_index) in
                       enumerate(zip(before, after)) if before_index != after_index}
            self.assertTrue(changed, atlas)
            self.assertLessEqual(changed, owned, f"GP001_{atlas} changed texels outside owner/mask")

    def test_english_japanese_difference_masks_preserve_plaque_and_atlas_background_indices(self):
        old = _approved_group1()
        new, _ = wheel.apply(old)
        for atlas, crops in (("02", wheel.PAIRED_02), ("10", wheel.PAIRED_10)):
            entry = find_tmx_entry(old, wheel.TARGET_TEXTURES[atlas])
            english, japanese, _ = wheel._load_images()
            mask = wheel._paired_label_mask(english[atlas], japanese[atlas],
                                            (entry.width, entry.height))
            before, after = _decode_indices(old, entry), _decode_indices(new, entry)
            for left, top, right, bottom in crops:
                for y in range(top, bottom):
                    for x in range(left, right):
                        if mask.getpixel((x, y)) == 0:
                            position = y * entry.width + x
                            self.assertEqual(before[position], after[position],
                                             f"GP001_{atlas} plaque/background index changed at {(x, y)}")

    def test_old_japanese_only_label_support_is_covered_in_all_owned_tiles(self):
        english, japanese, _ = wheel._load_images()
        old = _approved_group1()
        new, _ = wheel.apply(old)
        for atlas, rects in (("02", wheel.PAIRED_02), ("10", wheel.PAIRED_10)):
            entry = find_tmx_entry(old, wheel.TARGET_TEXTURES[atlas])
            mask = wheel._paired_label_mask(english[atlas], japanese[atlas],
                                            (entry.width, entry.height))
            english_alpha = wheel._resize(english[atlas], (entry.width, entry.height)).getchannel("A")
            japanese_only = ImageChops.subtract(japanese[atlas].getchannel("A"),
                                                 english[atlas].getchannel("A"))
            japanese_only = japanese_only.point(lambda value: 255 if value > 0 else 0)
            japanese_only = japanese_only.resize((entry.width, entry.height), Image.Resampling.LANCZOS)
            after = _decode_indices(new, entry)
            palette = wheel._decode_palette(old, entry)
            for left, top, right, bottom in rects:
                for y in range(top, bottom):
                    for x in range(left, right):
                        if japanese_only.getpixel((x, y)) > 0:
                            self.assertGreater(mask.getpixel((x, y)), 0,
                                               f"GP001_{atlas} old-only stroke not masked at {(x, y)}")
                            position = y * entry.width + x
                            if english_alpha.getpixel((x, y)) == 0:
                                self.assertEqual(0, palette[after[position]][3],
                                                 f"GP001_{atlas} old-only stroke remains visible at {(x, y)}")

        old = _approved_group1()
        new, _ = wheel.apply(old)
        for atlas, rects in (("03", wheel.GOLD_RECTS.values()), ("08", wheel.GLOW_RECTS.values())):
            entry = find_tmx_entry(old, wheel.TARGET_TEXTURES[atlas])
            alpha = english[atlas].getchannel("A").resize((entry.width, entry.height), Image.Resampling.LANCZOS)
            before, after = _decode_indices(old, entry), _decode_indices(new, entry)
            transparent = next(i for i, color in enumerate(wheel._decode_palette(old, entry)) if color[3] == 0)
            owned = set()
            for left, top, right, bottom in rects:
                owned.update(y * entry.width + x for y in range(top, bottom) for x in range(left, right))
                for y in range(top, bottom):
                    for x in range(left, right):
                        if alpha.getpixel((x, y)) == 0:
                            self.assertEqual(transparent, after[y * entry.width + x],
                                             f"GP001_{atlas} Japanese residue at {(x, y)}")
            changed = {position for position, (before_index, after_index) in
                       enumerate(zip(before, after)) if before_index != after_index}
            self.assertLessEqual(changed, owned, f"GP001_{atlas} changes escaped single-label UVs")

if __name__ == "__main__":
    unittest.main()
