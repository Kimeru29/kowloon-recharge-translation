"""Regression checks for the r67 START-history-only orientation probe."""
from __future__ import annotations

from pathlib import Path
import struct
import unittest

from tools.r67_history_direction_probe import (
    BASE_SHA,
    FACTORY_END_VA,
    FACTORY_START_VA,
    FLAG_VA,
    HISTORY_JAL_VA,
    HORIZONTAL_FLAG_WORD,
    OLD_HISTORY_JAL,
    VA_MINUS_OFFSET,
    _sha,
    _validate_relocation,
    apply,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "local/r67-07-containment.elf"
PRISTINE = ROOT / "../startup-flow-v10/fixtures/elf/SLPM_665.11"
CANDIDATE = ROOT / "local/r67-08-history-direction.elf"


class HistoryDirectionProbe(unittest.TestCase):
    def test_relative_branch_checker_fails_closed(self):
        # beq zero,zero,+1 skips out of this four-byte clone.
        with self.assertRaisesRegex(ValueError, "outside function"):
            _validate_relocation(struct.pack("<I", 0x10000001), 0x1000, 0x1004)
        with self.assertRaisesRegex(ValueError, "absolute J"):
            _validate_relocation(struct.pack("<I", 0x08000400), 0x1000, 0x1004)

    @unittest.skipUnless(BASE.exists() and PRISTINE.exists() and CANDIDATE.exists(),
                         "private approved r67 ELF fixtures unavailable")
    def test_clone_is_history_only_and_protected_bytes_unchanged(self):
        baseline = BASE.read_bytes()
        pristine = PRISTINE.read_bytes()
        candidate = CANDIDATE.read_bytes()
        self.assertEqual(BASE_SHA, _sha(baseline))
        produced, report = apply(baseline, pristine)
        self.assertEqual(candidate, produced)
        self.assertFalse(report["style_ids_modified"])
        self.assertFalse(report["release_approved"])
        self.assertTrue(report["preserves_approved_help"])
        self.assertEqual(FACTORY_END_VA-FACTORY_START_VA,
                         report["instruction_bytes_cloned"])
        self.assertEqual([100, 101, 1400585, 1400586],
                         report["changed_existing_elf_bytes"])

        def word(data, off):
            return struct.unpack_from("<I", data, off)[0]

        # Native constructor and all its callers except history remain unchanged.
        factory = FACTORY_START_VA - VA_MINUS_OFFSET
        self.assertEqual(baseline[factory:factory+FACTORY_END_VA-FACTORY_START_VA],
                         candidate[factory:factory+FACTORY_END_VA-FACTORY_START_VA])
        self.assertEqual(word(baseline, HISTORY_JAL_VA-VA_MINUS_OFFSET),
                         OLD_HISTORY_JAL)
        self.assertNotEqual(word(candidate, HISTORY_JAL_VA-VA_MINUS_OFFSET),
                            OLD_HISTORY_JAL)
        # The clone uses the original style tables but fixes its direction argument.
        clone_elf_offset = len(baseline) + (-len(baseline) % 4)
        self.assertEqual(word(candidate, clone_elf_offset + FLAG_VA-FACTORY_START_VA),
                         HORIZONTAL_FLAG_WORD)
        # No format/pointer table changes anywhere in the existing executable.
        approved = set(range(0x64,0x68)) | set(range(HISTORY_JAL_VA-VA_MINUS_OFFSET,HISTORY_JAL_VA-VA_MINUS_OFFSET+4))
        for at,(old,new) in enumerate(zip(baseline,candidate)):
            if old!=new:
                self.assertIn(at,approved)

    @unittest.skipUnless(BASE.exists() and PRISTINE.exists(),
                         "private approved r67 ELF fixtures unavailable")
    def test_drift_detection_rejects_modified_executable(self):
        baseline = bytearray(BASE.read_bytes())
        baseline[0x155F08] ^= 1
        with self.assertRaisesRegex(ValueError, "baseline drift"):
            apply(bytes(baseline), PRISTINE.read_bytes())


if __name__ == "__main__":
    unittest.main()
