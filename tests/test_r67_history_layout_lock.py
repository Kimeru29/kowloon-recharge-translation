"""Lock the user-approved r67.12 history layout, without freezing other defects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from tools.r67_history_layout_lock import (
    DEFAULT_MANIFEST,
    HistoryLayoutDriftError,
    read_lock,
    verify_bytes,
    verify_elf_file,
    verify_iso_file,
)

ROOT = Path(__file__).resolve().parents[1]
APPROVED_ELF = ROOT / "local/r67-12-history-compact.elf"
APPROVED_ISO = ROOT / "local/r67-candidates/67.12-history-compact-diagnostic.iso"
EXPECTED = {
    "adv_history_layout_and_row_spacing": (0x1538C0, 1392, "c8a1406fb9f3672f659249066960745af7c918db7473ddfb28cdb770ba372843"),
    "adv_history_font_creator": (0x155E90, 160, "f84ff13d474f66531d74dc204c7559d77cbbebd0494ae6bf3a550550d4d75e23"),
    "history_horizontal_constructor_clone": (0x863CA0, 576, "fd1a98baa46194657614d276313e230fdf8f7655c9bdfbc1e7c101721fd46c35"),
    "history_chronological_ring_helper": (0x863EE0, 48, "8d44f8d2c4074edce03955e3b7b11a5140ebcc9fe2da013de638b49cda7c851f"),
}


class HistoryLayoutLock(unittest.TestCase):
    def test_four_owner_fingerprints_are_pinned_in_repository(self):
        lock = read_lock()
        self.assertIn("USER_APPROVED", lock["status"])
        self.assertIn("remain unverified", lock["approval_scope"])
        self.assertEqual(set(EXPECTED), {entry["name"] for entry in lock["locked_regions"]})
        for region in lock["locked_regions"]:
            self.assertEqual(
                EXPECTED[region["name"]],
                (region["offset"], region["size"], region["sha256"])
            )
        self.assertEqual(
            "d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179",
            lock["reference_stage_sha256"]
        )

    def test_invalid_or_overlapping_lock_regions_are_rejected(self):
        lock = json.loads(DEFAULT_MANIFEST.read_text())
        lock["locked_regions"][1]["offset"] = lock["locked_regions"][0]["offset"]
        path = ROOT / "local/r67-history-layout-invalid-lock-test.json"
        if path.exists():
            self.skipTest("Refusing to overwrite an existing file")
        try:
            path.write_text(json.dumps(lock))
            with self.assertRaisesRegex(HistoryLayoutDriftError, "overlapping"):
                read_lock(path)
        finally:
            path.unlink(missing_ok=True)

    @unittest.skipUnless(APPROVED_ELF.exists(), "Untracked approved r67.12 ELF not available")
    def test_protected_elf_matches_and_unrelated_changes_remain_allowed(self):
        lock = read_lock()
        self.assertEqual(set(EXPECTED), set(verify_elf_file(APPROVED_ELF, lock)))
        payload = bytearray(APPROVED_ELF.read_bytes())
        payload[0x200000] ^= 1  # unrelated executable byte outside protected ranges
        self.assertEqual(set(EXPECTED), set(verify_bytes(payload, lock)))
        for name, (offset, _, _) in EXPECTED.items():
            with self.subTest(owner=name):
                payload[offset] ^= 1
                with self.assertRaisesRegex(HistoryLayoutDriftError, name):
                    verify_bytes(payload, lock)
                payload[offset] ^= 1

    @unittest.skipUnless(APPROVED_ISO.exists(), "Untracked approved r67.12 ISO not available")
    def test_final_iso_installed_elf_matches_the_same_lock(self):
        self.assertEqual(set(EXPECTED), set(verify_iso_file(APPROVED_ISO, read_lock())))

    def test_new_candidate_can_be_guarded_with_environment_paths(self):
        """Set R67_HISTORY_LOCK_ELF/ISO to make future candidate tests mandatory."""
        lock = read_lock()
        for env, validator in (
            ("R67_HISTORY_LOCK_ELF", verify_elf_file),
            ("R67_HISTORY_LOCK_ISO", verify_iso_file),
        ):
            path_text = os.getenv(env)
            if path_text:
                with self.subTest(env=env):
                    self.assertEqual(set(EXPECTED), set(validator(Path(path_text), lock)))


if __name__ == "__main__":
    unittest.main()
