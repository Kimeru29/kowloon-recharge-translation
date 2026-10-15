"""Gameplay-approved r67.15f lock, independent of diagnostic build reports."""
from __future__ import annotations

import hashlib
import json
import mmap
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.r67_15f_approved_lock import (
    ROOT, ISO, MANIFEST, assert_unchanged_from_approved,
    load_manifest, verify_approved_iso, verify_elf_and_art, verify_source_owners,
)
from tools.r67_15f_item_panel_layout import (
    ACTION_HOOK_FILE_OFFSET, TITLE_HOOK_FILE_OFFSET,
    COMPOUND_SCALE, CANT_SCALE, PIVOT_X, COMPOUND_X_DELTA,
    CANT_X_DELTA, TITLE_BUDGET, TITLE_SCALE_CAP, TITLE_SCALE_Y,
    title_metrics,
)
from tools.iso9660_patch import index_iso, find_record

REFERENCE_ELF = ROOT / "local/r67-15f-item-panel-layout.elf"
GP004 = ROOT / "local/r67-15d-group4-clean.BIN"


class ApprovedSourceOwnerTests(unittest.TestCase):
    def test_approval_manifest_is_explicit_and_cannot_self_update(self):
        manifest = load_manifest()
        self.assertEqual(manifest["approval_status"], "gameplay-approved")
        self.assertEqual(manifest["release"], "r67.15f")
        self.assertEqual(manifest["iso_size_bytes"], 2_095_382_528)
        self.assertEqual(len(manifest["protected_tmx_sha256"]), 4)
        self.assertEqual(len(manifest["tool_sha256"]), 3)
        self.assertIn("user authorization", manifest["policy"].lower())

    def test_all_original_native_art_and_release_owners_are_source_locked(self):
        self.assertEqual(len(verify_source_owners()), 3)

    def test_changed_generator_source_fails_closed_instead_of_updating_hashes(self):
        from tools import r67_15f_approved_lock as lock
        real_hash = lock.hash_file

        def changed(path: Path) -> str:
            if path.name == "r67_15f_item_panel_layout.py":
                return "0" * 64
            return real_hash(path)

        with patch.object(lock, "hash_file", side_effect=changed):
            with self.assertRaisesRegex(ValueError, "implementation changed"):
                lock.verify_source_owners()

    def test_approved_native_backings_preserve_original_left_edge_and_scale_y(self):
        self.assertEqual(PIVOT_X, -29.0)
        for scale, displacement in ((COMPOUND_SCALE, COMPOUND_X_DELTA),
                                     (CANT_SCALE, CANT_X_DELTA)):
            x = 175.0
            before_left = x - 1.0 * PIVOT_X
            after_left = (x + displacement) - scale * PIVOT_X
            self.assertEqual(before_left, after_left)
            self.assertGreater(scale, 1.0)
        self.assertEqual((COMPOUND_SCALE, COMPOUND_X_DELTA), (2.0, -29.0))
        self.assertEqual((CANT_SCALE, CANT_X_DELTA), (1.25, -7.25))

    def test_complete_items_titles_fit_actual_card_budget(self):
        self.assertEqual(TITLE_BUDGET, 196)
        self.assertEqual((TITLE_SCALE_CAP, TITLE_SCALE_Y), (0.625, 0.75))
        for glyphs, spaces in ((17, 1), (11, 1), (9, 1), (27, 0), (1, 0), (0, 0)):
            with self.subTest(glyphs=glyphs, spaces=spaces):
                metrics = title_metrics(glyphs, spaces)
                self.assertLessEqual(metrics["advance"], TITLE_BUDGET)
                self.assertLessEqual(metrics["scale_x"], TITLE_SCALE_CAP)
                self.assertEqual(metrics["scale_y"], TITLE_SCALE_Y)

    def test_exact_approved_native_hook_words_and_owned_offsets(self):
        manifest = load_manifest()
        self.assertEqual(manifest["native_hook_words"], {
            "0x14b58": "5d922508",
            "0xdb44": "8a92250c",
        })
        self.assertEqual((ACTION_HOOK_FILE_OFFSET, TITLE_HOOK_FILE_OFFSET),
                         (0x14B58, 0xDB44))


@unittest.skipUnless(ISO.is_file(), "Approved 2 GB ISO fixture not installed")
class ApprovedFinishedImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            _, outer = index_iso(image)
            executable = find_record(outer, "SLPM_665.11")
            cvm = find_record(outer, "DATA.CVM")
            start = cvm.extent * 2048 + 0x1800
            _, inner = index_iso(image, start)
            atlas = find_record(inner, "BLBRD/B_GP004.BIN")
            cls.elf = bytes(image[executable.extent * 2048:
                                  executable.extent * 2048 + executable.size])
            cls.art = bytes(image[start + atlas.extent * 2048:
                                  start + atlas.extent * 2048 + atlas.size])

    def test_full_disc_and_all_installed_UI_owners_have_approved_digests(self):
        proof = verify_approved_iso()
        self.assertEqual(proof["iso"], load_manifest()["iso_sha256"])
        self.assertEqual(proof["protected_textures"], 4)

    def test_locked_executable_protects_compound_bubble_and_item_titles(self):
        self.assertEqual(verify_elf_and_art(self.elf, self.art)["protected_textures"], 4)
        bad = bytearray(self.elf)
        bad[ACTION_HOOK_FILE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "native executable"):
            verify_elf_and_art(bytes(bad), self.art)
        bad = bytearray(self.elf)
        bad[TITLE_HOOK_FILE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "native executable"):
            verify_elf_and_art(bytes(bad), self.art)

    def test_protected_english_stat_art_rejects_mutations(self):
        bad = bytearray(self.art)
        from tools.tmx import find_tmx_entry
        for name in load_manifest()["protected_tmx_sha256"]:
            with self.subTest(name=name):
                entry = find_tmx_entry(self.art, name)
                bad[:] = self.art
                bad[entry.pixel_offset] ^= 1
                with self.assertRaisesRegex(ValueError, "Group-4"):
                    verify_elf_and_art(self.elf, bytes(bad))

    def test_future_candidates_cannot_silently_change_any_accepted_15f_byte(self):
        assert_unchanged_from_approved(self.elf, self.elf, self.art, self.art)
        mutated = bytearray(self.elf)
        mutated[0x3912B4] ^= 1
        with self.assertRaisesRegex(ValueError, "modifies approved"):
            assert_unchanged_from_approved(self.elf, bytes(mutated), self.art, self.art)
        altered_art = bytearray(self.art)
        altered_art[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "modifies approved"):
            assert_unchanged_from_approved(self.elf, self.elf, self.art, bytes(altered_art))


if __name__ == "__main__":
    unittest.main()
