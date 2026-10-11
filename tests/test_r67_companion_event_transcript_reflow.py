"""r67.14n: official PS4 transcript completeness and frozen generic renderer."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_companion_event_transcript_reflow import (
    reflow, SOURCE_SHA256, FIRST_FIELD_PTR,SECOND_FIELD_PTR,
    THIRD_RECORD_HEADER,THIRD_RECORD_TEXT_PTR,
    DOOR_FIRST_FIELD_PTR,DOOR_SECOND_FIELD_PTR,
    EXPECTED,FIRST_TEXT,SECOND_TEXT,OFFICIAL_DOOR,LINE_LIMIT
)
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_VA
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.localization import encode_ps2_english
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.startup_acceptance import verify_startup_elf

ROOT=Path(__file__).resolve().parents[1]
M=ROOT/'local/r67-14m-companion-event-stable-timing.elf'
N=ROOT/'local/r67-14n-complete-companion-event-text.elf'

class TranscriptReflow(unittest.TestCase):
    @unittest.skipUnless(M.exists() and N.exists(), "private compiled ELFs missing")
    def test_exact_three_pointer_overlays_plus_single_record_absence_only(self):
        source=M.read_bytes()
        self.assertEqual(sha(source),SOURCE_SHA256)
        output,report=reflow(source)
        self.assertEqual(output,N.read_bytes())
        self.assertFalse(report['runtime_approved'])
        self.assertFalse(report['release_approved'])
        self.assertGreater(len(output),len(source))
        self.assertEqual(struct.unpack_from('<I',output,0x64)[0],
                         len(output)-ELF_SEGMENT_FO)
        changes={i for i,(a,b) in enumerate(zip(source,output)) if a!=b}
        allowed=set(range(0x64,0x68))
        for addr in (FIRST_FIELD_PTR,SECOND_FIELD_PTR,THIRD_RECORD_HEADER,DOOR_FIRST_FIELD_PTR):
            allowed.update(range(addr,addr+4))
        self.assertTrue(changes)
        self.assertFalse(changes-allowed)
        self.assertEqual(struct.unpack_from('<I',output,THIRD_RECORD_HEADER)[0],0)
        self.assertEqual(struct.unpack_from('<I',output,THIRD_RECORD_TEXT_PTR)[0],EXPECTED[THIRD_RECORD_TEXT_PTR])
        self.assertEqual(struct.unpack_from('<I',output,DOOR_SECOND_FIELD_PTR)[0],EXPECTED[DOOR_SECOND_FIELD_PTR])
        for ptr,text in ((FIRST_FIELD_PTR,FIRST_TEXT),(SECOND_FIELD_PTR,SECOND_TEXT),
                         (DOOR_FIRST_FIELD_PTR,OFFICIAL_DOOR)):
            va=struct.unpack_from('<I',output,ptr)[0]
            off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
            body=encode_ps2_english(text,collapse_spaces=False)+b'\0'
            self.assertEqual(output[off:off+len(body)],body)
            self.assertLessEqual(len(text),LINE_LIMIT)

    def test_complete_original_english_message_is_preserved_verbatim(self):
        source={v[0]:v[2] for v in COMPANION_COMMENT_DATA}
        joined=' '.join(source[v] for v in (0x3C1A70,0x3C1A88,0x3C1AA0))
        self.assertEqual(' '.join((FIRST_TEXT,SECOND_TEXT)),joined)
        self.assertEqual(source[0x3C1F38],OFFICIAL_DOOR)
        self.assertEqual(source[0x3C1F50],'unlocked now.')
        self.assertEqual(len(COMPANION_COMMENT_DATA),1650)
        self.assertEqual(len(COMPANION_AFK_TRANSLATIONS),600)
        self.assertEqual(len(FIRST_TEXT),32)
        self.assertEqual(len(SECOND_TEXT),36)

    @unittest.skipUnless(N.exists(), "private candidate ELF missing")
    def test_startup_accepts_complete_reflow_but_rejects_partial_transcript(self):
        data=N.read_bytes()
        checks={item['name']:item['ok'] for item in verify_startup_elf(data)}
        self.assertTrue(checks['companion_hud_comments'])
        broken=bytearray(data)
        struct.pack_into('<I',broken,THIRD_RECORD_HEADER,1)
        checks={item['name']:item['ok'] for item in verify_startup_elf(bytes(broken))}
        self.assertFalse(checks['companion_hud_comments'])
        broken=bytearray(data)
        struct.pack_into('<I',broken,SECOND_FIELD_PTR,EXPECTED[SECOND_FIELD_PTR])
        checks={item['name']:item['ok'] for item in verify_startup_elf(bytes(broken))}
        self.assertFalse(checks['companion_hud_comments'])

    @unittest.skipUnless(M.exists(), "verified r67.14m source ELF missing")
    def test_wrong_base_and_reapplication_fail_closed(self):
        src=M.read_bytes()
        with self.assertRaisesRegex(ValueError,'Wrong r67.14m'):
            reflow(src[:-1])
        result,_=reflow(src)
        with self.assertRaisesRegex(ValueError,'Wrong r67.14m'):
            reflow(result)

if __name__=='__main__':unittest.main()
