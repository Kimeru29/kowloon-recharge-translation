"""Regression gates for r67.14d pre-layout scale for Chamber of Lions.

Verifies that ONLY the native text routine's ctor call is cloned/redirected,
not bubble graphics or common font constructor. Exact source script pointers
remain the only eligible messages, with approved Y/X anchors unchanged.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import struct
import unittest

from tools.r67_chamber_story_pre_layout import (
    apply, make_pre_layout_constructor, make_story_dispatch,
    _check_relocatable_native_function, CLONE_SOURCE_VA, CLONE_END_VA,
    CTOR_JAL_VA, CTOR_JAL_ORIGINAL, FONT_CTOR_VA, ORIGINAL_RENDERER_VA,
    APPROVED_SHA256, APPROVED_POINTERS, SCRIPT_POINTER_OFFSETS,
    STORY_CALLS, HORIZONTAL_SCALE, SHORT_MESSAGE_X, ELF_BIAS, _float_word, _jal
)
from tools.r67_history_layout_lock import read_lock, verify_bytes

ROOT=Path(__file__).resolve().parents[1]
APPROVED=ROOT/"local/r67-12-history-compact.elf"
REFINED=ROOT/"local/r67-14d-chamber-prelayout.elf"
PREVIOUS=ROOT/"local/r67-14c-chamber-story-only.elf"

class ChamberPreLayout(unittest.TestCase):
    def test_scalar_and_y_coordinates_are_preserved(self):
        self.assertEqual(0.40,HORIZONTAL_SCALE)
        self.assertEqual((280.0,300.0),tuple(y for _,y in STORY_CALLS))
        self.assertEqual(205.0,SHORT_MESSAGE_X)
        self.assertEqual(3,len(APPROVED_POINTERS))

    def test_constructor_wrapper_forwards_native_stack_arguments_and_scales_early(self):
        payload=make_pre_layout_constructor()
        words=struct.unpack("<"+"I"*(len(payload)//4),payload)
        # Stack arguments to original constructor come from old caller's SP
        # +0,+8,+16. Wrapper must preserve all 3, NOT shift them.
        self.assertEqual(0x27bdffc0,words[0]) # addiu sp,-64
        self.assertEqual(0xafbf0020,words[1]) # sw ra,+32(sp)
        for i,n in enumerate((0,8,16)):
            self.assertEqual(0x8fa80040+(n),words[2+2*i])
            self.assertEqual(0xafa80000+(n),words[3+2*i])
        self.assertEqual(_jal(FONT_CTOR_VA),words[8])
        self.assertEqual(0,words[9])
        self.assertIn(0xac480048,words) # sw t0,0x48(v0)
        # scale is float 0.40, never touches object +0x4c (Y scale).
        self.assertNotIn(0xac48004c,words)
        self.assertEqual((0x03e00008,0),words[-2:])
        scale_word=_float_word(HORIZONTAL_SCALE)
        self.assertIn(0x3c080000|(scale_word>>16),words)
        self.assertIn(0x35080000|(scale_word&0xffff),words)

    @unittest.skipUnless(APPROVED.exists(),"private executable fixture unavailable")
    def test_cloned_native_renderer_is_relocatable_with_single_ctor_jal(self):
        approved=APPROVED.read_bytes()
        source=_check_relocatable_native_function(approved)
        self.assertEqual(576,len(source))
        self.assertEqual(CTOR_JAL_ORIGINAL,struct.unpack_from("<I",source,CTOR_JAL_VA-CLONE_SOURCE_VA)[0])
        produced,meta=apply(approved)
        clone_va=int(meta["cloned_native_text_renderer_va"],16)
        clone_file=clone_va-0x902f00+0x803150
        clone=produced[clone_file:clone_file+len(source)]
        changed=[i for i,(x,y) in enumerate(zip(source,clone)) if x!=y]
        self.assertTrue(changed)
        self.assertTrue(all(CTOR_JAL_VA-CLONE_SOURCE_VA<=i<CTOR_JAL_VA-CLONE_SOURCE_VA+4 for i in changed))
        ctor_va=int(meta["ctor_wrapper_va"],16)
        self.assertEqual(_jal(ctor_va),struct.unpack_from("<I",clone,CTOR_JAL_VA-CLONE_SOURCE_VA)[0])
        self.assertEqual(source[CTOR_JAL_VA-CLONE_SOURCE_VA+4:],
                         clone[CTOR_JAL_VA-CLONE_SOURCE_VA+4:])
        self.assertEqual(source[:CTOR_JAL_VA-CLONE_SOURCE_VA],
                         clone[:CTOR_JAL_VA-CLONE_SOURCE_VA])

    @unittest.skipUnless(APPROVED.exists() and REFINED.exists(),"private executable fixture unavailable")
    def test_existing_approved_elf_and_comment_only_callsite_patch(self):
        original=APPROVED.read_bytes()
        new=REFINED.read_bytes()
        self.assertEqual(APPROVED_SHA256,hashlib.sha256(original).hexdigest())
        rebuilt,meta=apply(original)
        self.assertEqual(rebuilt,new)
        self.assertEqual(meta["output_sha256"],hashlib.sha256(new).hexdigest())
        self.assertFalse(meta["runtime_approved"])
        self.assertTrue(meta["preserved_bubble_and_background"])
        permitted=set(range(0x64,0x68))
        for site,_ in STORY_CALLS:
            off=site-ELF_BIAS
            permitted.update(range(off,off+4))
            self.assertNotEqual(original[off:off+4],new[off:off+4])
            self.assertEqual(original[off+4:off+8],new[off+4:off+8])
        touched=[i for i,(x,y) in enumerate(zip(original,new)) if x!=y]
        self.assertTrue(touched)
        self.assertFalse(set(touched)-permitted)
        for off,ptr in zip(SCRIPT_POINTER_OFFSETS,APPROVED_POINTERS,strict=True):
            self.assertEqual(ptr,struct.unpack_from("<I",new,off)[0])
        # Shared renderer, the shared font ctor, two screen backing resources
        # and all approved history regions have zero changed original bytes.
        for begin,end in (
            (CLONE_SOURCE_VA,CLONE_END_VA),
            (FONT_CTOR_VA,0x188D88),
            (0x1660C0,0x16613C),
        ):
            before=begin-ELF_BIAS
            after=end-ELF_BIAS
            self.assertEqual(original[before:after],new[before:after])
        self.assertEqual(4,len(verify_bytes(new,read_lock())))

    @unittest.skipUnless(PREVIOUS.exists() and REFINED.exists(),"private fixture unavailable")
    def test_new_variant_does_not_modify_previously_approved_existing_bytes(self):
        older=PREVIOUS.read_bytes()
        updated=REFINED.read_bytes()
        self.assertGreater(len(updated),len(older))
        # Only the 2 original callsite JALs can differ in the common region.
        allowed=set()
        for site,_ in STORY_CALLS:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
        # ELF load length changes due to the distinct append-only helper.
        allowed.update(range(0x64,0x68))
        approved_length=len(APPROVED.read_bytes())
        # Both variants have independent append-only payloads. Compare only
        # the pre-existing approved ELF region, never two different tails.
        changed=[i for i,(a,b) in enumerate(zip(older[:approved_length],updated[:approved_length])) if a!=b]
        self.assertFalse(set(changed)-allowed)

    @unittest.skipUnless(APPROVED.exists(),"private executable fixture unavailable")
    def test_wrong_original_data_fails_closed(self):
        source=bytearray(APPROVED.read_bytes())
        source[0x6623c]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            apply(bytes(source))

if __name__=="__main__":
    unittest.main()
