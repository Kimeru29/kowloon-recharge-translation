import struct
import unittest
from dataclasses import replace

from tools.iso9660_patch import IsoRecord
from tools.r67_15h_rofs_audit import audit_records


class RofsAuditTests(unittest.TestCase):
    def setUp(self):
        self.record = IsoRecord('DATA/AREA.BIN', 10, 32, 0, 0)
        self.original = bytearray(128)
        struct.pack_into('<I', self.original, 18, 32)
        struct.pack_into('<I', self.original, 26, 10)
        self.original[32:41] = b'AREA.BIN\0'

    def audit(self, candidate=None, records=None):
        return audit_records(bytes(self.original),
                             bytes(self.original) if candidate is None else candidate,
                             (self.record,), (self.record,) if records is None else records)

    def test_matches_installed_metadata_and_counts_relocation(self):
        candidate = bytearray(self.original)
        struct.pack_into('<I', candidate, 18, 64)
        struct.pack_into('<I', candidate, 26, 20)
        report = self.audit(candidate, (replace(self.record, extent=20, size=64),))
        self.assertEqual(report['embedded_rofs_file_records'], 1)
        self.assertEqual(report['relocated_or_resized_records'], 1)
        self.assertEqual(report['mismatches'], 0)

    def test_rejects_stale_size_or_extent(self):
        for change in ({'size': 33}, {'extent': 11}):
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, 'metadata mismatch'):
                self.audit(records=(replace(self.record, **change),))

    def test_rejects_missing_added_and_duplicate_files(self):
        for records in ((), (self.record, replace(self.record, path='EXTRA.BIN')),
                        (self.record, self.record)):
            with self.subTest(records=records), self.assertRaises(ValueError):
                self.audit(records=records)

    def test_rejects_changed_filename_and_truncated_candidate(self):
        candidate = bytearray(self.original)
        candidate[32] = ord('X')
        with self.assertRaisesRegex(ValueError, 'filename'):
            self.audit(candidate)
        with self.assertRaisesRegex(ValueError, 'outside'):
            self.audit(self.original[:30])

    def test_rejects_ambiguous_original_lookup(self):
        self.original.extend(self.original)
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            self.audit()

    def test_directories_are_excluded_but_empty_input_rejected(self):
        directory = IsoRecord('DATA', 1, 2048, 2, 0)
        report = audit_records(bytes(self.original), bytes(self.original),
                               (directory, self.record), (directory, self.record))
        self.assertEqual(report['embedded_rofs_file_records'], 1)
        with self.assertRaisesRegex(ValueError, 'empty'):
            audit_records(b'', b'', (directory,), (directory,))
