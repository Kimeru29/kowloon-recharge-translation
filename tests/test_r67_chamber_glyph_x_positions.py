"""r67.14f regression: move only native glyph X positions for three comments.

Grounding: slot3 snapshot user supplied during original automatic comment,
font object at 0x14E4480 with 30 linked glyph/sentinel nodes. X coordinates
begin 117.0 and advance EXACTLY 16.0 native pixels per glyph. Node +0x10 is
glyph X and +0x120 next pointer; spaces and terminator have class 0xFFFFFF0B/F.
"""
from __future__ import annotations
import struct
import unittest
import zipfile
from pathlib import Path
from tools.r67_chamber_glyph_x_positions import (
    apply,compress_glyph_x,make_story_helper,sha,GLYPH_ADVANCE_FACTOR,
    ORIGINAL_GLYPH_ADVANCE, MAX_GLYPH_NODES, FONT_NODE_HEAD, GLYPH_NODE_NEXT,
    GLYPH_NODE_KIND_HIGH16,GLYPH_NODE_X,FONT_ORIGIN_X,
    cop1_arith
)
from tools.r67_chamber_story_text_only import (
    APPROVED_SHA256,STORY_CALLS,ELF_BIAS,HORIZONTAL_SCALE,_float_word
)
from tools.r67_history_layout_lock import read_lock,verify_bytes

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-12-history-compact.elf"
PRIOR=ROOT/"local/r67-14c-chamber-story-only.elf"
CURRENT=ROOT/"local/r67-14f-chamber-glyph-x.elf"
STATE=ROOT/"local/pcsx2-67.06-isolated/slot3-chamber-oldman-20261010.p2s"
EXPECTED_STATE_SHA="9372b86d139b90e0b2a3ae8215c3db8d1f3d870581d7b06a4be60bbf49e07d6a"

def branch_targets(code:bytes):
    words=struct.unpack("<"+"I"*(len(code)//4),code)
    for i,w in enumerate(words):
        if w>>26 in (4,5):
            distance=struct.unpack("<h",struct.pack("<H",w&65535))[0]
            yield i,i+1+distance

def is_native_glyph(node:bytes)->bool:
    return (struct.unpack_from("<I",node)[0]>>16)==GLYPH_NODE_KIND_HIGH16

def geometry_from_memory(memory:bytes,font_address:int):
    head=struct.unpack_from("<I",memory,font_address+FONT_NODE_HEAD)[0]
    origin=struct.unpack_from("<f",memory,font_address+FONT_ORIGIN_X)[0]
    points=[]
    for _ in range(MAX_GLYPH_NODES):
        if not head:break
        if not (0x800000<=head<len(memory)-0x124):raise ValueError("Invalid glyph pointer")
        node=memory[head:head+0x124]
        if is_native_glyph(node):
            x,y=struct.unpack_from("<2f",node,GLYPH_NODE_X)
            points.append((x,y))
        head=struct.unpack_from("<I",node,GLYPH_NODE_NEXT)[0]
    return origin,points

class ChamberGlyphX(unittest.TestCase):
    def test_native_geometry_ratio_fits_in_safe_text_body(self):
        self.assertEqual(0.40,HORIZONTAL_SCALE)
        self.assertEqual(16.0,ORIGINAL_GLYPH_ADVANCE)
        self.assertEqual(0.55,GLYPH_ADVANCE_FACTOR)
        self.assertEqual(8.8,round(ORIGINAL_GLYPH_ADVANCE*GLYPH_ADVANCE_FACTOR,2))
        # Native green speech balloon has a 288-pixel-wide body.
        # Approved 14c text left inset leaves 264 native pixels for text.
        total=28*ORIGINAL_GLYPH_ADVANCE*GLYPH_ADVANCE_FACTOR
        right_edge=total+16*HORIZONTAL_SCALE
        self.assertLess(right_edge,264.0)
        self.assertGreater(264.0-right_edge,10.0)

    def test_cop1_encodings_are_sub_mul_add_with_in_place_f4(self):
        self.assertEqual(0x46002101,cop1_arith(1,4,4,0))
        self.assertEqual(0x46022102,cop1_arith(2,4,4,2))
        self.assertEqual(0x46002100,cop1_arith(0,4,4,0))
        words=struct.unpack("<"+"I"*(len(compress_glyph_x())//4),compress_glyph_x())
        # One glyph X write only, never the neighbouring Y +0x14.
        self.assertEqual(1,words.count(0xE5440010)) # swc1 f4,0x10(t2)
        self.assertNotIn(0xE5440014,words)
        self.assertIn(0xC5440010,words) # lwc1 f4,0x10(t2)
        self.assertEqual((0x03E00008,0),words[-2:])
        self.assertEqual(0x27BDFFC0,words[0])
        self.assertEqual(0x27BD0040,words[-3])
        self.assertEqual(64,MAX_GLYPH_NODES)
        for index,target in branch_targets(compress_glyph_x()):
            self.assertTrue(0<=target<len(words),(index,target))

    def test_caller_registers_are_restored_and_original_v0_preserved(self):
        words=struct.unpack("<"+"I"*(len(compress_glyph_x())//4),compress_glyph_x())
        for reg,off in ((31,0),(9,4),(10,8),(11,12),(12,16),(13,20)):
            self.assertEqual(1,words.count((43<<26)|(29<<21)|(reg<<16)|off))
            self.assertEqual(1,words.count((35<<26)|(29<<21)|(reg<<16)|off))
        for reg,off in ((0,24),(2,28),(4,32)):
            self.assertEqual(1,words.count((57<<26)|(29<<21)|(reg<<16)|off))
            self.assertEqual(1,words.count((49<<26)|(29<<21)|(reg<<16)|off))
        self.assertFalse(any((w>>16)&31==2 and (w>>26) in (9,13,15,35,43) for w in words))

    def test_guards_and_bounded_next_link_loop(self):
        words=struct.unpack("<"+"I"*(len(compress_glyph_x())//4),compress_glyph_x())
        self.assertIn(0x8D4A0120,words) # lw t2,0x120(t2)
        self.assertIn(0x8D4C0000,words) # lw t4,(t2), glyph atlas class
        self.assertIn(0x296C0040,words) # slti t4,t3,64
        self.assertEqual(1,words.count(0xE5440010))

    def test_only_approved_text_wrapper_is_extended(self):
        for _,y in STORY_CALLS:
            content=make_story_helper(y,0x963CC0)
            word=struct.unpack("<"+"I"*(len(content)//4),content)
            self.assertEqual((0x03E00008,0),word[-2:])
            for start,target in branch_targets(content):
                self.assertTrue(0<=target<len(word),(start,target))

    @unittest.skipUnless(STATE.exists(),"isolated user save snapshot missing")
    def test_original_saved_chamber_glyphs_prove_x_advance_is_independent(self):
        self.assertEqual(EXPECTED_STATE_SHA,sha(STATE.read_bytes()))
        with zipfile.ZipFile(STATE) as z:
            memory=z.read("eeMemory.bin")
        for font in (0x14E4480,0x14E7DC0):
            origin,points=geometry_from_memory(memory,font)
            self.assertEqual(117.0,origin)
            self.assertGreaterEqual(len(points),8)
            # Skip sentinel space nodes; consecutive visible glyphs can be
            # 16 or 32 native pixels apart, proving independent position.
            gaps=[b[0]-a[0] for a,b in zip(points,points[1:])]
            self.assertTrue(all(g in (16.0,32.0) for g in gaps),gaps)
            corrected=[origin+(x-origin)*GLYPH_ADVANCE_FACTOR for x,y in points]
            self.assertLess(max(corrected)-origin+16*HORIZONTAL_SCALE,264.0)
            self.assertTrue(all(y==313.0 for x,y in points))

    @unittest.skipUnless(BASE.exists(),"native story renderer fixture unavailable")
    def test_native_glyph_builder_completes_before_story_renderer_returns(self):
        baseline=BASE.read_bytes()
        # 0x189E40 native story renderer calls 0x192400 glyph-list builder
        # synchronously at 0x18A028, then 0x190C90 / 0x18CB50 to finish,
        # and only returns at 0x18A078. The 14f helper runs AFTER return,
        # so glyph nodes are already linked and their X positions are real.
        from tools.r67_chamber_story_text_only import _jal
        def instr(va:int)->int:
            return struct.unpack_from("<I",baseline,va-ELF_BIAS)[0]
        self.assertEqual(_jal(0x192400),instr(0x18A028))
        self.assertEqual(_jal(0x190C90),instr(0x18A04C))
        self.assertEqual(_jal(0x18CB50),instr(0x18A058))
        self.assertEqual(0x03E00008,instr(0x18A078)) # jr ra
        self.assertEqual(0,instr(0x18A07C)) # delay slot nop

    @unittest.skipUnless(BASE.exists() and PRIOR.exists() and CURRENT.exists(),"generated private ELF fixtures missing")
    def test_only_two_story_callsites_modified_and_history_lock_preserved(self):
        baseline=BASE.read_bytes()
        old=PRIOR.read_bytes()
        new=CURRENT.read_bytes()
        self.assertEqual(APPROVED_SHA256,sha(baseline))
        self.assertEqual(new,apply(baseline)[0])
        approved_len=len(baseline)
        allowed=set(range(0x64,0x68))
        for site,_ in STORY_CALLS:
            allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
        self.assertFalse({i for i,(a,b) in enumerate(zip(baseline,new)) if a!=b}-allowed)
        self.assertFalse({i for i,(a,b) in enumerate(zip(old[:approved_len],new[:approved_len])) if a!=b}-allowed)
        self.assertEqual(4,len(verify_bytes(new,read_lock())))

    @unittest.skipUnless(BASE.exists(),"approved baseline fixture missing")
    def test_corrupt_input_fails_closed(self):
        damaged=bytearray(BASE.read_bytes())
        damaged[STORY_CALLS[0][0]-ELF_BIAS]^=1
        with self.assertRaisesRegex(ValueError,"Approved r67.12 ELF"):
            apply(bytes(damaged))

if __name__=="__main__":
    unittest.main()
