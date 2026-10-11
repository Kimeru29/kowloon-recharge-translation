"""r67.14m: event-only deterministic hold; native AFK path is a hard lock."""
from __future__ import annotations
import hashlib
import struct
import unittest
from pathlib import Path
from tools.r67_companion_event_stable_timing import (
    apply, timer_helper, SOURCE_SHA256, HOOK_VA, DELAY_VA,
    ORIGINAL_STATE_SETUP, ORIGINAL_STATE_STORE, ORIGINAL_SHARED_TIMER_STORE_VA,
    ORIGINAL_SHARED_TIMER_STORE, ORIGINAL_RECORD_LOAD, ORIGINAL_EVENT_CHECK,
    EVENT_DURATION_FRAMES, EVENT_BOUNDARY
)
from tools.r67_chamber_story_text_only import (
    ELF_BIAS,ELF_SEGMENT_VA,ELF_SEGMENT_FO,_jal
)
from tools.r67_chamber_runtime_probe import StateMemory
from tools.r67_chamber_pre_glyph_font_target import sha

ROOT=Path(__file__).resolve().parents[1]
L=ROOT/'local/r67-14l-native-event-second-line.elf'
M=ROOT/'local/r67-14m-companion-event-stable-timing.elf'
CAPTURE=ROOT/'local/r67-14k-20261011-slot1-user-live-copy.p2s'

class StableEventTiming(unittest.TestCase):
    @unittest.skipUnless(L.exists() and M.exists(),"private source and output ELF required")
    def test_exact_private_helper_only_and_program_header(self):
        source=L.read_bytes();candidate,report=apply(source)
        self.assertEqual(sha(source),SOURCE_SHA256)
        self.assertEqual(candidate,M.read_bytes())
        self.assertFalse(report['user_visual_approved'])
        self.assertEqual(report['event_hold_frames'],300)
        self.assertEqual(report['helper_bytes'],40)
        self.assertEqual(len(candidate)-len(source),40)
        newva=int(report['private_helper_va'],16)
        self.assertEqual(struct.unpack_from('<I',source,HOOK_VA-ELF_BIAS)[0],ORIGINAL_STATE_SETUP)
        self.assertEqual(struct.unpack_from('<I',source,DELAY_VA-ELF_BIAS)[0],ORIGINAL_STATE_STORE)
        self.assertEqual(struct.unpack_from('<I',candidate,HOOK_VA-ELF_BIAS)[0],_jal(newva))
        self.assertEqual(struct.unpack_from('<I',candidate,DELAY_VA-ELF_BIAS)[0],0)
        self.assertEqual(struct.unpack_from('<I',source,ORIGINAL_SHARED_TIMER_STORE_VA-ELF_BIAS)[0],ORIGINAL_SHARED_TIMER_STORE)
        self.assertEqual(struct.unpack_from('<I',candidate,ORIGINAL_SHARED_TIMER_STORE_VA-ELF_BIAS)[0],ORIGINAL_SHARED_TIMER_STORE)
        allowed=set(range(0x64,0x68))
        for va in (HOOK_VA,DELAY_VA): allowed.update(range(va-ELF_BIAS,va-ELF_BIAS+4))
        diffs={i for i,(a,b) in enumerate(zip(source,candidate)) if a!=b}
        self.assertFalse(diffs-allowed)
        self.assertEqual(candidate[ELF_SEGMENT_FO+newva-ELF_SEGMENT_VA:ELF_SEGMENT_FO+newva-ELF_SEGMENT_VA+40],timer_helper())

    def test_helper_has_no_afk_timer_store_when_record_id_at_or_above_boundary(self):
        instructions=struct.unpack('<'+'I'*(len(timer_helper())//4),timer_helper())
        self.assertEqual(instructions,(
            0x2402000B,  # state v0=11
            0xA6020002,  # sh v0,2(s0)
            0x86020004,  # native read task record
            0x28420259,  # slti v0,v0,0x259
            0x10400003,  # beqz v0,done, bypass timer
            0,          # delay slot
            0x2402012C,  # event hold = 300
            0xA6020008,  # event-only sh timer
            0x03E00008,0
        ))
        self.assertEqual(EVENT_BOUNDARY,0x259)
        self.assertEqual(EVENT_DURATION_FRAMES,300)
        # Static mini-flow at the checked branch and its delay slot:
        branch_idx=4
        branch_target=branch_idx+1+(instructions[branch_idx]&0xFFFF)
        self.assertEqual(branch_target,8) # AFK lands directly at jr ra
        self.assertEqual(instructions[branch_idx+1],0)
        for case in (EVENT_BOUNDARY,EVENT_BOUNDARY+1,0xFFFF):
            self.assertFalse(case<EVENT_BOUNDARY)
        for case in (0,2,50,EVENT_BOUNDARY-1):
            self.assertTrue(case<EVENT_BOUNDARY)

    def test_existing_afk_renderer_and_156_240_timer_overrides_are_locked(self):
        self.assertEqual(ORIGINAL_STATE_SETUP,0x2402000B)
        self.assertEqual(ORIGINAL_STATE_STORE,0xA6020002)
        self.assertEqual(ORIGINAL_RECORD_LOAD,0x86020004)
        self.assertEqual(ORIGINAL_EVENT_CHECK,0x28420259)
        for va,expected in ((0x1662F8,0x2402009C),
                            (0x1662FC,0xA6020008),
                            (0x166320,0x240200F0),
                            (0x166324,0xA6020008)):
            self.assertEqual(struct.unpack_from('<I',L.read_bytes(),va-ELF_BIAS)[0],expected)
            self.assertEqual(struct.unpack_from('<I',M.read_bytes(),va-ELF_BIAS)[0],expected)
        before=L.read_bytes();after=M.read_bytes()
        for start,end in (
            (0x1661D0,0x16620C),   # special AFK constructor, branch delay and return
            (0x1662A0,0x1662DC),   # specialized second constructor
            (0x1662E8,0x166340),   # native event/AFK discrimination and overrides
            (0x1950A0,0x195260),   # AFK renderer unchanged
            (0x166138,0x1661D0),   # original event records and first renderer unchanged
            (0x18CB50,0x18E1F0),   # ordinary font renderer unchanged
        ):
            self.assertEqual(before[start-ELF_BIAS:end-ELF_BIAS],
                             after[start-ELF_BIAS:end-ELF_BIAS])

    @unittest.skipUnless(CAPTURE.exists(),"archived user r67.14k state unavailable")
    def test_real_user_state_demonstrates_pointer_derived_timer(self):
        state=StateMemory(CAPTURE)
        object_ptr=state.read32(0xE11C80+0x2C)
        timer=state.read32(0xE11C80+0x8)&0xFFFF
        self.assertEqual(object_ptr,0x153053AC)
        self.assertEqual(timer,0x5399)
        self.assertEqual((object_ptr&0xFFFF)-timer,19)
        self.assertNotEqual(timer,EVENT_DURATION_FRAMES)

    @unittest.skipUnless(L.exists(),"baseline private ELF unavailable")
    def test_reapplication_and_unknown_elf_are_rejected(self):
        original=L.read_bytes()
        with self.assertRaisesRegex(ValueError,"non-approved"):
            apply(original[:-1])
        after,_=apply(original)
        with self.assertRaisesRegex(ValueError,"non-approved"):
            apply(after)

if __name__=="__main__":unittest.main()
