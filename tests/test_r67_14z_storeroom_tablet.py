"""Immutable y acceptance + narrowly scoped Storeroom regression tests."""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_14y_approved_lock import (
    MANIFEST,verify_frozen_y,verify_new_diagnostic_scope,require_dual_approval,
)
from tools.r67_14z_storeroom_tablet import (
    expected_writes,verify_official,ROOM_OWNERS,TABLET_OWNERS,
    TABLET_TEXT,ROOM_EN,TABLET_RECORD,Y_STAGE_SHA,read_string,sha,
)
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit
from tools.r67_14z_iso_release import audit,Y_ISO,Z_ISO,Y_STAGE,Z_STAGE

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(Y_STAGE.is_file() and Z_STAGE.is_file(),"Local approved y and candidate z ELF required")
class ApprovedYScopedStoreroomTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=Y_STAGE.read_bytes()
        cls.new=Z_STAGE.read_bytes()
        cls.lock=json.loads(MANIFEST.read_text())

    def test_approved_y_elf_is_immutable_reference(self):
        report=verify_frozen_y(self.old,self.lock)
        self.assertEqual(report["status"],"PASS_ALL_APPROVED_Y_EXECUTABLE_BYTES")
        self.assertEqual(sha(self.old),Y_STAGE_SHA)

    def test_approved_y_code_or_text_mutation_fails_closed(self):
        for off in (0x165EE0-0xFFF80,0x338A80,0x407460,0x58A120,0x5910A0):
            with self.subTest(off=hex(off)):
                mutated=bytearray(self.old)
                mutated[off]^=1
                with self.assertRaisesRegex(ValueError,"user-approved y executable"):
                    verify_frozen_y(bytes(mutated),self.lock)

    def test_exactly_five_requested_native_owners_with_all_prior_content_unchanged(self):
        report=verify_new_diagnostic_scope(self.old,self.new,self.lock,ROOM_OWNERS+TABLET_OWNERS)
        self.assertEqual(report["status"],"PASS_EXACT_FIVE_REQUESTED_POINTER_OWNERS_ONLY")
        self.assertTrue(report["previous_ui_owners_verified"])

    def test_unapproved_owner_cannot_sneak_into_release(self):
        changed=bytearray(self.new)
        changed[0x338A84]^=1 # already accepted No save-menu option
        with self.assertRaisesRegex(ValueError,"outside explicit scope"):
            verify_new_diagnostic_scope(self.old,bytes(changed),self.lock,ROOM_OWNERS+TABLET_OWNERS)

    def test_official_ps4_room_name_and_three_inscription_source_rows(self):
        sources=verify_official()
        self.assertEqual(len(sources),4)
        self.assertEqual(sources[0]["official"],"Storeroom")
        expected,_=expected_writes(self.old)
        self.assertEqual(expected,self.new)

    def test_all_two_room_aliases_translate_to_same_exact_english(self):
        owners=[struct.unpack_from("<I",self.new,off)[0] for off in ROOM_OWNERS]
        self.assertEqual(owners[0],owners[1])
        self.assertEqual(read_string(self.new,owners[0]).decode("cp932").replace('Ｓ','S')[:1],'S')
        self.assertEqual(len(read_string(self.new,owners[0]).decode("cp932")),len(ROOM_EN))

    def test_storeroom_tablet_original_three_rows_keep_quote_markers_and_fit(self):
        pointers=struct.unpack_from("<6I",self.new,TABLET_RECORD)
        self.assertEqual(pointers[0:2],(0x962C7A,0x962D3C))
        for i,ptr in enumerate(pointers[2:5]):
            text=read_string(self.new,ptr)
            self.assertLessEqual(len(text.decode("cp932")),21)
            self.assertEqual(len(text),2*len(text.decode("cp932")))
        self.assertEqual(pointers[5],0x962C94)
        self.assertEqual(assert_all_tablets_fit(self.new)["overwide_rows"],0)

    def test_reject_unrelated_room_owner_preimage_change(self):
        b=bytearray(self.old)
        struct.pack_into("<I",b,ROOM_OWNERS[0],0)
        with self.assertRaisesRegex(ValueError,"exact approved r67.14y"):
            expected_writes(bytes(b))

    def test_approved_new_release_requires_two_explicit_reviews(self):
        with self.assertRaisesRegex(ValueError,"explicit_user_visual_approval"):
            require_dual_approval(dict(release_status="DIAGNOSTIC"))
        with self.assertRaisesRegex(ValueError,"documented_ai_technical_review"):
            require_dual_approval(dict(release_status="APPROVED_FOR_MAIN",
                explicit_user_visual_approval="2026-10-12 screenshot of Storeroom and three tablet rows"))

    @unittest.skipUnless(Z_ISO.is_file() and Y_ISO.is_file(),"Full ISO artifacts required")
    def test_finished_iso_frozen_delta_audit_remains_exact(self):
        report=audit(Y_ISO,Z_ISO,self.old,self.new)
        self.assertEqual(report["unexplained_bytes"],0)
        self.assertEqual(report["previous_approved_y_iso_sha256"],self.lock["iso_sha256"])

if __name__=="__main__":unittest.main()
