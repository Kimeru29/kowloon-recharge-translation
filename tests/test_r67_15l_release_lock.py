"""Fail-closed lock for the built r67.15l diagnostic artifacts."""
import hashlib
import json
import mmap
import unittest

from tools import r67_15l_iso_release as release


# Replace only after the authorized build has completed and its artifact was audited.
EXPECTED_CANDIDATE_ISO_SHA256 = "c70dd6e70c9be85c05732bfc3f4fa60ff1c9e7c280470d7ebe9c76c7a7290f94"


class EmotionWheelReleaseLockTests(unittest.TestCase):
    def test_built_candidate_is_pinned_and_contains_the_prepared_resource(self):
        self.assertNotEqual(EXPECTED_CANDIDATE_ISO_SHA256, "PENDING_BUILD",
                            "Finalize this lock with the audited candidate SHA-256")
        self.assertTrue(release.OUTPUT_ISO.is_file(), f"Missing candidate ISO: {release.OUTPUT_ISO}")
        self.assertTrue(release.OUTPUT_ELF.is_file(), f"Missing installed ELF: {release.OUTPUT_ELF}")
        self.assertTrue(release.OUTPUT_REPORT.is_file(), f"Missing build report: {release.OUTPUT_REPORT}")

        self.assertTrue(release.OUTPUT_AUDIT.is_file(), f"Missing whole-ISO audit: {release.OUTPUT_AUDIT}")
        digest = release._sha_file(release.OUTPUT_ISO)
        self.assertEqual(digest, EXPECTED_CANDIDATE_ISO_SHA256)
        replacement, components = release.prepare()
        report = json.loads(release.OUTPUT_REPORT.read_text())
        audit = json.loads(release.OUTPUT_AUDIT.read_text())
        self.assertEqual(report["candidate_iso_sha256"], EXPECTED_CANDIDATE_ISO_SHA256)
        self.assertEqual(report["components"], json.loads(json.dumps(components)))
        self.assertEqual(report["whole_iso_audit"], audit)
        self.assertEqual(report["resource_replacements"][0]["path"], release.WHEEL_RESOURCE_PATH)
        self.assertEqual(hashlib.sha256(release.OUTPUT_ELF.read_bytes()).hexdigest(),
                         release.APPROVED_ELF_SHA256)

        with release.OUTPUT_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
            inventory = release._inventory(image, (replacement.path,))
            record, offset = inventory.resources[replacement.path]
            installed = bytes(image[offset:offset + record.size])
            self.assertEqual(installed, replacement.replacement)
            elf = bytes(image[inventory.executable_offset:
                              inventory.executable_offset + inventory.executable.size])
            self.assertEqual(elf, release.OUTPUT_ELF.read_bytes())
        self.assertEqual(report["whole_iso_audit"]["unexplained_bytes"], 0)
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["gameplay_approved"])


if __name__ == "__main__":
    unittest.main()
