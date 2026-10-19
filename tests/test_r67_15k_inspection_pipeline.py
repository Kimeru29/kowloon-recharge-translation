"""Exercise real inspection strings through native nodes and draw submission."""
import struct
import unicodedata
import unittest

from unicorn import mips_const as reg
from tests.r67_native_text_pipeline import (
    NativeTextPipeline, load_historical_ee_memory, RUNTIME_FONT_16X18,
    CONVERTER, NODE_BUILDER, GLYPH_BUILDER, OUTPUT, MEMCPY,
    NATIVE_NODE_ALLOC, NATIVE_RESOURCE_ACQUIRE, NATIVE_RESOURCE_RELEASE,
)
from tools.r67_15j_inspection_layout import catalogue
from tools.r67_15k_description_layout import build


class InspectionPipelineTests(unittest.TestCase):
    def test_native_isis_group_survives_opacity_rebuild_draw_order_and_font_growth(self):
        baseline = NativeTextPipeline().source
        source, report = build(baseline)
        records = catalogue(source)
        record = 0x592a70  # Isis variant with the third, PS2-only body field.
        self.assertEqual(unicodedata.normalize('NFKC', records[record][0]),
                         'Isis’ Inscription')
        pointers = struct.unpack_from('<6I', source, record)[1:5]
        probe = NativeTextPipeline(source, runtime_ee=load_historical_ee_memory(),
                                   lower_ranges=((0x902f00 + len(baseline) - 0x803150,
                                                  0x902f00 + len(source) - 0x803150),))
        uc = probe.uc
        template = bytes(uc.mem_read(RUNTIME_FONT_16X18, 0x254))
        owner = 0x1150000
        fonts = [0x1120000 + i * 0x300 for i in range(4)]
        handles = [0x1140000 + i * 0x100 for i in range(4)]
        next_node = 0x1f20000
        submitted = []

        def returned(engine, value=0):
            engine.reg_write(reg.UC_MIPS_REG_V0, value)
            engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

        def memcpy(engine):
            dest, src, size = (engine.reg_read(r) & 0xffffffff for r in
                               (reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1, reg.UC_MIPS_REG_A2))
            engine.mem_write(dest, bytes(engine.mem_read(src, size)))
            returned(engine, dest)

        def strlen(engine):
            address = engine.reg_read(reg.UC_MIPS_REG_A0) & 0xffffffff
            for size in range(4096):
                if not engine.mem_read(address + size, 1)[0]:
                    returned(engine, size)
                    return
            self.fail('unbounded source string')

        def allocate(engine):
            nonlocal next_node
            self.assertEqual(engine.reg_read(reg.UC_MIPS_REG_A0), 0x130)
            node = next_node
            next_node += 0x130
            engine.mem_write(node, bytes(0x130))
            returned(engine, node)

        def acquire(engine):
            returned(engine, engine.reg_read(reg.UC_MIPS_REG_A0))

        def context(engine):
            engine.mem_write(0x1100080, struct.pack('<f', 1.))
            returned(engine, 0x1100000)

        def draw(engine):
            self.assertEqual(engine.reg_read(reg.UC_MIPS_REG_A0), 4)
            pointer = engine.reg_read(reg.UC_MIPS_REG_A1) & 0xffffffff
            submitted.extend(struct.unpack('<ff', engine.mem_read(pointer + off, 8))
                             for off in (0, 0x40, 0x80, 0xc0))
            returned(engine)

        external = {MEMCPY: memcpy, 0x39f820: strlen, NATIVE_NODE_ALLOC: allocate,
                    NATIVE_RESOURCE_ACQUIRE: acquire, NATIVE_RESOURCE_RELEASE: returned,
                    0x1a0190: context, 0x1f01000: returned, 0x1f01010: draw}
        uc.mem_write(0x8de240, struct.pack('<I', 0x1f01000))
        uc.mem_write(0x8de250, struct.pack('<I', 0x1f01010))

        def run(address, *args):
            result = probe.execute(address, args=args, external=external,
                                   instruction_limit=3000000)
            self.assertTrue(result.returned, result.tail)

        visible = []
        for index, (font, handle, pointer) in enumerate(zip(fonts, handles, pointers)):
            uc.mem_write(font, template + bytes(4))
            uc.mem_write(font + 4, bytes(8))
            uc.mem_write(font + 0x14, struct.pack('<ff', 88., 348. + index * 18.))
            uc.mem_write(font + 0x28, bytes(8))
            uc.mem_write(font + 0x48, struct.pack('<ff', 1., 1.))
            uc.mem_write(font + 0x254, struct.pack('<I', owner))
            uc.mem_write(handle + 0x3c, struct.pack('<I', font))
            uc.mem_write(owner + 0x38 + index * 4, struct.pack('<I', handle))
            run(CONVERTER, 0, OUTPUT, pointer)
            run(NODE_BUILDER, handle, OUTPUT)
            run(GLYPH_BUILDER, font)
            nodes = []
            node = struct.unpack('<I', uc.mem_read(font + 4, 4))[0]
            while node:
                code = struct.unpack('<I', uc.mem_read(node, 4))[0]
                if code < 0xffffff00:
                    nodes.append(node)
                node = struct.unpack('<I', uc.mem_read(node + 0x120, 4))[0]
            visible.append(nodes)
        self.assertGreater(sum(map(len, visible)), 30)

        # Bypassing the owner callback must expose the original wide quads.
        for handle in handles:
            run(0x188420, handle)
        self.assertGreater(max(x for x, _ in submitted), 424.)

        for scale, order in ((1., range(4)), (1., reversed(range(4))),
                             (1.25, (2, 0, 3, 1))):
            for font, handle in zip(fonts, handles):
                uc.mem_write(font + 0x48, struct.pack('<ff', scale, scale))
                uc.reg_write(reg.UC_MIPS_REG_F12, 0x3f800000)
                run(0x18ad30, handle)
            submitted.clear()
            for index in order:
                run(report['inspection_draw_va'], handles[index])
            self.assertEqual(len(submitted), sum(map(len, visible)) * 4)
            for x, y in submitted:
                self.assertGreaterEqual(x, 88.)
                self.assertLessEqual(x, 424.)
                self.assertGreaterEqual(y, 348.)
                self.assertLessEqual(y, 438.)
            prior_bottom = 348.
            for font, nodes in zip(fonts, visible):
                self.assertEqual(bytes(uc.mem_read(font + 0x48, 8)), struct.pack('<ff', scale, scale))
                if nodes:
                    tops = [struct.unpack('<f', uc.mem_read(n + 0x14, 4))[0] for n in nodes]
                    bottoms = [struct.unpack('<f', uc.mem_read(n + 0xd4, 4))[0] for n in nodes]
                    self.assertGreaterEqual(min(tops), prior_bottom)
                    prior_bottom = max(bottoms)
            before = [bytes(uc.mem_read(n + off, 8)) for group in visible for n in group
                      for off in (0x10, 0x50, 0x90, 0xd0)]
            run(report['inspection_draw_va'], handles[0])
            after = [bytes(uc.mem_read(n + off, 8)) for group in visible for n in group
                     for off in (0x10, 0x50, 0x90, 0xd0)]
            self.assertEqual(after, before)


if __name__ == '__main__':
    unittest.main()
