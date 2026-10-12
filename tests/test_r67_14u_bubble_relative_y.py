"""r67.14u focused regression: native bubble variant geometry and scoped locks."""
from __future__ import annotations

import json,struct,unittest
from pathlib import Path
from tools.r67_14u_companion_bubble_relative_y import (
    EVENT_Y_WRAPPERS,SOURCE_T_SHA,GEOMETRY_Y,RUNTIME_BUBBLE_VARIANT_OFFSET,
    text_y_helper,preimage_event,apply,
)
from tools.r67_14u_scoped_approval_lock import validate_scoped
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST,verify_ui
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST,verify_approved
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,_jal,_float_word
from tools.r67_lion_statue_ui import sha

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/"local/r67-14t-lion-and-tablets.elf"
U=ROOT/"local/r67-14u-bubble-relative-dialogue.elf"
ISO=ROOT/"local/r67-candidates/67.14u-bubble-relative-dialogue.iso"

@unittest.skipUnless(T.is_file() and U.is_file(),"Ignored diagnostic ELF artifacts required")
class BubbleVariantRelativeYTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=T.read_bytes()
        cls.candidate=U.read_bytes()

    def test_native_sprite_variants_have_exact_58_unit_shift(self):
        preimage_event(self.source)
        self.assertEqual(GEOMETRY_Y,(172.0,230.0))
        self.assertEqual(RUNTIME_BUBBLE_VARIANT_OFFSET,0x2f8)

    def test_lower_user_accepted_layout_is_identity_for_both_rows(self):
        self.assertEqual([entry[1] for entry in EVENT_Y_WRAPPERS],[280.0,300.0])
        self.assertEqual([entry[1]-GEOMETRY_Y[1] for entry in EVENT_Y_WRAPPERS],[50.0,70.0])
        self.assertEqual(EVENT_Y_WRAPPERS[1][1]-EVENT_Y_WRAPPERS[0][1],20.0)

    def test_upper_reuses_same_content_insets_and_row_spacing(self):
        self.assertEqual([entry[2] for entry in EVENT_Y_WRAPPERS],[222.0,242.0])
        self.assertEqual([entry[2]-GEOMETRY_Y[0] for entry in EVENT_Y_WRAPPERS],[50.0,70.0])
        self.assertEqual(EVENT_Y_WRAPPERS[1][2]-EVENT_Y_WRAPPERS[0][2],20.0)

    def test_each_real_compiled_helper_reads_task_variant_and_branches(self):
        for i,(site,low,high) in enumerate(EVENT_Y_WRAPPERS):
            with self.subTest(site=hex(site)):
                helper=text_y_helper(low,high)
                words=struct.unpack("<"+"I"*(len(helper)//4),helper)
                self.assertEqual(words[0],0x860802f8)  # lh t0,0x2f8(s0)
                self.assertEqual(words[1],0x15000004)  # bnez t0,target lower
                self.assertEqual(words[2],0)           # branch delay NOP
                self.assertEqual(words[-2:],(0x03e00008,0))
                self.assertIn(_float_word(high)>>16,[w&0xffff for w in words])
                self.assertIn(_float_word(low)>>16,[w&0xffff for w in words])
                ptr=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
                candidate_call=struct.unpack_from("<I",self.candidate,ptr)[0]
                helper_va=ELF_SEGMENT_VA+((len(self.source)+3)//4*4)-ELF_SEGMENT_FO+i*len(helper)
                self.assertEqual(candidate_call,_jal(helper_va))
                self.assertEqual(self.candidate[ptr+4:ptr+8],self.source[ptr+4:ptr+8])

    def test_new_candidate_has_only_exact_scoped_exceptions(self):
        scoped=validate_scoped(self.candidate,self.source)
        self.assertEqual(scoped["status"],"PASS_SCOPED_Q_PRIVATE_EVENT_Y_EXCEPTION_AND_ALL_T_APPROVED_UI")
        self.assertEqual(scoped["other_original_elf_bytes_modified"],0)

    def test_same_original_event_comments_and_row_controls(self):
        for start,end in ((0x3D3420,0x3D3468),(0x166080-0xfff80,0x166340-0xfff80)):
            self.assertEqual(self.candidate[start:end],self.source[start:end])

    def test_strict_q_lock_is_not_silently_rebased(self):
        q=json.loads(Q_MANIFEST.read_text())
        self.assertEqual(verify_approved(self.source,q)["approved_regions"],4)
        with self.assertRaisesRegex(ValueError,"private_helpers owner drifted"):
            verify_approved(self.candidate,q)

    def test_lion_and_tablet_accepted_owners_stay_exact(self):
        rebuilt=bytearray(self.candidate)
        for site,_,_ in EVENT_Y_WRAPPERS:
            p=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
            rebuilt[p:p+4]=self.source[p:p+4]
        ui=verify_ui(bytes(rebuilt),json.loads(T_MANIFEST.read_text()))
        self.assertEqual(ui["overwide_rows"],0)
        self.assertEqual(ui["lion_approved_horizontal_scale"],0.72)

    def test_wrong_elf_or_random_word_edit_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Unexpected r67.14t"):
            apply(self.candidate)
        wrong=bytearray(self.candidate)
        wrong[0x863fc8+3]^=1
        with self.assertRaisesRegex(ValueError,"Unapproved event-Y"):
            validate_scoped(bytes(wrong),self.source)

    def test_native_variant_geometry_mutation_fails_closed(self):
        tampered=bytearray(self.source)
        off=0x4f8dbc-0xfff80 # second native sprite Y 230.0
        tampered[off]^=1
        with self.assertRaisesRegex(ValueError,"Native event bubble variant"):
            preimage_event(bytes(tampered))

    @unittest.skipUnless(ISO.is_file(),"Finished ISO required")
    def test_finished_iso_is_distinct_version(self):
        self.assertIn("14u",ISO.name)
        self.assertNotEqual(self.source,self.candidate)

if __name__=="__main__":
    unittest.main()
