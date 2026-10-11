"""r67.14q: semantic fit of just one line, all native rendering/timing frozen."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_companion_event_final_line_fit import (
    apply,SOURCE_SHA256,EXPECTED_FROZEN,ORIGINAL_LONG_LINE,FIT_LINE,FIRST_LINE,
    FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND
)
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_companion_event_final_spacing_timing import NEW_EVENT_TIMER,NEW_EVENT_ADVANCE
from tools.localization import encode_ps2_english
from tools.startup_acceptance import verify_startup_elf
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud_data import COMPANION_COMMENT_DATA

ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'local/r67-14p-final-event-spacing-timing.elf'
NEW=ROOT/'local/r67-14q-opening-final-line-fit.elf'

class ClosingLineFit(unittest.TestCase):
    @unittest.skipUnless(PREV.exists() and NEW.exists(),"Private diagnostic ELF fixtures absent")
    def test_only_one_original_dialogue_pointer_and_size_word_change(self):
        baseline=PREV.read_bytes()
        candidate,report=apply(baseline)
        self.assertEqual(sha(baseline),SOURCE_SHA256)
        self.assertEqual(candidate,NEW.read_bytes())
        self.assertEqual(report['modified_original_byte_count'],2)
        self.assertEqual(len(candidate)-len(baseline),66)
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['official_source_text_verbatim'])
        diffs={i for i,(a,b) in enumerate(zip(baseline,candidate)) if a!=b}
        self.assertEqual(diffs,{0x64,SECOND_ALIAS})
        self.assertEqual(struct.unpack_from('<I',candidate,0x64)[0],len(candidate)-ELF_SEGMENT_FO)
        for off,original in EXPECTED_FROZEN.items():
            self.assertEqual(struct.unpack_from('<I',baseline,off)[0],original)
            if off != SECOND_ALIAS:
                self.assertEqual(candidate[off:off+4],baseline[off:off+4])
        newptr=struct.unpack_from('<I',candidate,SECOND_ALIAS)[0]
        offset=ELF_SEGMENT_FO+newptr-ELF_SEGMENT_VA
        self.assertEqual(candidate[offset:offset+65],
                         encode_ps2_english(FIT_LINE,collapse_spaces=False)+b'\0')
        old_offset=ELF_SEGMENT_FO+EXPECTED_FROZEN[SECOND_ALIAS]-ELF_SEGMENT_VA
        self.assertEqual(candidate[old_offset:old_offset+73],
                         encode_ps2_english(ORIGINAL_LONG_LINE,collapse_spaces=False)+b'\0')

    def test_no_renderer_changes_or_automatic_afk_timing_regressions(self):
        self.assertEqual(len(ORIGINAL_LONG_LINE),36)
        self.assertEqual(len(FIT_LINE),len(FIRST_LINE))
        self.assertEqual(NEW_EVENT_ADVANCE,0.40)
        self.assertEqual(NEW_EVENT_TIMER,240)
        self.assertEqual(len(COMPANION_COMMENT_DATA),1650)
        self.assertEqual(len(COMPANION_AFK_TRANSLATIONS),600)
        self.assertTrue(FIT_LINE.startswith('switch into battle mode'))
        self.assertTrue(FIT_LINE.endswith('anytime.'))

    @unittest.skipUnless(NEW.exists(),"Diagnostic candidate ELF absent")
    def test_acceptance_allows_only_exact_shortening_and_existing_native_headers(self):
        correct=NEW.read_bytes()
        def valid(data:bytes)->bool:
            return next(x['ok'] for x in verify_startup_elf(data) if x['name']=='companion_hud_comments')
        self.assertTrue(valid(correct))
        for addr,value in ((THIRD_HEADER,0),(THIRD_POINTER,0),(EERIE_POINTER,0),
                           (DOOR_FIRST,0),(SECOND_ALIAS,0)):
            bad=bytearray(correct)
            struct.pack_into('<I',bad,addr,value)
            self.assertFalse(valid(bytes(bad)),hex(addr))

    @unittest.skipUnless(PREV.exists(),"Exact approved source unavailable")
    def test_reject_unknown_sources_and_reapplication(self):
        data=PREV.read_bytes()
        with self.assertRaisesRegex(ValueError,'Wrong r67.14p'):
            apply(data[:-1])
        altered,_=apply(data)
        with self.assertRaisesRegex(ValueError,'Wrong r67.14p'):
            apply(altered)

if __name__=='__main__':unittest.main()
