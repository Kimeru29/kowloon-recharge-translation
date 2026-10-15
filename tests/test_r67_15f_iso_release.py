"""Release-builder guards for the bounded r67.15f diagnostic image."""
from __future__ import annotations

import unittest

from tools.r67_15f_iso_release import (
    CANDIDATE_ISO, PREVIOUS_ISO, SOURCE_ART, _assert_protected_art_chunks,
    _art_patch_contract, _check_art_ownership_ranges, _compare_expected_bytes, _validate_art_changes,
    _validate_elf_changes, audit,
)
from tools.tmx import find_tmx_entry


class R6715FReleaseGuardTests(unittest.TestCase):
    def test_accepts_only_declared_existing_owners_and_generated_append(self):
        before = b"abcdefgh"
        after = b"abXdefgh+payload"
        owners = {"panel_pointer": ((2, 3),)}

        changed = _validate_elf_changes(before, after, owners)

        self.assertEqual(changed[2], (ord("X"), "panel_pointer"))
        self.assertEqual(changed[8], (ord("+"), "appended_patch_payload"))

    def test_rejects_existing_byte_mutation_outside_declared_owners(self):
        with self.assertRaisesRegex(ValueError, "unowned ELF byte 0x3"):
            _validate_elf_changes(b"abcdefgh", b"abcXefgh", {"panel": ((2, 3),)})

    def test_art_patch_is_confined_to_declared_label_tile_and_palette_bytes(self):
        before = b"0123456789abcdef"
        after = bytearray(before)
        after[5] = ord("X")
        allowed = {"gp004_05_title_tile": ((4, 8),)}
        changed = _validate_art_changes(before, after, allowed)
        self.assertEqual(changed, {5: (ord("X"), "gp004_05_title_tile")})

        after[12] ^= 1
        with self.assertRaisesRegex(ValueError, "unowned GP004 byte 0xc"):
            _validate_art_changes(before, after, allowed)

    @unittest.skipUnless(SOURCE_ART.exists(), "Requires the pinned GP004 fixture")
    def test_protected_gp004_textures_are_byte_exact(self):
        baseline = SOURCE_ART.read_bytes()
        _assert_protected_art_chunks(baseline, baseline)

        altered = bytearray(baseline)
        entry = find_tmx_entry(baseline, "GRP004/GP004_05.TMX")
        altered[entry.base_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "GP004_05"):
            _assert_protected_art_chunks(baseline, altered)

    @unittest.skipUnless(SOURCE_ART.exists(), "Requires the pinned GP004 fixture")
    def test_art_owner_ranges_must_stay_inside_gp004_14_pixels_or_palette(self):
        baseline = SOURCE_ART.read_bytes()
        target = find_tmx_entry(baseline, "GRP004/GP004_14.TMX")
        _check_art_ownership_ranges(
            {"header_tile": ((target.pixel_offset, target.pixel_offset + 4),)}, target
        )

        protected = find_tmx_entry(baseline, "GRP004/GP004_05.TMX")
        with self.assertRaisesRegex(ValueError, "escapes target TMX"):
            _check_art_ownership_ranges(
                {"wrong_tile": ((protected.pixel_offset, protected.pixel_offset + 4),)},
                target,
            )

    @unittest.skipUnless(SOURCE_ART.exists(), "Requires the pinned GP004 fixture")
    def test_release_contract_accepts_exactly_the_sixteen_named_gp004_14_tiles(self):
        _apply, owners, target_name = _art_patch_contract()
        expected_names = {
            "Shots", "ATK", "Range", "AP", "Durability", "Absorption", "Recovery", "Increase",
            "Strength", "Mind", "Vitality", "Spirit", "Insight", "Instinct", "Agility",
            "Instinct / Spirit",
        }
        self.assertEqual(target_name, "GRP004/GP004_14.TMX")
        self.assertEqual(set(owners), expected_names)
        target = find_tmx_entry(SOURCE_ART.read_bytes(), target_name)
        _check_art_ownership_ranges(owners, target)

    @unittest.skipUnless(CANDIDATE_ISO.exists(), "Requires the completed 15f ISO")
    def test_full_disc_audit_covers_the_finished_two_gigabyte_candidate(self):
        proof = audit(PREVIOUS_ISO, CANDIDATE_ISO)
        self.assertEqual(proof["status"], "PASS_EXACT_15E_BASELINE_ZERO_UNEXPLAINED")
        self.assertEqual(proof["complete_disc_bytes_compared"], 2_095_382_528)
        self.assertEqual(proof["unexplained_bytes"], 0)
        self.assertTrue(proof["gp004_18_and_gp004_19_unchanged"])

    def test_whole_image_audit_rejects_an_unexplained_candidate_mutation(self):
        baseline = b"0123456789abcdef"
        candidate = bytearray(baseline)
        candidate[4] = ord("X")
        expected = {4: (ord("X"), "panel_pointer")}
        self.assertEqual(_compare_expected_bytes(baseline, candidate, expected),
                         {"panel_pointer": 1})

        candidate[12] ^= 1
        with self.assertRaisesRegex(ValueError, "unexplained finished-ISO byte 0xc"):
            _compare_expected_bytes(baseline, candidate, expected)


if __name__ == "__main__":
    unittest.main()
