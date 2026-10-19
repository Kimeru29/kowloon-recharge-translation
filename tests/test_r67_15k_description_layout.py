import struct
import unittest
from pathlib import Path

from tools.r67_15k_description_layout import build, SOURCE_SHA256, BIAS
from tools.r67_chamber_story_text_only import _jal
from tools.r67_15k_word_wrap import fixture
from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn import mips_const as reg

ROOT = Path(__file__).resolve().parents[1]


class OwnedLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'local/r67-15j-generic-text-bounds.elf').read_bytes()
        cls.raw, cls.report = build(cls.source)

    def test_only_three_owned_calls_and_load_size_change(self):
        allowed = set(range(0x64, 0x68))
        for va in (0x11518c, 0x29acbc, 0x29badc):
            allowed.update(range(va - BIAS, va - BIAS + 4))
        changed = {i for i, (a, b) in enumerate(zip(self.source, self.raw)) if a != b}
        self.assertFalse(changed - allowed)
        self.assertEqual(struct.unpack_from('<I', self.raw, 0x29badc - BIAS)[0], _jal(0x29a520))
        self.assertEqual(self.report['source_sha256'], SOURCE_SHA256)

    def test_copied_allocator_changes_only_private_size_and_callback(self):
        start = self.report['allocator_va'] - 0x902f00 + 0x803150
        copied = self.raw[start:start + 0x2b8]
        original = self.source[0x188ad0 - BIAS:0x188d88 - BIAS]
        allowed = set(range(0x6c, 0x70)) | set(range(0x234, 0x23c))
        self.assertFalse({i for i, (a, b) in enumerate(zip(original, copied)) if a != b} - allowed)
        self.assertEqual(struct.unpack_from('<I', copied, 0x6c)[0] & 0xffff, 0x258)

    def machine(self, ram):
        uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
        uc.mem_map(0, 0x2000000)
        uc.mem_write(0, bytes(ram))
        uc.mem_write(0x100000, self.raw[0x80:0x803150])
        uc.mem_write(0x902f00, self.raw[0x803150:])
        start = 0x902f00 + len(self.source) - 0x803150
        for va in range((start + 3) & ~3, 0x902f00 + len(self.raw) - 0x803150, 4):
            word = struct.unpack('<I', uc.mem_read(va, 4))[0]
            if word >> 26 in (0x1e, 0x1f):
                opcode = 55 if word >> 26 == 0x1e else 63
                uc.mem_write(va, struct.pack('<I', (word & 0x3ffffff) | opcode << 26))
        return uc

    def test_final_callbacks_wrap_live_nodes_and_preserve_registers_and_scales(self):
        for kind in ('details', 'inspection'):
            paragraphs = ['Compressed gas grenade that is very lethal upon impact. [Blast] 20% Sprain']
            metrics = dict(width=198., height=60., scale=.5)
            if kind == 'inspection':
                paragraphs = ['Ancient Heracleion epitaph.', 'Strong Kirlian effect identified.',
                              '台座に固定されている。', '']
                metrics = dict(width=336., height=90., scale=1., space_ratio=.5)
            ram, context, visible = fixture(paragraphs, **metrics)
            handle, parent = 0x8000, 0x9000
            for index in range(context.count):
                font = context.fonts[index]
                struct.pack_into('<I', ram, handle + index * 0x100 + 0x3c, font)
                struct.pack_into('<I', ram, parent + 0x38 + index * 4, handle + index * 0x100)
                struct.pack_into('<I', ram, font + 0x254, parent)
                struct.pack_into('<ff', ram, font + 0x14, 26., 19. + index * 18.)
            uc = self.machine(ram)
            for index in range(1, 32):
                uc.reg_write(getattr(reg, f'UC_MIPS_REG_{index}'), 0x40000000 + index)
            uc.reg_write(reg.UC_MIPS_REG_A0, handle)
            uc.reg_write(reg.UC_MIPS_REG_SP, 0x1f08000)
            uc.reg_write(reg.UC_MIPS_REG_RA, 0x1f00000)
            before = [uc.reg_read(getattr(reg, f'UC_MIPS_REG_{i}')) for i in range(1, 32)]
            for _ in range(2):
                uc.emu_start(self.report[kind + '_draw_va'], 0x188420, count=3000000)
                self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_PC), 0x188420)
                self.assertEqual([uc.reg_read(getattr(reg, f'UC_MIPS_REG_{i}'))
                                  for i in range(1, 32)], before)
                for node, _char in visible:
                    x, y = struct.unpack('<ff', uc.mem_read(node + 0x10, 8))
                    right, bottom = struct.unpack('<ff', uc.mem_read(node + 0xd0, 8))
                    self.assertGreaterEqual(x, 26.)
                    self.assertGreaterEqual(y, 19.)
                    self.assertLessEqual(right, 26. + metrics['width'])
                    self.assertLessEqual(bottom, 19. + metrics['height'])
                self.assertEqual(bytes(uc.mem_read(context.fonts[0] + 0x48, 8)),
                                 struct.pack('<ff', metrics['scale'], metrics['scale']))

    def test_owned_allocator_forwards_native_arguments_and_owns_metadata(self):
        uc = self.machine(bytearray(0x2000000))
        stack, private, task, parent = 0x1f08000, 0x1100000, 0x1101000, 0x1102000
        uc.reg_write(reg.UC_MIPS_REG_SP, stack)
        uc.reg_write(reg.UC_MIPS_REG_RA, 0x1f00000)
        uc.reg_write(reg.UC_MIPS_REG_S1, parent)
        uc.reg_write(reg.UC_MIPS_REG_A0, parent + 0x500)
        uc.reg_write(reg.UC_MIPS_REG_A1, 0)
        uc.reg_write(reg.UC_MIPS_REG_A2, 0)
        uc.reg_write(reg.UC_MIPS_REG_A3, 0xff3acc13)
        values = (88., 348., 512., 448., 0., 0., 108., .25)
        for i, value in enumerate(values):
            uc.reg_write(reg.UC_MIPS_REG_F12 + i,
                         struct.unpack('<I', struct.pack('<f', value))[0])
        for offset, value in ((0, .5), (8, .75), (16, 1.)):
            uc.mem_write(stack + offset, struct.pack('<f', value))
        observed = []

        def external(engine, pc, _size, _data):
            if pc == 0x1051f0:
                self.assertEqual(engine.reg_read(reg.UC_MIPS_REG_A0), 0x258)
                engine.mem_write(private, b'\xcc' * 0x260)
                engine.reg_write(reg.UC_MIPS_REG_V0, private)
            elif pc == 0x1a1130:
                observed.append((engine.reg_read(reg.UC_MIPS_REG_A3),
                                 engine.reg_read(reg.UC_MIPS_REG_T0),
                                 engine.reg_read(reg.UC_MIPS_REG_T1)))
                engine.mem_write(task + 0x3c, struct.pack('<I', private))
                engine.reg_write(reg.UC_MIPS_REG_V0, task)
            else:
                return
            engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

        uc.hook_add(UC_HOOK_CODE, external)
        uc.emu_start(self.report['inspection_constructor_va'], 0x1f00000, count=100000)
        self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_PC), 0x1f00000)
        self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_V0), task)
        self.assertEqual(observed, [(self.report['inspection_draw_va'], 0x188a90, private)])
        self.assertEqual(struct.unpack('<2f', uc.mem_read(private + 0x14, 8)), (88., 348.))
        self.assertEqual(struct.unpack('<4f', uc.mem_read(private + 0x38, 16)), (.25, .5, .75, 1.))
        self.assertEqual(struct.unpack('<I', uc.mem_read(private + 0x254, 4))[0], parent)
        self.assertEqual(bytes(uc.mem_read(private + 0x258, 8)), b'\xcc' * 8)


if __name__ == '__main__':
    unittest.main()
