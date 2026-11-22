from pathlib import Path
import tempfile
import unittest

from tools.corpus import scan_corpus
from tools.exact_import import import_exact_mtx
from tools.r67n_inventory import japanese_runs, exact_evidence, physical_labels, relation_name


class InventoryTests(unittest.TestCase):
    def test_text_scan_starts_after_header_and_does_not_treat_cp932_trail_as_opcode(self):
        # Two CP932 characters, the first with ASCII-looking trail byte 0x72.
        pair = '詠'.encode('cp932')
        self.assertEqual(pair[-1], 0x72)
        raw = b'\x01\0\0\0' + pair + '見'.encode('cp932') + b'wc_\0'
        self.assertEqual([(s, e) for s, e, _ in japanese_runs(raw, 4)], [(4, 8)])
        self.assertEqual(list(japanese_runs('見る'.encode('cp932') + b'commands_', 4)), [])

    def test_control_only_file_emits_no_japanese_or_dc_entry_estimate(self):
        self.assertEqual(list(japanese_runs(b'\x01\0\0\0edonsclononedoffbt600_\0\0', 4)), [])

    def test_missing_counterpart_is_an_unresolved_relation(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root/'ps2').mkdir()
            (root/'ps4').mkdir()
            (root/'ps2'/'A.MTX').write_bytes(b'\1\0\0\0_\0\0\0')
            row = scan_corpus(root/'ps2', root/'ps4')['assets'][0]
            self.assertEqual(relation_name(row), 'missing counterpart; correspondence unresolved')

    def test_exact_payload_replay_yields_mapped_byte_ranges_and_rejects_drift(self):
        raw = b'\1\0\0\0' + '見る'.encode('cp932') + b'wc_\0'
        dc = {'keys':[4,5], 'values':['Look', 'See']}
        result = import_exact_mtx(raw, raw, dc)
        rows = exact_evidence(raw, raw, dc, result)
        self.assertEqual(set(rows), {4, 5})
        self.assertEqual(rows[5]['installed_offset'], 13)
        with self.assertRaisesRegex(ValueError, 'replay'):
            exact_evidence(raw, raw, dc, result[:-1] + b'x')
        with self.assertRaisesRegex(ValueError, 'source'):
            exact_evidence(raw, raw[:-1]+b'x', dc, result)

    def test_ksf_native_scan_excludes_japanese_in_control_data(self):
        raw = bytearray(b'\1\0' + bytes(2320))
        raw[10:14] = '見る'.encode('cp932')
        self.assertEqual(list(physical_labels(bytes(raw))), [])
        with self.assertRaisesRegex(ValueError, 'record'):
            list(physical_labels(bytes(raw[:-1])))
