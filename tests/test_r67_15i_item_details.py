"""Native terminal-node and full-catalogue Details regressions."""
import struct
import unittest
from pathlib import Path
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn import mips_const as reg
from tools.r67_15i_item_details import build, catalogue_rows

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'local/r67-15h-details-transition-diagnostic.elf'
HANDLE,PRIVATE,NODES,STACK,RET=0x1100000,0x1101000,0x1110000,0x1F08000,0x1100800


def run_details(raw, codes):
    uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000,0x900000)
    uc.mem_map(0x1100000,0x100000)
    uc.mem_map(0x1F00000,0x10000)
    uc.mem_write(0x100000,raw[0x80:0x803150])
    uc.mem_write(0x902F00,raw[0x803150:])
    target=(struct.unpack_from('<I',raw,0x1520C)[0]&0x3FFFFFF)<<2
    # Lower only this appended helper's SQ/LQ, preserving 64-bit lanes.
    for va in range(target,min(target+0x500,0x902F00+len(raw)-0x803150),4):
        w=struct.unpack('<I',uc.mem_read(va,4))[0]
        if w>>26 in (0x1E,0x1F):
            op=55 if w>>26==0x1E else 63
            uc.mem_write(va,struct.pack('<I',(w&0x3FFFFFF)|op<<26))
    uc.mem_write(HANDLE+0x3C,struct.pack('<I',PRIVATE))
    uc.mem_write(PRIVATE+4,struct.pack('<I',NODES))
    uc.mem_write(PRIVATE+0x48,struct.pack('<ff',0.5,0.5))
    for i,word in enumerate(codes):
        node=NODES+i*0x130
        uc.mem_write(node,struct.pack('<I',word))
        uc.mem_write(node+0x120,struct.pack('<I',node+0x130 if i+1<len(codes) else 0))
    uc.reg_write(reg.UC_MIPS_REG_SP,STACK)
    uc.reg_write(reg.UC_MIPS_REG_RA,RET)
    calls=[]
    def hook(e,pc,size,data):
        if pc==RET: e.emu_stop()
        elif pc==0x975A78:
            # Upstream sparse-pointer selection/constructor is unchanged.
            e.reg_write(reg.UC_MIPS_REG_V0,HANDLE)
            e.reg_write(reg.UC_MIPS_REG_PC,e.reg_read(reg.UC_MIPS_REG_RA))
        elif pc==0x18CB50:
            # REAL scale setter writes the fields; only GPU geometry is omitted.
            calls.append(e.reg_read(reg.UC_MIPS_REG_A0))
            e.reg_write(reg.UC_MIPS_REG_V0,0xDEAD)
            e.reg_write(reg.UC_MIPS_REG_PC,e.reg_read(reg.UC_MIPS_REG_RA))
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(target,RET,count=20000)
    words=[struct.unpack('<I',uc.mem_read(NODES+i*0x130,4))[0] for i in range(len(codes))]
    return uc,words,calls


class DetailsTests(unittest.TestCase):
    def test_native_end_node_does_not_abort_layout(self):
        raw,_=build(SOURCE.read_bytes())
        uc,words,calls=run_details(raw,[0x1160000,0xFFFFFF0B,0x1160000,0xFFFFFF0F])
        self.assertEqual(calls,[PRIVATE])
        self.assertEqual(words,[0x1160000,0xFFFFFF0A,0x1160000,0xFFFFFF0F])
        self.assertEqual(struct.unpack('<f',uc.mem_read(PRIVATE+0x2C,4))[0],-9)

    def test_real_glyph_pointer_low_bytes_are_not_control_codes(self):
        raw,_=build(SOURCE.read_bytes())
        _,words,calls=run_details(raw,[0x11FFF00,0xFFFFFF0B,0xFFFFFF0F])
        self.assertEqual(calls,[PRIVATE])
        self.assertEqual(words,[0x11FFF00,0xFFFFFF0A,0xFFFFFF0F])

    def test_old_helper_rejects_native_terminator(self):
        _,words,calls=run_details(SOURCE.read_bytes(),[0x1160000,0xFFFFFF0B,0xFFFFFF0F])
        self.assertEqual(calls,[])
        self.assertEqual(words[1],0xFFFFFF0B)

    def test_every_catalogue_description_gets_layout_and_fits(self):
        source=SOURCE.read_bytes()
        raw,report=build(source)
        rows=catalogue_rows(source)
        self.assertEqual(len(rows),431)
        witnessed=[]
        for item_id,lines in rows.items():
            codes=[]
            for index,line in enumerate(lines):
                if index: codes.append(0xFFFFFF0E)
                codes.extend(0xFFFFFF0B if c in (' ','　') else 0x1160000 for c in line)
            codes.append(0xFFFFFF0F)
            with self.subTest(item_id=item_id):
                uc,words,calls=run_details(raw,codes)
                self.assertEqual(calls,[PRIVATE])
                self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_V0),HANDLE)
                self.assertEqual(struct.unpack('<ff',uc.mem_read(PRIVATE+0x48,8)),(0.5,0.5))
                self.assertEqual(struct.unpack('<f',uc.mem_read(PRIVATE+0x2C,4))[0],-9)
                self.assertNotIn(0xFFFFFF0B,words)
                x=y=0
                for word in words:
                    if word==0xFFFFFF0F: continue
                    if word==0xFFFFFF0E: x=0;y+=9
                    else: x+=8
                    self.assertLessEqual(x,220)
                    self.assertLessEqual(y+9,60)
                if any('Ｓｈｏｔｇｕｎ' in line or 'Ｈｉｇｈ' in line for line in lines):
                    witnessed.append(item_id)
        self.assertTrue(witnessed)
        self.assertEqual(report['maximum_advance'],216)
        self.assertEqual(report['maximum_height'],54)

    def test_unknown_controls_fail_closed_and_other_ui_hooks_are_untouched(self):
        source=SOURCE.read_bytes();raw,_=build(source)
        _,words,calls=run_details(raw,[0xFFFFFF0B,0xFFFFFF49,0xFFFFFF0F])
        self.assertEqual(calls,[])
        self.assertEqual(words[0],0xFFFFFF0B)
        for offset in (0xDB44,0x14B58,0x154D8,0x155CC,0x1563C):
            self.assertEqual(raw[offset:offset+4],source[offset:offset+4])

    def test_native_parser_emits_signed_end_marker(self):
        # Execute the actual converter's termination and node-control packing.
        uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS64|UC_MODE_LITTLE_ENDIAN)
        uc.mem_map(0x100000,0x100000);uc.mem_map(0x1100000,0x1000)
        source=SOURCE.read_bytes()
        for lo,hi in ((0x195464,0x19546C),(0x192684,0x192690)):
            uc.mem_write(lo,source[lo-0xFFF80:hi-0xFFF80])
        uc.reg_write(reg.UC_MIPS_REG_S2,0x1100000)
        uc.emu_start(0x195464,0x19546C,count=2)
        code=struct.unpack('<H',uc.mem_read(0x1100000,2))[0]
        self.assertEqual(code,0xFF0F)
        uc.reg_write(reg.UC_MIPS_REG_S1,code)
        uc.emu_start(0x192684,0x192690,count=3)
        self.assertEqual(struct.unpack('<I',uc.mem_read(0x1100000,4))[0],0xFFFFFF0F)
