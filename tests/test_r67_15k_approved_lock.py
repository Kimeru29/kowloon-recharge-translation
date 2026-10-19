"""Post-playtest, fail-closed r67.15k approval and release integrity tests."""
from __future__ import annotations

import json
import mmap
import unittest
from unittest.mock import patch

from tools.r67_15k_approved_lock import (
    ELF, ISO, ROOT, REPORT, assert_preserved, manifest, sha256_file,
    verify_approved_iso, verify_historical_report, verify_installed,
    verify_sources,
)
from tools.iso9660_patch import find_record, index_iso


class ApprovalRecordTests(unittest.TestCase):
    def test_user_approval_is_recorded_separately_from_diagnostic_results(self):
        record = manifest()
        self.assertEqual(record["approval_status"], "gameplay-approved")
        self.assertIn("2026-10-19", record["user_confirmation"])
        self.assertEqual(record["iso_size_bytes"], 2_095_382_528)
        self.assertEqual(record["runtime_save_load"], "not independently tested")
        self.assertEqual(len(record["protected_native_call_words"]), 5)
        self.assertEqual(len(record["protected_tmx_sha256"]), 4)

    def test_g_through_k_implementation_and_existing_regressions_are_locked(self):
        report = verify_sources()
        self.assertGreaterEqual(report["verified_source_files"], 25)
        self.assertIn("tools/native/r67_description_wrap.c", manifest()["source_sha256"])
        self.assertIn("tools/r67_15k_word_wrap.py", manifest()["source_sha256"])
        self.assertIn("tests/test_r67_15k_release_lock.py", manifest()["source_sha256"])

    def test_unapproved_producer_change_fails_instead_of_refreshing_baseline(self):
        from tools import r67_15k_approved_lock as lock
        original = lock.sha256_file

        def drift(path):
            if path.name == "r67_15k_word_wrap.py":
                return "0" * 64
            return original(path)

        with patch.object(lock, "sha256_file", side_effect=drift):
            with self.assertRaisesRegex(ValueError, "source or regression changed"):
                verify_sources()

    def test_historical_diagnostic_is_not_rewritten_to_claim_runtime_tests(self):
        result = verify_historical_report()
        self.assertTrue(result["historical_report_unchanged"])
        self.assertTrue(result["approved_2gb_audit"])
        self.assertEqual(result["history_regions"], 4)
        self.assertEqual(result["save_descriptors"], 15)
        raw = json.loads(REPORT.read_text())
        self.assertFalse(raw["gameplay_approved"])
        self.assertFalse(raw["runtime_verified"])
        self.assertFalse(raw["save"]["cross_release_runtime_test_performed"])

    def test_historical_report_change_is_caught(self):
        from tools import r67_15k_approved_lock as lock
        original = lock.sha256_file
        with patch.object(lock, "sha256_file",
                          side_effect=lambda p: "0" * 64 if p == REPORT else original(p)):
            with self.assertRaisesRegex(ValueError, "Historical.*changed"):
                lock.verify_historical_report()


@unittest.skipUnless(ISO.is_file() and ELF.is_file(), "Requires immutable local approved r67.15k release")
class ApprovedReleaseContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with ISO.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as image:
            _, records = index_iso(image)
            exe = find_record(records, "SLPM_665.11")
            cvm = find_record(records, "DATA.CVM")
            base = cvm.extent * 2048 + 0x1800
            _, inner = index_iso(image, base)
            art = find_record(inner, "BLBRD/B_GP004.BIN")
            cls.original_elf = bytes(image[exe.extent * 2048:
                                           exe.extent * 2048 + exe.size])
            cls.original_art = bytes(image[base + art.extent * 2048:
                                           base + art.extent * 2048 + art.size])

    def test_shipped_two_gigabyte_iso_elf_and_four_UI_textures_match_approval(self):
        proof = verify_approved_iso()
        self.assertEqual(proof["iso_sha256"], manifest()["iso_sha256"])
        self.assertEqual(proof["locked_native_calls"], 5)
        self.assertEqual(proof["locked_tmx"], 4)
        self.assertEqual(sha256_file(ELF), manifest()["installed_elf_sha256"])

    def test_approved_native_callbacks_refuse_memory_mutations(self):
        verify_installed(self.original_elf, self.original_art)
        for off in (0x1520C, 0x19AD3C, 0x19BB5C, 0x14B58, 0xDB44):
            with self.subTest(offset=hex(off)):
                modified = bytearray(self.original_elf)
                modified[off] ^= 1
                with self.assertRaisesRegex(ValueError, "executable changed"):
                    verify_installed(bytes(modified), self.original_art)

    def test_approved_legacy_textures_refuse_regeneration_changes(self):
        modified = bytearray(self.original_art)
        from tools.tmx import find_tmx_entry
        for name in manifest()["protected_tmx_sha256"]:
            with self.subTest(name=name):
                modified[:] = self.original_art
                entry = find_tmx_entry(self.original_art, name)
                modified[entry.pixel_offset] ^= 1
                with self.assertRaisesRegex(ValueError, "artwork changed"):
                    verify_installed(self.original_elf, bytes(modified))

    def test_candidate_safeguard_rejects_any_unapproved_original_byte_change(self):
        assert_preserved(original_elf=self.original_elf, modified_elf=self.original_elf,
                         original_art=self.original_art, modified_art=self.original_art)
        changed = bytearray(self.original_elf)
        changed[0x3912B4] ^= 1
        with self.assertRaisesRegex(ValueError, "needs new approval"):
            assert_preserved(original_elf=self.original_elf, modified_elf=bytes(changed),
                             original_art=self.original_art, modified_art=self.original_art)
        changed_art = bytearray(self.original_art)
        changed_art[-1] ^= 1
        with self.assertRaisesRegex(ValueError, "needs new approval"):
            assert_preserved(original_elf=self.original_elf, modified_elf=self.original_elf,
                             original_art=self.original_art, modified_art=bytes(changed_art))


if __name__ == "__main__":
    unittest.main()
