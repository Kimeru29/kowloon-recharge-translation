"""Validation of r67.14e guarded before-glyph horizontal scale.

Specifically tests the high-risk areas that made r67.14d fail:
original native code is NOT cloned, caller return/timing untouched,
native constructor stack is never wrapped, and the s7 matching marker
is restored for all exits.
"""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from tools.r67_chamber_pre_glyph_marker import (
    sha, apply, comment_text_helper, pre_glyph_font_clear_helper,
    COMMENT_ONLY_MARKER, FONT_OBJ_XSCALE_OFFSET, PRE_GLYPH_CALL_SITE,
    PRE_GLYPH_ORIGINAL_CALLEE, CALL_SITE_PREIMAGE, APPROVED_POINTERS,
    APPROVED_SHA256, ELF_BIAS, STORY_CALLS, HORIZONTAL_SCALE,
    _float_word, _jal
)
from tools.r67_chamber_story_text_only import make_helper as accepted_helper
from tools.r67_history_layout_lock import read_lock, verify_bytes

ROOT=Path(__file__).resolve().parents[1]
APPROVED=ROOT/"local/r67-12-history-compact.elf"
PREVIOUS=ROOT/"local/r67-14c-chamber-story-only.elf"
PROPOSED=ROOT/"local/r67-14e-chamber-pre-glyph.elf"

def decode_branches(code:bytes):
    ins=struct.unpack("<"+"I"*(len(code)//4),code)
    for i,w in enumerate(ins):
        op=w>>26
        rs=(w>>21)&31
        rt=(w>>16)&31
        if op in (4,5):
            target=i+1+struct.unpack("<h",struct.pack("<H",w&0xffff))[0]
            yield i,op,rs,rt,target

class ChamberOnlyPreGlyph(unittest.TestCase):
    def test_guarded_shared_call_does_not_intercept_font_constructor(self):
        code=pre_glyph_font_clear_helper()
        w=struct.unpack("<"+"I"*(len(code)//4),code)
        self.assertEqual(0x27BDFFE0,w[0])
        self.assertEqual((0xAFBF0000,0xAFA80004,0xAFA90008),w[1:4])
        self.assertEqual(_jal(PRE_GLYPH_ORIGINAL_CALLEE),w[4])
        self.assertEqual(0,w[5]) # native JAL delay-slot is NOP
        self.assertIn(0xAE490048,w) # sw t1,+0x48(s2)
        self.assertNotIn(0xAE49004C,w) # NEVER modify vertical character scale
        self.assertEqual(0x8FA90008,w[-6])
        self.assertEqual(0x8FA80004,w[-5])
        self.assertEqual(0x8FBF0000,w[-4])
        self.assertEqual(0x27BD0020,w[-3])
        self.assertEqual((0x03E00008,0),w[-2:])
        self.assertTrue(any(op==5 and (rs,rt)==(23,8) for _,op,rs,rt,_ in decode_branches(code)))
        self.assertTrue(any(op==4 and (rs,rt)==(18,0) for _,op,rs,rt,_ in decode_branches(code)))
        for i,_,_,_,dest in decode_branches(code):
            self.assertTrue(0<=dest<len(w),f"Unbounded branch @{i}")

    def test_only_matched_story_uses_transient_callee_saved_register(self):
        for _,y in STORY_CALLS:
            enhanced=comment_text_helper(y)
            accepted=accepted_helper(y)
            self.assertGreater(len(enhanced),len(accepted))
            words=struct.unpack("<"+"I"*(len(enhanced)//4),enhanced)
            self.assertIn(0xAFB70010,words) # save s7 only to wrapper's own stack
            self.assertIn(0x8FB70010,words) # restore on all normal exits
            self.assertEqual(1,words.count(0xAFB70010))
            self.assertEqual(1,words.count(0x8FB70010))
            self.assertEqual(1,words.count(_jal(0x189E40)))
            self.assertEqual((0x03E00008,0),words[-2:])
            for i,_,_,_,dest in decode_branches(enhanced):
                self.assertTrue(0<=dest<len(words),f"Unbounded branch @{i}")
            # Marker is set in matched path only, and never in original/other.
            self.assertIn(0x3C170000|(COMMENT_ONLY_MARKER>>16),words)
            self.assertIn(0x36F70000|(COMMENT_ONLY_MARKER&0xffff),words)
            self.assertEqual(HORIZONTAL_SCALE,0.40)

    @unittest.skipUnless(APPROVED.exists() and PROPOSED.exists(),"generated private ELF fixtures unavailable")
    def test_only_3_original_JALs_and_segment_length_changed(self):
        before=APPROVED.read_bytes()
        current=PROPOSED.read_bytes()
        self.assertEqual(APPROVED_SHA256,sha(before))
        self.assertEqual(current,apply(before)[0])
        self.assertEqual(4,len(verify_bytes(current,read_lock())))
        allowed=set(range(0x64,0x68))
        for site,_ in STORY_CALLS:
            allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
        allowed.update(range(PRE_GLYPH_CALL_SITE-ELF_BIAS,PRE_GLYPH_CALL_SITE-ELF_BIAS+4))
        for site,word in ((*((site, _jal(0x189E40)) for site,_ in STORY_CALLS),
                           (PRE_GLYPH_CALL_SITE,CALL_SITE_PREIMAGE))):
            self.assertEqual(word,struct.unpack_from("<I",before,site-ELF_BIAS)[0])
            self.assertEqual(0,struct.unpack_from("<I",current,site-ELF_BIAS+4)[0])
        changed={i for i,(a,b) in enumerate(zip(before,current)) if a!=b}
        self.assertTrue(changed)
        self.assertFalse(changed-allowed)
        # Exactly same approved sprite+renderer bytes; no cloned font owner.
        for start,end in (
            (0x1660C0,0x16613C),
            (0x188AD0,0x188D88),
            (0x189E40,PRE_GLYPH_CALL_SITE),
            (PRE_GLYPH_CALL_SITE+4,0x18A080),
            (0x18CB50,0x18D350),
            (0x192400,0x192E00),
        ):
            off=start-ELF_BIAS
            self.assertEqual(before[off:end-ELF_BIAS],current[off:end-ELF_BIAS])
        self.assertIn(b"SLPM-66511",current)
        self.assertIn(b"BISLPM-66511Save",current)

    @unittest.skipUnless(PREVIOUS.exists() and PROPOSED.exists() and APPROVED.exists(),"prior private ISO fixtures unavailable")
    def test_same_approved_y_text_and_graphics_as_previous_iteration(self):
        last=PREVIOUS.read_bytes()
        current=PROPOSED.read_bytes()
        original_len=len(APPROVED.read_bytes())
        allowed=set(range(0x64,0x68))
        for site,_ in STORY_CALLS:
            allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
        allowed.update(range(PRE_GLYPH_CALL_SITE-ELF_BIAS,PRE_GLYPH_CALL_SITE-ELF_BIAS+4))
        differences=[i for i,(a,b) in enumerate(zip(last[:original_len],current[:original_len])) if a!=b]
        self.assertFalse(set(differences)-allowed)

    @unittest.skipUnless(APPROVED.exists(),"private fixture unavailable")
    def test_fail_closed_when_native_callsite_or_translation_differs(self):
        damaged=bytearray(APPROVED.read_bytes())
        damaged[PRE_GLYPH_CALL_SITE-ELF_BIAS]^=1
        with self.assertRaisesRegex(ValueError,"approved"):
            apply(bytes(damaged))


if __name__=="__main__":
    unittest.main()
