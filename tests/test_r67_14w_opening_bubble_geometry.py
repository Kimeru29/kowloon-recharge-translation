"""MIPS interpreter-backed r67.14w opening bubble resource restoration lock.

Unlike the previous static geometry-value tests, this runs EVERY instruction
in the private helper against disposable simulated EE game state. It checks
the actual native side effects for the targeted opening row, both slots, the
already approved Eerie line, other Chamber lines, AFK and invalid inputs.

No real PCSX2 state or memory cards are touched. This is still not visual
runtime gameplay approval.
"""
from __future__ import annotations
import struct,unittest,json
from pathlib import Path
from tools.r67_14w_restore_opening_bubble_shape import (
    apply,preimage,make_geometry_helper,
    ORIGINAL_RECONSTRUCTION_STORE_VA,ORIGINAL_RECONSTRUCTION_STORE,
    NATIVE_DELAY_SLOT_VA,NATIVE_DELAY_SLOT,NATIVE_NEXT_VA,NATIVE_NEXT_WORD,
    GREEN_STATIC_VA,BLUE_STATIC_VA,BLUE_FRAME_STRIDE,
    GREEN_NATIVE,GREEN_NATIVE_PIVOT_X,BLUE_NATIVE,BLUE_NATIVE_PIVOT_Y,
)
from tools.r67_14w_scoped_approval_lock import validate_scoped
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,_jal
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q_MANIFEST

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"local/r67-14t-lion-and-tablets.elf"
NEW=ROOT/"local/r67-14w-opening-bubble-restored.elf"
TASK=0x10000000

def s16(x):
    return x-0x10000 if x&0x8000 else x

def s32(x):
    return x-0x100000000 if x&0x80000000 else x

def execute_helper(record,subrow,slot,*,code=None):
    raw=make_geometry_helper() if code is None else code
    words=struct.unpack("<"+"I"*(len(raw)//4),raw)
    registers=[0]*32
    registers[16]=TASK # s0
    registers[3]=slot  # native lh v1,0x2f8(s0) already ran in JAL delay slot
    registers[31]=0x00ABCDEF
    registers[8]=0x1111
    registers[9]=0x2222
    registers[4]=0xDEAD
    memory={}
    halfwords={TASK+4:record,TASK+0xA:subrow,TASK+0x2f8:slot}
    memory[TASK+0x5C]=0xBAADF00D
    for selected in (0,1):
        for index in range(4):
            memory[GREEN_STATIC_VA+selected*0x30+4*index]=0x11110000+selected*16+index
    for frame in range(3):
        for index in range(4):
            memory[BLUE_STATIC_VA+frame*0x30+4*index]=0x22220000+frame*16+index
    original=dict(memory)
    pc=0
    steps=0
    while pc<len(words):
        steps+=1
        if steps>200:raise RuntimeError("MIPS helper did not terminate")
        word=words[pc];op=word>>26
        rs=(word>>21)&31;rt=(word>>16)&31
        imm=word&0xffff
        def value(n):return registers[n]&0xffffffff
        if op in (4,5):
            taken=(value(rs)==value(rt)) if op==4 else (value(rs)!=value(rt))
            if words[pc+1]!=0:raise ValueError("Branch delay slot was not NOP")
            pc=(pc+1+s16(imm)) if taken else pc+2
        elif op==33:   # lh, sign extend
            addr=value(rs)+s16(imm)
            data=halfwords[addr]
            registers[rt]=(data if data<0x8000 else data-0x10000)&0xffffffff
            pc+=1
        elif op==43:   # sw
            memory[(value(rs)+s16(imm))&0xffffffff]=value(rt)
            pc+=1
        elif op==9:    # addiu
            registers[rt]=(value(rs)+s16(imm))&0xffffffff
            pc+=1
        elif op==11:   # sltiu
            registers[rt]=int(value(rs)<(s16(imm)&0xffffffff))
            pc+=1
        elif op==15:   # lui
            registers[rt]=(imm<<16)&0xffffffff
            pc+=1
        elif op==13:   # ori
            registers[rt]=value(rs)|imm
            pc+=1
        elif op==0:
            funct=word&0x3f
            rd=(word>>11)&31
            shift=(word>>6)&31
            if funct==0 and word!=0:
                registers[rd]=(value(rt)<<shift)&0xffffffff
            elif funct==33:
                registers[rd]=(value(rs)+value(rt))&0xffffffff
            elif funct==8:
                if words[pc+1]!=0:raise ValueError("Return delay slot changed")
                return memory,original,registers,steps
            elif word:
                raise ValueError(f"Unexpected native instruction {word:#x}")
            pc+=1
        else:
            raise ValueError(f"Unexpected native opcode {op} word {word:#x}")
        registers[0]=0
    raise RuntimeError("Helper fell off end without native JR")


@unittest.skipUnless(OLD.is_file() and NEW.is_file(),"Requires ignored immutable t/w stage ELFs")
class OpeningBubbleNativeGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=OLD.read_bytes()
        cls.candidate=NEW.read_bytes()

    def test_prior_58_delta_is_horizontal_not_vertical(self):
        preimage(self.source)
        for slot,x in enumerate((172.0,230.0)):
            kind,resource,other,actual_x,actual_y=struct.unpack_from(
                "<2I3f",self.source,0x3f8e1c+20*slot)
            self.assertEqual((kind,resource,other,actual_x,actual_y),
                             (2,0x68+slot,249.0,x,346.0))
        self.assertEqual(346-GREEN_NATIVE[2],269)
        self.assertEqual((280-269,300-269),(11,31))

    def test_preexisting_approved_dialogue_Y_loads_identical_q(self):
        for va in (0x963D78,0x963E54):
            at=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
            self.assertEqual(self.source[at:at+8],self.candidate[at:at+8])

    def test_original_event_store_performed_and_native_slot_unchanged(self):
        for record,subrow,slot in ((2,1,0),(2,1,1),(2,0,0),(0,1,0),(601,0,1)):
            with self.subTest(record=record,row=subrow,slot=slot):
                modified,initial,regs,steps=execute_helper(record,subrow,slot)
                self.assertEqual(modified[TASK+0x5c],0)
                self.assertEqual(regs[3],slot)
                self.assertEqual(regs[16],TASK)
                self.assertEqual(regs[31],0xABCDEF)
                self.assertEqual((regs[8],regs[9]),(0x1111,0x2222))
                self.assertLess(steps,100)

    def test_both_companion_slots_restore_exact_original_green_shape(self):
        for slot in (0,1):
            with self.subTest(slot=slot):
                memory,original,_,_=execute_helper(2,1,slot)
                green=GREEN_STATIC_VA+slot*0x30
                self.assertEqual(
                    tuple(memory[green+i*4] for i in range(4)),
                    tuple(struct.unpack("<I",struct.pack("<f",v))[0] for v in
                          (GREEN_NATIVE[0],GREEN_NATIVE[1],GREEN_NATIVE_PIVOT_X[slot],GREEN_NATIVE[2]))
                )
                other=GREEN_STATIC_VA+(1-slot)*0x30
                self.assertEqual([memory[other+4*i] for i in range(4)],
                                 [original[other+4*i] for i in range(4)])

    def test_all_three_blue_animation_frames_restore_exact_original_shape(self):
        for slot in (0,1):
            memory,old,_,_=execute_helper(2,1,slot)
            for frame in range(3):
                at=BLUE_STATIC_VA+frame*BLUE_FRAME_STRIDE
                expected=(*BLUE_NATIVE[:3],BLUE_NATIVE_PIVOT_Y[frame])
                self.assertEqual(tuple(memory[at+4*i] for i in range(4)),
                    tuple(struct.unpack("<I",struct.pack("<f",x))[0] for x in expected))

    def test_eerie_other_chamber_afk_and_invalid_slots_do_not_touch_ui_geometry(self):
        for record,subrow,slot in (
            (2,0,0), # user-approved Eerie place.
            (2,2,1), # other Chamber subrow
            (3,1,0), # other event record
            (601,1,1),# AFK specialized text family
            (2,1,2), # out-of-range slot
            (2,1,-1),# invalid signed slot
        ):
            with self.subTest(record=record,row=subrow,slot=slot):
                memory,initial,_,_=execute_helper(record,subrow,slot)
                self.assertEqual({k:v for k,v in memory.items() if k!=TASK+0x5C},
                                 {k:v for k,v in initial.items() if k!=TASK+0x5C})

    def test_one_native_jal_replaces_only_exact_original_store(self):
        bytecode=make_geometry_helper()
        at=ORIGINAL_RECONSTRUCTION_STORE_VA-0xfff80
        start=ELF_SEGMENT_VA+(len(self.source)+3)//4*4-ELF_SEGMENT_FO
        self.assertEqual(struct.unpack_from("<I",self.candidate,at)[0],_jal(start))
        self.assertEqual(self.candidate[at+4:at+8],self.source[at+4:at+8])
        self.assertEqual(self.candidate[
            ELF_SEGMENT_FO+start-ELF_SEGMENT_VA:ELF_SEGMENT_FO+start-ELF_SEGMENT_VA+len(bytecode)
        ],bytecode)

    def test_exactly_one_q_approval_exception_and_all_t_surfaces_preserved(self):
        report=validate_scoped(self.candidate,self.source)
        self.assertEqual(report["status"],"PASS_ONE_EXACT_OPENING_EVENT_CONSTRUCTION_EXCEPTION")
        self.assertEqual(report["other_original_executable_bytes_modified"],0)
        self.assertEqual(report["lion_item_fit_scale"],0.72)
        self.assertEqual(report["all_native_stone_tablets"],58)

    def test_mutated_new_helper_or_native_event_callsite_rejected(self):
        for address in (ORIGINAL_RECONSTRUCTION_STORE_VA-0xfff80,
                        len(self.source)+4,len(self.candidate)-8):
            corrupted=bytearray(self.candidate)
            corrupted[address]^=1
            with self.subTest(at=hex(address)),self.assertRaises(ValueError):
                validate_scoped(bytes(corrupted),self.source)

    def test_unknown_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Source must be exact"):
            apply(self.candidate)

if __name__=="__main__":unittest.main()
