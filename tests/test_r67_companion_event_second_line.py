"""Bounded r67.14l event-only two-line native control-flow correction."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_companion_event_second_line import (
    apply,EXPECTED_K_SHA,EVENT_BRANCH_VA,EVENT_DELAY_VA,EVENT_BRANCH_NEW,
    EVENT_DELAY_NEW,EVENT_BRANCH_ORIGINAL,EVENT_DELAY_ORIGINAL,
    FIRST_ROW_STORE_VA,AFK_SECOND_ROW_STORE_VA,FIRST_ROW_STORE,
    NATIVE_NEXT_ROW_SLL_VA,NEXT_ROW_SHIFT,NATIVE_FIRST_ROW_INDEX_LOAD_VA
)
from tools.r67_chamber_story_text_only import ELF_BIAS
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.r67_chamber_runtime_probe import StateMemory,snapshot

ROOT=Path(__file__).resolve().parents[1]
K=ROOT/'local/r67-14k-generic-companion-event.elf'
L=ROOT/'local/r67-14l-native-event-second-line.elf'
SLOT=ROOT/'local/r67-14k-20261011-slot1-user-live-copy.p2s'

class UniversalEventSecondLine(unittest.TestCase):
    @unittest.skipUnless(K.exists() and L.exists(),'private exact ELF fixtures absent')
    def test_four_byte_diagnostic_changes_only_branch_and_delay_slot(self):
        original=K.read_bytes()
        self.assertEqual(sha(original),EXPECTED_K_SHA)
        modified,report=apply(original)
        self.assertEqual(modified,L.read_bytes())
        self.assertEqual(len(original),len(modified))
        self.assertEqual(report['modified_bytes'],4)
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['release_approved'])
        for va,w1,w2 in (
            (EVENT_BRANCH_VA,EVENT_BRANCH_ORIGINAL,EVENT_BRANCH_NEW),
            (EVENT_DELAY_VA,EVENT_DELAY_ORIGINAL,EVENT_DELAY_NEW),
        ):
            self.assertEqual(struct.unpack_from('<I',original,va-ELF_BIAS)[0],w1)
            self.assertEqual(struct.unpack_from('<I',modified,va-ELF_BIAS)[0],w2)
        changes={i for i,(a,b) in enumerate(zip(original,modified)) if a!=b}
        self.assertEqual(changes,{EVENT_BRANCH_VA-ELF_BIAS,
                                  EVENT_DELAY_VA-ELF_BIAS,
                                  EVENT_DELAY_VA-ELF_BIAS+2,
                                  EVENT_DELAY_VA-ELF_BIAS+3})

    @unittest.skipUnless(K.exists() and L.exists(),'private exact ELF fixtures absent')
    def test_native_flow_preserves_first_object_and_afk_continuation(self):
        before=K.read_bytes()
        after=L.read_bytes()
        for va,expected in (
            (FIRST_ROW_STORE_VA,FIRST_ROW_STORE),
            (AFK_SECOND_ROW_STORE_VA,FIRST_ROW_STORE),
            (NATIVE_NEXT_ROW_SLL_VA,NEXT_ROW_SHIFT),
            (NATIVE_FIRST_ROW_INDEX_LOAD_VA,EVENT_DELAY_NEW),
        ):
            self.assertEqual(struct.unpack_from('<I',after,va-ELF_BIAS)[0],expected)
            self.assertEqual(struct.unpack_from('<I',before,va-ELF_BIAS)[0],expected)
        # The 0x1661c8 MIPS branch targets 0x16620c, not 0x166208.
        displacement=EVENT_BRANCH_NEW&0xFFFF
        self.assertEqual(EVENT_BRANCH_VA+4+displacement*4,NATIVE_NEXT_ROW_SLL_VA)
        self.assertEqual(EVENT_DELAY_NEW,0x8602000A)  # lh v0,10(s0)
        # AFK's specialized 0x1950A0 constructor & post-constructor block,
        # all companion sprites, original renderer, AFK data and old row Y are frozen.
        for start,end in (
            (0x1661D0,0x1661C8+0x40),
            (0x1661FC,0x16620C),
            (0x16620C,0x1662EC),
            (0x1950A0,0x195200),
            (0x18CB50,0x18E1F0),
            (0x1666B0,0x166748),
        ):
            self.assertEqual(after[start-ELF_BIAS:end-ELF_BIAS],
                             before[start-ELF_BIAS:end-ELF_BIAS])

    def test_source_table_proves_simultaneous_and_sequential_dialogues_are_distinct(self):
        # (file owner offset, english) including both 2-line and two distinct records.
        a={pointer:text for rec in COMPANION_COMMENT_DATA for pointer in rec[4] for text in (rec[2],)}
        self.assertEqual(a[0x3D3438],"Make sure you're always ready")
        self.assertEqual(a[0x3D343C],"to switch into battle mode at")
        self.assertEqual(a[0x3D3638],"Get into battle mode and use")
        self.assertEqual(a[0x3D3648],"your weapons to attack!")
        self.assertEqual(0x3D343C-0x3D3438,4)  # same record, two fields
        self.assertEqual(0x3D3648-0x3D3638,16) # NEXT record, not same bubble

    @unittest.skipUnless(SLOT.exists(),'saved-frame evidence unavailable')
    def test_user_slot1_short_message_is_complete_with_no_second_source(self):
        from zipfile import ZipFile
        reader=StateMemory(SLOT)
        s=snapshot(reader)
        self.assertEqual(s['comment_index'],2)
        self.assertEqual(s['text_owners'][0]['font_origin_y'],280.0)
        self.assertEqual(s['text_owners'][0]['font_scale_x'],0.4000000059604645)
        self.assertEqual(reader.read32(0x4D33A8),0x9630BA) # "Eerie place."
        self.assertEqual(reader.read32(0x4D33AC),0x794150) # empty-second sentinel

    @unittest.skipUnless(K.exists(),'baseline ELF absent')
    def test_wrong_source_or_reapplication_refused(self):
        raw=K.read_bytes()
        with self.assertRaisesRegex(ValueError,'exact r67.14k'):
            apply(raw[:-1])
        fixed,_=apply(raw)
        with self.assertRaisesRegex(ValueError,'exact r67.14k'):
            apply(fixed)

if __name__=='__main__':unittest.main()
