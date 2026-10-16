"""Component and finished-image guards for the future r67.15g ISO build."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_RESERVE

try:
    from tools.r67_15g_iso_release import (
        audit_component,
        build,
        check_elf_growth,
        compare_expected_bytes,
        compose_components,
        normalize_component_ranges,
        require_release_ready,
        release_scope,
        source_executable_capacity,
        validate_route_evidence,
        CORPUS,
        SOURCE_ISO,
    )
except ModuleNotFoundError:
    audit_component = check_elf_growth = compare_expected_bytes = compose_components = normalize_component_ranges = None
    require_release_ready = release_scope = validate_route_evidence = None
    build = None
    source_executable_capacity = None
    SOURCE_ISO = Path("/path/that/does/not/exist.iso")
    CORPUS = Path("/path/that/does/not/exist")


def make_elf() -> bytes:
    data = bytearray(ELF_SEGMENT_FO + 0x100)
    data[:4] = b"\x7fELF"
    struct.pack_into("<8I", data, 0x54, 1, ELF_SEGMENT_FO, 0x902F00, 0,
                     len(data) - ELF_SEGMENT_FO, 0x10000, 7, 16)
    return bytes(data)


class R6715GReleaseGuardTests(unittest.TestCase):
    def test_release_integration_surface_exists(self):
        self.assertIsNotNone(compose_components, "15g release integration is not implemented")

    def test_normalizes_tuple_and_named_half_open_ranges(self):
        help_ranges = normalize_component_ranges(
            "help", ((0x64, 0x68), (0x200, 0x204)), len(make_elf())
        )
        prologue_ranges = normalize_component_ranges(
            "prologue", {"altar_name": ((0x300, 0x304),), "anubis": ((0x310, 0x314),)},
            len(make_elf()),
        )
        self.assertEqual(help_ranges, {"help:001": ((0x200, 0x204),)})
        self.assertEqual(prologue_ranges["prologue:altar_name"], ((0x300, 0x304),))

    def test_help_adapter_matches_current_component_half_open_contract(self):
        from tools.r67_15g_help_layout import PERMITTED_EXISTING_RANGES

        normalized = normalize_component_ranges("help", PERMITTED_EXISTING_RANGES, len(make_elf()) + 0x600000)
        self.assertEqual(normalized["help:000"], (PERMITTED_EXISTING_RANGES[0],))

    def test_rejects_overlap_and_broad_or_malformed_owner_ranges(self):
        with self.assertRaisesRegex(ValueError, "overlap"):
            normalize_component_ranges(
                "details", {"a": ((0x200, 0x208),), "b": ((0x204, 0x20C),)}, len(make_elf())
            )
        with self.assertRaisesRegex(ValueError, "broad"):
            normalize_component_ranges("details", ((0x100, 0x11000),), len(make_elf()))
        with self.assertRaisesRegex(ValueError, "range format"):
            normalize_component_ranges("help", ((0x200, 0x204, 0x208),), len(make_elf()))

    def test_component_audit_accepts_only_owned_prefix_changes_and_append(self):
        before = make_elf()
        after = bytearray(before + b"\x00\x11payload")
        after[0x200] = 0x42
        struct.pack_into("<I", after, 0x64, len(after) - ELF_SEGMENT_FO)
        ranges = {"tablet:row_pointer": ((0x200, 0x204),)}
        report = {"appended_extent": {"start": hex(len(before)), "end_exclusive": hex(len(after))}}
        audit = audit_component("tablet", before, bytes(after), report, ranges)
        self.assertEqual(audit["changed_existing_offsets"], ["0x64", "0x200"])
        self.assertEqual(audit["appended_extent"], [len(before), len(after)])

    def test_component_audit_normalizes_details_bytearray_output(self):
        before = make_elf()
        after = bytearray(before)
        after[0x200] = 0x42
        audit = audit_component("details", before, after, {}, {"details:hook": ((0x200, 0x204),)})
        self.assertEqual(audit["changed_existing_offsets"], ["0x200"])

    def test_partial_details_report_is_not_release_eligible(self):
        with self.assertRaisesRegex(ValueError, "Details catalogue is incomplete"):
            require_release_ready({"components": [{"component": "details", "report": {
                "status": "PARTIAL_OFFICIAL_SUBSET", "unresolved_records": 2,
            }}]})

    def test_default_scope_keeps_partial_details_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Details catalogue is incomplete"):
            release_scope(self._partial_component_report())

    def test_complete_details_uses_unchanged_default_diagnostic_status(self):
        result = release_scope({"components": [{"component": "details", "report": {
            "status": "PATCHED_ALL_OFFICIAL_DESCRIPTIONS", "unresolved_records": 0,
        }}]})
        self.assertEqual(result, {
            "status": "DIAGNOSTIC_NOT_GAMEPLAY_APPROVED",
            "scope_complete": True,
            "coverage_gap": None,
        })
        self.assertEqual(
            release_scope({"components": [{"component": "details", "report": {
                "status": "PATCHED_ALL_OFFICIAL_DESCRIPTIONS", "unresolved_records": 0,
            }}]}, allow_partial_diagnostic=True),
            result,
        )

    def test_explicit_partial_diagnostic_scope_preserves_gap_and_native_rows(self):
        result = release_scope(self._partial_component_report(), allow_partial_diagnostic=True)
        self.assertEqual(result["status"], "PARTIAL_DIAGNOSTIC_NOT_GAMEPLAY_APPROVED")
        self.assertFalse(result["scope_complete"])
        gap = result["coverage_gap"]
        self.assertEqual(gap["unresolved_records"], 2)
        self.assertEqual(gap["unresolved_item_ids"], [334, 501])
        self.assertEqual(gap["preserved_native_japanese_item_ids"], [334, 501])
        self.assertEqual(gap["preserved_native_japanese_source_rows"], {
            "334": ["desc.334.1"], "501": ["desc.501.1", "desc.501.2"]
        })
        self.assertEqual(gap["preserved_native_japanese_source_row_count"], 3)
        self.assertEqual(gap["actionable_blocker"], "Official corpus entries unavailable")
        self.assertEqual(gap["partially_translated_item_ids"], [334])
        self.assertEqual(gap["fully_japanese_preserved_item_ids"], [501])
        self.assertEqual(gap["catalogue_records"], 4)
        self.assertEqual(gap["official_exact_records"], 2)
        self.assertEqual(gap["source_rows"], 5)
        self.assertEqual(gap["official_exact_source_rows"], 2)

    def test_partial_opt_in_rejects_invalid_flags_and_inconsistent_counts(self):
        for invalid_flag in (1, "true", None):
            with self.subTest(flag=invalid_flag):
                with self.assertRaisesRegex(ValueError, "must be a bool"):
                    release_scope(self._partial_component_report(), allow_partial_diagnostic=invalid_flag)

        report = self._partial_component_report()
        report["components"][0]["report"]["unresolved_records"] = 3
        with self.assertRaisesRegex(ValueError, "count does not match"):
            release_scope(report, allow_partial_diagnostic=True)

        report = self._partial_component_report()
        report["components"][0]["report"]["preserved_native_japanese_item_ids"] = [334]
        with self.assertRaisesRegex(ValueError, "native rows do not match"):
            release_scope(report, allow_partial_diagnostic=True)

        report = self._partial_component_report()
        report["components"][0]["report"]["preserved_native_japanese_source_row_count"] = 4
        with self.assertRaisesRegex(ValueError, "source-row count"):
            release_scope(report, allow_partial_diagnostic=True)

        report = self._partial_component_report()
        report["components"][0]["report"]["release_eligibility"] = "FULL_CATALOGUE_COVERED"
        with self.assertRaisesRegex(ValueError, "exact partial Details status"):
            release_scope(report, allow_partial_diagnostic=True)

    def test_build_rejects_non_boolean_opt_in_before_any_build_prerequisite(self):
        with self.assertRaisesRegex(ValueError, "must be a bool"):
            build(allow_partial_diagnostic=1)

    @unittest.skipUnless(SOURCE_ISO.is_file(), "Requires approved r67.15f source ISO")
    def test_build_source_preflight_indexes_the_real_iso_buffer(self):
        executable_size = source_executable_capacity()
        self.assertGreater(executable_size, 0)

    @staticmethod
    def _partial_component_report():
        return {"components": [{"component": "details", "report": {
            "status": "PARTIAL_OFFICIAL_SUBSET",
            "release_eligibility": "PARTIAL_NOT_FULL_SCOPE",
            "unresolved_records": 2,
            "unresolved_item_ids": [334, 501],
            "preserved_native_japanese_item_ids": [334, 501],
            "preserved_native_japanese_source_rows": {
                "334": ["desc.334.1"], "501": ["desc.501.1", "desc.501.2"]
            },
            "preserved_native_japanese_source_row_count": 3,
            "partially_translated_records": [334],
            "fully_japanese_preserved_item_ids": [501],
            "valid_catalogue_records": 4,
            "official_exact_records": 2,
            "source_rows": 5,
            "official_exact_source_rows": 2,
            "actionable_blocker": "Official corpus entries unavailable",
        }}]}

    def test_route_audit_shape_requires_exact_source_provenance_and_choice_status(self):
        report = {
            "audit_kind": "finished_iso_exact_payload_audit", "read_only": True,
            "assets": {
                name: {"verification": "official_exact", "official_import_entries": count,
                       "official_ps4_source_sha256": "a" * 64, "official_map_sha256": "b" * 64,
                       "official_regenerated_sha256": "c" * 64}
                for name, count in (("ADV/DG/DG00_00.MTX", 195),
                                    ("ADV/DG/DG00_01.MTX", 34),
                                    ("ADV/MS/MS00_02.MTX", 593))
            },
            "choice_assets": {
                "ADV/MS/MS00_02.KSF": {"official_choice_entries": 10,
                    "finished_sha256": "d" * 64, "regenerated_sha256": "d" * 64,
                    "counts": {"fit": 10, "approved_compaction": 0, "unresolved": 0}},
                "ADV/DG/DG00_00.KSF": {"official_choice_entries": 5,
                    "counts": {"fit": 3, "approved_compaction": 2, "unresolved": 0},
                    "approved_compaction_offsets": [9339, 11689]},
            },
            "unresolved_choice_entries": [], "endpoint_capture_checklist": ["pending runtime captures"],
        }
        accepted = validate_route_evidence(report)
        self.assertTrue(accepted["static_payload_provenance_passed"])
        self.assertFalse(accepted["runtime_route_captures_complete"])
        report["choice_assets"]["ADV/MS/MS00_02.KSF"]["counts"]["fit"] = 9
        with self.assertRaisesRegex(ValueError, "ten-choice"):
            validate_route_evidence(report)

    def test_component_audit_rejects_unowned_wrong_filesz_and_excess_growth(self):
        before = make_elf()
        changed = bytearray(before)
        changed[0x205] = 1
        with self.assertRaisesRegex(ValueError, "unowned"):
            audit_component("tablet", before, bytes(changed), {}, {"tablet:ptr": ((0x200, 0x204),)})

        wrong_size = bytearray(before + b"data")
        with self.assertRaisesRegex(ValueError, "PT_LOAD"):
            audit_component("tablet", before, bytes(wrong_size), {}, {"tablet:ptr": ((0x200, 0x204),)})

        oversized = bytearray(before + bytes(0x10001))
        struct.pack_into("<I", oversized, 0x64, len(oversized) - ELF_SEGMENT_FO)
        with self.assertRaisesRegex(ValueError, "reserved"):
            audit_component("tablet", before, bytes(oversized), {}, {"tablet:ptr": ((0x200, 0x204),)})

        malformed = bytearray(before)
        malformed[:4] = b"NOPE"
        with self.assertRaisesRegex(ValueError, "malformed ELF"):
            audit_component("tablet", bytes(malformed), bytes(malformed), {}, {})

    def test_iso_growth_reuses_14y_volume_overlap_and_zero_slack_guard(self):
        entry = SimpleNamespace(extent=1, size=4, sectors=1)
        image = bytearray(8192)
        check_elf_growth(image, entry, [entry], 4, 5)
        image[2048 + 4] = 1
        with self.assertRaisesRegex(ValueError, "nonzero sector data"):
            check_elf_growth(image, entry, [entry], 4, 5)
        with self.assertRaisesRegex(ValueError, "outside existing volume"):
            check_elf_growth(bytes(4096), entry, [entry], 4, 4097)

    @unittest.skipUnless(CORPUS.is_file(), "Requires owned official English.bytes corpus")
    def test_component_chain_uses_fixed_order_and_signature_specific_inputs(self):
        source = make_elf()
        calls = []
        corpus_bytes = CORPUS.read_bytes()

        def component(name, owner, expected_input):
            def transform(raw, corpus_input):
                calls.append((name, corpus_input))
                self.assertEqual(corpus_input, expected_input)
                out = bytearray(raw)
                out.extend(name.encode("ascii"))
                out[owner] ^= 1
                struct.pack_into("<I", out, 0x64, len(out) - ELF_SEGMENT_FO)
                report = {"appended_extent": [len(raw), len(out)]}
                if name == "prologue":
                    report["status"] = "DIAGNOSTIC_STATIC_PROLOGUE_TEXT_ONLY"
                if name == "details":
                    report.update(status="PATCHED_ALL_OFFICIAL_DESCRIPTIONS", unresolved_records=0)
                return bytes(out), report
            if name == "details":
                def apply(raw, *, corpus_path):
                    return transform(raw, corpus_path)
            else:
                apply = transform
            span = (owner, owner + 4)
            return SimpleNamespace(apply=apply, PERMITTED_EXISTING_RANGES=(span,))

        modules = {
            "tablet": component("tablet", 0x200, Path("official.bytes")),
            "help": component("help", 0x210, corpus_bytes),
            "prologue": component("prologue", 0x220, Path("official.bytes")),
            "details": component("details", 0x230, Path("official.bytes")),
        }
        result, report = compose_components(
            source, Path("official.bytes"), corpus_bytes, components=modules
        )
        self.assertEqual([name for name, _ in calls], ["tablet", "help", "prologue", "details"])
        self.assertGreater(len(result), len(source))
        self.assertEqual([entry["component"] for entry in report["components"]],
                         ["tablet", "help", "prologue", "details"])

    def test_exact_image_delta_rejects_outside_inside_and_missing_changes(self):
        baseline = b"0123456789abcdef"
        expected = {4: (ord("X"), "elf/tablet-pointer")}
        good = bytearray(baseline)
        good[4] = ord("X")
        self.assertEqual(compare_expected_bytes(baseline, good, expected), {"elf/tablet-pointer": 1})

        outside = bytearray(good)
        outside[12] ^= 1
        with self.assertRaisesRegex(ValueError, "unexplained"):
            compare_expected_bytes(baseline, outside, expected)

        wrong_value = bytearray(good)
        wrong_value[4] = ord("Y")
        with self.assertRaisesRegex(ValueError, "unexplained"):
            compare_expected_bytes(baseline, wrong_value, expected)

        missing = bytearray(baseline)
        with self.assertRaisesRegex(ValueError, "absent"):
            compare_expected_bytes(baseline, missing, expected)


if __name__ == "__main__":
    unittest.main()
