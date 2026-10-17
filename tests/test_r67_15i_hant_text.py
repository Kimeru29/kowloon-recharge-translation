"""Exercise HANT with live caller state and the actual position setters."""
import struct
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn import mips_const as reg
from tools.r67_15i_hant_text import build

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'local/r67-15h-details-transition-diagnostic.elf'
BIAS = 0xFFF80
OWNER, PRIVATE, STACK, RET = 0x1100000, 0x1101000, 0x1F08000, 0x1100800
HANDLES = [0x1120000 + i * 0x1000 for i in range(19)]


def run_viewport(raw, count=19, scroll=40, incoming=(79, 0x27), nulls=(), mode=4):
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x900000)
    uc.mem_map(0x1100000, 0x100000)
    uc.mem_map(0x1F00000, 0x10000)
    uc.mem_write(0x100000, raw[0x80:0x803150])
    uc.mem_write(0x902F00, raw[0x803150:])
    # Preserve native stack semantics for unsupported EE SQ/LQ using 64-bit
    # SD/LD in this control-flow harness; upper EE lanes are not claimed here.
    for va in range(0x28FD60, 0x28FF08, 4):
        w = struct.unpack('<I', uc.mem_read(va, 4))[0]
        if w >> 26 in (0x1E, 0x1F):
            op = 55 if w >> 26 == 0x1E else 63
            uc.mem_write(va, struct.pack('<I', (w & 0x3FFFFFF) | op << 26))
    uc.mem_write(OWNER + 0x3C, struct.pack('<I', PRIVATE))
    uc.mem_write(PRIVATE + 0x1A78, struct.pack('<I', count & 0xFFFFFFFF))
    uc.mem_write(PRIVATE + 0x17E0, struct.pack('<HHI', 5, 0xA55A, mode))
    for i, handle in enumerate(HANDLES):
        uc.mem_write(PRIVATE + 0x1A94 + i * 4, struct.pack('<I', 0 if i in nulls else handle))
        uc.mem_write(handle + 0x3C, struct.pack('<I', handle + 0x100))
    for i in range(min(max(count, 0), 80)):
        uc.mem_write(PRIVATE + 0x120 + i * 0x48,
                     struct.pack('<ff', 64, 131 + 16*i - scroll) + f'row-{i}\0'.encode())
    for name, value in [('A0', OWNER), ('SP', STACK), ('RA', RET),
                        ('S4', incoming[0]), ('S5', incoming[1])]:
        uc.reg_write(getattr(reg, 'UC_MIPS_REG_' + name), value)
    calls, row_reads, faults = [], [], []

    def hook(e, pc, size, data):
        ra = e.reg_read(reg.UC_MIPS_REG_RA)
        a0 = e.reg_read(reg.UC_MIPS_REG_A0)
        if pc == RET:
            e.emu_stop()
        elif pc in (0x28FDF4, 0x28FDF8):
            row_reads.append(pc)
        elif pc == 0x1A1860:
            e.reg_write(reg.UC_MIPS_REG_V0, int(a0 in HANDLES))
            e.reg_write(reg.UC_MIPS_REG_PC, ra)
        elif pc in (0x18AAB0, 0x18AAE0):
            # Execute the REAL setters, including a0 -> private dereference.
            if a0 not in HANDLES:
                faults.append(a0)
                e.emu_stop()
        elif pc == 0x18CB50:
            # Only geometry generation is outside this viewport test.
            e.reg_write(reg.UC_MIPS_REG_PC, ra)
        elif pc == 0x18A080:
            if ra != 0x28FDC4:
                a1 = e.reg_read(reg.UC_MIPS_REG_A1)
                calls.append((a0, bytes(e.mem_read(a1, 16)).split(b'\0')[0]))
            e.reg_write(reg.UC_MIPS_REG_A0, 0xDEAD)
            e.reg_write(reg.UC_MIPS_REG_V0, 0xBAD)
            e.reg_write(reg.UC_MIPS_REG_PC, ra)
        elif pc == 0x1C66D0:
            raise AssertionError('unexpected native assertion')
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(0x28FD60, 0x28FF08, count=30000)
    return uc, calls, row_reads, faults


@unittest.skipUnless(SOURCE.exists(), 'Requires local 15h ELF')
class HantTextTests(unittest.TestCase):
    def test_live_caller_registers_do_not_hide_menu_rows(self):
        raw, _ = build(SOURCE.read_bytes())
        _uc, calls, _reads, faults = run_viewport(raw)
        self.assertEqual(faults, [])
        self.assertEqual([text for _handle, text in calls], [f'row-{i}'.encode() for i in range(19)])

    def test_actual_x_setter_preserves_handle_for_y_setter(self):
        raw, _ = build(SOURCE.read_bytes())
        _uc, calls, _reads, faults = run_viewport(raw, incoming=(0, 0))
        self.assertEqual(faults, [])
        self.assertEqual(len(calls), 19)

    def test_original_15h_reproduces_both_regressions(self):
        _, calls, _, faults = run_viewport(SOURCE.read_bytes())
        self.assertEqual(calls, [])
        _, _, _, faults = run_viewport(SOURCE.read_bytes(), incoming=(0,0))
        self.assertEqual(faults, [HANDLES[0]+0x100])

    def test_all_modes_and_caller_state_preserve_native_output(self):
        raw, _ = build(SOURCE.read_bytes())
        for mode in range(8):
            for incoming in [(79,39),(0x1120000,0x1101000),(0,0),(-1 & 0xFFFFFFFF,19)]:
                with self.subTest(mode=mode,incoming=incoming):
                    uc, calls, _, faults = run_viewport(raw, incoming=incoming, mode=mode)
                    self.assertEqual(faults, [])
                    self.assertEqual(len(calls), 19)
                    self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_S4), incoming[0])
                    self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_S5), incoming[1])
                    self.assertEqual(bytes(uc.mem_read(PRIVATE+0x17E0,8)),struct.pack('<HHI',5,0xA55A,mode))
                    for i,handle in enumerate(HANDLES):
                        self.assertEqual(struct.unpack('<ff',uc.mem_read(handle+0x114,8)),(64.0,91.0+16*i))

    def test_empty_and_malformed_counts_never_read_row_coordinates(self):
        raw, _ = build(SOURCE.read_bytes())
        for count in (0,81,0xFFFFFFFF):
            _, calls, reads, faults = run_viewport(raw,count=count)
            self.assertEqual((calls,reads,faults),([],[],[]))

    def test_scroll_sweeps_null_slots_and_all_valid_counts(self):
        raw, _ = build(SOURCE.read_bytes())
        for count in (1,16,17,19,34,55,70,80):
            for scroll in range(0, max(1, count*16), 5):
                nulls = (3,17)
                _, calls, _, faults = run_viewport(raw,count=count,scroll=scroll,nulls=nulls)
                visible=[i for i in range(count) if 89<131+16*i-scroll<383]
                expected=[f'row-{i}'.encode() for slot,i in enumerate(visible) if slot not in nulls]
                self.assertEqual(faults,[])
                self.assertEqual([text for _,text in calls],expected)
