from __future__ import annotations

import hashlib
import struct
import tempfile
import unittest
from pathlib import Path

from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO
from tools import r67_15h_iso_release as release


def make_elf() -> bytes:
    data = bytearray(ELF_SEGMENT_FO + 0x100)
    data[:4] = b"\x7fELF"
    struct.pack_into("<8I", data, 0x54, 1, ELF_SEGMENT_FO, 0x902F00, 0,
                     len(data) - ELF_SEGMENT_FO, 0x10000, 7, 16)
    return bytes(data)


class R6715HReleaseTests(unittest.TestCase):
    def test_audits_sequential_component_stages_and_is_deterministic(self):
        source = make_elf()

        def apply(before: bytes):
            after = bytearray(before + b"payload")
            after[0x200] = 0x41
            struct.pack_into("<I", after, 0x64, len(after) - ELF_SEGMENT_FO)
            return bytes(after), {"status": "STATIC_DIAGNOSTIC", "appended_extent": [len(before), len(after)]}

        components = (("item_layout", apply, {"layout_word": ((0x200, 0x204),)}),)
        prepared = release._prepare_stages(source, components)
        repeated = release._prepare_stages(source, components)
        self.assertEqual(prepared, repeated)
        self.assertEqual(prepared.candidate[0x200], 0x41)
        self.assertEqual(prepared.components[0]["component"], "item_layout")

    def test_rejects_unowned_component_byte_drift(self):
        source = make_elf()

        def apply(before: bytes):
            after = bytearray(before)
            after[0x210] = 1
            return bytes(after), {}

        with self.assertRaisesRegex(ValueError, "unowned"):
            release._prepare_stages(source, (("item_layout", apply, {"owner": ((0x200, 0x204),)}),))

    def test_rejects_mutation_outside_the_declared_owner(self):
        source = make_elf()

        def apply(before: bytes):
            after = bytearray(before)
            after[0x210] = 1
            return bytes(after), {"modified_existing_offsets": ["0x210"]}

        with self.assertRaisesRegex(ValueError, "unowned"):
            release._prepare_stages(source, (("hant", apply, {"row_pool": ((0x200, 0x204),)}),))

    def test_rejects_change_report_that_disagrees_with_bytes(self):
        source = make_elf()

        def apply(before: bytes):
            after = bytearray(before)
            after[0x200] = 1
            return bytes(after), {"modified_existing_offsets": ["0x204"]}

        with self.assertRaisesRegex(ValueError, "report disagrees"):
            release._prepare_stages(source, (("hant", apply, {"row_pool": ((0x200, 0x208),)}),))

    def test_rejects_noop_component(self):
        source = make_elf()

        def apply(before: bytes):
            return before, {"status": "NOOP"}

        with self.assertRaisesRegex(ValueError, "made no changes"):
            release._prepare_stages(source, (("hant", apply, {}),))

    def test_rejects_missing_and_duplicate_component_names(self):
        source = make_elf()
        with self.assertRaisesRegex(ValueError, "explicit ordered component"):
            release._prepare_stages(source, ())
        identity = lambda before: (before, {})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            release._prepare_stages(source, (("hant", identity, {}), ("hant", identity, {})))

    def test_public_preparation_order_is_item_layout_then_hant_pool(self):
        with self.assertRaisesRegex(ValueError, "item_layout.*hant_pool"):
            release._validate_component_order((("hant_pool", lambda value: (value, {}), {}),))
        release._validate_component_order((
            ("item_layout", lambda value: (value, {}), {}),
            ("hant_pool", lambda value: (value, {}), {}),
        ))

    def test_rejects_nondeterministic_component_output(self):
        source = make_elf()
        calls = 0

        def apply(before: bytes):
            nonlocal calls
            calls += 1
            after = bytearray(before)
            after[0x200] = calls
            return bytes(after), {}

        with self.assertRaisesRegex(ValueError, "not deterministic"):
            release._prepare_stages(source, (("hant", apply, {"owner": ((0x200, 0x204),)}),))

    def test_output_creation_refuses_existing_target(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "diagnostic.iso"
            target.write_bytes(b"prior")
            with self.assertRaises(FileExistsError):
                release._write_exclusive(target, b"new")
            self.assertEqual(target.read_bytes(), b"prior")

    def test_report_carries_partial_scope_input_hash_and_runtime_boundary(self):
        source = make_elf()
        prepared = release.Prepared15H(source, source, (), {}, hashlib.sha256(source).hexdigest())
        route = {"read_only": True, "static_payload_provenance_passed": True}
        report = release.make_report(prepared, "g-iso-hash", "g-elf-hash", route_context=route)
        self.assertFalse(report["scope_complete"])
        self.assertEqual(report["unresolved_details_records"], 36)
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["gameplay_approved"])
        self.assertEqual(report["input_iso_sha256"], "g-iso-hash")
        self.assertEqual(report["input_elf_sha256"], "g-elf-hash")
        self.assertEqual(report["loading_confirmation"], "PENDING")
        self.assertFalse(report["reported_hant_observation"]["causality_confirmed"])
        self.assertFalse(report["reported_hant_observation"]["runtime_hang_verified"])
        self.assertEqual(report["resource_lookup_consistency"]["source"], "parent-provided audit")
        self.assertEqual(report["resource_lookup_consistency"]["embedded_rofs_file_records"], 10656)
        self.assertEqual(report["route_evidence"], route)


if __name__ == "__main__":
    unittest.main()
