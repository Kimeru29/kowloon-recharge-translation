from hashlib import sha256
import unittest

from tools import r67p_surface_art as art


@unittest.skipUnless(art.O_ISO.is_file() and art.K_ELF.is_file() and art.PS4_BUNDLES.is_dir(),
                     "Pinned r67.15o and artwork source fixtures are unavailable")
class InstalledSurfaceArtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf, cls.containers = art.read_artwork(art.O_ISO)

    def test_hant_recording_popup_port_is_reproduced_from_exact_official_asset(self):
        overlay = art.build_overlays(art.O_ISO)
        self.assertEqual(set(overlay), {"BLBRD/B_GP059.BIN"})
        before = self.containers["BLBRD/B_GP059.BIN"]
        after = overlay["BLBRD/B_GP059.BIN"]
        self.assertEqual(len(after), 263744)
        self.assertEqual(sha256(after).hexdigest(),
                         "f0ba2ba39ea16940c46e3a73d3966b41a346448f06a536f04dcd68c99c55ffb3")
        self.assertEqual(before[:0x140], after[:0x140])
        self.assertEqual(before[0x40540:], after[0x40540:])

    def test_popup_missing_confirm_branch_is_rejected(self):
        damaged = bytearray(self.elf)
        damaged[0x292F3C - 0xFFF80] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T. recording owner"):
            art.verify_hant_recording_owner(damaged)

    def test_wheel_dispatch_and_installed_uv_tables_are_locked(self):
        evidence = art.verify_wheel(self.elf, self.containers["BLBRD/B_GP001.BIN"])
        self.assertEqual(evidence["frames"], 820)
        self.assertEqual(evidence["mapper_cases"], 13)
        self.assertEqual(evidence["forced_modes"], 8)

    def test_wheel_geometry_or_palette_drift_is_rejected(self):
        damaged = bytearray(self.elf)
        damaged[0x444C10 - 0xFFF80 + 0x14] ^= 1
        with self.assertRaisesRegex(ValueError, "wheel"):
            art.verify_wheel(damaged, self.containers["BLBRD/B_GP001.BIN"])
        damaged = bytearray(self.containers["BLBRD/B_GP001.BIN"])
        damaged[0x140] ^= 1
        with self.assertRaisesRegex(ValueError, "wheel"):
            art.verify_wheel(self.elf, damaged)
