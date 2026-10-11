"""Regression tests: text-only correction for the Chamber of Lions comment."""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256,APPROVED_POINTERS,SCRIPT_POINTER_OFFSETS,ELF_BIAS,STORY_CALLS,
    ORIGINAL_JAL,ORIGINAL_RENDERER_VA,HORIZONTAL_SCALE,SHORT_MESSAGE_X,
    _float_word,_jal,make_helper,apply,
)
from tools.r67_history_layout_lock import read_lock,verify_bytes

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-12-history-compact.elf"
PROBE=ROOT/"local/r67-14c-chamber-story-only.elf"


class ChamberStoryTextOnly(unittest.TestCase):
    def test_screen_safe_layout_for_all_three_full_official_strings(self):
        full_sentences=(
            "Make sure you're always ready",
            "to switch into battle mode at",
            "any time.",
        )
        self.assertEqual([29,29,9],[len(line) for line in full_sentences])
        for line in full_sentences:
            native_width=len(line)*16*HORIZONTAL_SCALE
            self.assertLessEqual(native_width,264.0)
        # Accepted native green group2 frame: body y=269..349;
        # two glyph lines have comfortable upper/lower clearance.
        self.assertGreaterEqual(STORY_CALLS[0][1],269+7)
        self.assertLess(STORY_CALLS[1][1]+16,349-6)
        self.assertEqual((280.0,300.0),tuple(v for _,v in STORY_CALLS))
        self.assertEqual(205.0,SHORT_MESSAGE_X)
        self.assertEqual(0.40,HORIZONTAL_SCALE)

    def test_byte_exact_local_helpers_have_explicit_source_pointer_checks(self):
        for _,y in STORY_CALLS:
            code=make_helper(y)
            self.assertEqual(204,len(code))
            words=struct.unpack("<"+("I"*(len(code)//4)),code)
            self.assertEqual((0x03e00008,0),words[-2:]) # jr ra; nop
            self.assertIn(_jal(ORIGINAL_RENDERER_VA),words)
            self.assertIn(0x8C48003C,words)  # lw t0,0x3c(v0)
            self.assertIn(0xAD090048,words)  # sw t1,0x48(t0)
            self.assertIn(_float_word(HORIZONTAL_SCALE)&0xFFFF,
                          tuple(w&0xffff for w in words))
            self.assertIn(_float_word(y)>>16,tuple(w&0xffff for w in words))
            for p in APPROVED_POINTERS:
                self.assertIn(p>>16,tuple(w&0xffff for w in words))
                self.assertIn(p&0xffff,tuple(w&0xffff for w in words))
            # Every static PC-relative branch must stay within its own helper.
            for index,w in enumerate(words):
                op=w>>26
                if op in (4,5):
                    immediate=struct.unpack("<h",struct.pack("<H",w&0xffff))[0]
                    dest=index+1+immediate
                    self.assertGreaterEqual(dest,0)
                    self.assertLess(dest,len(words))

    @unittest.skipUnless(BASE.exists() and PROBE.exists(),"private generated ELF fixtures not mounted")
    def test_only_two_story_callsites_and_ptload_header_change(self):
        before=BASE.read_bytes()
        after=PROBE.read_bytes()
        assert hashlib.sha256(before).hexdigest()==APPROVED_SHA256
        generated,meta=apply(before)
        self.assertEqual(generated,after)
        self.assertEqual(meta["new_elf_sha256"],hashlib.sha256(after).hexdigest())
        self.assertEqual(408,len(after)-len(before))
        self.assertFalse(meta["runtime_verified"])
        self.assertFalse(meta["release_approved"])
        allowed=set(range(0x64,0x68))
        for site,_ in STORY_CALLS:
            off=site-ELF_BIAS
            self.assertEqual(ORIGINAL_JAL,struct.unpack_from("<I",before,off)[0])
            self.assertEqual(0,struct.unpack_from("<I",after,off+4)[0])
            self.assertNotEqual(ORIGINAL_JAL,struct.unpack_from("<I",after,off)[0])
            allowed.update(range(off,off+4))
        changed={i for i,(a,b) in enumerate(zip(before,after)) if a!=b}
        self.assertTrue(changed)
        self.assertFalse(changed-allowed)
        for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
            self.assertEqual(ptr,struct.unpack_from("<I",after,off)[0])
        # Shared font constructor never changed, nor any pre-existing sprite.
        for start,end in ((0x188AD0-ELF_BIAS,0x188D88-ELF_BIAS),
                          (0x350B40,0x350C40),(0x380E30,0x380E60),
                          (0x3F8E1C,0x3F8E70)):
            self.assertEqual(before[start:end],after[start:end])
        self.assertEqual(4,len(verify_bytes(after,read_lock())))

    @unittest.skipUnless(PROBE.exists() and (ROOT/"local/r67-14b-chamber-story-only.elf").exists(),
                         "previous diagnostic ELF fixture absent")
    def test_refinement_changes_only_two_horizontal_font_scale_literals(self):
        previous=(ROOT/"local/r67-14b-chamber-story-only.elf").read_bytes()
        current=PROBE.read_bytes()
        self.assertEqual(len(previous),len(current))
        touched=[i for i,(x,y) in enumerate(zip(previous,current)) if x!=y]
        self.assertEqual([0x863FB8,0x863FB9,0x864084,0x864085],touched)
        # Both Y anchors, all X origins, both font objects, and both bubble
        # layers must be bit-identical to the user's nearly-approved version.
        old_word=struct.pack("<I",_float_word(0.55))
        new_word=struct.pack("<I",_float_word(HORIZONTAL_SCALE))
        for off in (0x863FB8,0x864084):
            self.assertEqual(previous[off:off+2],old_word[2:])
            self.assertEqual(current[off:off+2],new_word[2:])
            self.assertEqual(previous[off+4:off+6],old_word[:2])
            self.assertEqual(current[off+4:off+6],new_word[:2])

    @unittest.skipUnless(BASE.exists(),"private approved baseline ELF not mounted")
    def test_fail_closed_on_drift(self):
        before=bytearray(BASE.read_bytes())
        before[STORY_CALLS[0][0]-ELF_BIAS]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            apply(bytes(before))


if __name__=="__main__":
    unittest.main()
