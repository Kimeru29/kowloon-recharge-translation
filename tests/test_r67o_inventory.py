from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import struct
import unittest

from tools import r67o_inventory as inventory
from tools.r67o_choices import ChoiceCorpus, ChoiceFile, ChoiceRecord, ChoiceRow


def digest(raw):
    return sha256(raw).hexdigest()


class ContinuationInventoryTests(unittest.TestCase):
    def test_checks_full_installed_range_and_its_absolute_coordinate(self):
        row = {'installed_offset': 1, 'installed_length': 2, 'installed_iso_offset': 101,
               'installed_bytes_sha256': digest(b'bc')}
        inventory.verify_installed_range(row, b'abcd', 100)
        with self.assertRaisesRegex(ValueError, 'installed range'):
            inventory.verify_installed_range(row, b'aBcd', 100)
        with self.assertRaisesRegex(ValueError, 'installed range'):
            inventory.verify_installed_range(row, b'abcd', 200)

    def test_changed_raw_source_fails_its_fingerprint(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'SOURCE.MTX'
            path.write_bytes(b'a\0b')
            self.assertEqual(b'a\0b', inventory.read_pinned(path, digest(b'a\0b')))
            path.write_bytes(b'a\0c')
            with self.assertRaisesRegex(ValueError, 'hash drift'):
                inventory.read_pinned(path, digest(b'a\0b'))

    def test_pairs_official_entries_by_array_index_even_with_repeated_key(self):
        entries = [
            {'file': 'FN/SCENE.MTX', 'official_array_index': i, 'dc_key': 9,
             'official_text_utf8_sha256': digest(text.encode())}
            for i, text in enumerate(('One', 'Two'))
        ]
        dc = {'keys': [9, 9], 'values': ['One', 'Two']}
        inventory.verify_dc_rows('FN/SCENE.MTX', entries, dc)
        with self.assertRaisesRegex(ValueError, 'official DC identity'):
            inventory.verify_dc_rows('FN/SCENE.MTX', entries, {**dc, 'values': ['Two', 'One']})
        with self.assertRaisesRegex(ValueError, 'official DC identity'):
            inventory.verify_dc_rows('FN/SCENE.MTX', [entries[0], entries[0]], dc)

    def test_projects_aliases_and_unaligned_tail_after_insertion(self):
        before = struct.pack('<4H', 2, 4, 4, 0) + b'JPEn_\0\0\0' + b'wcZ'
        after = struct.pack('<4H', 2, 5, 5, 0) + b'LONGEEn_\0\0\0\0' + b'wcZ'
        edit = inventory.Edit(8, 10, 8, 13, digest(b'JP'), digest(b'LONGE'), (0,))
        projection = inventory.PositionMap(before, after, [edit])
        self.assertEqual(13, projection.at(10, 2))
        self.assertEqual(22, projection.at(18, 1))
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            projection.at(9, 2)
        with self.assertRaisesRegex(ValueError, 'pointer'):
            inventory.PositionMap(before, after[:4] + b'\0\0' + after[6:], [edit])
        with self.assertRaisesRegex(ValueError, 'unchanged'):
            inventory.PositionMap(before, after[:-1] + b'X', [edit])

    def test_alternate_asset_keeps_logical_identity(self):
        rows = {('MS/MS01_03.MTX', 7): {
            'file': 'MS/MS01_03.MTX', 'official_array_index': 7, 'dc_key': 33,
            'status': inventory.UNRESOLVED,
        }}
        inventory.install_mtx_entry(rows, ('MS/MS01_03.MTX', 7), 33, 'KWLNSCR.MTX',
                                    (10, 14), digest(b'line'), 'exact', 100)
        self.assertEqual(1, len(rows))
        self.assertEqual('MS/MS01_03.MTX', rows['MS/MS01_03.MTX', 7]['file'])
        self.assertEqual('KWLNSCR.MTX', rows['MS/MS01_03.MTX', 7]['installed_asset'])
        self.assertEqual(110, rows['MS/MS01_03.MTX', 7]['installed_iso_offset'])
        inventory.project_inherited('MS/MS01_03.MTX', rows.values(), b'control', 200)
        self.assertEqual(110, rows['MS/MS01_03.MTX', 7]['installed_iso_offset'])
        with self.assertRaisesRegex(ValueError, 'already installed'):
            inventory.install_mtx_entry(rows, ('MS/MS01_03.MTX', 7), 33, 'KWLNSCR.MTX',
                                        (10, 14), digest(b'line'), 'exact', 100)

    def test_choice_table_rejects_hash_pointer_and_preimage_drift(self):
        base = 0x900000
        raw = b'J' * 30
        file = ChoiceFile('x.KSF', b'adv/x.KSF', 2400, '', '', '', '')
        row = ChoiceRow('x.KSF', 4, 64, 85, 0, 'A', b'\x81\x40', (0x4081,), raw, raw, '')
        record = ChoiceRecord(file.loaded_name, 3, 40, b'\x01\0\0\0',
                              b'\x02' + bytes(37), (row,))
        corpus = ChoiceCorpus((file,), (record,), ())
        table = (struct.pack('<20sI', file.loaded_name, file.installed_size)
                 + struct.pack('<IHH4s38s2x4I', 40, 0, 3, record.flags, record.header,
                               base + 92, 0, 0, 0)
                 + raw * 2 + b'\x81\x40\0')

        def check(data, expected_hash):
            return inventory.read_choice_rows(data, base, corpus, expected_hash)

        self.assertEqual({('x.KSF', 4): (152, 2)}, check(table, digest(table)))
        with self.assertRaisesRegex(ValueError, 'table hash'):
            check(table[:-2], digest(table))
        bad_ptr = table[:76] + struct.pack('<I', base + 93) + table[80:]
        with self.assertRaisesRegex(ValueError, 'row pointer'):
            check(bad_ptr, digest(bad_ptr))
        bad_preimage = table[:92] + b'X' + table[93:]
        with self.assertRaisesRegex(ValueError, 'preimage'):
            check(bad_preimage, digest(bad_preimage))

    def test_reused_speaker_counts_occurrences_without_installing_source_rows(self):
        occurrences = [
            {'file': name, 'official_proof_id': 'same'} for name in ('FD/ONE.MTX', 'FD/TWO.MTX')
        ]
        definitions = {'same': {'ps4_dc': [{'keys': [11, 12]}]}}
        counts = inventory.speaker_counts(definitions, occurrences)
        self.assertEqual({'verified_fixed_label_pairs': 1, 'used_fixed_label_pairs': 1,
                          'localized_occurrences': 2, 'affected_files': 2}, counts)
