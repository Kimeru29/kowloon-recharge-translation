"""r67.14p: only native event X pen step & event display timer; AFK hard locked."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_companion_event_final_spacing_timing import (
    apply,SOURCE_SHA256,NEW_EVENT_ADVANCE,NEW_EVENT_TIMER,TIMER_IMMEDIATE_VA,
    PRE_LAYOUT_FACTOR_HI_VA,PRE_LAYOUT_FACTOR_LO_VA,
    NATIVE_AFK_156_SET_VA,NATIVE_AFK_240_SET_VA,
    FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND,
)
from tools.r67_chamber_story_text_only import (
    ELF_SEGMENT_FO,ELF_SEGMENT_VA,ELF_BIAS,_i,_float_word
)
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_companion_event_generic_fit import (
    GENERIC_FONT_ADVANCE,NATIVE_GLYPH_ADVANCE,BUBBLE_WIDTH,PADDING_EACH_SIDE
)
from tools.r67_companion_event_stable_timing import EVENT_DURATION_FRAMES
from tools.r67_companion_event_complete_opening_only import REFLOW
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.startup_acceptance import verify_startup_elf

ROOT=Path(__file__).resolve().parents[1]
O=ROOT/'local/r67-14o-keep-native-third-event.elf'
P=ROOT/'local/r67-14p-final-event-spacing-timing.elf'

class FinalEventPolicy(unittest.TestCase):
    @unittest.skipUnless(O.exists() and P.exists(),"private compiled executable fixtures missing")
    def test_exact_three_private_mips_instruction_words_only(self):
        src=O.read_bytes();out,report=apply(src)
        self.assertEqual(sha(src),SOURCE_SHA256)
        self.assertEqual(out,P.read_bytes())
        self.assertEqual(len(out),len(src))
        self.assertEqual(report['changed_existing_byte_count'],5)
        self.assertFalse(report['runtime_approved'])
        self.assertEqual(report['old_event_hold_frames'],300)
        self.assertEqual(report['new_event_hold_frames'],240)
        oldbits=_float_word(GENERIC_FONT_ADVANCE)
        newbits=_float_word(NEW_EVENT_ADVANCE)
        expected={
            PRE_LAYOUT_FACTOR_HI_VA:(_i(15,0,9,oldbits>>16),_i(15,0,9,newbits>>16)),
            PRE_LAYOUT_FACTOR_LO_VA:(_i(13,9,9,oldbits&0xFFFF),_i(13,9,9,newbits&0xFFFF)),
            TIMER_IMMEDIATE_VA:(_i(9,0,2,EVENT_DURATION_FRAMES),_i(9,0,2,NEW_EVENT_TIMER))
        }
        allowed=set()
        for va,(old,new) in expected.items():
            off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
            allowed.update(range(off,off+4))
            self.assertEqual(struct.unpack_from('<I',src,off)[0],old)
            self.assertEqual(struct.unpack_from('<I',out,off)[0],new)
        changed={i for i,(a,b) in enumerate(zip(src,out)) if a!=b}
        self.assertFalse(changed-allowed)
        self.assertEqual(len(changed),5)
        for ptr in (FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
                    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND):
            self.assertEqual(src[ptr:ptr+4],out[ptr:ptr+4])

    def test_event_duration_reduction_exact_and_glyphs_not_overlapped(self):
        self.assertEqual(EVENT_DURATION_FRAMES,300)
        self.assertEqual(NEW_EVENT_TIMER,240)
        self.assertEqual(NEW_EVENT_TIMER*5,EVENT_DURATION_FRAMES*4)
        self.assertEqual(NEW_EVENT_ADVANCE,0.4)
        self.assertEqual(NEW_EVENT_ADVANCE*NATIVE_GLYPH_ADVANCE,
                         0.40*NATIVE_GLYPH_ADVANCE)
        self.assertLess(max(map(len,REFLOW))*NEW_EVENT_ADVANCE*NATIVE_GLYPH_ADVANCE,
                        BUBBLE_WIDTH-2*PADDING_EACH_SIDE)
        self.assertEqual(len(COMPANION_COMMENT_DATA),1650)
        self.assertEqual(len(COMPANION_AFK_TRANSLATIONS),600)

    @unittest.skipUnless(O.exists() and P.exists(),"compiled ELF fixtures missing")
    def test_afk_native_156_240_overrides_and_special_constructor_are_byte_identical(self):
        old=O.read_bytes();new=P.read_bytes()
        for va,frames in ((NATIVE_AFK_156_SET_VA,156),(NATIVE_AFK_240_SET_VA,240)):
            expected=_i(9,0,2,frames)
            self.assertEqual(struct.unpack_from('<I',old,va-ELF_BIAS)[0],expected)
            self.assertEqual(struct.unpack_from('<I',new,va-ELF_BIAS)[0],expected)
        for start,end in ((0x1661D0,0x16620C),(0x1662E8,0x166340),
                          (0x1950A0,0x195260),(0x18CB50,0x18E1F0)):
            self.assertEqual(old[start-ELF_BIAS:end-ELF_BIAS],
                             new[start-ELF_BIAS:end-ELF_BIAS])

    @unittest.skipUnless(P.exists(),"candidate missing")
    def test_startup_translation_acceptance_remains_valid(self):
        ok={r['name']:r['ok'] for r in verify_startup_elf(P.read_bytes())}
        self.assertTrue(ok['companion_hud_comments'])

    @unittest.skipUnless(O.exists(),"baseline ELF fixture missing")
    def test_wrong_baseline_or_reapplication_is_refused(self):
        raw=O.read_bytes()
        with self.assertRaisesRegex(ValueError,'unknown ELF'):
            apply(raw[:-1])
        patched,_=apply(raw)
        with self.assertRaisesRegex(ValueError,'unknown ELF'):
            apply(patched)

if __name__=='__main__':unittest.main()
