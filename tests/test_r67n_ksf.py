import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.ksf_import import import_exact_ksf
from tools.r67n_ksf import audit_file, generate, verify_native_reader, native_slots


def scenario(labels, next_type=2):
    record = bytearray(0x90c)
    record[0] = 2
    keys = []
    for value in labels:
        record.append(1)
        keys.append(2 + len(record))
        record.extend(value.encode('cp932').ljust(30, b'\0'))
    record.extend(bytes(4 - len(labels)))
    tail = bytearray(2320)
    tail[0] = next_type
    tail[2] = 7
    return b'\x02\0' + bytes(record + tail), keys


class NativeChoiceTests(unittest.TestCase):
    def test_crossed_active_label_is_restored_without_touching_next_label(self):
        raw, keys = scenario(['選', '見'])
        dc = {'keys': keys, 'values': ['a' * 30, 'Look']}
        installed, _ = import_exact_ksf(raw, raw, dc)
        output, rows = audit_file('test.KSF', raw, raw, dc, installed)
        self.assertEqual(output[keys[0]:keys[0]+30], raw[keys[0]:keys[0]+30])
        self.assertEqual(output[keys[0]+30:], installed[keys[0]+30:])
        self.assertEqual(rows[0]['classification'], 'deliberate technical-safety fallback')
        self.assertGreater(rows[0]['installed_first_nul_distance'], 30)

    def test_crossed_inactive_flag_and_next_record_header_are_repaired(self):
        raw, keys = scenario(['選', '見'], next_type=0)
        dc = {'keys': [keys[1]], 'values': ['x' * 33]}
        installed, _ = import_exact_ksf(raw, raw, dc)
        output, rows = audit_file('test.KSF', raw, raw, dc, installed)
        self.assertEqual(output, raw)
        self.assertEqual(rows[0]['restored_structural_offsets'], list(range(keys[1]+30, keys[1]+33)))

    def test_four_exact_cp932_blank_rows_are_verified_without_writes(self):
        values = ['\u3000' * n for n in [4, 6, 3, 5]]
        raw, keys = scenario(values)
        dc = {'keys': keys, 'values': values}
        out, rows = audit_file('test.KSF', raw, raw, dc, raw)
        self.assertEqual(raw, out)
        self.assertEqual([r['classification'] for r in rows], ['official U+3000 no-op'] * 4)

    def test_rejects_source_mismatch_and_unknown_installed_change(self):
        raw, keys = scenario(['選'])
        dc = {'keys': keys, 'values': ['See']}
        installed, _ = import_exact_ksf(raw, raw, dc)
        with self.assertRaisesRegex(ValueError, 'byte-identical'):
            audit_file('test.KSF', raw, raw[:-1], dc, installed)
        with self.assertRaisesRegex(ValueError, 'installed'):
            audit_file('test.KSF', raw, raw, dc, installed[:-1] + b'x')

    def test_rejects_false_dc_key_and_incomplete_record(self):
        raw, keys = scenario(['選'])
        with self.assertRaisesRegex(ValueError, 'native label'):
            audit_file('test.KSF', raw, raw, {'keys':[keys[0]+1], 'values':['See']}, raw)
        with self.assertRaisesRegex(ValueError, 'record'):
            native_slots(raw[:-1])

    def test_native_anchor_rejects_instruction_drift(self):
        elf = Path('local/r67-15k-description-word-wrap.elf')
        if not elf.exists():
            self.skipTest('owned native ELF unavailable')
        data = bytearray(elf.read_bytes())
        verify_native_reader(data)
        data[0x22d144 - 0x100000 + 0x80] ^= 1
        with self.assertRaisesRegex(ValueError, 'native'):
            verify_native_reader(data)

    def test_29_bytes_plus_nul_preserve_the_last_byte(self):
        raw, keys = scenario(['選'])
        dc = {'keys': keys, 'values': ['t' * 29]}
        installed, _ = import_exact_ksf(raw, raw, dc)
        out, _ = audit_file('test.KSF', raw, raw, dc, installed)
        self.assertEqual(out, installed)
        self.assertEqual(out[keys[0]:keys[0] + 30], b't' * 29 + b'\0')

    def test_rejects_blank_with_different_number_of_ideographic_spaces(self):
        raw, keys = scenario(['\u3000' * 4])
        with self.assertRaisesRegex(ValueError, 'unrecognized KSF'):
            audit_file('test.KSF', raw, raw, {'keys': keys, 'values': ['\u3000' * 3]}, raw)

    def test_owned_sources_reproduce_overlay_and_reject_stale_output(self):
        ps2 = Path('local/r67n-sources/assets/ADV')
        ps4 = Path('local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV')
        iso = Path('local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso')
        if not (ps2.is_dir() and ps4.is_dir() and iso.is_file()):
            self.skipTest('owned r67m KSF corpus unavailable')
        with TemporaryDirectory() as tmp:
            target = Path(tmp) / 'ksf'
            report = generate(ps2, ps4, iso, target)
            self.assertEqual(report['files_changed'], 8)
            self.assertEqual(report['classifications']['official U+3000 no-op'], 4)
            self.assertEqual(report['classifications']['deliberate technical-safety fallback'], 11)
            self.assertEqual(report['exceeds_native_with_accepted_spacing'], 59)
            self.assertEqual(report['exceeds_native_with_raw_spacing'], 112)
            self.assertEqual(report, generate(ps2, ps4, iso, target))
            (target / 'overlay' / 'unexpected.KSF').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError, 'already exists'):
                generate(ps2, ps4, iso, target)
