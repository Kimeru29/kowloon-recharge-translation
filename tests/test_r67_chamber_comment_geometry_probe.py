"""Regression gates for the unapproved chamber-comment constructor probe.

The patch must touch only the font constructor's one instruction, append its
narrow helper, and preserve all user-approved layout owners. No screenshot of
the automatic Chamber of Lions dialogue has yet accepted this geometry.
"""
from __future__ import annotations
import struct
import unittest
from pathlib import Path
from tools.r67_chamber_comment_geometry_probe import (
    BASELINE_SHA, HOOK_VA, NEXT_VA, BIAS, ORIGINAL_HOOK, UNALTERED_DELAY_SLOT,
    OLD_X, OLD_Y, NEW_Y, NEW_X_SCALE, ins_j, make_helper, apply, sha,
)
from tools.r67_history_layout_lock import read_lock, verify_bytes

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"local/r67-12-history-compact.elf"
TARGET=ROOT/"local/r67-13-chamber-comment-diagnostic.elf"
ISO=ROOT/"local/r67-candidates/67.13-chamber-comment-geometry-diagnostic.iso"


class ChamberCommentGeometry(unittest.TestCase):
    def test_target_and_constants_are_bounded_and_float_exact(self):
        self.assertEqual((117.0,313.0),(OLD_X,OLD_Y))
        self.assertEqual((285.0,0.68),(NEW_Y,NEW_X_SCALE))
        self.assertNotEqual(NEW_Y,OLD_Y)
        self.assertTrue(0.4 < NEW_X_SCALE < 1.0)
        self.assertEqual(0x188CEC,HOOK_VA)
        self.assertEqual(0x188CF4,NEXT_VA)
        self.assertEqual(0xAE020048,ORIGINAL_HOOK)
        self.assertEqual(0xAE02004C,UNALTERED_DELAY_SLOT)

    def test_mips_helper_branch_and_jumps_preserve_original_path(self):
        data=make_helper()
        words=struct.unpack("<"+"I"*(len(data)//4),data)
        self.assertEqual(108,len(data))
        self.assertEqual(ORIGINAL_HOOK,words[0])
        self.assertEqual(ins_j(NEXT_VA),words[-2])
        self.assertEqual(0,words[-1])  # delay slot of jump
        self.assertEqual([5,5,5],[(words[n]>>26) for n in (5,9,14)])
        for n in (5,9,14):
            # A non-matching style/coordinate must branch to register restores.
            target=n+1+struct.unpack("<h",struct.pack("<H",words[n]&0xFFFF))[0]
            self.assertEqual(22,target)
            self.assertEqual(0,words[n+1])
        self.assertEqual(0x8FA80000,words[22])
        self.assertEqual(0x8FA90004,words[23])
        self.assertEqual(0x27BD0020,words[24])
        # Font parameters: 313.0f, 117.0f, 285.0f, 0.68f.
        joined=data
        for val in (0x42EA0000,0x439C8000,0x438E8000,0x3F2E147B):
            high=struct.pack("<I",0x3C000000|(9<<16)|(val>>16))
            # new Y and scale live in t0 ($8), and match values in t1 ($9)
            if val in (0x438E8000,0x3F2E147B):
                high=struct.pack("<I",0x3C080000|(val>>16))
            self.assertIn(high,joined)

    @unittest.skipUnless(SOURCE.exists() and TARGET.exists(),"private generated ELF fixtures absent")
    def test_elf_patch_is_minimal_and_history_lock_still_passes(self):
        old=SOURCE.read_bytes()
        new=TARGET.read_bytes()
        self.assertEqual(BASELINE_SHA,sha(old))
        rebuilt,meta=apply(old)
        self.assertEqual(rebuilt,new)
        self.assertEqual("0x188cec",meta["patch_site_va"])
        self.assertFalse(meta["release_approved"])
        self.assertFalse(meta["runtime_verified"])
        self.assertEqual(108,len(new)-len(old))
        allowed=set(range(0x64,0x68))|set(range(HOOK_VA-BIAS,HOOK_VA-BIAS+4))
        changes={i for i,(x,y) in enumerate(zip(old,new)) if x!=y}
        self.assertTrue(changes)
        self.assertFalse(changes-allowed)
        self.assertEqual(UNALTERED_DELAY_SLOT,struct.unpack_from("<I",new,HOOK_VA-BIAS+4)[0])
        self.assertEqual(4,len(verify_bytes(new,read_lock())))
        self.assertEqual(4,len(verify_bytes(old,read_lock())))
        self.assertEqual(old[0x3D3400:0x3D34A0],new[0x3D3400:0x3D34A0])
        for text in (b"SLPM-66511",b"BISLPM-66511Save"):
            self.assertIn(text,new)

    @unittest.skipUnless(SOURCE.exists(),"private approved ELF fixture absent")
    def test_wrong_source_elf_is_rejected(self):
        b=bytearray(SOURCE.read_bytes())
        b[HOOK_VA-BIAS]^=1
        with self.assertRaisesRegex(ValueError,"baseline checksum"):
            apply(bytes(b))

    def test_existing_user_approved_guide_is_unmodified(self):
        lock=read_lock()
        self.assertIn("USER_APPROVED",lock["status"])
        self.assertEqual(4,len(lock["locked_regions"]))
        self.assertFalse(lock["approval_scope"].startswith("all history cases"))


if __name__=="__main__":
    unittest.main()
