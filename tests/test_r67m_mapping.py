"""Adversarial checks for the recovered script correspondence rules."""
import struct
import unittest

from tools.localization import DcLocalization, encode_ps2_english
from tools.structural_import import StructuralImportError, import_structural_mtx


def script(body):
    return struct.pack('<4H', 2, 2, 2, 2) + body + b'_'


class RecoveredMappingTests(unittest.TestCase):
    def test_first_and_last_name_placeholders_keep_native_commands_in_english_order(self):
        raw = script(b'pm' + '　'.encode('cp932') + b'pn' + 'です'.encode('cp932') + b'wc')
        group = DcLocalization.from_json(raw, {'keys': [8], 'values': ['(pn1) (pm1)']}).groups[0]
        self.assertEqual(group.encoded_replacement(), b'pn' + encode_ps2_english(' ') + b'pm')

    def test_first_name_placeholder_requires_matching_source_command(self):
        raw = script(b'px' + '名前'.encode('cp932') + b'wc')
        with self.assertRaisesRegex(ValueError, 'substitution|control'):
            DcLocalization.from_json(raw, {'keys': [8], 'values': ['(pn1)']})

    def test_name_placeholder_remains_native_control_between_english_glyphs(self):
        raw = script('君は'.encode('cp932') + b'px' + 'だ'.encode('cp932') + b'wc')
        group = DcLocalization.from_json(raw, {'keys': [8], 'values': ['Hello, (px)!']}).groups[0]
        self.assertEqual(group.encoded_replacement(),
                         encode_ps2_english('Hello, ') + b'px' + encode_ps2_english('!'))

    def test_name_placeholder_without_source_control_is_rejected(self):
        raw = script('名前'.encode('cp932') + b'wc')
        with self.assertRaisesRegex(ValueError, 'substitution|control'):
            DcLocalization.from_json(raw, {'keys': [8], 'values': ['Hello, (px)!']})

    def test_unknown_name_macro_fails_closed(self):
        raw = script(b'pmyh' + '名前'.encode('cp932') + b'wc')
        with self.assertRaisesRegex(ValueError, 'substitution|control'):
            DcLocalization.from_json(raw, {'keys': [8], 'values': ['(pmyh)']})

    def test_nonconsecutive_boundary_key_does_not_become_synthetic(self):
        raw = script('二文字'.encode('cp932') + b'wc')
        with self.assertRaisesRegex(ValueError, 'terminator'):
            DcLocalization.from_json(raw, {'keys': [8, 10], 'values': ['First', 'Second']})

    def test_terminator_key_cannot_be_swallowed_as_continuation(self):
        raw = script('字'.encode('cp932') + b'wc')
        with self.assertRaises(ValueError):
            DcLocalization.from_json(raw, {'keys': [8, 9, 10], 'values': ['One', 'Two', 'Three']})

    def test_two_byte_continuation_chain_retains_order_and_terminator(self):
        raw = script('三文字'.encode('cp932') + b'wc')
        group = DcLocalization.from_json(raw, {'keys': [8, 9, 10],
                                               'values': ['First', 'Second', 'Third']}).groups[0]
        self.assertEqual(group.synthetic_keys, (9, 10))
        self.assertEqual(group.lines, ('First', 'Second', 'Third'))
        self.assertEqual(raw[group.replace_end:group.replace_end + 2], b'wc')

    def test_numeric_drift_does_not_prove_a_short_repeated_speaker(self):
        text = '【皆守】'.encode('cp932')
        ps4 = script(b'ch001' + text + b'wc_aaaa_ch001' + text + b'wc')
        ps2 = script(b'ch002' + text + b'wc_bbbb_ch002' + text + b'wc')
        dc = {'keys': [ps4.index(text)], 'values': ['【Minakami】']}
        with self.assertRaisesRegex(StructuralImportError, 'could not prove'):
            import_structural_mtx(ps2, ps4, dc)

    def test_unique_long_exact_context_can_anchor_a_speaker_without_numeric_normalization(self):
        name = '【皆守】'.encode('cp932')
        context = ('この文章は同じ場面でしか登場しない十分に長い台詞です。' * 2).encode('cp932')
        ps4 = script(b'ch001' + name + b'wcr' + context + b'wc')
        ps2 = script(b'ch002' + name + b'wcr' + context + b'wc')
        result = import_structural_mtx(ps2, ps4, {'keys': [ps4.index(name)], 'values': ['【Minakami】']})
        self.assertIn(b'ch002' + encode_ps2_english('【Minakami】'), result.data)
        self.assertIn(context, result.data)
        self.assertEqual(result.spans[0].mode, 'unique_context')


if __name__ == '__main__':
    unittest.main()
