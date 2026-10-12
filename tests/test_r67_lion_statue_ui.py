"""Focused native-owner and fail-closed regression tests for r67.14r."""
from __future__ import annotations

import hashlib
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

from tools import r67_lion_statue_ui as target
from tools.r67_14q_approved_lock import MANIFEST, verify_approved
import json

ROOT = Path(__file__).resolve().parents[1]
APPROVED = ROOT / "local/r67-14q-opening-final-line-fit.elf"


@unittest.skipUnless(APPROVED.is_file(), "Needs ignored, approved r67.14q baseline ELF")
class LionStatueNativeOwnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = APPROVED.read_bytes()
        cls.candidate, cls.report = target.apply(cls.source)

    def test_source_and_distinct_owner_preimages(self) -> None:
        self.assertEqual(target.sha(self.source), target.APPROVED_ELF_SHA256)
        self.assertEqual(len(target.CALL_SITES), 2)
        self.assertEqual(
            target.item_pointer(self.source),
            struct.unpack_from("<I", self.source, target.ITEM_NAME_POINTER_OFFSET)[0],
        )
        for site, expected in target.CALL_CONTEXTS.items():
            actual = struct.unpack_from("<4I", self.source, site - target.ELF_BIAS - 8)
            self.assertEqual(expected, actual)

    def test_exact_original_bytes_whitelisted(self) -> None:
        modifications = {
            pos for pos, (a, b) in enumerate(zip(self.source, self.candidate)) if a != b
        }
        allow = set(range(0x64, 0x68))
        for site in target.CALL_SITES:
            allow.update(range(site - target.ELF_BIAS, site - target.ELF_BIAS + 4))
        self.assertTrue(modifications)
        self.assertLessEqual(modifications, allow)
        self.assertEqual(self.candidate[:4], self.source[:4])
        self.assertEqual(
            struct.unpack_from("<I", self.candidate, target.ITEM_NAME_POINTER_OFFSET),
            struct.unpack_from("<I", self.source, target.ITEM_NAME_POINTER_OFFSET),
        )

    def test_helper_targets_and_pointer_conditional(self) -> None:
        helper = target.make_helper(target.item_pointer(self.source))
        va = int(self.report["private_helper_va"], 16)
        self.assertEqual(self.candidate[target.ELF_SEGMENT_FO + va - target.ELF_SEGMENT_VA:target.ELF_SEGMENT_FO + va - target.ELF_SEGMENT_VA + len(helper)], helper)
        for site in target.CALL_SITES:
            self.assertEqual(
                struct.unpack_from("<I", self.candidate, site - target.ELF_BIAS)[0],
                target._jal(va),
            )
        words = struct.unpack("<" + "I" * (len(helper) // 4), helper)
        self.assertIn(target._jal(target.ORIGINAL_TEXT_SETTER), words)
        self.assertIn(target._jal(target.NATIVE_XY_SCALING_SETTER), words)
        self.assertEqual(words[-2:], (0x03E00008, 0))
        self.assertIn(target._float_word(target.FIT_HORIZONTAL_SCALE) >> 16, [w & 0xffff for w in words])
        self.assertIn(target._float_word(1.0) >> 16, [w & 0xffff for w in words])
        self.assertEqual(self.report["other_items_unchanged_by_pointer_gate"], True)

    def test_both_existing_approved_locks_survive(self) -> None:
        manifest = json.loads(MANIFEST.read_text())
        result = verify_approved(self.candidate, manifest)
        self.assertEqual(result["status"], "PASS_R67_14Q_VISUALLY_APPROVED_OWNERS")

    def test_unknown_elf_fails_closed(self) -> None:
        modified = bytearray(self.source)
        modified[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, "gameplay-approved"):
            target.apply(bytes(modified))

    def test_item_name_mutation_is_rejected_even_if_source_fingerprint_is_rebased(self) -> None:
        modified = bytearray(self.source)
        struct.pack_into("<I", modified, target.ITEM_NAME_POINTER_OFFSET, 0)
        with patch.object(target, "APPROVED_ELF_SHA256", hashlib.sha256(modified).hexdigest()):
            with self.assertRaisesRegex(ValueError, "catalog pointer/string"):
                target.apply(bytes(modified))

    def test_native_callsite_mutation_is_rejected_even_if_source_fingerprint_is_rebased(self) -> None:
        modified = bytearray(self.source)
        site = target.CALL_SITES[-1] - target.ELF_BIAS
        modified[site] ^= 1
        with patch.object(target, "APPROVED_ELF_SHA256", hashlib.sha256(modified).hexdigest()):
            with self.assertRaisesRegex(ValueError, "native name-text owner"):
                target.apply(bytes(modified))


if __name__ == "__main__":
    unittest.main()
