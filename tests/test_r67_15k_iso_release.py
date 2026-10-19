import unittest
from tools import r67_15k_iso_release as release


class DescriptionReleaseTests(unittest.TestCase):
    def test_wrong_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, '15j input'):
            release.prepare(b'wrong')

    def test_deterministic_composition_keeps_every_unowned_j_byte(self):
        source = release.SOURCE_ELF.read_bytes()
        result = release.prepare(source)
        self.assertEqual(result, release.prepare(source))
        self.assertEqual([r['component'] for r in result.components], ['description_wrap'])
        for lo, hi in ((0xdb44, 0xdb48), (0x14b58, 0x14b5c),
                       (0x154d8, 0x15640), (0x18fdd4, 0x18fecc)):
            self.assertEqual(result.candidate[lo:hi], source[lo:hi])

    def test_user_confirmation_is_not_new_runtime_approval(self):
        status = release.runtime_status()
        self.assertTrue(status['prior_doorway_user_confirmed'])
        self.assertTrue(status['prior_hant_visibility_user_confirmed'])
        self.assertFalse(status['runtime_verified'])
        self.assertFalse(status['gameplay_approved'])
        self.assertEqual(status['unresolved_details_translations'], 36)


if __name__ == '__main__':
    unittest.main()
