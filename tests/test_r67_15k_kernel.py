"""Execute the emitted layout kernel, not a Python translation of its policy."""
import ctypes
import struct
import unittest

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
from unicorn import mips_const as reg
from tools.r67_15k_word_wrap import Context, fixture, invoke
from tools.r67_15k_kernel import build_kernel


class NativeKernelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code, cls.report = build_kernel(0x980000)

    def execute(self, ram, context):
        uc = Uc(UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN | UC_MODE_MIPS64)
        uc.mem_map(0, 0x2000000)
        uc.mem_write(0, bytes(ram))
        uc.mem_write(0x980000, self.code)
        uc.mem_write(0x1e00000, bytes(context))
        uc.reg_write(reg.UC_MIPS_REG_A0, 0)
        uc.reg_write(reg.UC_MIPS_REG_A1, 0x1e00000)
        uc.reg_write(reg.UC_MIPS_REG_SP, 0x1f08000)
        uc.reg_write(reg.UC_MIPS_REG_RA, 0x1f00000)
        uc.emu_start(self.report['entry_va'], 0x1f00000, count=3000000)
        self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_PC), 0x1f00000)
        result = Context.from_buffer_copy(bytes(uc.mem_read(0x1e00000, ctypes.sizeof(Context))))
        return uc, result

    def test_native_and_host_layouts_match_for_growth_grouping_and_overcapacity(self):
        cases = [(['Compressed gas grenade that is very lethal upon impact. [Blast] 20% Sprain'],
                  dict(width=198., height=60., scale=.5)),
                 (['Ancient Heracleion epitaph.', 'Strong Kirlian effect identified.',
                   '台座に固定されている。', ''],
                  dict(width=336., height=90., scale=1., space_ratio=.5)),
                 (['Long description with every word retained. ' * 8],
                  dict(width=198., height=60., scale=1.25)),
                 (['X' * 60], dict(width=198., height=60., scale=.5))]
        for paragraphs, metrics in cases:
            with self.subTest(paragraphs=paragraphs):
                ram, context, visible = fixture(paragraphs, **metrics)
                uc, native = self.execute(ram, context)
                self.assertEqual(uc.reg_read(reg.UC_MIPS_REG_V0), 1)
                self.assertEqual(invoke(ram, context), 1)
                self.assertEqual(native.factor, context.factor)
                self.assertEqual(native.rows, context.rows)
                for node, _ in visible:
                    for offset in (0x10, 0x50, 0x90, 0xd0):
                        self.assertEqual(bytes(uc.mem_read(node + offset, 8)),
                                         ram[node + offset:node + offset + 8])

    def test_relocation_is_position_independent_and_no_unresolved_symbols_remain(self):
        alternate, report = build_kernel(0x98fff0)
        self.assertEqual(len(alternate), len(self.code))
        self.assertEqual(report['unresolved_symbols'], [])
        self.assertGreater(report['relocations'], 0)
        self.assertEqual(report['stack_bytes'], 64)


if __name__ == '__main__':
    unittest.main()
