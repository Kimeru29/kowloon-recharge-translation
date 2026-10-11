"""Regression gates for read-only 67.04 renderer-owner investigations."""
from __future__ import annotations

from pathlib import Path
import unittest

from tools.r67_04_owner_audit import audit, NATIVE_FONT_CALLSITES

ROOT = Path(__file__).resolve().parents[1]
PRISTINE = ROOT.parent / "startup-flow-v10/fixtures/elf/SLPM_665.11"
BEFORE = ROOT / "local/r67-02-layout.elf"
WITH_HISTORY = ROOT / "local/r67-02-history.elf"
RELEASE_6703 = ROOT / "local/r67-03.elf"


class RendererOwnershipAuditTests(unittest.TestCase):
    def test_independent_font_owner_inventory_is_not_conflated(self):
        self.assertEqual(len(NATIVE_FONT_CALLSITES), 11)
        self.assertIn(0x151614, NATIVE_FONT_CALLSITES)
        self.assertIn(0x159D54, NATIVE_FONT_CALLSITES)
        self.assertNotEqual(0x151614, 0x159D54)

    @unittest.skipUnless(all(p.exists() for p in (PRISTINE, BEFORE, WITH_HISTORY, RELEASE_6703)),
                         "Owned private ELF files required")
    def test_6703_still_contains_unverified_history_shim_and_preserves_renderers(self):
        inputs = [p.read_bytes() for p in (PRISTINE, BEFORE, WITH_HISTORY, RELEASE_6703)]
        result = audit(*inputs)
        self.assertFalse(result["release_allowed"])
        self.assertTrue(result["experimental_shim_unchanged_since_6702"])
        self.assertEqual("0x962ffc", result["experimental_shim_target_va"])
        self.assertEqual(11, len(result["pristine_native_constructor_callsites"]))
        self.assertEqual(6, len(result["accepted_region_sha256"]))
        self.assertEqual(["0x3c1a50", "0x3c1f38"],
                         [x["source"] for x in result["dungeon_story_comment_sources"]])
        self.assertEqual(3, len(result["unverified"]))

        invalid = bytearray(inputs[-1])
        invalid[0x150048] ^= 1  # accepted main speaker geometry
        with self.assertRaisesRegex(ValueError, "Previously shipped renderer region changed"):
            audit(*inputs[:3], bytes(invalid))
        invalid = bytearray(inputs[-1])
        invalid[0x159D54] ^= 1  # candidate history JAL
        with self.assertRaisesRegex(ValueError, "Shipped 67.03 history shim provenance changed"):
            audit(*inputs[:3], bytes(invalid))
        invalid = bytearray(inputs[0])
        invalid[0x159D54] ^= 1  # pristine callsite ownership
        with self.assertRaisesRegex(ValueError, "Pristine native constructor caller inventory changed"):
            audit(bytes(invalid), *inputs[1:])
        invalid = bytearray(inputs[-1])
        invalid[0x200000] ^= 1  # byte outside sampled approved renderer spans
        with self.assertRaisesRegex(ValueError, "audit input ELF fingerprint mismatch"):
            audit(*inputs[:3], bytes(invalid))


if __name__ == "__main__":
    unittest.main()
