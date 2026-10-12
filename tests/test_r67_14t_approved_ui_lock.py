"""Mutation-based r67.14t gameplay-approved Lion and Stone tablet protection."""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST
from tools.r67_14t_stone_tablet_fit import MAX_GLYPH_CELLS
from tools.r67_14q_approved_lock import extract_iso_elf,MANIFEST as Q_MANIFEST
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/"local/r67-14t-lion-and-tablets.elf"
ISO=ROOT/"local/r67-candidates/67.14t-lion-statue-and-tablets.iso"
REPORT=ROOT/"local/r67-14t-build.json"

@unittest.skipUnless(T.exists(),"Requires ignored user-approved r67.14t staged reference ELF")
class ApprovedUILockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf=T.read_bytes()
        cls.manifest=json.loads(MANIFEST.read_text())

    def assertRejected(self,offset,pattern):
        modified=bytearray(self.elf)
        modified[offset]^=0x01
        with self.assertRaisesRegex(ValueError,pattern):
            verify_ui(bytes(modified),self.manifest)

    def test_approved_staged_elf_matches_both_user_accepted_surfaces(self):
        result=verify_ui(self.elf,self.manifest)
        self.assertEqual(result["status"],"PASS_VISUALLY_ACCEPTED_LION_AND_STONE_TABLET_STATIC_OWNERS")
        self.assertEqual(result["lion_approved_horizontal_scale"],0.72)
        self.assertEqual(result["lion_approved_native_callsites"],2)
        self.assertEqual(result["accepted_tablet_record_count"],3)
        self.assertEqual(result["all_registered_tablets"],58)
        self.assertEqual(result["all_inscription_rows_checked"],160)
        self.assertEqual(result["overwide_rows"],0)

    def test_user_accepted_lion_popup_and_push_owners_are_frozen(self):
        for off in (0x2A2A6C,0x2A6060):
            with self.subTest(site=hex(off)):
                self.assertRejected(off-0xFFF80,"Lion item popup/PUSH")

    def test_user_accepted_lion_helper_geometry_cannot_change(self):
        for pos in (0x86425c,0x864260,0x864261):
            with self.subTest(file_offset=hex(pos)):
                self.assertRejected(pos,"Lion UI size/position")

    def test_user_accepted_lion_name_pointer_cannot_change(self):
        self.assertRejected(0x391928,"catalog pointer/string")

    def test_stone_tablet_header_and_body_pointers_are_locked(self):
        for pos in (0x58A250,0x590F30,0x590F38,0x590F40,0x590FB0,0x590FBC,0x590FC0):
            with self.subTest(file_offset=hex(pos)):
                self.assertRejected(pos,"Stone tablet")

    def test_stone_tablet_glyph_data_are_locked_as_well_as_pointers(self):
        # Source text mutations must fail even if all pointer words are unchanged.
        for row in (0x590F38,0x590FBC):
            ptr=struct.unpack_from("<I",self.elf,row)[0]
            pos=ELF_SEGMENT_FO+ptr-ELF_SEGMENT_VA
            with self.subTest(approved_row=hex(row)):
                self.assertRejected(pos+8,"Stone tablet content")

    def test_previous_r67_14q_event_lock_still_applies(self):
        self.assertRejected(0x3d3438,"Approved native word drift")

    @unittest.skipUnless(ISO.exists() and REPORT.exists(),"Requires approved diagnostic ISO/report")
    def test_finished_iso_embedded_elf_matches_accepted_ui_lock(self):
        actual=extract_iso_elf(ISO,json.loads(Q_MANIFEST.read_text()),REPORT)
        result=verify_ui(actual,self.manifest)
        self.assertEqual(result["all_registered_tablets"],58)
        self.assertEqual(result["overwide_rows"],0)

if __name__=="__main__":
    unittest.main()
