"""r67.14i: fail closed on exact two private JAL delay-slot restores."""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from tools.r67_chamber_restore_argument import (
    patch, APPROVED_G_SHA256, G_WRAPPERS, JAL_BYTE_OFFSET,
    RESTORE_T0_FROM_STACK, RESTORE_T1_FROM_STACK,
)
from tools.r67_chamber_story_text_only import (
    ELF_SEGMENT_VA, ELF_SEGMENT_FO, ELF_BIAS, ORIGINAL_RENDERER_VA, _jal
)
from tools.r67_chamber_runtime_probe import StateMemory, snapshot

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"local/r67-14g-chamber-true-font.elf"
CANDIDATE=ROOT/"local/r67-14i-restore-t0.elf"
G_STATE=ROOT/"local/r67-14g-20261011-slot1-genuine-bubble-copy.p2s"

class ArgumentRestore(unittest.TestCase):
    @unittest.skipUnless(SOURCE.exists() and CANDIDATE.exists(), "private ELF fixtures missing")
    def test_restores_t0_only_before_native_renderer(self):
        original=SOURCE.read_bytes()
        result,report=patch(original)
        self.assertEqual(hashlib.sha256(original).hexdigest(),APPROVED_G_SHA256)
        self.assertEqual(result,CANDIDATE.read_bytes())
        self.assertEqual(len(result),len(original))
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["release_approved"])
        self.assertEqual(6,report["changed_existing_bytes"])
        expected=set()
        for site,va in G_WRAPPERS:
            offset=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA+JAL_BYTE_OFFSET
            expected.update((offset+4,offset+6,offset+7))
            self.assertEqual(struct.unpack_from("<3I",original,offset-4),
                             (RESTORE_T1_FROM_STACK,_jal(ORIGINAL_RENDERER_VA),0))
            self.assertEqual(struct.unpack_from("<3I",result,offset-4),
                             (RESTORE_T1_FROM_STACK,_jal(ORIGINAL_RENDERER_VA),RESTORE_T0_FROM_STACK))
            self.assertEqual(struct.unpack_from("<I",result,site-ELF_BIAS)[0],
                             _jal(va))
        changed={i for i,(a,b) in enumerate(zip(original,result)) if a!=b}
        self.assertEqual(changed,expected)
        # Both original native callers copy their source pointer t1 into t0
        # immediately before entering the wrapper.
        for site,_ in G_WRAPPERS:
            self.assertEqual(0x0120402D,struct.unpack_from("<I",result,site-ELF_BIAS-4)[0])

    @unittest.skipUnless(SOURCE.exists(), "private ELF missing")
    def test_fails_closed_on_wrong_hash_or_already_patched_version(self):
        data=SOURCE.read_bytes()
        with self.assertRaisesRegex(ValueError,"SHA-256 drift"):
            patch(data[:-1])
        result,_=patch(data)
        with self.assertRaisesRegex(ValueError,"SHA-256 drift"):
            patch(result)

    @unittest.skipUnless(G_STATE.exists(), "new saved game proof unavailable")
    def test_14g_saved_comment_was_unmatched_and_native_t0_got_last_comparison(self):
        reader=StateMemory(G_STATE)
        s=snapshot(reader)
        self.assertIn("pre-layout font-clear hook",s["instruction_fingerprint"])
        self.assertTrue(s["official_source_ptrs_match"])
        self.assertEqual(s["comment_index"],2)
        # Task record 2, row 0 script source at 0x4D33A8 = "Eerie place.",
        # NOT the last comparator 0x92D140 = "any time.".
        actual=reader.read32(0x4D33A8)
        self.assertEqual(actual,0x9630BA)
        self.assertNotEqual(actual,0x92D140)
        t=s["text_owners"][0]
        self.assertEqual(t["font_origin_y"],313.0)
        self.assertEqual(t["font_scale_x"],1.0)
        self.assertEqual([(n["x"],n["y"]) for n in t["nodes"][:3]],
                         [(117.0,313.0),(133.0,313.0),(149.0,313.0)])

if __name__=="__main__": unittest.main()
