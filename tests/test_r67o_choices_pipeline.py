"""Execute the eight patched call owners and their real n font/task routines."""
from __future__ import annotations

import struct
import unittest

from unicorn import UC_HOOK_CODE
from unicorn import mips_const as R

from tests.r67_native_text_pipeline import MEMCPY, NATIVE_GP, STACK, NativeTextPipeline
from tests.test_r67o_choices import ELF, PS2, SUPPLEMENT, checked_corpus
from tests.test_r67o_choices_native import candidate
from tools.r67o_choices import (
    ACTIVATION, ANIMATOR_CTOR, ANIMATOR_SIZE, CURSOR_CTOR, CURSOR_MOVE, DISPLAY_PREPROCESS,
    FONT_CTOR, FONT_SETTER, INITIAL_PREPROCESS, OWNER_CALLS, _font_table,
)
from tools.localization import encode_ps2_english


STATE = 0x1103000
FILE = 0x1200000
SOURCE = 0x1101000
SENTINEL = bytes(range(16))
DRAW_STATE = 0x1F01000
DRAW_QUADS = 0x1F01010
MATRIX_ALLOC = 0x1F01020
MATRIX_FREE = 0x1F01030
TASK_DATA = 0x1109000
GIVEN, FAMILY = 0x7C4BA0, 0x7C4BC0
FONT_DESC = 0x5D77D0


def wide(text: str) -> bytes:
    return encode_ps2_english(text, collapse_spaces=False)


def sign32(value):
    return struct.unpack('<i', struct.pack('<I', value & 0xffffffff))[0]


def round_float(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


class ChoiceMachine:
    def __init__(self, source, report):
        self.source = source
        self.report = report
        self.pipeline = NativeTextPipeline(source, lower_ranges=(
            (0x1023D0, 0x102A84), (0x1068F0, 0x108064), (0x188940, 0x188AD0),
            (0x18B060, 0x18CB50), (0x18E200, 0x18E294),
            (0x18F4B0, 0x190EF0), (0x22C2E8, 0x22C414),
            (0x2518B0, 0x251958), (0x24D5A0, 0x24D970), (0x251470, 0x251FC4), (0x349E20, 0x34A014),
            (0x34D950, 0x34D98C), *report['ee_ranges'],
        ))
        self.ee = self.pipeline.uc
        self.ee.mem_map(FILE, 0x400000)
        self.next = 0x1600000
        self.ee.mem_map(self.next, 0x400000)
        self.allocations = {}
        self.tasks = {}
        self.freed = []
        self.submitted = []
        self.render_states = []
        self.accumulator = 0.0

        # These EE-only scalar operations are interpreted in the harness
        # memory. The candidate retains their original instruction preimages.
        for start, end in ((0x1023D0, 0x108064), (0x18CB50, 0x18E1F0),
                           (0x2518B0, 0x251958), (0x24D5A0, 0x24D970), (0x251470, 0x251FC4)):
            self.ee.hook_add(UC_HOOK_CODE, self.ee_arithmetic, begin=start, end=end - 1)
        self.put32(NATIVE_GP - 0x1DAC, STATE)
        self.put32(NATIVE_GP - 0x1D70, TASK_DATA)
        self.put32(0x8DE240, DRAW_STATE)
        self.put32(0x8DE250, DRAW_QUADS)
        self.put32(0x8DE364, MATRIX_ALLOC)
        self.put32(0x8DE368, MATRIX_FREE)
        self.put32(0x8DE22C, 0x34D480)
        self.putfloat(0x8DE238, 512.0)
        context = self.alloc(0x100)
        self.putfloat(context + 0x80, 1.0)
        self.putfloat(context + 0x84, 0.125)
        self.put32(NATIVE_GP - 0x1E90, context)
        self.external = {
            0x1051F0: self.allocate_word, 0x105170: self.allocate_zero,
            0x105340: self.free_word, 0x1A1130: self.add_font,
            0x1A1190: self.add_task, 0x1A1860: self.task_present, 0x1A1430: self.release_task,
            0x39F708: self.strcpy, 0x39F820: self.strlen, 0x3A3ED0: self.format_copy,
            0x39FCC0: self.strncpy, 0x39FE80: self.strstr,
            MEMCPY: self.memcpy, 0x39C570: self.memset, 0x39D7D8: self.noop,
            0x187F10: self.noop, 0x187F90: self.noop,
            0x1C66D0: self.assertion, DRAW_STATE: self.draw_state, DRAW_QUADS: self.draw_quad,
            0x105FE0: self.noop, 0x1060A0: self.ready, 0x173FA0: self.noop,
            0x105DF0: self.noop, 0x106500: self.noop, MATRIX_ALLOC: self.matrix_alloc, MATRIX_FREE: self.matrix_free,
        }
        self.font_atlas(0)
        self.font_atlas(2)

    def ee_arithmetic(self, ee, pc, _size, _data):
        # The existing pipeline already handles these two instructions.
        if pc in (0x18E010, 0x18E014):
            return
        word = self.read32(pc)
        if word >> 26 == 17 and (word >> 21 & 31) == 16 and word & 63 in range(0x18, 0x20):
            function = word & 63
            a, b = (self.fpr(word >> shift & 31) for shift in (11, 16))
            if function == 0x18:
                self.accumulator = round_float(a + b)
            elif function == 0x19:
                self.accumulator = round_float(a - b)
            elif function == 0x1A:
                self.accumulator = round_float(a * b)
            else:
                if function not in (0x1C, 0x1D, 0x1E, 0x1F):
                    raise AssertionError(f'unexpected EE COP1 opcode {word:#x} at {pc:#x}')
                result = round_float(self.accumulator + a * b * (-1 if function & 1 else 1))
                if function in (0x1C, 0x1D):
                    self.set_fpr(word >> 6 & 31, result)
                else:
                    self.accumulator = result
            ee.reg_write(R.UC_MIPS_REG_PC, pc + 4)
        elif word >> 26 == 0 and word & 63 == 24 and (word >> 11 & 31):
            rs, rt, rd = (word >> shift & 31 for shift in (21, 16, 11))
            product = sign32(self.reg(rs)) * sign32(self.reg(rt))
            self.set_reg(rd, sign32(product))
            ee.reg_write(R.UC_MIPS_REG_LO, sign32(product) & 0xffffffffffffffff)
            ee.reg_write(R.UC_MIPS_REG_HI, sign32(product >> 32) & 0xffffffffffffffff)
            ee.reg_write(R.UC_MIPS_REG_PC, pc + 4)

    def font_atlas(self, style):
        # The executable owns widths, height and complete style-to-glyph
        # indices. Supply one loaded-cache slot per real native glyph index.
        # Atlas RAM locations naturally depend on the allocation history.
        descriptor = FONT_DESC + 0x30 * style
        indices = _font_table(self.source, style)
        slots = self.alloc(4 * len(indices))
        owners = self.alloc(0x18 * len(indices))
        width, height = self.read(descriptor + 4, 2)
        for index in range(len(indices)):
            entry = owners + index * 0x18
            self.put32(slots + 4 * index, entry)
            self.write(entry, struct.pack('<HHHHB', (index % 8) * width, (index % 7) * height, index, 1, 1))
        self.put32(descriptor + 0x2C, slots)
        self.put32(descriptor + 0x14, self.alloc(0x40))
        return slots

    def read(self, address, n):
        return bytes(self.ee.mem_read(address, n))

    def write(self, address, data):
        self.ee.mem_write(address, data)

    def read32(self, address):
        return struct.unpack('<I', self.read(address, 4))[0]

    def read16(self, address):
        return struct.unpack('<H', self.read(address, 2))[0]

    def put32(self, address, value):
        self.write(address, struct.pack('<I', value))

    def put16(self, address, value):
        self.write(address, struct.pack('<H', value))

    def putfloat(self, address, value):
        self.write(address, struct.pack('<f', value))

    def floats(self, address, n):
        return struct.unpack(f'<{n}f', self.read(address, 4 * n))

    def cstring(self, address, maximum=101):
        raw = self.read(address, maximum)
        if b'\0' not in raw:
            raise AssertionError(f'unterminated native input at {address:#x}')
        return raw[:raw.index(0)]

    def reg(self, number):
        return self.ee.reg_read(R.UC_MIPS_REG_0 + number) & 0xffffffffffffffff

    def set_reg(self, number, value):
        self.ee.reg_write(R.UC_MIPS_REG_0 + number, value & 0xffffffffffffffff)

    def fpr(self, number):
        return struct.unpack('<f', struct.pack('<I', self.ee.reg_read(R.UC_MIPS_REG_F0 + number) & 0xffffffff))[0]

    def set_fpr(self, number, value):
        self.ee.reg_write(R.UC_MIPS_REG_F0 + number, struct.unpack('<I', struct.pack('<f', value))[0])

    def ret(self, value=0):
        self.set_reg(2, value)
        self.ee.reg_write(R.UC_MIPS_REG_PC, self.reg(31))

    def noop(self, _engine):
        self.ret()

    def ready(self, _engine):
        self.ret(1)

    def assertion(self, _engine):
        raise AssertionError(f'native assertion {self.cstring(self.reg(4), 80)!r}:{self.reg(5)}')

    def memcpy(self, _engine):
        dest, source, size = (self.reg(i) for i in (4, 5, 6))
        self.write(dest, self.read(source, size))
        self.ret(dest)

    def memset(self, _engine):
        dest, value, size = (self.reg(i) for i in (4, 5, 6))
        self.write(dest, bytes([value & 0xff]) * size)
        self.ret(dest)

    def strcpy(self, _engine):
        dest, source = self.reg(4), self.reg(5)
        self.write(dest, self.cstring(source) + b'\0')
        self.ret(dest)

    def format_copy(self, _engine):
        if b'%' in self.cstring(self.reg(5)):
            raise AssertionError('format string contains a directive')
        self.strcpy(_engine)

    def strlen(self, _engine):
        self.ret(len(self.cstring(self.reg(4), 512)))

    def strncpy(self, _engine):
        dest, source, count = (self.reg(i) for i in (4, 5, 6))
        self.write(dest, self.read(source, count).split(b'\0', 1)[0].ljust(count, b'\0'))
        self.ret(dest)

    def strstr(self, _engine):
        source, needle = self.reg(4), self.reg(5)
        start = self.cstring(source, 512).find(self.cstring(needle, 512))
        self.ret(source + start if start >= 0 else 0)

    def alloc(self, size):
        address = self.next + 16
        self.next = (address + size + 31) & ~15
        self.write(address - 16, SENTINEL)
        self.write(address, bytes(size))
        self.write(address + size, SENTINEL)
        self.allocations[address] = size
        return address

    def allocate_word(self, _engine):
        self.ret(self.alloc(self.reg(4)))

    def allocate_zero(self, _engine):
        self.ret(self.alloc(self.reg(5)))

    def matrix_alloc(self, _engine):
        self.ret(self.alloc(0x100))

    def matrix_free(self, _engine):
        self.freed.append(self.reg(5))
        self.ret()

    def free_word(self, _engine):
        address = self.reg(4)
        if address not in self.allocations or address in self.freed:
            raise AssertionError(f'invalid native free: {address:#x}')
        self.freed.append(address)
        self.ret()

    def _add_task(self, update, destroy):
        handle = self.alloc(0x40)
        private = self.reg(9)
        self.put32(handle + 0x3C, private)
        self.put32(handle + 0x34, update)
        self.put32(handle + 0x38, destroy)
        self.tasks[handle] = (self.reg(4), update, destroy, private, True)
        self.ret(handle)

    def add_font(self, _engine):
        self._add_task(self.reg(7), self.reg(8))

    def add_task(self, _engine):
        self._add_task(self.reg(7), self.reg(8))

    def task_present(self, _engine):
        task = self.tasks.get(self.reg(4))
        self.ret(int(task is not None and task[-1]))

    def release_task(self, _engine):
        self.ret()
        handle = self.reg(4)
        if handle in self.tasks:
            self.tasks[handle] = (*self.tasks[handle][:-1], False)

    def draw_state(self, _engine):
        self.render_states.append((self.reg(4), self.reg(5)))
        self.ret()

    def draw_quad(self, _engine):
        if (self.reg(4), self.reg(6)) != (4, 4):
            raise AssertionError('unexpected native draw primitive')
        self.submitted.append([self.floats(self.reg(5) + vertex * 0x40, 12) for vertex in range(4)])
        self.ret()

    def run(self, address, *arguments, stop_at=(), watch=(), extra=None):
        result = self.pipeline.execute(address, args=arguments + (0,) * (4 - len(arguments)),
                                       stop_at=stop_at, external={**self.external, **(extra or {})},
                                       watch_addresses=watch, instruction_limit=1_500_000)
        if not result.returned:
            raise AssertionError(f'native routine {address:#x} did not return: {result.tail}')
        return result

    def callsite(self, site, *arguments, stop_at=(), watch=()):
        return self.run(site, *arguments, stop_at=(site + 8, *stop_at), watch=watch)

    def setup_record(self, record, family=b'', given=b'', mutation=None):
        path = record.rows[0].path
        raw = bytearray((PS2 / path).read_bytes())
        for row in record.rows:
            raw[row.offset:row.offset + 30] = row.preimage
        if mutation:
            mutation(raw)
        self.write(FILE, bytes(raw))
        self.write(STATE, bytes(0x3300))
        self.put32(STATE + 0x3158, FILE)
        self.put16(STATE + 0x3150, record.ordinal)
        self.write(STATE + 0x3160, record.loaded_name + b'\0')
        self.write(FAMILY - 4, b'\xbe' * 4)
        self.write(FAMILY, family.ljust(32, b'\0'))
        self.write(GIVEN, given.ljust(32, b'\0'))

    def run_record(self):
        self.run(0x22C2E8, 0, 0, 0, STATE, stop_at=(0x22C414,))
        return [self.cstring(STATE + 0x298 + i * 108)
                for i in range(self.read(STATE + 0x32E7, 1)[0])]

    def font(self, slot, row):
        self.set_reg(16, slot)
        for i, value in enumerate((129. - 39 * slot, 30., 512., 448., 0., 0., 299., 1.), 12):
            self.set_fpr(i, value)
        for off in (0, 8, 16):
            self.putfloat(STACK + off, 1.0)
        result = self.callsite(FONT_CTOR, TASK_DATA, 2, 0, 0xffffffff)
        task = result.v0
        self.set_reg(18, slot)
        self.write(SOURCE, row + b'\0')
        self.callsite(FONT_SETTER, task, SOURCE)
        return task

    def nodes(self, task):
        font = self.tasks[task][3]
        values = []
        node = self.read32(font + 4)
        while node:
            if node in values or len(values) > 60:
                raise AssertionError('unexpected invalid native node list')
            values.append(node)
            node = self.read32(node + 0x120)
        return values

    def animated(self, slot, font_task, rate=1, duration=3):
        self.set_reg(18, slot)
        self.set_fpr(12, float(rate))
        return self.callsite(ANIMATOR_CTOR, font_task, 99, duration, duration).v0

    def assert_canaries(self, test):
        for address, size in self.allocations.items():
            test.assertEqual(SENTINEL, self.read(address - 16, 16), (hex(address), size))
            test.assertEqual(SENTINEL, self.read(address + size, 16), (hex(address), size))


@unittest.skipUnless(ELF.is_file(), 'Pinned r67.15n ELF is unavailable')
class ChoicePipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.report = candidate()
        cls.corpus = checked_corpus(SUPPLEMENT.is_file())

    def setUp(self):
        self.machine = ChoiceMachine(self.source, self.report)

    def test_native_dispatch_from_type2_reader_to_draw_submission(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 4 and all(not x.dynamic for x in r.rows))
        m.setup_record(group)
        rows = m.run_record()
        self.assertEqual([row.encoded for row in group.rows], rows)
        self.assertEqual(1, m.run(self.report['entries']['choice_mode'], STATE).v0)
        for slot, row in enumerate(rows):
            task = m.font(slot, row)
            private = m.tasks[task][3]
            self.assertEqual(0x18B9B0, m.tasks[task][1])
            self.assertEqual(FONT_DESC, m.read32(private + 0x10))
            self.assertEqual((24., 22. + 39 * slot, 512., 448.), m.floats(private + 0x14, 4))
            self.assertEqual(row, m.cstring(private + 0x51).replace(b'\n', b''))
            self.assertEqual(0xFFFFFF0F, m.read32(m.nodes(task)[-1]))
            m.submitted.clear()
            m.run(m.tasks[task][1], task)
            self.assertEqual(sum(t < 0xff00 for t in group.rows[slot].tokens), len(m.submitted))
            self.assertTrue(all(24. <= v[0] < 472. and 22. + 39 * slot <= v[1] < 58. + 39 * slot
                                for quad in m.submitted for v in quad))
        m.assert_canaries(self)

    def test_guard_rejects_changed_active_siblings_file_and_ordinal(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) >= 2 and not any(x.dynamic for x in r.rows))
        for invalid in ('preimage', 'mask', 'name', 'ordinal', 'source'):
            with self.subTest(invalid=invalid):
                m.setup_record(group)
                address, value = {
                    'preimage': (FILE + group.rows[-1].offset, b'X'),
                    'mask': (FILE + group.rows[-1].offset - 1, b'\0'),
                    'name': (STATE + 0x3160 + 6, b'X'),
                    'ordinal': (STATE + 0x3150, struct.pack('<H', group.ordinal + 1)),
                    'source': (SOURCE, b'X'),
                }[invalid]
                m.write(address, value)
                m.write(STATE + 0x32EA, b'\1')
                m.write(SOURCE + 0x300, b'<' + b'\xcc' * 101 + b'>')
                m.set_reg(17, 0)
                pointer = SOURCE if invalid == 'source' else FILE + group.rows[0].offset
                result = m.callsite(ACTIVATION, SOURCE + 0x301, pointer)
                self.assertEqual(SOURCE + 0x301, result.v0)
                self.assertEqual(m.cstring(pointer), m.cstring(SOURCE + 0x301))
                self.assertEqual(0, m.run(self.report['entries']['choice_mode'], STATE).v0)
                self.assertEqual(OWNER_CALLS[INITIAL_PREPROCESS], m.callsite(
                    INITIAL_PREPROCESS, SOURCE + 0x301, stop_at=(OWNER_CALLS[INITIAL_PREPROCESS],)).pc)
                self.assertEqual(b'<', m.read(SOURCE + 0x300, 1))
                self.assertEqual(b'>', m.read(SOURCE + 0x366, 1))

    def test_animated_child_indices_canaries_and_native_cancellation(self):
        m = self.machine
        group = max((r for r in self.corpus.records if not any(row.dynamic for row in r.rows)),
                    key=lambda r: max(len(row.tokens) for row in r.rows))
        m.setup_record(group)
        rows = m.run_record()
        slot = max(range(len(group.rows)), key=lambda i: len(group.rows[i].tokens))
        font_task = m.font(slot, rows[slot])
        font = m.tasks[font_task][3]
        nodes = m.nodes(font_task)
        logical_nodes = [node for node in nodes if m.read32(node) not in (0xffffff0e, 0xffffff0f)]
        self.assertEqual(56, len(logical_nodes))
        self.assertEqual(1, sum(m.read32(node) == 0xffffff0e for node in nodes))

        animator = m.animated(slot, font_task)
        _, callback, destructor, private, _ = m.tasks[animator]
        self.assertEqual(ANIMATOR_SIZE, m.allocations[private])
        self.assertEqual(0x18CAB0, destructor)
        self.assertEqual(56, m.read16(private + 0x10))
        result = m.run(callback, animator, watch=(0x18C3E0,))
        self.assertEqual([nodes.index(node) for node in logical_nodes], [w[2] for w in result.watched])
        children = [m.read32(private + 0x18 + i * 4) for i in range(56)]
        self.assertEqual(56, len(set(children)))
        self.assertEqual(b'\0' * (56 * 4), m.read(private + 0xF8, 56 * 4))
        self.assertEqual(logical_nodes, [m.read32(m.tasks[child][3] + 0xC) for child in children])
        self.assertEqual(1, m.run(0x18CB40, animator).v0)
        self.assertTrue(all(m.read16(node + 0x12E) == 0xFFFF for node in logical_nodes))
        for child in children:
            m.run(m.tasks[child][1], child)
        m.run(0x18CAE0, animator)
        self.assertEqual(2, m.run(0x18CB40, animator).v0)
        m.run(callback, animator)
        self.assertEqual(3, m.run(0x18CB40, animator).v0)
        self.assertEqual(1, m.run(0x18CB30, animator).v0)
        for step in (0., 1. / 3., 1.):
            m.run(m.tasks[children[0]][1], children[0])
            self.assertAlmostEqual(step, m.floats(logical_nodes[0] + 0x11C, 1)[0], places=5)
        for _ in range(4):
            m.run(callback, animator)
        self.assertEqual(2, m.run(0x18CB40, animator).v0)

        m.run(0x18CB10, animator)
        self.assertEqual(5, m.run(0x18CB40, animator).v0)
        m.run(callback, animator)
        self.assertEqual(7, m.run(0x18CB40, animator).v0)
        self.assertEqual(0xFFFFFFFF, m.run(callback, animator).v0)
        self.assertEqual((1.0,), m.floats(font + 0x44, 1))
        self.assertTrue(all(m.floats(node + 0x11C, 1) == (1.0,)
                            for node in logical_nodes if m.read32(node) < 0xFFFFFF00))
        self.assertTrue(all(not m.tasks[child][-1] for child in children))
        for child in children:
            m.run(m.tasks[child][2], child)
        m.run(destructor, animator)
        self.assertEqual({private, *(m.tasks[child][3] for child in children)}, set(m.freed))
        m.assert_canaries(self)

    def test_name_fields_are_bounded_before_both_preprocessors_and_setter(self):
        go = ((wide('Habaki'), wide('Kuro'), 'EN'), (wide('M') * 15, wide('N') * 15, 'EN'),
              (b'', b'', 'EN'), (b'A' * 32, wide('N'), 'JP'),
              (b'B\0', wide('N'), 'JP'), (b'\x82\x20', wide('N'), 'JP'),
              (b'\x82\xfc', wide('N'), 'JP'))
        groups = [r for r in self.corpus.records if any(row.dynamic for row in r.rows)]
        self.assertEqual(4, len(groups))
        for group in groups:
            for family, given, wanted in go:
                with self.subTest(file=group.loaded_name, family=family, given=given):
                    m = self.machine
                    m.setup_record(group, family, given)
                    nearby = m.read(GIVEN - 4, 68)
                    rows = m.run_record()
                    expect = [r.encoded.replace(b'\x01', family).replace(b'\x02', given)
                              if wanted == 'EN' else r.pristine.split(b'\0')[0]
                              for r in group.rows]
                    self.assertEqual(expect, rows)
                    self.assertEqual(1 if wanted == 'EN' else 3, m.run(
                        self.report['entries']['choice_mode'], STATE).v0)
                    for slot, row in enumerate(rows):
                        m.set_reg(18, slot)
                        src = STATE + 0x298 + 108 * slot
                        result = m.callsite(DISPLAY_PREPROCESS, src, stop_at=(0x24D5A0,))
                        self.assertEqual(DISPLAY_PREPROCESS + 8, result.pc)
                        self.assertEqual(src, result.v0)
                        saved = m.read(STATE + 0x298, len(rows) * 108)
                        task = m.font(slot, row)
                        private = m.tasks[task][3]
                        self.assertEqual(0 if wanted == 'EN' else 2, m.read32(private + 0xC))
                        self.assertEqual(row, m.cstring(private + 0x51).replace(b'\n', b''))
                        self.assertEqual(saved, m.read(STATE + 0x298, len(rows) * 108))
                    self.assertEqual(nearby, m.read(GIVEN - 4, 68))
        self.machine.assert_canaries(self)

    def test_cursor_native_sprite_submission_tracks_first_line_across_four_slots(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 4 and not any(row.dynamic for row in r.rows))
        m.setup_record(group)
        m.run_record()
        maximum = m.run(self.report['entries']['choice_cursor_cells'], STATE).v0
        self.assertTrue(1 <= maximum <= 18)
        m.set_fpr(12, 299.)
        stock_xy = int.from_bytes(struct.pack('<ff', 129., 100.), 'little')
        cursor = m.callsite(CURSOR_CTOR, TASK_DATA, stock_xy, 5).v0
        _, stock_update, destructor, private, _ = m.tasks[cursor]
        self.assertEqual((0x1025E0, 0x1023D0), (stock_update, destructor))
        update = m.read32(cursor + 0x34)
        self.assertEqual(self.report['entries']['cursor_update'], update)
        self.assertEqual((24., 22.), m.floats(private + 8, 2))
        self.assertEqual(maximum, m.read16(private + 4))
        frame_table = m.read32(0x485240 + 4)
        texture = m.alloc(0x100)
        m.put32(texture, 0x12345678)
        for sprite in range(0x8D, 0x92):
            frame = m.read32(frame_table + sprite * 8)
            count = m.read32(frame_table + sprite * 8 + 4)
            for frame_index in range(count):
                texture_index = m.read16(frame + frame_index * 0x30 + 2)
                m.put32(0x7B7868 + 252 + texture_index * 4, texture)

        def verify_draw(objects, y):
            m.submitted.clear()
            for obj in objects:
                m.run(0x106D80, obj)
            self.assertEqual(len(objects), len(m.submitted))
            self.assertTrue(all(4 <= v[0] <= 20 and y <= v[1] <= y + 17
                                for q in m.submitted for v in q),
                            (y, maximum, [[v[:2] for v in quad] for quad in m.submitted]))
            self.assertTrue(all(0 <= v[4] <= 1 and 0 <= v[5] <= 1 for q in m.submitted for v in q))

        m.run(update, cursor)
        m.run(update, cursor)
        flash = m.read32(private + 0x24)
        self.assertEqual(0x91, m.read16(flash + 0x84))
        tested_frames = set()
        for _ in range(10):
            if m.read16(private) == 2:
                verify_draw([flash], 22.)
                tested_frames.add(m.read16(flash + 0x86))
            m.run(update, cursor)
        self.assertGreater(len(tested_frames), 1)
        self.assertEqual(3, m.read16(private))
        sprite_objects = [m.read32(private + 0x24 + n * 4) for n in range(4)]
        self.assertEqual([0x8D, 0x90, 0x8E, 0x8F],
                         [m.read16(obj + 0x84) for obj in sprite_objects])
        for slot in (0, 1, 2, 3, 1, 0):
            previous = m.floats(private + 0x0C, 1)[0]
            target = 22. + 39 * slot
            m.write(STATE + 0x32E8, bytes([slot]))
            m.callsite(CURSOR_MOVE, cursor, stock_xy)
            self.assertEqual((24., target), m.floats(private + 0x10, 2))
            for step in range(1, 6):
                m.run(update, cursor)
                y = m.floats(private + 0x0C, 1)[0]
                self.assertAlmostEqual(previous + (target - previous) * (step / 5), y, places=4)
                verify_draw(sprite_objects, y)
            self.assertEqual(3, m.read16(private))
            self.assertEqual((24., target), m.floats(private + 8, 2))
        m.write(STATE + 0x32E8, b'\xff')
        m.callsite(CURSOR_MOVE, cursor, stock_xy)
        self.assertEqual(3, m.read16(private))
        m.run(destructor, cursor)
        self.assertIn(private, m.freed)
        self.assertTrue(all(m.read16(obj + 0x80) == 4 for obj in sprite_objects))
        reopened = m.callsite(CURSOR_CTOR, TASK_DATA, stock_xy, 5).v0
        self.assertNotEqual(cursor, reopened)
        self.assertEqual((24., 22.), m.floats(m.tasks[reopened][3] + 8, 2))
        m.run(destructor, reopened)
        m.assert_canaries(self)

    def test_all_logical_counts_and_invalid_native_lists(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 1 and not r.rows[0].dynamic)
        m.setup_record(group)
        m.run_record()
        context = self.report['entries']['choice_context']
        entries = self.report['entries']
        # This synthetic stress case installs rows in the test context only.
        # It runs the actual setter, node builder, constructor and child factory.
        for count in range(1, 57):
            with self.subTest(count=count):
                text = wide('A') + (wide('Z') + b' ') * ((count - 1) // 2)
                if count % 2 == 0:
                    text += b' '
                m.write(SOURCE, text + b'\0')
                measured = m.run(entries['choice_layout'], SOURCE, SOURCE + 0x100, SOURCE + 0x200)
                self.assertEqual(count, measured.v0)
                wrapped = m.cstring(SOURCE + 0x100)
                m.write(context + 0x5C, text + b'\0')
                m.write(context + 0x5C + 101, wrapped + b'\0')
                m.write(STATE + 0x298, text + b'\0')
                font = m.font(0, text)
                animator = m.animated(0, font)
                values = list(enumerate(m.nodes(font)))
                logical = [i for i, node in values if m.read32(node) not in (0xffffff0e, 0xffffff0f)]
                _, callback, _, private, _ = m.tasks[animator]
                self.assertEqual(count, m.read16(private + 0x10))
                actual = m.run(callback, animator, watch=(0x18C3E0,)).watched
                self.assertEqual(logical, [call[2] for call in actual])
                self.assertEqual(count, len(actual))
                self.assertEqual(count, len({m.read32(private + 0x18 + i * 4) for i in range(count)}))
        for case in ('empty', 'short', 'terminal', 'cycle', 'invalid address', 'overflow', 'bad token'):
            with self.subTest(case=case):
                m.setup_record(group)
                row, = m.run_record()
                font = m.font(0, row)
                private = m.tasks[font][3]
                nodes = m.nodes(font)
                offset, data = {
                    'empty': (private + 4, bytes(4)),
                    'short': (nodes[0] + 0x120, bytes(4)),
                    'terminal': (nodes[-1], struct.pack('<I', 0xffffff0a)),
                    'cycle': (nodes[-2] + 0x120, struct.pack('<I', nodes[0])),
                    'invalid address': (nodes[0] + 0x120, struct.pack('<I', 0x2000000)),
                    'overflow': (private + 0x250, struct.pack('<H', 58)),
                    'bad token': (nodes[0], struct.pack('<I', 0xffffff0e)),
                }[case]
                m.write(offset, data)
                animator = m.animated(0, font)
                _, callback, _, animator_private, _ = m.tasks[animator]
                self.assertEqual(0, m.read16(animator_private + 0x10))
                self.assertEqual([], m.run(callback, animator, watch=(0x18C3E0,)).watched)
                m.run(0x18CAE0, animator)
                m.run(callback, animator)
                self.assertEqual(7, m.run(0x18CB40, animator).v0)
        m.assert_canaries(self)

    def test_render_complete_keeps_the_native_animation_state_contract(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 1 and not r.rows[0].dynamic)
        for cycle in range(2):
            m.setup_record(group)
            row, = m.run_record()
            font = m.font(0, row)
            animator = m.animated(0, font, duration=1)
            _, callback, destructor, private, _ = m.tasks[animator]
            count = m.read16(private + 0x10)
            m.run(callback, animator)
            children = [m.read32(private + 0x18 + i * 4) for i in range(count)]
            for child in children:
                m.run(m.tasks[child][1], child)
            m.run(0x18CAE0, animator)
            for logical, child in enumerate(children):
                self.assertEqual(2, m.run(0x18CB40, animator).v0)
                m.run(callback, animator)
                self.assertEqual(logical + 1, m.run(0x18CB30, animator).v0)
                self.assertEqual(3, m.run(0x18CB40, animator).v0)
                m.run(m.tasks[child][1], child)
                self.assertEqual(0xFFFFFFFF, m.run(m.tasks[child][1], child).v0)
                m.run(m.tasks[child][2], child)
                m.run(callback, animator)
                m.run(callback, animator)
            self.assertEqual(7, m.run(0x18CB40, animator).v0)
            self.assertEqual(0xFFFFFFFF, m.run(callback, animator).v0)
            m.run(destructor, animator)
            m.run(m.tasks[font][2], font)
            self.assertIn(private, m.freed)
        m.assert_canaries(self)

    def test_each_bridge_restores_preserved_registers_and_native_stack_arguments(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 1 and not r.rows[0].dynamic)
        m.setup_record(group)
        row, = m.run_record()
        font_task = m.font(0, row)
        entries = self.report['entries']
        targets = {
            ACTIVATION: (0x39F708, (SOURCE, FILE + group.rows[0].offset), 0, 0, 0),
            INITIAL_PREPROCESS: (INITIAL_PREPROCESS + 8, (SOURCE,), 0, 0, 0),
            DISPLAY_PREPROCESS: (DISPLAY_PREPROCESS + 8, (SOURCE,), 0, 0, 0),
            FONT_CTOR: (0x18BF10, (TASK_DATA, 2, 0, 0xffffffff), 0, 0, 0),
            FONT_SETTER: (entries['english_setter'], (font_task, SOURCE), 0, 0, 0),
            ANIMATOR_CTOR: (entries['animator_constructor'], (font_task, 7, 5, 3), 0, 0, 0),
            CURSOR_CTOR: (entries['cursor_constructor'], (TASK_DATA, 0x42C0000042FF0000, 5), 0, 0, 0),
            CURSOR_MOVE: (0x102590, (TASK_DATA, 0x42C0000042FF0000), 0, 0, 0),
        }
        # Runtime GP and sp are inherent game caller values. Sentinel high
        # doublewords catch accidental use of ordinary 32-bit save/restore.
        for site, (target, args, s0, s1, s2) in list(targets.items())[1:] + [(ACTIVATION, targets[ACTIVATION])]:
            with self.subTest(site=hex(site)):
                m.write(SOURCE, row + b'\0')
                registers = {16: s0, 17: s1, 18: s2, **{i: 0x1234567800000000 + i for i in range(19, 24)},
                             30: 0x1234567800000000 | 30}
                for i, value in registers.items():
                    m.set_reg(i, value)
                for i in range(20, 32):
                    m.set_fpr(i, i + 0.25)
                stack = bytes(range(32))
                m.write(STACK, stack)
                result = m.callsite(site, *args, stop_at=(target,))
                self.assertEqual(target, result.pc)
                self.assertEqual(registers, {i: m.reg(i) for i in registers})
                self.assertEqual(tuple(i + 0.25 for i in range(20, 32)), tuple(m.fpr(i) for i in range(20, 32)))
                self.assertEqual(site + 8, m.reg(31))
                self.assertEqual(STACK, m.reg(29))
                self.assertEqual(NATIVE_GP, m.reg(28))
                self.assertEqual(stack, m.read(STACK, len(stack)))
                if site == FONT_CTOR:
                    self.assertEqual((TASK_DATA, 0, 0, 0xffffffff), tuple(m.reg(i) for i in range(4, 8)))
                    self.assertEqual((24., 22.), (m.fpr(12), m.fpr(13)))
                if site == ANIMATOR_CTOR:
                    self.assertEqual(args, tuple(m.reg(i) for i in range(4, 8)))

    def test_all_name_lengths_and_default_bytes_use_native_owner_bridges(self):
        m = self.machine
        entry = self.report['entries']['choice_copy_source']
        m.write(SOURCE, b'<' + b'\xbb' * 101 + b'>')
        scratch = SOURCE + 1
        observed = 0
        for group in (r for r in self.corpus.records if any(row.dynamic for row in r.rows)):
            m.setup_record(group)
            m.write(STATE + 0x32EA, b'\1')
            for family_size in range(16):
                for given_size in range(16):
                    family, given = wide('M') * family_size, wide('N') * given_size
                    m.write(FAMILY, family.ljust(32, b'\0'))
                    m.write(GIVEN, given.ljust(32, b'\0'))
                    for slot, row in enumerate(group.rows):
                        m.set_reg(17, slot)
                        result = m.callsite(ACTIVATION, scratch, FILE + row.offset)
                        self.assertEqual(scratch, result.v0)
                        resolved = m.callsite(INITIAL_PREPROCESS, scratch, stop_at=(0x24D5A0,))
                        self.assertEqual(INITIAL_PREPROCESS + 8, resolved.pc)
                        self.assertEqual(row.encoded.replace(b'\x01', family).replace(b'\x02', given),
                                         m.cstring(scratch))
                        self.assertEqual((b'<', b'>'), (m.read(SOURCE, 1), m.read(scratch + 101, 1)))
                    observed += 1
        self.assertEqual(1024, observed)
        n = ELF.read_bytes()
        defaults = [struct.unpack_from('<I', n, offset)[0] for offset in (0x586630, 0x586634, 0x586640, 0x586644)]
        self.assertEqual([wide(name) for name in ('Habaki', 'Kuro', 'Hiyuu', 'Tatsuma')],
                         [m.cstring(pointer) for pointer in defaults])
        self.assertGreater(entry, 0x902F00)

    def test_native_converter_all_proven_rows_preserves_case_punctuation_and_spaces(self):
        m = self.machine
        seen = set()
        for row in [row for group in self.corpus.records for row in group.rows] + list(self.corpus.blank_rows):
            if row.text in seen:
                continue
            seen.add(row.text)
            text = row.encoded.replace(b'\x01', wide('ABC')).replace(b'\x02', wide('Qxy'))
            m.write(SOURCE, text + b'\0\0')
            result = m.run(0x1952F0, 0, SOURCE + 0x180, SOURCE)
            self.assertEqual(row.tokens + (0xFF0F,),
                             struct.unpack(f'<{result.v0 + 1}H', m.read(SOURCE + 0x180, 2 * (result.v0 + 1))),
                             (row.path, row.array_index))
        self.assertEqual(len({row.text for group in self.corpus.records for row in group.rows}
                             | {row.text for row in self.corpus.blank_rows}), len(seen))

    def test_true_draw_quads_of_maximum_row_in_every_slot_include_uv_and_alpha(self):
        from tools.r67o_choices import layout_units

        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 4 and not any(row.dynamic for row in r.rows))
        longest = max((row for group in self.corpus.records for row in group.rows), key=lambda row: len(row.tokens))
        m.setup_record(group)
        m.run_record()
        context = self.report['entries']['choice_context']
        m.write(SOURCE, longest.encoded + b'\0')
        m.run(self.report['entries']['choice_layout'], SOURCE, SOURCE + 0x100, SOURCE + 0x200)
        wrapped = m.cstring(SOURCE + 0x100)
        split, widths = layout_units(longest.tokens)
        self.assertEqual((448, 320), widths)
        for slot in range(4):
            base = context + 0x5C + 202 * slot
            m.write(base, longest.encoded + b'\0')
            m.write(base + 101, wrapped + b'\0')
            m.write(STATE + 0x298 + 108 * slot, longest.encoded + b'\0')
        for slot in range(4):
            handle = m.font(slot, longest.encoded)
            self.assertTrue(m.run(0x18B100, handle, 200).returned)
            m.set_reg(8, 0xAB)
            m.run(0x18B060, handle, 0xFE, 0xDC, 0xBA)
            m.submitted.clear()
            m.run(0x18B9B0, handle)
            native_visible = m.submitted[1::2]  # First quad is the native shifted shadow pass.
            self.assertEqual(sum(t < 0xFF00 for t in longest.tokens), len(native_visible))
            y0, x, y, visible = 22. + 39 * slot, 24., 22. + 39 * slot, 0
            for index, unit in enumerate(longest.tokens):
                if index == split:
                    x, y = 24., y + 18.
                if unit in (0xFF0A, 0xFF0B):
                    x += 8. if unit == 0xFF0A else 16.
                    continue
                quad = native_visible[visible]
                visible += 1
                self.assertEqual([(x, y), (x + 15, y), (x, y + 17), (x + 15, y + 17)],
                                 [v[:2] for v in quad])
                u, v = (unit % 8) * 16 / 256, (unit % 7) * 18 / 256
                self.assertEqual([(u, v), (u + 16 / 256, v), (u, v + 18 / 256), (u + 16 / 256, v + 18 / 256)],
                                 [vertex[4:6] for vertex in quad])
                self.assertTrue(all(vertex[8:12] == (254., 220., 186., 171.) for vertex in quad))
                self.assertTrue(all(24. <= vertex[0] <= 471. and y0 <= vertex[1] <= y0 + 35 for vertex in quad))
                x += 16.
        m.assert_canaries(self)

    def test_native_controller_masks_and_branch_ordinals_are_preserved(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 4
                     and len(set(struct.unpack_from('<4H', r.header, 6))) > 1)
        m.setup_record(group)
        rows = m.run_record()
        observed = []
        m.external[0x1697B0] = m.noop
        m.external[0x2531A0] = lambda _: (observed.append((m.reg(4), m.cstring(m.reg(5)))), m.ret())
        m.external[0x22CC70] = m.noop
        m.put16(0x7A39CE, 0x8000)
        for expected in (1, 2, 3, 3):
            m.run(0x215AA0)
            self.assertEqual(expected, m.read(STATE + 0x32E8, 1)[0])
        m.put16(0x7A39CE, 0x2000)
        for expected in (2, 1, 0, 0):
            m.run(0x215AA0)
            self.assertEqual(expected, m.read(STATE + 0x32E8, 1)[0])
        for selected, value in enumerate(rows):
            m.write(STATE + 0x32EA, b'\1')
            m.write(STATE + 0x32E8, bytes([selected]))
            m.put16(0x7A39CE, 0x20)
            m.run(0x22C44C, stop_at=(0x22C830,))
            self.assertEqual((10 + selected, value), observed[-1])
            self.assertEqual(bytes((9 + selected, 14 + selected)), m.read(STATE + 0x327E, 2))
            self.assertEqual(9, m.read16(STATE + 0x314E))
            m.set_reg(16, FILE + group.offset)
            m.run(0x22C6C0, STATE, stop_at=(0x22C6E8,))
            branch, = struct.unpack_from('<H', group.header, 6 + 2 * selected)
            self.assertEqual(branch, m.read16(STATE + 0x327A))
        m.put16(0x7A39CE, 0x100)
        m.run(0x22C44C, stop_at=(0x22C830,))
        self.assertEqual(b'\1', m.read(STATE + 0x3200, 1))
        self.assertEqual(6, m.read16(STATE + 0x314E))
        self.assertEqual(4, len(observed))
        m.assert_canaries(self)

    def test_case_zero_rejects_nodes_invalidated_after_construction(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 1 and len(r.rows[0].tokens) >= 2)
        m.setup_record(group)
        row, = m.run_record()
        font = m.font(0, row)
        animator = m.animated(0, font)
        _, callback, _, private, _ = m.tasks[animator]
        self.assertGreater(m.read16(private + 0x10), 0)
        first, *_ = m.nodes(font)
        m.put32(first + 0x120, first)
        self.assertEqual([], m.run(callback, animator, watch=(0x18C3E0,)).watched)
        self.assertEqual(0, m.read16(private + 0x10))
        m.assert_canaries(self)

    def test_a_bad_sibling_prevents_any_children_across_the_record(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 2 and not any(x.dynamic for x in r.rows))
        m.setup_record(group)
        rows = m.run_record()
        first = m.font(0, rows[0])
        animator = m.animated(0, first)
        second = m.font(1, rows[1])
        broken = m.nodes(second)[0]
        m.put32(broken + 0x120, broken)
        later = m.animated(1, second)
        for handle in (animator, later):
            _, callback, _, private, _ = m.tasks[handle]
            self.assertEqual([], m.run(callback, handle, watch=(0x18C3E0,)).watched)
            self.assertEqual(0, m.read16(private + 0x10))
        m.assert_canaries(self)

    def test_unknown_record_delegates_all_eight_native_call_sites(self):
        m = self.machine
        self.assertEqual(set(OWNER_CALLS), set(site['address'] for site in self.report['call_sites']))
        m.write(STATE, b'\0' * 0x3300)
        m.write(SOURCE, b'stock\0')
        for site, target in OWNER_CALLS.items():
            with self.subTest(site=hex(site)):
                args = (SOURCE + 0x200, SOURCE, 0, 0)
                saved = tuple(m.reg(i) for i in (16, 17, 18, 19, 20, 21, 22, 23, 30))
                result = m.callsite(site, *args, stop_at=(target,))
                self.assertEqual(target, result.pc)
                self.assertEqual(args, tuple(m.reg(i) for i in (4, 5, 6, 7)))
                self.assertEqual(saved, tuple(m.reg(i) for i in (16, 17, 18, 19, 20, 21, 22, 23, 30)))

    def test_valid_names_missing_a_style_zero_glyph_use_bounded_pristine_layout(self):
        m = self.machine
        group = next(r for r in self.corpus.records if any(row.dynamic for row in r.rows))
        family = '〇'.encode('cp932')
        given = wide('N') * 15
        code = int.from_bytes(family, 'big')
        self.assertIn(code, _font_table(self.source, 2))
        self.assertNotIn(code, _font_table(self.source, 0))
        m.setup_record(group, family, given)
        rows = m.run_record()
        self.assertEqual(2, m.run(self.report['entries']['choice_mode'], STATE).v0)
        for slot, (row, display) in enumerate(zip(group.rows, rows, strict=True)):
            original = row.pristine.split(b'\0')[0].decode('cp932')
            expected = original.replace('pm', family.decode('cp932')).replace('pn', given.decode('cp932')).encode('cp932')
            self.assertEqual(expected, display)
            handle = m.font(slot, display)
            font = m.tasks[handle][3]
            self.assertEqual(2, m.read32(font + 0xC))
            self.assertEqual(expected, m.cstring(font + 0x51))
            m.animated(slot, handle)
        m.assert_canaries(self)

    def test_normal_menu_owner_builds_all_live_slots_and_cancels_before_reveal(self):
        m = self.machine
        for slots in range(1, 5):
            group = next(r for r in self.corpus.records if len(r.rows) == slots and not any(x.dynamic for x in r.rows))
            m.setup_record(group)
            count = len(m.run_record())
            self.assertEqual(slots, count)
            m.write(TASK_DATA, bytes(0x200))
            menu = m.alloc(0x68)
            private = m.alloc(0x40)
            m.put32(menu + 0x3C, private)
            m.run(0x251470, menu)
            self.assertEqual(b'\1', m.read(private, 1))
            fonts = [m.read32(TASK_DATA + 0x94 + i * 4) for i in range(slots)]
            self.assertEqual(slots, len({f for f in fonts if f}))
            for slot, font in enumerate(fonts):
                self.assertEqual((24., 22. + 39 * slot), m.floats(m.tasks[font][3] + 0x14, 2))
            m.run(0x251470, menu)
            self.assertEqual(b'\3', m.read(private, 1))
            animators = [m.read32(TASK_DATA + 0xB0 + i * 4) for i in range(slots)]
            for slot, (font, handle) in enumerate(zip(fonts, animators, strict=True)):
                self.assertEqual(font, m.tasks[handle][0])
                data = m.tasks[handle][3]
                self.assertEqual(len(group.rows[slot].tokens), m.read16(data + 0x10))
                self.assertEqual(0, m.read32(data + 0x14))
                self.assertEqual(0, m.run(0x18CB40, handle).v0)
            # Cancellation before parent advances case 0 releases the font
            # handles via the real choice cleanup. The stock scheduler owns
            # recursive task teardown, which the harness invokes explicitly.
            m.run(0x2518B0)
            for handle in animators:
                m.run(m.tasks[handle][2], handle)
            for font in fonts:
                self.assertFalse(m.tasks[font][-1])
                m.run(m.tasks[font][2], font)
            self.assertTrue(all(m.read32(TASK_DATA + 0x94 + i * 4) == 0 for i in range(slots)))
        m.assert_canaries(self)

    def test_stock_cases_four_and_six_keep_their_original_transitions(self):
        m = self.machine
        group = next(r for r in self.corpus.records if len(r.rows) == 1 and not r.rows[0].dynamic)
        m.setup_record(group)
        row, = m.run_record()
        font = m.font(0, row)
        handle = m.animated(0, font)
        _, callback, _, private, _ = m.tasks[handle]
        m.run(callback, handle)
        m.write(private + 0x0C, b'\6')
        m.run(callback, handle)
        self.assertEqual(6, m.run(0x18CB40, handle).v0)
        m.write(private + 0x0C, b'\4')
        m.run(callback, handle)
        self.assertEqual(2, m.run(0x18CB40, handle).v0)
        m.put16(private + 0x0E, m.read16(private + 0x10))
        m.write(private + 0x0C, b'\4')
        m.run(callback, handle)
        self.assertEqual(7, m.run(0x18CB40, handle).v0)
        m.assert_canaries(self)
