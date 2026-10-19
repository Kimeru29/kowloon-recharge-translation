"""Execute the emitted layout kernel, not a Python translation of its policy."""
import ctypes
import struct
import unittest

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
from unicorn import mips_const as reg
from tools.r67_15k_word_wrap import Context, fixture, invoke
from tools.r67_15k_kernel import audit_ee_cop1, build_kernel


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

    def test_shipped_cop1_functions_are_supported_by_the_ee_not_just_generic_mips(self):
        # EE S-format dispatch accepts CMP.F/EQ/LT/LE at 30/32/34/36, not the
        # generic signaling comparisons at 3C/3E that Unicorn also implements.
        supported = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                     0x16, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x1f,
                     0x24, 0x28, 0x29, 0x30, 0x32, 0x34, 0x36}
        bad = []
        for offset in range(0, self.report['text_size'], 4):
            word = struct.unpack_from('<I', self.code, offset)[0]
            if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 not in supported:
                bad.append((hex(0x980000 + offset), hex(word)))
        self.assertEqual(bad, [])

    def test_raw_audit_rejects_generic_comparisons_and_unsupported_formats(self):
        for word in (0x4604083c, 0x4604083e, 0x46040835, 0x46040837,
                     0x46200000, 0x46800021, 0x45040000):
            with self.subTest(word=hex(word)):
                with self.assertRaisesRegex(ValueError, 'unsupported EE COP1'):
                    audit_ee_cop1(struct.pack('<I', word), 0x980000)
        audit_ee_cop1(struct.pack('<II', 0x46040834, 0x46040836))


if __name__ == '__main__':
    unittest.main()
