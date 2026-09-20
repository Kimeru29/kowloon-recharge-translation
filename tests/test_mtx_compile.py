from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.localization import DcLocalization
from tools.mtx import MtxFile, MtxReplacement
from tests.local_fixtures import require_local_fixture


ROOT = Path(__file__).parents[1] / "fixtures" / "DG00_00"
require_local_fixture(ROOT / "original.MTX")
require_local_fixture(ROOT / "en.mtxdc.json")
RAW = (ROOT / "original.MTX").read_bytes()
DC = json.loads((ROOT / "en.mtxdc.json").read_text())


class MtxCompileTests(unittest.TestCase):
    def test_rebuilds_pointer_regions_and_relocates_all_entry_points(self) -> None:
        localization = DcLocalization.from_json(RAW, DC)
        original = MtxFile.parse(RAW)
        replacements = tuple(
            MtxReplacement(group.anchor, group.replace_end, group.encoded_replacement())
            for group in localization.groups
        )

        translated = original.apply_replacements(replacements)
        rebuilt = translated.compile()
        reparsed = MtxFile.parse(rebuilt)

        self.assertEqual(len(original.pointer_words), len(reparsed.pointer_words))
        self.assertEqual(original.header_size, reparsed.header_size)
        self.assertEqual(tuple(sorted(reparsed.pointer_offsets)), reparsed.pointer_offsets)
        self.assertTrue(all(offset % 4 == 0 for offset in reparsed.pointer_offsets))
        self.assertNotEqual(original.pointer_words, reparsed.pointer_words)

    def test_preserves_non_text_control_markers(self) -> None:
        localization = DcLocalization.from_json(RAW, DC)
        original = MtxFile.parse(RAW)
        replacements = tuple(
            MtxReplacement(group.anchor, group.replace_end, group.encoded_replacement())
            for group in localization.groups
        )
        rebuilt = original.apply_replacements(replacements).compile()

        self.assertEqual(RAW.count(b"wc"), rebuilt.count(b"wc"))
        self.assertEqual(RAW.count(b"ds01"), rebuilt.count(b"ds01"))
        self.assertEqual(RAW.count(b"sbr"), rebuilt.count(b"sbr"))

        reparsed = MtxFile.parse(rebuilt)
        offsets = reparsed.pointer_offsets
        for start, end in zip(offsets, offsets[1:] + (len(rebuilt),)):
            self.assertTrue(rebuilt[start:end].rstrip(b"\x00").endswith(b"_"))

    def test_contains_official_english_and_removes_corresponding_japanese(self) -> None:
        localization = DcLocalization.from_json(RAW, DC)
        original = MtxFile.parse(RAW)
        replacements = tuple(
            MtxReplacement(group.anchor, group.replace_end, group.encoded_replacement())
            for group in localization.groups
        )
        rebuilt = original.apply_replacements(replacements).compile()

        self.assertIn("Ｈｅｙ，　ｏｖｅｒ　ｈｅｒｅ．".encode("cp932"), rebuilt)
        self.assertNotIn("おい、こっちじゃ".encode("cp932"), rebuilt)
        self.assertIn(
            "Ｇｏ　ａｆｔｅｒ　ｔｈｅｍ！rＤｏｎ’ｔ　ｌｏｓｅ　ｓｉｇｈｔ　ｏｆ　ｔｈｅｍ！".encode("cp932"),
            rebuilt,
        )

    def test_rejects_replacement_that_crosses_pointer_region_boundary(self) -> None:
        original = MtxFile.parse(RAW)

        with self.assertRaisesRegex(ValueError, "pointer region"):
            original.apply_replacements((MtxReplacement(1960, 1980, b"X"),))


if __name__ == "__main__":
    unittest.main()
