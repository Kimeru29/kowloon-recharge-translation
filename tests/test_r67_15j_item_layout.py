"""End-to-end helper metrics consumed by the original native quad builder."""
import struct
import unittest
from pathlib import Path

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn import mips_const as reg
from tests.r67_native_geometry import render
from tools.r67_15i_item_details import catalogue_rows
from tools import r67_15j_item_layout as layout

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'local/r67-15i-hant-text-item-details.elf'
HANDLE, PRIVATE, NODES, STACK, RET = 0x1100000, 0x1101000, 0x1110000, 0x1F08000, 0x1100800


def execute(raw, codes, hook_offset=0x1520C, *, cycle=False, action_id=0,
            target_override=None, update=False, font_descriptor=0x5D77D0,
            origin=(0.,0.), return_context=False, callback=False, lower_start=None):
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x900000)
    uc.mem_map(0x1100000, 0x100000)
    uc.mem_map(0x1F00000, 0x10000)
    uc.mem_write(0x100000, raw[0x80:0x803150])
    uc.mem_write(0x902F00, raw[0x803150:])
    target = (struct.unpack_from('<I', raw, hook_offset)[0] & 0x3FFFFFF) << 2
    if target_override is not None: target=target_override
    for va in range(target if lower_start is None else lower_start,
                    0x902F00 + len(raw) - 0x803150 - 3, 4):
        word = struct.unpack('<I', uc.mem_read(va, 4))[0]
        if word >> 26 in (0x1E, 0x1F):
            op = 55 if word >> 26 == 0x1E else 63
            uc.mem_write(va, struct.pack('<I', (word & 0x3FFFFFF) | op << 26))
    uc.mem_write(HANDLE + 0x3C, struct.pack('<I', PRIVATE))
    uc.mem_write(PRIVATE + 4, struct.pack('<I', NODES))
    uc.mem_write(PRIVATE + 0x10, struct.pack('<I', font_descriptor))
    uc.mem_write(PRIVATE + 0x14,struct.pack('<ff',*origin))
    uc.mem_write(PRIVATE + 0x48, struct.pack('<ff', 1., 1.))
    for i, word in enumerate(codes):
        node = NODES + i * 0x130
        uc.mem_write(node, struct.pack('<I', word))
        nxt = node + 0x130 if i + 1 < len(codes) else NODES if cycle else 0
        uc.mem_write(node + 0x120, struct.pack('<I', nxt))
    uc.reg_write(reg.UC_MIPS_REG_SP, STACK)
    uc.reg_write(reg.UC_MIPS_REG_RA, RET)
    uc.reg_write(reg.UC_MIPS_REG_A0,HANDLE)
    uc.reg_write(reg.UC_MIPS_REG_S2,0x1150000)
    uc.mem_write(0x1150000,struct.pack('<I',0x1151000))
    uc.reg_write(reg.UC_MIPS_REG_S0, 0x1140000)
    uc.mem_write(0x1140018, struct.pack('<I',action_id))
    if callback:
        uc.reg_write(reg.UC_MIPS_REG_A0,0x1170000)
        uc.mem_write(0x117003C,struct.pack('<I',0x1150000))
        uc.mem_write(0x1150004,struct.pack('<I',0x1170100))
        uc.mem_write(0x1170100,struct.pack('<I',HANDLE))
        uc.mem_write(0x115000C,struct.pack('<h',2))
    calls = []
    def hook(e, pc, size, data):
        if pc == RET:
            e.emu_stop()
        elif pc in (0x975A78, 0x189E40, 0x18A080):
            e.reg_write(reg.UC_MIPS_REG_V0, 0xABCD if pc==0x18A080 else HANDLE)
            e.reg_write(reg.UC_MIPS_REG_PC, e.reg_read(reg.UC_MIPS_REG_RA))
        elif pc == 0x18CB50:
            calls.append(pc)
            e.reg_write(reg.UC_MIPS_REG_PC, e.reg_read(reg.UC_MIPS_REG_RA))
        elif callback and pc in (0x1A1860,0x1A16A0,0x18AB10,0x107D60,0x18AD30):
            if pc==0x18AB10:
                e.mem_write(e.reg_read(reg.UC_MIPS_REG_A0),struct.pack('<ff',*origin))
            e.reg_write(reg.UC_MIPS_REG_V0,1 if pc==0x1A1860 else 0x1151000 if pc==0x107D60 else 0)
            e.reg_write(reg.UC_MIPS_REG_PC,e.reg_read(reg.UC_MIPS_REG_RA))
    uc.hook_add(UC_HOOK_CODE, hook)
    uc.emu_start(target, RET, count=100000)
    if uc.reg_read(reg.UC_MIPS_REG_PC) != RET:
        raise AssertionError('helper failed to return within its instruction bound')
    words = [struct.unpack('<I', uc.mem_read(NODES+i*0x130, 4))[0] for i in range(len(codes))]
    scale = struct.unpack('<ff', uc.mem_read(PRIVATE+0x48, 8))
    pitch = 18 + struct.unpack('<f', uc.mem_read(PRIVATE+0x2C, 4))[0]
    if return_context:
        return words,scale,pitch,calls,{
            'origin':struct.unpack('<ff',uc.mem_read(PRIVATE+0x14,8)),
            'return':uc.reg_read(reg.UC_MIPS_REG_V0),
            'animation_phase':struct.unpack('<h',uc.mem_read(0x115000C,2))[0],
            'animation_tracking':struct.unpack('<f',uc.mem_read(0x1150034,4))[0],
            'animation_origin':struct.unpack('<f',uc.mem_read(0x1150010,4))[0],
            'cursor_origin':struct.unpack('<f',uc.mem_read(0x115103C,4))[0]}
    return words, scale, pitch, calls


def codes_for(rows):
    codes = []
    for i, line in enumerate(rows):
        if i: codes.append(0xFFFFFF0E)
        codes.extend(0xFFFFFF0B if c in (' ', '　') else 0x1160000 for c in line)
    return codes + [0xFFFFFF0F]


class ItemLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        cls.raw, cls.report = layout.build(cls.source)

    def assert_geometry(self, rows, offset=0x1520C, width=198, height=60):
        words, (sx, sy), pitch, calls = execute(self.raw, codes_for(rows), offset)
        self.assertEqual(len(calls), 1)
        native_codes = [word if word >= 0xFFFFFF00 else ord('A') for word in words[:-1]]
        geometry = render(self.source, native_codes, scale_x=sx, scale_y=sy,
                          origin=(0., 0.), line_spacing=pitch-18)
        self.assertLessEqual(geometry.bounds.right, width + 0.001)
        self.assertLessEqual(geometry.bounds.bottom, height + 0.001)
        return sx

    def test_all_431_details_use_real_quad_geometry_inside_frame(self):
        for item_id, rows in catalogue_rows(self.source).items():
            with self.subTest(item_id=item_id):
                self.assert_geometry(rows)

    def test_all_446_official_names_fit_all_three_recipe_owners(self):
        from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA
        self.assertEqual(len(DUNGEON_ITEM_NAME_DATA), 446)
        for item_id, _, _, english, _ in DUNGEON_ITEM_NAME_DATA:
            with self.subTest(item_id=item_id):
                self.assert_geometry([english], 0x154D8, 114, 18)
        for offset in (0x155CC, 0x1563C):
            self.assert_geometry(['Hydrochloric Acid'], offset, 114, 18)

    def test_per_row_spaces_and_glyphs_are_independent(self):
        self.assert_geometry(['A' * 27, 'A A A A A A A A A A A A A A'])
        self.assertEqual(self.assert_geometry(['Short']), .5)
        self.assert_geometry(['A'] * 12)

    def test_old_recipe_terminator_skips_layout_but_new_does_not(self):
        codes = codes_for(['Hydrochloric Acid'])
        self.assertEqual(execute(self.source, codes, 0x154D8)[3], [])
        self.assertEqual(len(execute(self.raw, codes, 0x154D8)[3]), 1)

    def test_invalid_controls_and_cycles_do_not_partially_mutate_nodes(self):
        for codes, cycle in (([0xFFFFFF0B, 0xFFFFFF49, 0xFFFFFF0F], False),
                             ([0x1160000, 0xFFFFFF0B], True)):
            words, scale, _, calls = execute(self.raw, codes, cycle=cycle)
            self.assertEqual(words, codes)
            self.assertEqual(scale, (1., 1.))
            self.assertEqual(calls, [])

    def test_only_owned_calls_and_load_size_change(self):
        allowed = set(range(0x64, 0x68))
        for spans in layout.ALLOWED_SOURCE_RANGES.values():
            for lo, hi in spans: allowed.update(range(lo, hi))
        changed = {i for i, (a,b) in enumerate(zip(self.source,self.raw)) if a != b}
        self.assertFalse(changed - allowed)
        for lo, hi in ((0xDB44, 0xDB48), (0x14B58, 0x14B5C),
                       (0x18FE54, 0x18FF30)):
            self.assertEqual(self.source[lo:hi], self.raw[lo:hi])

    def test_all_new_item_actions_fit_and_accepted_bubbles_are_unchanged(self):
        from tools import r67_15j_action_layout as actions
        from tools.r67_15j_action_labels import H_ITEM_ACTIONS
        from tools.r67_15j_help_layout import frames
        self.assertEqual(frames(self.source,4,0x5e),((96,32,-29,-3),))
        raw,_=actions.build(self.raw)
        for action_id,spec in enumerate(H_ITEM_ACTIONS):
            with self.subTest(action=spec.key):
                words,(sx,sy),pitch,calls=execute(raw,codes_for([spec.english]),actions.HOOK,action_id=action_id)
                if action_id in (1,3):
                    self.assertEqual(calls,[])
                    self.assertEqual((sx,sy),(1.,1.))
                    continue
                self.assertEqual(len(calls),1)
                native_codes=[w if w>=0xFFFFFF00 else ord('A') for w in words[:-1]]
                geometry=render(self.source,native_codes,scale_x=sx,scale_y=sy,origin=(51.,6.))
                self.assertGreaterEqual(geometry.bounds.left,51.)
                self.assertLessEqual(geometry.bounds.right,117.001)
                self.assertLessEqual(geometry.bounds.bottom,27.)
        self.assertEqual(self.source[0x14B58:0x14B5c],raw[0x14B58:0x14B5c])
