"""r67.14o: exact unabridged PS4 opening without r67.14n record-header regression."""
from __future__ import annotations
import struct
import unittest
from pathlib import Path

from tools.r67_companion_event_complete_opening_only import (
    apply, BASE_SHA, FIRST_ALIAS,SECOND_ALIAS,THIRD_HEADER,THIRD_POINTER,
    EERIE_HEADER,EERIE_POINTER,DOOR_FIRST,DOOR_SECOND,ORIGINAL_POINTERS,REFLOW
)
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.localization import encode_ps2_english
from tools.startup_acceptance import verify_startup_elf
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'local/r67-14m-companion-event-stable-timing.elf'
NEW=ROOT/'local/r67-14o-keep-native-third-event.elf'

class CompleteOpeningOnly(unittest.TestCase):
    @unittest.skipUnless(OLD.exists() and NEW.exists(),"private diagnostic ELF fixtures unavailable")
    def test_unchanged_binary_except_two_opening_pointers_and_appended_wide_text(self):
        source=OLD.read_bytes();modified,report=apply(source)
        self.assertEqual(sha(source),BASE_SHA)
        self.assertEqual(modified,NEW.read_bytes())
        self.assertFalse(report['runtime_verified'])
        self.assertEqual(report['joined_visible_text'],report['official_original_sentence'])
        allow=set(range(0x64,0x68))
        for addr in (FIRST_ALIAS,SECOND_ALIAS):allow.update(range(addr,addr+4))
        actual={i for i,(a,b) in enumerate(zip(source,modified)) if a!=b}
        self.assertEqual(len(actual),7)
        self.assertFalse(actual-allow)
        self.assertEqual(struct.unpack_from('<I',modified,0x64)[0],len(modified)-ELF_SEGMENT_FO)
        for off,text in zip((FIRST_ALIAS,SECOND_ALIAS),REFLOW,strict=True):
            ptr=struct.unpack_from('<I',modified,off)[0]
            word=encode_ps2_english(text,collapse_spaces=False)+b'\0'
            idx=ELF_SEGMENT_FO+ptr-ELF_SEGMENT_VA
            self.assertEqual(modified[idx:idx+len(word)],word)
        for off,expected in ((THIRD_HEADER,1),(THIRD_POINTER,0x92D140),
                             (EERIE_HEADER,1),(EERIE_POINTER,0x9630BA),
                             (DOOR_FIRST,0x962DC8),(DOOR_SECOND,0x92D854)):
            self.assertEqual(struct.unpack_from('<I',source,off)[0],expected)
            self.assertEqual(struct.unpack_from('<I',modified,off)[0],expected)
        self.assertEqual(len(COMPANION_COMMENT_DATA),1650)
        self.assertEqual(len(COMPANION_AFK_TRANSLATIONS),600)

    @unittest.skipUnless(NEW.exists(),"candidate ELF absent")
    def test_startup_must_reject_r67_14n_header_regression_and_partial_reflow(self):
        correct=NEW.read_bytes()
        def passed(blob:bytes)->bool:
            return next(c['ok'] for c in verify_startup_elf(blob) if c['name']=='companion_hud_comments')
        self.assertTrue(passed(correct))
        for offset,new_value in ((THIRD_HEADER,0),
                                 (SECOND_ALIAS,ORIGINAL_POINTERS[1]),
                                 (EERIE_POINTER,0x92D084),
                                 (DOOR_FIRST,0)):
            broken=bytearray(correct)
            struct.pack_into('<I',broken,offset,new_value)
            self.assertFalse(passed(bytes(broken)),hex(offset))

    def test_official_transcript_preserved_and_rows_fit(self):
        english={row[0]:row[2] for row in COMPANION_COMMENT_DATA}
        self.assertEqual(
            ' '.join(REFLOW),
            ' '.join(english[v] for v in (0x3C1A70,0x3C1A88,0x3C1AA0))
        )
        self.assertEqual([len(x) for x in REFLOW],[32,36])

    @unittest.skipUnless(OLD.exists(),"source ELF absent")
    def test_wrong_source_and_double_patch_fail_closed(self):
        initial=OLD.read_bytes()
        with self.assertRaisesRegex(ValueError,"Wrong r67.14m"):
            apply(initial[:-1])
        out,_=apply(initial)
        with self.assertRaisesRegex(ValueError,"Wrong r67.14m"):
            apply(out)

if __name__=='__main__': unittest.main()
