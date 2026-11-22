from __future__ import annotations

import struct
import unittest

from tools.localization import encode_ps2_english
from tools.mtx import MtxFile, MtxReplacement
from tools.r67n_names import repair_exact


class NameRepairTests(unittest.TestCase):
    def setUp(self):
        first = b'px' + 'あ'.encode('cp932') + b'r' + 'いう'.encode('cp932') + b'wc_'
        self.raw = struct.pack('<4H', 2, 5, 0, 0) + first + 'え'.encode('cp932') + b'wc_\0\0\0'
        self.dc = {'keys': [8, 13, 20], 'values': ['First', '(pn1) (pm1), (px).', 'Done']}
        self.legacy = MtxFile.parse(self.raw).apply_replacements(tuple(
            MtxReplacement(a, b, encode_ps2_english(line))
            for (a,b),line in zip(((8,12),(13,17),(20,22)), self.dc['values'])
        )).compile()

    def test_full_replay_repairs_only_literal_names_and_maps_each_group(self):
        result = repair_exact(self.raw,self.raw,self.dc,self.legacy)
        self.assertEqual('repaired',result.status)
        expected = b'pn'+encode_ps2_english(' ')+b'pm'+encode_ps2_english(', ')+b'px'+encode_ps2_english('.')
        group = result.groups[1]
        self.assertEqual(expected, result.output[group['output_start']:group['output_end']])
        self.assertEqual([8,13,20],[g['source_start'] for g in result.groups])
        self.assertIn(b'wc_',result.output)
        self.assertEqual(1,result.output.count(b'px'))
        self.assertEqual(result,repair_exact(self.raw,self.raw,self.dc,self.legacy))
        self.assertEqual('already_native',repair_exact(self.raw,self.raw,self.dc,result.output).status)
        for occurrence in result.occurrences:
            self.assertEqual(occurrence['control'].encode(),result.output[occurrence['output_offset']:occurrence['output_offset']+2])

    def test_refuses_unversioned_drift_and_unsupported_control(self):
        with self.assertRaisesRegex(ValueError,'identical'):
            repair_exact(self.raw,self.raw+b'x',self.dc,self.legacy)
        with self.assertRaisesRegex(ValueError,'installed'):
            repair_exact(self.raw,self.raw,self.dc,self.legacy+b'x')
        with self.assertRaisesRegex(ValueError,'Unsupported'):
            repair_exact(self.raw,self.raw,{'keys':[8],'values':['(pmyh)']},self.legacy)

    def test_structural_replays_pinned_cluster_without_matching_new_text(self):
        from tools.r67n_names import repair_structural
        ps4 = self.raw[:8] + 'あい'.encode('cp932') + self.raw[12:]
        spans = [
            {'first_group': 0, 'last_group': 1, 'ps4_start': 8, 'ps4_end': 17,
             'ps2_start': 8, 'ps2_end': 17},
            {'first_group': 2, 'last_group': 2, 'ps4_start': 20, 'ps4_end': 22,
             'ps2_start': 20, 'ps2_end': 22}]
        result = repair_structural(self.raw,ps4,self.dc,self.legacy,spans)
        self.assertEqual(result.output,repair_exact(self.raw,self.raw,self.dc,self.legacy).output)
        self.assertEqual([8,13,20],[g['source_start'] for g in result.groups])
        self.assertEqual([8,13,20],[line['dc_key'] for group in result.groups for line in group['lines']])
        with self.assertRaisesRegex(ValueError,'group'):
            repair_structural(self.raw,ps4,self.dc,self.legacy,spans[:1])
        with self.assertRaisesRegex(ValueError,'installed'):
            repair_structural(self.raw,ps4,self.dc,self.legacy[:-1],spans)

    def test_known_speaker_control_can_be_inserted_into_owned_english_line(self):
        source = struct.pack('<2H', 1, 0) + b'bg79' + '日本語'.encode('cp932') + b'wc_\0\0\0'
        dc = {'keys': [8], 'values': ['Yes, (px).']}
        legacy = MtxFile.parse(source).apply_replacements((
            MtxReplacement(8, 14, encode_ps2_english('Yes, (px).')),
        )).compile()
        result = repair_exact(source, source, dc, legacy)
        self.assertEqual(b'bg79', result.output[4:8])
        self.assertEqual(b'wc_', result.output[result.groups[0]['output_end']:].rstrip(b'\0'))
        self.assertEqual(1, result.output.count(b'px'))

    def test_duplicate_pointer_slots_keep_the_same_target_after_shortening(self):
        raw = bytearray(self.raw)
        struct.pack_into('<H', raw, 4, 5)
        legacy = bytearray(self.legacy)
        struct.pack_into('<H', legacy, 4, struct.unpack_from('<H', legacy, 2)[0])
        repaired = repair_exact(bytes(raw), bytes(raw), self.dc, bytes(legacy))
        header = MtxFile.parse(repaired.output).pointer_offsets
        self.assertEqual(header[1], header[2])
        self.assertEqual(header[1], repaired.groups[2]['output_start'])
