"""Focused ownership and corpus checks for the r67.15g prologue patch."""
from __future__ import annotations

import hashlib
import struct
import unicodedata
import unittest
from pathlib import Path

try:
    from tools.r67_15g_prologue import (
        HANT_ANUBIS_POINTERS,
        PERMITTED_EXISTING_RANGES,
        apply,
    )
except ModuleNotFoundError:
    HANT_ANUBIS_POINTERS = ()
    PERMITTED_EXISTING_RANGES = ()
    apply = None


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-15f-item-panel-layout.elf"


@unittest.skipUnless(SOURCE.is_file(), "Requires the parent-approved 15f ELF")
class PrologueNativeTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = SOURCE.read_bytes()

    def test_remaining_room_and_boss_labels_use_exact_official_words(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        result, report = apply(self.source)
        expected = {
            0x5CD794: "Altar of Anubis",
            0x594E78: "Anubis",
        }
        for owner, text in expected.items():
            with self.subTest(owner=hex(owner)):
                pointer = struct.unpack_from("<I", result, owner)[0]
                file_offset = int(report["translation_segment_file_offset"], 16) + pointer - int(
                    report["translation_segment_va"], 16
                )
                end = result.index(0, file_offset)
                actual = unicodedata.normalize("NFKC", result[file_offset:end].decode("cp932"))
                self.assertEqual(actual, text)
        self.assertEqual(report["official_corpus_sha256"], "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b")
        expected_owners = sorted((0x594E78, 0x5CD794, *HANT_ANUBIS_POINTERS))
        self.assertEqual(report["translated_owners"], [hex(owner) for owner in expected_owners])
        self.assertEqual([row["glyph_cells"] for row in report["translated_rows"][:2]], [15, 6])
        self.assertEqual(
            hashlib.sha256(self.source).hexdigest(),
            report["baseline_15f_elf_sha256_for_traceability"],
        )

    def test_only_declared_pointer_words_and_segment_size_change_in_existing_elf(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        result, report = apply(self.source)
        changed = {
            offset
            for offset, (before, after) in enumerate(zip(self.source, result, strict=False))
            if before != after
        }
        permitted = set(range(0x64, 0x68))
        for start, end in PERMITTED_EXISTING_RANGES:
            permitted.update(range(start, end))
        self.assertLessEqual(changed, permitted)
        self.assertEqual(report["modified_existing_offsets"], [hex(offset) for offset in sorted(changed)])
        self.assertEqual(report["permitted_existing_ranges"], [[hex(start), hex(end)] for start, end in PERMITTED_EXISTING_RANGES])

    def test_optional_anubis_enemy_description_is_word_wrapped_in_same_fixed_slots(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        result, report = apply(self.source)
        self.assertEqual(len(HANT_ANUBIS_POINTERS), 17)
        page = report["optional_hant_anubis_page"]
        self.assertEqual(page["row_count"], 17)
        self.assertTrue(page["conservative_width_bound_applied"])
        self.assertEqual(page["official_exact_match_count"], 17)
        self.assertEqual(page["record_table_file_offset"], "0x5c2410")
        self.assertEqual(page["native_getter_va"], "0x2a9fe0")
        self.assertEqual(page["native_getter_callsite_va"], "0x291ec0")
        self.assertEqual(page["metadata_getter_va"], "0x2aa020")
        self.assertEqual(page["dynamic_row_indices"], [5, 7, 18])
        self.assertEqual(page["max_official_glyph_cells"], 40)
        self.assertEqual(page["constructor_extent_pixels"], 512)
        self.assertIsNone(page["proven_usable_text_width_pixels"])
        self.assertEqual(page["known_conservative_text_width_pixels"], 336)
        self.assertEqual(page["known_conservative_max_cells"], 28)
        self.assertEqual(page["row_buffer_bytes"], 64)
        self.assertEqual(page["max_exact_encoded_row_bytes"], 80)
        self.assertEqual(page["max_rendered_glyph_cells"], 28)
        self.assertLessEqual(page["max_rendered_row_bytes_including_nul"], 57)
        self.assertTrue(page["reflowed"])
        self.assertTrue(page["changed"])
        self.assertTrue(page["source_row_indices_preserved"])
        self.assertTrue(all(len(row["source_sha256"]) == 64 for row in page["rows"]))
        self.assertEqual(
            page["packed_description_rows"],
            [
                "[Description] King of the",
                "underworld who announces",
                "death. Appears as a dog or",
                "jackal. Tomb robbers can see",
                "murals or carvings of",
                "Anubis. [Remarks] Weak",
                "against Fire, Cleanse.",
                "[Treasure]",
            ],
        )
        self.assertEqual(page["packed_source_row_indices"], list(range(10, 18)))
        for row in page["rows"]:
            owner = int(row["record_field_offset"], 16)
            with self.subTest(owner=hex(owner)):
                pointer = struct.unpack_from("<I", result, owner)[0]
                file_offset = int(report["translation_segment_file_offset"], 16) + pointer - int(
                    report["translation_segment_va"], 16
                )
                end = result.index(0, file_offset)
                rendered = result[file_offset:end].decode("cp932")
                self.assertEqual(
                    unicodedata.normalize("NFKC", rendered),
                    unicodedata.normalize("NFKC", row["rendered_english"]),
                )
                self.assertLessEqual(len(rendered), 28)
                self.assertLessEqual(end - file_offset + 1, 64)
                self.assertTrue(row["translated"])
        packed = [row for row in page["rows"] if row["source_row_index"] in range(10, 18)]
        self.assertEqual(" ".join(row["rendered_english"] for row in packed), page["packed_official_word_stream"])
        self.assertIn("Tomb robbers can see murals or carvings of Anubis.", page["packed_official_word_stream"])
        for owner in (0x5C2424, 0x5C2458, 0x5C245C):
            with self.subTest(dynamic_blank=hex(owner)):
                self.assertEqual(result[owner:owner + 4], self.source[owner:owner + 4])
        self.assertEqual(result[0x5C2460:0x5C2464], self.source[0x5C2460:0x5C2464])
        self.assertFalse(report["runtime_verified"])

    def test_owned_pointer_preimage_drift_fails_closed(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        changed = bytearray(self.source)
        changed[0x5CD794] ^= 1
        with self.assertRaisesRegex(ValueError, "preimage"):
            apply(bytes(changed))

    def test_anubis_enemy_record_hierarchy_preimage_drift_fails_closed(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        changed = bytearray(self.source)
        changed[0x5C29B0] ^= 1
        with self.assertRaisesRegex(ValueError, "record-table preimage"):
            apply(bytes(changed))

    def test_wrong_official_corpus_is_rejected(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        with self.assertRaisesRegex(ValueError, "corpus hash"):
            apply(self.source, SOURCE)

    def test_sequential_append_is_preserved_and_new_payload_follows_it(self):
        self.assertIsNotNone(apply, "the prologue text component must be implemented")
        extended = bytearray(self.source + b"previous-component")
        while len(extended) & 3:
            extended.append(0)
        struct.pack_into("<I", extended, 0x64, len(extended) - 0x803150)
        result, report = apply(bytes(extended))
        self.assertEqual(report["source_elf_size"], len(extended))
        self.assertEqual(int(report["appended_extent"]["start"], 16), len(extended))
        self.assertGreater(len(result), len(extended))
        self.assertEqual(result[len(self.source):len(extended)], bytes(extended[len(self.source):]))


if __name__ == "__main__":
    unittest.main()
