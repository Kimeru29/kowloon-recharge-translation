from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import unittest

from tools.generate_hant_dictionary_definitions import render_module
from tools.hant_dictionary_definitions import DICTIONARY_DEFINITION_MAX_CELLS, definition_source_fingerprint, inventory_dictionary_definition_sources
from tools.hant_dictionary_definitions_data import (
    HANT_DICTIONARY_DEFINITION_DATA,
    HANT_DICTIONARY_ENGLISH_BYTES_SHA256,
    HANT_DICTIONARY_SOURCE_ELF_SHA256,
)
from tools.hant_layout import measured_hant_cells


ROOT = Path(__file__).resolve().parents[1]
ELF = ROOT / "fixtures" / "elf" / "SLPM_665.11"
ENGLISH_BYTES = Path("/private/tmp/khc-ps4-full/Media/StreamingAssets/data/English.bytes")


class HantDictionaryDefinitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = ELF.read_bytes()

    def test_generated_manifest_covers_every_selectable_definition_fail_closed(self) -> None:
        sources = {source.key: source for source in inventory_dictionary_definition_sources(self.raw)}
        records = {record[0]: record for record in HANT_DICTIONARY_DEFINITION_DATA}
        self.assertEqual(208, len(sources))
        self.assertEqual(208, len(records))
        self.assertEqual(set(sources), set(records))
        self.assertEqual(HANT_DICTIONARY_SOURCE_ELF_SHA256, sha256(self.raw).hexdigest())

        total_english_rows = 0
        for key, source in sources.items():
            record = records[key]
            _key, descriptor, table, source_rows, source_hash, english_rows, provenance = record
            with self.subTest(key=key):
                self.assertEqual(source.descriptor_offset, descriptor)
                self.assertEqual(source.source_table_offset, table)
                self.assertEqual(source.source_row_count, source_rows)
                self.assertEqual(source.source_sha256, source_hash)
                self.assertEqual(source_hash, definition_source_fingerprint(self.raw, table, source_rows))
                self.assertEqual("official_exact_reflow", provenance)
                self.assertTrue(english_rows)
                self.assertTrue(all(measured_hant_cells(row) <= DICTIONARY_DEFINITION_MAX_CELLS for row in english_rows))
                total_english_rows += len(english_rows)
        self.assertEqual(4177, total_english_rows)

    def test_generated_manifest_is_reproducible_from_owned_remaster_when_available(self) -> None:
        if not ENGLISH_BYTES.is_file():
            self.skipTest("owned CUSA27034 English.bytes corpus is not present")
        self.assertEqual(HANT_DICTIONARY_ENGLISH_BYTES_SHA256, sha256(ENGLISH_BYTES.read_bytes()).hexdigest())
        rendered = render_module(ELF, ENGLISH_BYTES)
        self.assertEqual((ROOT / "tools" / "hant_dictionary_definitions_data.py").read_text(encoding="utf-8"), rendered)


if __name__ == "__main__":
    unittest.main()
