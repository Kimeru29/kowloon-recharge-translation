import unittest
from pathlib import Path
from tools import r67_15i_iso_release as release


class ReleaseTests(unittest.TestCase):
    def test_rejects_wrong_source_before_composition(self):
        with self.assertRaisesRegex(ValueError,'15h input'):
            release.prepare(b'wrong')

    def test_real_components_are_deterministic_and_owned(self):
        prepared=release.prepare(release.SOURCE_ELF.read_bytes())
        self.assertEqual(prepared,release.prepare(release.SOURCE_ELF.read_bytes()))
        self.assertEqual([x['component'] for x in prepared.components],['item_details','hant_text'])
        self.assertGreater(len(prepared.candidate),len(prepared.source))
        self.assertEqual(prepared.candidate[0xDB44:0xDB48],prepared.source[0xDB44:0xDB48])

    def test_runtime_report_distinguishes_prior_user_result(self):
        report=release.runtime_status()
        self.assertTrue(report['prior_15h_doorway_user_confirmed'])
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['gameplay_approved'])
        self.assertEqual(report['unresolved_details_translations'],36)
        self.assertTrue(report['main_integration_authorized'])
