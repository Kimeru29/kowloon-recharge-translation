"""Regression locks for the user's visually accepted r67.14q Chamber comments.

Different native UI owners (Lion Statue pickup and pillar item-selection) are
deliberately outside the protected spans. These checks must run on every NEW
candidate ELF and embedded ISO, not just the r67.14q fixture.
"""
from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path

from tools.r67_14q_approved_lock import MANIFEST, extract_iso_elf, verify_approved
from tools.r67_chamber_story_text_only import ELF_BIAS

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-14q-opening-final-line-fit.elf"
ISO=ROOT/"local/r67-candidates/67.14q-opening-final-line-fit.iso"
REPORT=ROOT/"local/r67-14q-build.json"

class ApprovedCompanionCommentsLock(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads(MANIFEST.read_text())

    def test_committed_acceptance_manifest_is_explicit_and_stable(self):
        self.assertEqual(self.manifest["schema_version"],1)
        self.assertEqual(self.manifest["approved_git_commit"],"86e5319760b5ca1cabe69fde806e4811dd1c0fe8")
        self.assertEqual(self.manifest["baseline_elf_sha256"],
                         "c3babe784c07f83312273ac789040b74ea46d492eea48eee0f1ae17ce5c781ba")
        self.assertEqual(self.manifest["baseline_iso_sha256"],
                         "3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96")
        self.assertEqual(len(self.manifest["regions"]),4)
        self.assertEqual(len(self.manifest["approved_words"]),16)
        self.assertEqual(self.manifest["wide_text_by_pointer_alias"],{
            "0x3d3438":"Make sure you're always ready to",
            "0x3d343c":"switch into battle mode anytime."
        })

    @unittest.skipUnless(BASE.exists(),"private approved ELF fixture absent")
    def test_original_user_approved_elf_passes_owner_lock(self):
        source=BASE.read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),self.manifest["baseline_elf_sha256"])
        result=verify_approved(source,self.manifest)
        self.assertEqual(result["status"],"PASS_R67_14Q_VISUALLY_APPROVED_OWNERS")
        self.assertEqual(result["approved_regions"],4)
        self.assertTrue(result["whole_elf_is_baseline"])

    @unittest.skipUnless(ISO.exists() and REPORT.exists(),"private approved ISO/build report missing")
    def test_final_iso_embedded_elf_passes_despite_valid_builder_relocations(self):
        with ISO.open("rb") as stream:
            digest=hashlib.file_digest(stream,"sha256").hexdigest()
        self.assertEqual(digest,self.manifest["baseline_iso_sha256"])
        elf=extract_iso_elf(ISO,self.manifest,REPORT)
        result=verify_approved(elf,self.manifest)
        self.assertFalse(result["whole_elf_is_baseline"]) # valid ISO relocates pointers
        self.assertEqual(result["status"],"PASS_R67_14Q_VISUALLY_APPROVED_OWNERS")

    @unittest.skipUnless(BASE.exists(),"private ELF fixture absent")
    def test_detects_all_four_approved_owner_mutations(self):
        original=BASE.read_bytes()
        for item in self.manifest["regions"]:
            changed=bytearray(original)
            changed[item["file_offset"]+item["byte_length"]//2]^=1
            with self.subTest(item=item["name"]),self.assertRaisesRegex(ValueError,"drifted"):
                verify_approved(bytes(changed),self.manifest)

    @unittest.skipUnless(BASE.exists(),"private ELF fixture absent")
    def test_detects_dialogue_text_pointer_and_native_timer_drift(self):
        original=BASE.read_bytes()
        # Check all three independent protections: exact native timer,
        # exact header (r67.14n regression), and exact visible word bytes.
        altered_offsets=(0x864140,0x3d3440,0x3d343c,0x86418d)
        for off in altered_offsets:
            modified=bytearray(original)
            modified[off]^=1
            with self.subTest(offset=hex(off)),self.assertRaisesRegex(ValueError,"drift"):
                verify_approved(bytes(modified),self.manifest)

    @unittest.skipUnless(BASE.exists(),"private ELF fixture absent")
    def test_unrelated_lion_statue_renderer_owner_is_not_globally_frozen(self):
        original=BASE.read_bytes()
        modified=bytearray(original)
        # 0x2a23e0: independent native M_ObjGetDraw UI owner, NOT any
        # of the H_TalkBuddyTask/AFK protected regions.
        candidate_item_ui_offset=0x2A23E0-ELF_BIAS
        modified[candidate_item_ui_offset]^=1
        result=verify_approved(bytes(modified),self.manifest)
        self.assertFalse(result["whole_elf_is_baseline"])
        self.assertTrue(result["other_unrelated_ui_changes_are_allowed"])

    @unittest.skipUnless(BASE.exists(),"private ELF fixture absent")
    def test_rejects_truncated_or_unknown_header_and_manifest(self):
        data=BASE.read_bytes()
        for blob in (data[:300],b"BAD!"+data[4:]):
            with self.assertRaises(ValueError):
                verify_approved(blob,self.manifest)
        bad=dict(self.manifest,schema_version=200)
        with self.assertRaisesRegex(ValueError,"Unknown"):
            verify_approved(data,bad)

if __name__=="__main__":unittest.main()
