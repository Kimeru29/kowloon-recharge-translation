from __future__ import annotations

import unittest
from pathlib import Path

from tools.ksf import KsfFixedStringPatch, patch_fixed_strings
from tests.local_fixtures import require_local_fixture


FIXTURE = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "DG00_00" / "original.KSF")
RAW = FIXTURE.read_bytes()


class KsfFixedStringTests(unittest.TestCase):
    def test_patches_fixed_field_and_zero_fills_remaining_capacity(self) -> None:
        patch = KsfFixedStringPatch(offset=6959, capacity=30, text="Look around the area")

        result = patch_fixed_strings(RAW, (patch,))

        self.assertEqual(len(RAW), len(result))
        self.assertEqual(b"Look around the area", result[6959:6979])
        self.assertEqual(b"\x00" * 10, result[6979:6989])
        self.assertEqual(RAW[:6959], result[:6959])
        self.assertEqual(RAW[6989:], result[6989:])

    def test_accepts_exact_capacity_without_nul_when_field_is_fixed_width(self) -> None:
        patch = KsfFixedStringPatch(offset=9339, capacity=31, text="X" * 31)

        result = patch_fixed_strings(RAW, (patch,))

        self.assertEqual(b"X" * 31, result[9339:9370])
        self.assertEqual(RAW[9370:], result[9370:])

    def test_rejects_text_larger_than_fixed_field(self) -> None:
        patch = KsfFixedStringPatch(
            offset=9339,
            capacity=31,
            text="Pick up the device on the ground",
        )

        with self.assertRaisesRegex(ValueError, "31-byte KSF field"):
            patch_fixed_strings(RAW, (patch,))

    def test_rejects_non_ascii_probe_text(self) -> None:
        patch = KsfFixedStringPatch(offset=6959, capacity=30, text="Ｌｏｏｋ")

        with self.assertRaisesRegex(ValueError, "ASCII"):
            patch_fixed_strings(RAW, (patch,))

    def test_dg00_vertical_slice_probe_fits_all_five_fields(self) -> None:
        patches = (
            KsfFixedStringPatch(6959, 30, "Look around the area"),
            KsfFixedStringPatch(6990, 32, "Stand here"),
            KsfFixedStringPatch(9339, 31, "Pick up device on the ground", constrained=True),
            KsfFixedStringPatch(11689, 31, "Pick up device on the ground", constrained=True),
            KsfFixedStringPatch(14039, 31, "Say no"),
        )

        result = patch_fixed_strings(RAW, patches)

        self.assertEqual(len(RAW), len(result))
        for patch in patches:
            encoded = patch.text.encode("ascii")
            self.assertEqual(encoded, result[patch.offset:patch.offset + len(encoded)])


if __name__ == "__main__":
    unittest.main()
