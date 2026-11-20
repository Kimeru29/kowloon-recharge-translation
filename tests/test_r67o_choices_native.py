from functools import lru_cache
import struct
import unittest

from unicorn import mips_const as R

from tests.r67_native_text_pipeline import NativeTextPipeline
from tests.test_r67o_choices import ELF, SUPPLEMENT, checked_corpus


SCRATCH = 0x1101000
TEXT = 0x1101200
STATE = 0x1102000
FILE = 0x1120000


@lru_cache(maxsize=1)
def candidate():
    from tools.r67o_choices import build

    return build(ELF.read_bytes(), checked_corpus(SUPPLEMENT.is_file()))


@unittest.skipUnless(ELF.is_file(), 'Pinned r67.15n ELF is unavailable')
class ChoiceNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tools.r67o_choices import KERNEL

        if not KERNEL.is_file():
            raise AssertionError('native choice kernel has not been implemented')
        cls.source, cls.report = candidate()

    def setUp(self):
        self.pipeline = NativeTextPipeline(self.source, lower_ranges=self.report['ee_ranges'])
        self.ee = self.pipeline.uc
        self.entries = self.report['entries']

    def test_native_layout_preserves_all_characters_and_widths(self):
        row = max((row for r in checked_corpus().records for row in r.rows), key=lambda row: len(row.text))
        self.ee.mem_write(SCRATCH, b'<' + b'\xff' * 101 + b'>')
        self.ee.mem_write(TEXT, row.encoded + b'\0')
        result = self.pipeline.execute(
            self.entries['choice_layout'], args=(TEXT, SCRATCH + 1, TEXT + 0x100, 0))
        self.assertEqual(56, result.v0)
        value = bytes(self.ee.mem_read(SCRATCH, 103))
        self.assertEqual((b'<', b'>'), (value[:1], value[-1:]))
        wrapped = value[1:-1].split(b'\0')[0]
        self.assertEqual(row.encoded, wrapped.replace(b'\n', b''))
        self.assertEqual(1, wrapped.count(b'\n'))
        self.assertEqual(448, struct.unpack('<I', self.ee.mem_read(TEXT + 0x100, 4))[0])

    def test_native_layout_rejects_bad_input_without_touching_destination(self):
        for bad in (b'\x82\0', b'%\0', b'\x82\x20\0', b'\x82\x60' * 29 + b'\0', b'A' * 101):
            with self.subTest(bad=bad):
                self.ee.mem_write(TEXT, b'\0' * 200)
                self.ee.mem_write(TEXT, bad)
                self.ee.mem_write(SCRATCH, b'\xa5' * 103)
                result = self.pipeline.execute(
                    self.entries['choice_layout'], args=(TEXT, SCRATCH + 1, TEXT + 0x100, 0))
                self.assertEqual(0, result.v0)
                self.assertEqual(b'\xa5' * 103, bytes(self.ee.mem_read(SCRATCH, 103)))

    def test_build_mutates_only_verified_callsites_and_retains_all_stock_native_owners(self):
        from hashlib import sha256
        from tools.r67o_choices import OWNER_CALLS, build

        old = ELF.read_bytes()
        result, report = candidate()
        repeat, repeat_report = build(old, checked_corpus(SUPPLEMENT.is_file()))
        self.assertEqual(result, repeat)
        self.assertEqual(report, repeat_report)
        self.assertEqual(report['result_sha256'], sha256(result).hexdigest())
        self.assertEqual(set(OWNER_CALLS),
                         {owner['address'] for owner in report['call_sites']})
        self.assertEqual(len(old), report['appended_extent'][0])
        self.assertGreater(report['remaining_reserved_bytes'], 0)
        for address in (0x24EA58, 0x24EBB0, 0x259D90, 0x215AA0, 0x22C6C0,
                        0x1029B0, 0x1025E0, 0x18C1D0, 0x18C670, 0x18C7B0):
            off = address - 0xFFF80
            self.assertEqual(old[off:off + 8], result[off:off + 8])
        changed = {i for i, (before, after) in enumerate(zip(old, result)) if before != after}
        self.assertEqual(changed, set(report['changed_existing_offsets']))
        registered = {i for lo, hi in report['allowed_existing_ranges'] for i in range(lo, hi)}
        self.assertFalse(changed - registered)

    def test_display_line_feed_uses_the_last_available_byte(self):
        before = b'\x82\x60' * 22 + b' ' * 11 + b'\x82\x60' * 22
        for extra, expected in ((b'', 55), (b' ', 0)):
            self.ee.mem_write(SCRATCH, b'<' + b'\xdd' * 101 + b'>')
            self.ee.mem_write(TEXT, before + extra + b'\0')
            result = self.pipeline.execute(
                self.entries['choice_layout'], args=(TEXT, SCRATCH + 1, TEXT + 0x100, 0))
            self.assertEqual(expected, result.v0)
            written = bytes(self.ee.mem_read(SCRATCH, 103))
            if expected:
                self.assertEqual(100, len(written[1:-1].split(b'\0')[0]))
                self.assertEqual(before, written[1:-2].replace(b'\n', b''))
            else:
                self.assertEqual(b'\xdd' * 101, written[1:-1])
            self.assertEqual((b'<', b'>'), (written[:1], written[-1:]))
