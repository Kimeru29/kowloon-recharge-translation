"""r67.14h: guarded horizontal-step operand; no font-object/pre-layout mutation."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_chamber_cursor_advance_only import (
    apply, cursor_step_helper, CURSOR_STEP_SITE, CURSOR_ORIGINAL_WORD,
    CURSOR_DELAY_SLOT, VERTICAL_STEP_SITE, HORIZONTAL_ADVANCE_MULTIPLIER,
)
from tools.r67_chamber_pre_glyph_font_target import (
    COMMENT_ONLY_MARKER, PRE_GLYPH_CALL_SITE, CALL_SITE_PREIMAGE,
    comment_text_helper, sha,
)
from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256, APPROVED_POINTERS, STORY_CALLS, ORIGINAL_JAL,
    HORIZONTAL_SCALE, ELF_BIAS, _jal, _float_word,
)
from tools.r67_history_layout_lock import read_lock, verify_bytes

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'local/r67-12-history-compact.elf'
CANDIDATE=ROOT/'local/r67-14h-comment-horizontal-cursor.elf'
PREVIOUS=ROOT/'local/r67-14e-chamber-pre-glyph.elf'

class CursorOnly(unittest.TestCase):
    def test_shim_is_guarded_callee_safe_and_uses_native_step_only(self):
        code=cursor_step_helper()
        words=struct.unpack('<'+'I'*(len(code)//4),code)
        self.assertEqual((0x27BDFFF0,0xAFA80000,0xE7A20004,CURSOR_ORIGINAL_WORD),words[:4])
        self.assertIn((0x3C084C49,0x35084F4E),list(zip(words,words[1:])))
        self.assertIn((0x44881000,0x46020842),list(zip(words,words[1:])))  # mtc1 t0,f2; mul.s f1,f1,f2
        self.assertIn(0x16E80005,words)  # bne s7,t0, skip multiplier
        self.assertIn(0x3C080000|(_float_word(HORIZONTAL_ADVANCE_MULTIPLIER)>>16),words)
        self.assertEqual((0xC7A20004,0x8FA80000,0x27BD0010,0x03E00008,0),words[-5:])
        self.assertNotIn(0xAD090048,words) # no font +0x48 permanent write
        self.assertNotIn(0xAE490048,words) # no outer owner mutation
        self.assertNotIn(0xE6810048,words) # no swc1 f1,+0x48(s4)
        self.assertNotIn(0x46020880,words) # f2 is only temporary

    def test_same_wrapper_approved_y_and_source_pointers(self):
        self.assertEqual([280.0,300.0],[y for _,y in STORY_CALLS])
        self.assertEqual(3,len(APPROVED_POINTERS))
        self.assertEqual(HORIZONTAL_SCALE,0.40)
        for _,y in STORY_CALLS:
            words=struct.unpack('<'+'I'*(len(comment_text_helper(y))//4),comment_text_helper(y))
            self.assertIn(_jal(0x189E40),words)
            self.assertIn(0xAFB70010,words)
            self.assertIn(0x8FB70010,words)
            self.assertEqual((0x03E00008,0),words[-2:])

    @unittest.skipUnless(BASE.exists() and CANDIDATE.exists(),'generated ELF fixtures unavailable')
    def test_candidate_reproducible_and_only_three_callsites_changed(self):
        baseline=BASE.read_bytes()
        current=CANDIDATE.read_bytes()
        self.assertEqual(APPROVED_SHA256,sha(baseline))
        self.assertEqual(current,apply(baseline)[0])
        allowed=set(range(0x64,0x68))
        for site in [CURSOR_STEP_SITE]+[site for site,_ in STORY_CALLS]:
            allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
        changed={i for i,(a,b) in enumerate(zip(baseline,current)) if a!=b}
        self.assertTrue(changed)
        self.assertFalse(changed-allowed)
        self.assertEqual(4,len(verify_bytes(current,read_lock())))
        self.assertEqual(CURSOR_ORIGINAL_WORD,struct.unpack_from('<I',baseline,CURSOR_STEP_SITE-ELF_BIAS)[0])
        self.assertEqual(CURSOR_DELAY_SLOT,struct.unpack_from('<I',current,CURSOR_STEP_SITE-ELF_BIAS+4)[0])
        self.assertEqual(CALL_SITE_PREIMAGE,struct.unpack_from('<I',current,PRE_GLYPH_CALL_SITE-ELF_BIAS)[0])
        for site,_ in STORY_CALLS:
            self.assertEqual(ORIGINAL_JAL,struct.unpack_from('<I',baseline,site-ELF_BIAS)[0])
            self.assertEqual(0,struct.unpack_from('<I',current,site-ELF_BIAS+4)[0])
        for start,end in ((0x1660C0,0x16613C),(0x188AD0,0x188D88),
                          (0x189E40,0x18A200),(0x18DFFC,CURSOR_STEP_SITE),
                          (CURSOR_STEP_SITE+4,0x18E100),(0x192400,0x192E00)):
            off=start-ELF_BIAS; stop=end-ELF_BIAS
            self.assertEqual(baseline[off:stop],current[off:stop])
        self.assertEqual(struct.unpack_from('<I',baseline,VERTICAL_STEP_SITE-ELF_BIAS)[0],
                         struct.unpack_from('<I',current,VERTICAL_STEP_SITE-ELF_BIAS)[0])
        self.assertIn(b'BISLPM-66511Save',current)

    @unittest.skipUnless(PREVIOUS.exists() and CANDIDATE.exists(),'previous visual baseline ELF unavailable')
    def test_previous_approved_bubble_y_and_text_are_identical(self):
        original=PREVIOUS.read_bytes();new=CANDIDATE.read_bytes()
        from tools.r67_chamber_cursor_advance_only import ELF_SEGMENT_FO
        # The appended helpers differ but unchanged native section and dialogue bytes do not.
        for start,end in ((0x1660B8,0x1661B8),(0x1661C4,0x166288),
                          (0x166294,0x1663B0),(0x188AD0,0x189E40),
                          (0x189EE0,0x18A600)):
            self.assertEqual(original[start-ELF_BIAS:end-ELF_BIAS],
                             new[start-ELF_BIAS:end-ELF_BIAS])

    @unittest.skipUnless(BASE.exists(),'base ELF unavailable')
    def test_rejects_non_approved_baseline_or_changed_instruction(self):
        source=bytearray(BASE.read_bytes())
        source[CURSOR_STEP_SITE-ELF_BIAS]^=1
        with self.assertRaisesRegex(ValueError,'approved'):
            apply(bytes(source))

if __name__=='__main__':unittest.main()
