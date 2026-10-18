import unittest
from tools import r67_15j_iso_release as release


class ReleaseTests(unittest.TestCase):
    def test_rejects_wrong_source_before_composition(self):
        with self.assertRaisesRegex(ValueError,'15i input'):
            release.prepare(b'wrong')

    def test_all_components_compose_deterministically_with_narrow_ownership(self):
        source=release.SOURCE_ELF.read_bytes()
        prepared=release.prepare(source)
        self.assertEqual(prepared,release.prepare(source))
        self.assertEqual([row['component'] for row in prepared.components],
                         [name for name,_ in release.COMPONENTS])
        # The accepted card, bubble, pool and visibility fixes are not replaced.
        for lo,hi in ((0xDB44,0xDB48),(0x14B58,0x14B5C),(0x18FDD4,0x18FECC)):
            self.assertEqual(source[lo:hi],prepared.candidate[lo:hi])
        self.assertGreater(len(prepared.candidate),len(source))

    def test_prior_user_approval_is_not_candidate_runtime_approval(self):
        report=release.runtime_status()
        self.assertTrue(report['prior_doorway_user_confirmed'])
        self.assertTrue(report['prior_hant_visibility_user_confirmed'])
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['gameplay_approved'])
        self.assertEqual(report['unresolved_details_translations'],36)
        self.assertEqual(report['unresolved_dungeon_action_translations'],1)

    def test_unowned_mutation_is_rejected_by_stage_audit(self):
        from tools import r67_15h_iso_release as stages
        def corrupt(source):
            result=bytearray(source);result[0x200]^=1
            return bytes(result),{}
        with self.assertRaises(ValueError):
            stages._prepare_stages(release.SOURCE_ELF.read_bytes(),(('bad',corrupt,{}),))
