from __future__ import annotations

import hashlib
import unittest
from pathlib import Path

from tools.r67_15g_item_details import (
    CORPUS_PATH,
    CORPUS_SHA256,
    PANEL_HEIGHT,
    PANEL_WIDTH,
    ROW_HEIGHT,
    SOURCE_ELF,
    collect_catalogue,
    load_official_rows,
    map_official_descriptions,
    map_official_lines,
    render_native_description,
    wrap_description,
    apply,
)


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "local/r67-15f-item-panel-layout.elf"
BREAK = "＠改行"


class ItemDetailsCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.elf = BASELINE.read_bytes()
        cls.corpus_rows = load_official_rows(CORPUS_PATH)
        cls.records = collect_catalogue(cls.elf)
        cls.mapped, cls.unresolved = map_official_descriptions(
            cls.records, cls.corpus_rows
        )

    def test_corpus_identity_and_actual_native_description_owner(self) -> None:
        self.assertEqual(hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest(), CORPUS_SHA256)
        self.assertEqual(SOURCE_ELF, BASELINE)
        self.assertEqual((PANEL_WIDTH, PANEL_HEIGHT, ROW_HEIGHT), (220, 96, 9))
        # Getter 0x134B80 has exactly one native JAL caller: the Details
        # paragraph constructor at 0x115148, not the item-name catalogue.
        import struct

        calls = []
        for offset in range(0, len(self.elf) - 4, 4):
            word = struct.unpack_from("<I", self.elf, offset)[0]
            if word >> 26 == 3 and ((word & 0x03FFFFFF) << 2) == 0x134B80:
                calls.append(offset)
        self.assertEqual(calls, [0x151C8])
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x151C8)[0], 0x0C04D2E0)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x1520C)[0], 0x0C062790)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x1515C)[0], 0x24040004)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x15160)[0], 0x2405000B)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x1518C)[0], 0x3C0241D0)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x151A4)[0], 0x3C024180)
        self.assertEqual(struct.unpack_from("<I", self.elf, 0x151D4)[0], 0xC64101D8)

    def test_full_primary_and_alternate_catalogue_cardinality_and_aliases(self) -> None:
        ids = [record.item_id for record in self.records]
        self.assertEqual(len(ids), 431)
        self.assertEqual(len(set(ids)), 431)
        self.assertEqual(sum(record.table == "primary" for record in self.records), 394)
        self.assertEqual(sum(record.table == "alternate" for record in self.records), 37)
        aliases = {
            pointer: sorted(record.item_id for record in self.records
                            if record.description_pointer == pointer)
            for pointer in {record.description_pointer for record in self.records}
        }
        self.assertEqual(
            sorted(tuple(ids) for ids in aliases.values() if len(ids) > 1),
            [(0, 536), (89, 90), (137, 209, 238, 327)],
        )
        import struct
        from tools.r67_15g_item_details import (
            ALTERNATE_NAME_VA,
            PRIMARY_NAME_VA,
            _read_string,
            _table_offset,
        )

        names = []
        for base, first_id, end_id in (
            (PRIMARY_NAME_VA, 0, 500),
            (ALTERNATE_NAME_VA, 500, 537),
        ):
            offset = _table_offset(self.elf, base)
            names.extend(
                _read_string(self.elf, struct.unpack_from("<I", self.elf, offset + item_id * 4)[0])
                for item_id in range(first_id, end_id)
            )
        self.assertEqual(sum(name is not None for name in names[:500]), 446)
        self.assertEqual(sum(name is not None for name in names[500:]), 37)
        self.assertEqual(446 - 394, 52)  # named primary entries with no Details record

    def test_official_coverage_is_exact_and_missing_sources_fail_closed(self) -> None:
        self.assertEqual(len(self.mapped), 395)
        self.assertEqual(len(self.unresolved), 36)
        self.assertEqual(
            sorted(record.item_id for record in self.unresolved),
            list(range(500, 536)),
        )
        detail_334 = self.mapped[334]
        self.assertEqual(
            detail_334,
            'Common ammunition also called 9mm Parabellum, which means '
            '"to prepare for war" in Latin.',
        )
        self.assertIn("Movement AP -10%", self.mapped[112])

    def test_every_official_description_preserves_words_and_fits_native_panel(self) -> None:
        for item_id, translated in self.mapped.items():
            with self.subTest(item_id=item_id):
                lines = wrap_description(translated)
                self.assertLessEqual(len(lines) * ROW_HEIGHT, PANEL_HEIGHT)
                self.assertTrue(all(line and len(line) * 8 <= PANEL_WIDTH for line in lines))
                self.assertEqual(" ".join(" ".join(lines).split()),
                                 " ".join(translated.split()))
                self.assertEqual(
                    [word for line in lines for word in line.split()],
                    translated.split(),
                )

    def test_all_catalogue_rows_fit_including_exact_rows_and_preserved_japanese(self) -> None:
        line_map = map_official_lines(self.records, self.corpus_rows)
        for record in self.records:
            with self.subTest(item_id=record.item_id):
                rows = render_native_description(record, line_map[record.item_id])
                self.assertLessEqual(len(rows) * ROW_HEIGHT, PANEL_HEIGHT)
                self.assertTrue(all(len(row) * 8 <= PANEL_WIDTH for row, _ in rows))
        self.assertEqual(
            [item_id for item_id, values in line_map.items()
             if item_id >= 500 and any(value is not None for value in values)
             and any(value is None for value in values)],
            [500, 501, 504, 515, 534],
        )

    def test_ambiguous_official_key_and_malformed_source_pointer_are_rejected(self) -> None:
        record = next(record for record in self.records if record.item_id == 334)
        duplicate_rows = self.corpus_rows + [
            (record.source_lines[0], "different wording＠改行", 0xFFFFFF)
        ]
        mapped, unresolved = map_official_descriptions(
            [record], duplicate_rows
        )
        self.assertEqual(mapped, {})
        self.assertEqual([item.item_id for item in unresolved], [334])

        import struct

        malformed = bytearray(self.elf)
        struct.pack_into("<I", malformed, 0x39BF74 + 334 * 4, 0xFFFFFFFF)
        with self.assertRaisesRegex(ValueError, "description pointer|catalogue preimage"):
            collect_catalogue(bytes(malformed))


class ItemDetailsApplyTests(unittest.TestCase):
    def test_apply_patches_exact_subset_and_preserves_unmapped_native_pointers(self) -> None:
        source = BASELINE.read_bytes()
        result, report = apply(source, corpus_path=CORPUS_PATH)
        self.assertNotEqual(result, source)
        self.assertEqual(report["status"], "PARTIAL_OFFICIAL_SUBSET")
        self.assertEqual(report["valid_catalogue_records"], 431)
        self.assertEqual(report["fully_resolved_records"], 395)
        self.assertEqual(report["official_exact_records"], 391)
        self.assertEqual(report["empty_native_records"], 4)
        self.assertEqual(report["unresolved_records"], 36)
        self.assertEqual(report["source_rows"], 1452)
        self.assertEqual(report["official_exact_source_rows"], 1346)
        self.assertEqual(report["preserved_native_japanese_source_row_count"], 106)
        self.assertEqual(report["release_eligibility"], "PARTIAL_NOT_FULL_SCOPE")
        self.assertFalse(report["all_catalogue_descriptions_translated"])
        self.assertEqual(report["unresolved_item_ids"], list(range(500, 536)))
        self.assertEqual(report["preserved_native_japanese_item_ids"], list(range(500, 536)))
        self.assertEqual(report["partially_translated_records"], [500, 501, 504, 515, 534])
        self.assertEqual(
            report["fully_japanese_preserved_item_ids"],
            [item_id for item_id in range(500, 536)
             if item_id not in {500, 501, 504, 515, 534}],
        )
        self.assertEqual(report["unresolved_item_ids"][-1], 535)
        import struct

        self.assertNotEqual(struct.unpack_from("<I", result, 0x1520C)[0], 0x0C062790)
        # The table indexes full item IDs. An unknown slot remains zero so the
        # native helper falls back to the original Japanese pointer in t0.
        phoff = struct.unpack_from("<I", result, 28)[0]
        phents, phnum = struct.unpack_from("<HH", result, 42)
        segs = [struct.unpack_from("<8I", result, phoff + i * phents)
                for i in range(phnum)]
        va = int(report["translation_table_va"], 16)
        table_fo = next(p[1] + va - p[2] for p in segs
                        if p[0] == 1 and p[2] <= va < p[2] + p[4])
        self.assertNotEqual(struct.unpack_from("<I", result, table_fo + 500 * 4)[0], 0)
        self.assertEqual(struct.unpack_from("<I", result, table_fo + 502 * 4)[0], 0)
        self.assertNotEqual(struct.unpack_from("<I", result, table_fo + 334 * 4)[0], 0)

        pointer = struct.unpack_from("<I", result, table_fo + 500 * 4)[0]
        string_fo = next(p[1] + pointer - p[2] for p in segs
                         if p[0] == 1 and p[2] <= pointer < p[2] + p[4])
        end = result.index(b"\0", string_fo)
        mixed = result[string_fo:end].decode("cp932")
        self.assertIn("水の代わりに粒子化された", mixed)
        self.assertIn("消火銃。", mixed)
        self.assertIn("Ｃｌｅａｎｓｅ", mixed)

    def test_apply_accepts_an_earlier_independent_append(self) -> None:
        import struct

        prior = bytearray(BASELINE.read_bytes())
        prior.extend(b"\0" * 16)
        struct.pack_into("<I", prior, 0x64, len(prior) - 0x803150)
        result, report = apply(bytes(prior), corpus_path=CORPUS_PATH)
        self.assertGreater(len(result), len(prior))
        self.assertEqual(report["status"], "PARTIAL_OFFICIAL_SUBSET")

    def test_wrong_official_corpus_hash_is_rejected(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory(prefix="r67-15g-details-") as directory:
            altered = Path(directory) / "English.bytes"
            altered.write_bytes(CORPUS_PATH.read_bytes() + b"altered")
            with self.assertRaisesRegex(ValueError, "official English.bytes SHA-256"):
                apply(BASELINE.read_bytes(), corpus_path=altered)


if __name__ == "__main__":
    unittest.main()
