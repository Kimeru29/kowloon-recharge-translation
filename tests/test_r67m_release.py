"""Mandatory installed-candidate checks for the cumulative script/wheel release."""
import hashlib
import json
import mmap
import unittest
from pathlib import Path

from tools.iso9660_patch import find_record, index_iso
from tools.r67m_cumulative import sha_file

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'local/r67m-integration/release-20261031'
EXPECTED_ISO_SHA256 = '3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f'
EXPECTED_WHEEL_SHA256 = 'd92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee'


class InstalledCumulativeReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((RELEASE / 'release-report.json').read_text())
        cls.candidate = RELEASE / '67.15m-cumulative-script-wheel.iso'

    def test_exact_candidate_identity_and_current_preservation_gates(self):
        self.assertEqual(sha_file(self.candidate), EXPECTED_ISO_SHA256)
        self.assertEqual(self.report['candidate_iso_sha256'], EXPECTED_ISO_SHA256)
        self.assertEqual(self.report['newly_installed_script_files'], 28)
        self.assertEqual(self.report['newly_installed_official_entries'], 33801)
        self.assertEqual(self.report['whole_iso_audit']['unexplained_bytes'], 0)
        self.assertEqual(self.report['whole_iso_audit']['complete_disc_bytes_compared'], 2095382528)
        self.assertEqual(self.report['rofs']['embedded_rofs_file_records'], 10656)
        self.assertEqual(self.report['rofs']['mismatches'], 0)
        self.assertEqual(self.report['static_reports']['startup_scoped']['checks_passed'], 155)
        self.assertEqual(len(self.report['static_locks']['history_lock_regions']), 4)
        self.assertEqual(self.report['static_locks']['save_identity']['native_save_descriptors'], 15)
        self.assertFalse(self.report['runtime_verified'])

    def test_installed_scripts_wheel_and_approved_group4_match_exact_expected_payloads(self):
        with self.candidate.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            _, outer = index_iso(image)
            cvm = find_record(outer, 'DATA.CVM')
            base = cvm.extent * 2048 + 0x1800
            _, records = index_iso(image, base)
            expected = {row['path']: row['output_sha256'] for row in self.report['assets']}
            expected['BLBRD/B_GP001.BIN'] = EXPECTED_WHEEL_SHA256
            expected['BLBRD/B_GP004.BIN'] = '9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a'
            for path, digest in expected.items():
                record = find_record(records, path)
                start = base + record.extent * 2048
                self.assertEqual(hashlib.sha256(image[start:start + record.size]).hexdigest(), digest, path)
            self.assertTrue(self.report['emotion_wheel']['exact_15l_art_included'])


if __name__ == '__main__':
    unittest.main()
