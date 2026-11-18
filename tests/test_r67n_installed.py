"""Hash-pinned installed diagnostic checks; mandatory in the release environment."""
import json
import mmap
import os
from pathlib import Path
import unittest

from tools.iso9660_patch import find_record, index_iso
from tools.r67m_cumulative import audit_candidate, sha_file
from tools.r67n_release import digest
from tools.translation_overlay import collect_overlay

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "local/r67n-release"


class InstalledOfficialScriptDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidate = RELEASE / "67.15n-official-script-diagnostic.iso"
        if not cls.candidate.exists() and not os.environ.get("R67N_REQUIRED"):
            raise unittest.SkipTest("Owned r67.15n diagnostic fixture unavailable")
        cls.report = json.loads((RELEASE / "release-report.json").read_text())
        cls.lock = json.loads((ROOT / "translations/r67n_release_lock.json").read_text())

    def test_hash_identity_and_explicit_static_acceptance_boundary(self):
        self.assertEqual(sha_file(self.candidate), self.lock["candidate_iso_sha256"])
        self.assertEqual(self.report["candidate_iso_sha256"], self.lock["candidate_iso_sha256"])
        self.assertEqual(self.report["manifest_sha256"], sha_file(ROOT / "translations/r67n_script_transfer.json"))
        self.assertEqual(self.report["summary"]["new_mtx_official_entries"], 5275)
        self.assertEqual(self.report["summary"]["new_ksf_official_entries"], 116)
        self.assertEqual(self.report["summary"]["name_repair_occurrences"], 1288)
        self.assertEqual(self.report["rofs"]["embedded_rofs_file_records"], 10656)
        self.assertEqual(self.report["rofs"]["mismatches"], 0)
        self.assertEqual(self.report["static_reports"]["startup_scoped"]["checks_passed"], 155)
        self.assertEqual(len(self.report["static_locks"]["history_lock_regions"]), 4)
        self.assertEqual(self.report["static_locks"]["save_identity"]["native_save_descriptors"], 15)
        self.assertFalse(self.report["runtime_verified"])
        self.assertFalse(self.report["gameplay_approved"])

    def test_all_installed_delta_resources_and_original_wheel_match(self):
        with self.candidate.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            _, outer = index_iso(image)
            base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
            _, records = index_iso(image, base)
            expected = {"ADV/" + row["path"]: row["output_sha256"] for row in self.report["assets"]}
            expected["BLBRD/B_GP001.BIN"] = self.lock["wheel_sha256"]
            expected["BLBRD/B_GP004.BIN"] = self.lock["group4_sha256"]
            for path, fingerprint in expected.items():
                record = find_record(records, path)
                start = base + record.extent * 2048
                self.assertEqual(digest(image[start:start + record.size]), fingerprint, path)

    def test_independent_whole_disc_audit_reproduces_every_byte(self):
        baseline = ROOT / "local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso"
        overlay = collect_overlay([("verified-r67n-delta", ROOT / "local/r67n-release-inputs/overlay")])
        audit = audit_candidate(baseline, self.candidate, overlay)
        self.assertEqual(audit["unexplained_bytes"], 0)
        self.assertEqual(audit["complete_disc_bytes_compared"], 2095382528)
        self.assertEqual(audit["expected_and_actual_iso_sha256"], self.lock["candidate_iso_sha256"])


if __name__ == "__main__":
    unittest.main()
