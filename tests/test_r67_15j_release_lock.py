"""Pin the published diagnostic separately from any gameplay acceptance."""
import hashlib
import json
import mmap
import unittest
from tools import r67_15j_iso_release as release
from tools import r67_15g_iso_release as audit

ELF_SHA256='6ebb80d3346f4f5ab68bc49197419658603b14686e4a8b549b451c1c8d7e76d8'
ISO_SHA256='26ced321471b4415c2a855079c778502ed7c043d2e9467c8c1edc1833b58a079'


class ReleaseLockTests(unittest.TestCase):
    def test_composition_reproduces_locked_executable(self):
        candidate=release.prepare(release.SOURCE_ELF.read_bytes()).candidate
        self.assertEqual(hashlib.sha256(candidate).hexdigest(),ELF_SHA256)

    @unittest.skipUnless(release.OUTPUT_ISO.exists(),'Requires local r67.15j diagnostic ISO')
    def test_finished_artifact_matches_installed_executable_and_audit(self):
        self.assertEqual(audit.sha_file(release.OUTPUT_ISO),ISO_SHA256)
        elf=release.OUTPUT_ELF.read_bytes()
        self.assertEqual(hashlib.sha256(elf).hexdigest(),ELF_SHA256)
        with release.OUTPUT_ISO.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as image:
            record,offset,*_=audit._installed_records(image)
            self.assertEqual(bytes(image[offset:offset+record.size]),elf)
        report=json.loads(release.OUTPUT_REPORT.read_text())
        self.assertEqual(report['candidate_iso_sha256'],ISO_SHA256)
        self.assertEqual(report['whole_iso_audit']['unexplained_bytes'],0)
        self.assertEqual(report['whole_iso_audit']['complete_disc_bytes_compared'],2095382528)
        self.assertEqual(report['startup_scoped']['checks_passed'],155)
        self.assertEqual(len(report['history']['verified_regions']),4)
        self.assertEqual(report['save']['native_save_descriptors'],15)
        self.assertFalse(report['runtime_verified'])
