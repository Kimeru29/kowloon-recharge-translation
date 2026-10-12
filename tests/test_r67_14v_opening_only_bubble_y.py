"""r67.14v: opening-only upper-bubble correction; Eerie and other events locked."""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_14v_opening_only_bubble_y import (
    OPENING_SOURCE_POINTERS,EERIE_SOURCE_POINTER,text_y_helper,
    EVENT_Y_WRAPPERS,preimage_event,apply,
)
from tools.r67_14v_scoped_approval_lock import validate_scoped
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST,verify_ui
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST,verify_approved
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,_jal,_float_word

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/"local/r67-14t-lion-and-tablets.elf"
V=ROOT/"local/r67-14v-opening-dialogue-relative.elf"

@unittest.skipUnless(T.is_file() and V.is_file(),"Requires SHA-pinned diagnostics")
class OpeningOnlyBubbleYTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=T.read_bytes(); cls.new=V.read_bytes()

    def test_only_two_approved_opening_text_pointers_are_targeted(self):
        self.assertEqual(OPENING_SOURCE_POINTERS,(0x963F00,0x963F8C))
        self.assertEqual(EERIE_SOURCE_POINTER,0x9630BA)
        for p,actual in zip((0x3d3438,0x3d343c),OPENING_SOURCE_POINTERS,strict=True):
            self.assertEqual(struct.unpack_from("<I",self.new,p)[0],actual)
        self.assertEqual(struct.unpack_from("<I",self.new,0x3d3428)[0],EERIE_SOURCE_POINTER)
        self.assertNotIn(EERIE_SOURCE_POINTER,OPENING_SOURCE_POINTERS)

    def test_both_helpers_preserve_Eerie_and_unrelated_comment_y(self):
        for i,(_,base,adjusted) in enumerate(EVENT_Y_WRAPPERS):
            with self.subTest(row=i):
                words=struct.unpack("<"+"I"*(len(text_y_helper(base,adjusted))//4),
                                    text_y_helper(base,adjusted))
                self.assertEqual(words[0],0x860802f8) # native variant
                self.assertEqual(sum((w>>26)==4 and ((w>>21)&31)==9 and ((w>>16)&31)==8 for w in words),2)
                self.assertIn(0x35083f00,words)
                self.assertIn(0x35083f8c,words)
                self.assertNotIn(0x350830ba,words)
                self.assertIn(_float_word(base)>>16,[w&0xffff for w in words])
                self.assertIn(_float_word(adjusted)>>16,[w&0xffff for w in words])
                self.assertEqual(words[-2:],(0x03e00008,0))

    def test_native_geometry_is_relative_only_for_opening_on_upper_variant(self):
        preimage_event(self.old)
        self.assertEqual([(lo,hi) for _,lo,hi in EVENT_Y_WRAPPERS],
                         [(280.0,222.0),(300.0,242.0)])
        self.assertEqual(280-230,222-172)
        self.assertEqual(300-230,242-172)
        self.assertEqual(300-280,242-222)

    def test_new_code_only_modifies_two_scoped_event_y_loads(self):
        report=validate_scoped(self.new,self.old)
        self.assertEqual(report["other_original_elf_bytes_modified"],0)
        self.assertEqual(report["allowed_exact_event_Y_instruction_vas"],["0x963d78","0x963e54"])

    def test_rebuilding_the_same_candidate_is_deterministic(self):
        generated,r=apply(self.old)
        self.assertEqual(generated,self.new)
        self.assertTrue(r["eerie_place_unchanged_on_both_bubble_variants"])

    def test_original_q_native_snapshot_is_immutable(self):
        manifest=json.loads(Q_MANIFEST.read_text())
        self.assertEqual(verify_approved(self.old,manifest)["approved_regions"],4)
        with self.assertRaisesRegex(ValueError,"private_helpers owner drifted"):
            verify_approved(self.new,manifest)

    def test_previous_user_accepted_lion_and_stone_tablet_lock_stays_intact(self):
        surrogate=bytearray(self.new)
        for site,_,_ in EVENT_Y_WRAPPERS:
            pos=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
            surrogate[pos:pos+4]=self.old[pos:pos+4]
        result=verify_ui(bytes(surrogate),json.loads(T_MANIFEST.read_text()))
        self.assertEqual(result["lion_approved_horizontal_scale"],0.72)
        self.assertEqual(result["all_registered_tablets"],58)
        self.assertEqual(result["overwide_rows"],0)

    def test_unknown_repatch_or_source_mutation_rejected(self):
        with self.assertRaisesRegex(ValueError,"Only exact r67.14t"):
            apply(self.new)
        changed=bytearray(self.new)
        changed[0x8640a4]^=0x01
        with self.assertRaisesRegex(ValueError,"Unapproved event-Y callsite"):
            validate_scoped(bytes(changed),self.old)
if __name__=="__main__":unittest.main()
