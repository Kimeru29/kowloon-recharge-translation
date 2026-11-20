import mmap
import tempfile
import unittest
from pathlib import Path

from tests.test_build_translation_iso import make_nested_iso
from tools.build_translation_iso import build_translation_iso
from tools.iso9660_patch import index_iso, find_record
from tools.translation_overlay import collect_overlay
from tools import r67m_cumulative as cumulative


class CumulativeAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.target = self.root / 'source.iso', self.root / 'target.iso'
        make_nested_iso(self.source)
        overlay = self.root / 'overlay' / 'DG'
        overlay.mkdir(parents=True)
        (overlay / 'A.MTX').write_bytes(b'E' * 3000)
        self.overlay = collect_overlay([('proven-script', overlay.parent)])
        build_translation_iso(self.source, self.target, self.overlay)

    def test_every_byte_matches_independently_derived_writes(self):
        report = cumulative.audit_candidate(self.source, self.target, self.overlay)
        self.assertEqual(report['unexplained_bytes'], 0)
        self.assertEqual(report['complete_disc_bytes_compared'], self.source.stat().st_size)
        self.assertTrue(report['native_elf_preserved_except_rofs'])

    def test_mutation_in_translated_payload_is_rejected(self):
        raw = bytearray(self.target.read_bytes())
        raw[raw.index(b'E' * 3000)] ^= 1
        self.target.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'Unexpected|expected'):
            cumulative.audit_candidate(self.source, self.target, self.overlay)

    def test_mutation_outside_all_owned_writes_is_rejected(self):
        with self.target.open('r+b') as stream:
            stream.write(b'X')
        with self.assertRaisesRegex(ValueError, 'Unexpected|expected'):
            cumulative.audit_candidate(self.source, self.target, self.overlay)

    def test_native_code_mutation_inside_elf_allocation_is_rejected(self):
        with self.target.open('r+b') as stream, mmap.mmap(stream.fileno(), 0) as image:
            _, records = index_iso(image)
            record = find_record(records, 'SLPM_665.11')
            image[record.extent * 2048 + 40] ^= 1
        with self.assertRaisesRegex(ValueError, 'Unexpected|expected'):
            cumulative.audit_candidate(self.source, self.target, self.overlay)

    def test_existing_destination_cannot_be_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'exists|collision'):
            cumulative.build(self.source, self.target, self.overlay)


if __name__ == '__main__':
    unittest.main()
