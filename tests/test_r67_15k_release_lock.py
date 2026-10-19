"""Pin the corrected diagnostic without implying gameplay acceptance."""
import hashlib
import json
import mmap
import unittest

from tools import r67_15k_iso_release as release
from tools import r67_15g_iso_release as audit
from tools.r67_15k_kernel import audit_ee_cop1

ELF_SHA256 = 'fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d'
ISO_SHA256 = 'ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53'


class ReleaseLockTests(unittest.TestCase):
    def test_composition_reproduces_locked_executable(self):
        candidate = release.prepare(release.SOURCE_ELF.read_bytes()).candidate
        self.assertEqual(hashlib.sha256(candidate).hexdigest(), ELF_SHA256)

    @unittest.skipUnless(release.OUTPUT_ISO.exists(), 'Requires local r67.15k diagnostic ISO')
    def test_finished_artifact_matches_installed_executable_and_audit(self):
        self.assertEqual(audit.sha_file(release.OUTPUT_ISO), ISO_SHA256)
        elf = release.OUTPUT_ELF.read_bytes()
        self.assertEqual(hashlib.sha256(elf).hexdigest(), ELF_SHA256)
        with release.OUTPUT_ISO.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            record, offset, *_ = audit._installed_records(image)
            self.assertEqual(bytes(image[offset:offset + record.size]), elf)
        report = json.loads(release.OUTPUT_REPORT.read_text())
        self.assertEqual(report['candidate_iso_sha256'], ISO_SHA256)
        self.assertEqual(report['candidate_elf_sha256'], ELF_SHA256)
        self.assertEqual(report['whole_iso_audit']['unexplained_bytes'], 0)
        self.assertEqual(report['whole_iso_audit']['complete_disc_bytes_compared'], 2095382528)
        self.assertTrue(report['whole_iso_audit']['data_cvm_byte_identical'])
        self.assertEqual(report['startup_raw']['checks_passed'], 154)
        self.assertEqual(report['startup_scoped']['checks_passed'], 155)
        self.assertEqual(len(report['history']['verified_regions']), 4)
        self.assertEqual(report['save']['native_save_descriptors'], 15)
        self.assertEqual(report['finished_resource_lookup']['embedded_rofs_file_records'], 10656)
        self.assertFalse(report['runtime_verified'])
        self.assertFalse(report['gameplay_approved'])
        kernel = report['components'][0]['report']['kernel']
        code_offset = 0x803150 + kernel['entry_va'] - 0x902f00
        audit_ee_cop1(elf[code_offset:code_offset + kernel['text_size']], kernel['entry_va'])


if __name__ == '__main__':
    unittest.main()
