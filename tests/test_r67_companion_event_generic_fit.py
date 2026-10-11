"""Fail-closed regression for universal H_TalkBuddyTask event text layout."""
from __future__ import annotations
import struct
import unittest
from pathlib import Path
from tools.r67_companion_event_generic_fit import (
    apply, SOURCE_SHA256, WRAPPER_UNMATCHED_BRANCH_VAS, BRANCH_TO_MATCHED,
    GENERIC_FONT_ADVANCE, MAX_EVENT_CHARS, NATIVE_GLYPH_ADVANCE,
    BUBBLE_WIDTH, PADDING_EACH_SIDE, PRE_LAYOUT_FACTOR_HI_VA,
    PRE_LAYOUT_FACTOR_LO_VA
)
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_story_text_only import ELF_SEGMENT_VA,ELF_SEGMENT_FO, _float_word, _i
from tools.r67_chamber_restore_argument import RESTORE_T0_FROM_STACK,G_WRAPPERS
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud import wrap_companion_afk_text,COMPANION_AFK_WRAP_CELLS

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'local/r67-14i-restore-t0.elf'
CANDIDATE=ROOT/'local/r67-14k-generic-companion-event.elf'
OLD_J=ROOT/'local/r67-14j-glyph-x-only.elf'

class UniversalCompanionComments(unittest.TestCase):
    @unittest.skipUnless(SOURCE.exists() and CANDIDATE.exists(),'private compiled ELF fixtures unavailable')
    def test_only_two_original_unmatched_branches_and_pre_layout_scale_change(self):
        before=SOURCE.read_bytes()
        after,report=apply(before)
        self.assertEqual(sha(before),SOURCE_SHA256)
        self.assertEqual(after,CANDIDATE.read_bytes())
        self.assertEqual(len(after),len(before))
        self.assertEqual(report['changed_existing_bytes'],6)
        self.assertEqual(report['companion_event_english_lines'],1650)
        self.assertFalse(report['post_layout_glyph_node_mutation'])
        self.assertFalse(report['runtime_verified'])
        for address in WRAPPER_UNMATCHED_BRANCH_VAS:
            off=ELF_SEGMENT_FO+address-ELF_SEGMENT_VA
            self.assertEqual(struct.unpack_from('<I',before,off)[0],_i(4,0,0,15))
            self.assertEqual(struct.unpack_from('<I',after,off)[0],BRANCH_TO_MATCHED)
            self.assertEqual(struct.unpack_from('<I',before,off+4)[0],0)
            self.assertEqual(struct.unpack_from('<I',after,off+4)[0],0)
        factor=_float_word(GENERIC_FONT_ADVANCE)
        for va,expected in ((PRE_LAYOUT_FACTOR_HI_VA,_i(15,0,9,factor>>16)),
                            (PRE_LAYOUT_FACTOR_LO_VA,_i(13,9,9,factor&0xffff))):
            self.assertEqual(struct.unpack_from('<I',after,ELF_SEGMENT_FO+va-ELF_SEGMENT_VA)[0],expected)
        for site,helper in G_WRAPPERS:
            delay=ELF_SEGMENT_FO+helper+144-ELF_SEGMENT_VA
            self.assertEqual(struct.unpack_from('<I',after,delay)[0],RESTORE_T0_FROM_STACK)
        allowed={ELF_SEGMENT_FO+va-ELF_SEGMENT_VA+i for va in (*WRAPPER_UNMATCHED_BRANCH_VAS,PRE_LAYOUT_FACTOR_HI_VA,PRE_LAYOUT_FACTOR_LO_VA) for i in range(4)}
        changes={i for i,(a,b) in enumerate(zip(before,after)) if a!=b}
        self.assertTrue(changes)
        self.assertFalse(changes-allowed)

    def test_no_companion_id_or_phrase_exceptions_and_worst_case_width_fits(self):
        self.assertEqual(len(COMPANION_COMMENT_DATA),1650)
        lines=[line[2] for line in COMPANION_COMMENT_DATA]
        self.assertEqual(max(map(len,lines)),MAX_EVENT_CHARS)
        self.assertGreater(sum(len(line)>29 for line in lines),50)
        self.assertIn("Make sure you're always ready",lines)
        self.assertLess(MAX_EVENT_CHARS*NATIVE_GLYPH_ADVANCE*GENERIC_FONT_ADVANCE,
                        BUBBLE_WIDTH-2*PADDING_EACH_SIDE)
        self.assertTrue(all(line for line in lines))
        self.assertFalse(any('\n' in line or '\r' in line for line in lines))

    def test_afk_600_companion_records_remain_generically_wrapped(self):
        self.assertEqual(len(COMPANION_AFK_TRANSLATIONS),600)
        self.assertEqual(COMPANION_AFK_WRAP_CELLS,16)
        for pair in COMPANION_AFK_TRANSLATIONS:
            self.assertEqual(len(pair),2)
            for text in pair:
                rows=wrap_companion_afk_text(text)
                self.assertTrue(all(len(row)<=COMPANION_AFK_WRAP_CELLS for row in rows))
        # Repeated companion phrases are legitimate; there are 585 distinct records.
        self.assertEqual(len(set(COMPANION_AFK_TRANSLATIONS)),585)

    @unittest.skipUnless(SOURCE.exists(),'r67.14i baseline unavailable')
    def test_rejects_wrong_source_or_reapplication(self):
        source=SOURCE.read_bytes()
        with self.assertRaisesRegex(ValueError,'not verified r67.14i'):
            apply(source[:-1])
        patched,_=apply(source)
        with self.assertRaisesRegex(ValueError,'not verified r67.14i'):
            apply(patched)

    @unittest.skipUnless(SOURCE.exists() and CANDIDATE.exists(),'ELFs missing')
    def test_afk_specialized_constructors_and_already_approved_ui_unchanged(self):
        original=SOURCE.read_bytes();new=CANDIDATE.read_bytes()
        # Native AFK pretext / specialized constructor callsites and blue,
        # green/AFK metadata & original T_Buddy task native code are untouched.
        for start,end in ((0x166230,0x166290),(0x1950A0,0x195260),
                          (0x1666BC,0x16673C),(0x1661BC,0x1661C4),
                          (0x16628C,0x166294),(0x18CB50,0x18E1F0)):
            begin=start-0x100080;finish=end-0x100080
            self.assertEqual(new[begin:finish],original[begin:finish])
        # The two hook wrappers themselves remain at existing addresses/length:
        self.assertEqual(len(original),len(new))
        if OLD_J.exists():
            self.assertNotEqual(sha(new),sha(OLD_J.read_bytes()))

if __name__=='__main__':unittest.main()
