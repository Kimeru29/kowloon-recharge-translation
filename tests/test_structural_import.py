from __future__ import annotations

import json
import struct
import unittest
from pathlib import Path

from tools.localization import encode_ps2_english
from tools.mtx import MtxFile
from tools.structural_import import StructuralImportError, import_structural_mtx


def make_mtx(data: bytes) -> bytes:
    # Four u16 entries, all pointing at the single data region at offset 8.
    # The trailing '_' gives the compiler a safe 4-byte alignment terminator.
    return struct.pack("<4H", 2, 2, 2, 2) + data + b"_"


def key_for(raw: bytes, text: str) -> int:
    encoded = text.encode("cp932")
    offset = raw.index(encoded)
    return offset


class StructuralMtxImportTests(unittest.TestCase):
    def test_coalesces_two_semantically_equivalent_lines_when_japanese_split_moved(self) -> None:
        ps4_line1 = "復活を妨げようする者だと"
        ps4_line2 = "いう事だな？"
        ps2_line1 = "復活を妨げようと"
        ps2_line2 = "する者だという事だな？"
        ps4 = make_mtx(b"r" + ps4_line1.encode("cp932") + b"r" + ps4_line2.encode("cp932") + b"wc")
        ps2 = make_mtx(b"r" + ps2_line1.encode("cp932") + b"r" + ps2_line2.encode("cp932") + b"wc")
        dc = {
            "keys": [key_for(ps4, ps4_line1), key_for(ps4, ps4_line2)],
            "values": ["You  attempted  to  stop  my", "resurrection,  correct?"],
        }

        result = import_structural_mtx(ps2, ps4, dc)

        self.assertEqual(2, result.groups_total)
        self.assertEqual(0, result.direct_groups)
        self.assertEqual(2, result.semantic_groups)
        expected = encode_ps2_english("You attempted to stop my") + b"r" + encode_ps2_english("resurrection, correct?")
        self.assertIn(expected, result.data)
        self.assertNotIn(ps2_line1.encode("cp932"), result.data)
        MtxFile.parse(result.data)

    def test_rejects_unrelated_changed_japanese_even_with_same_control_shape(self) -> None:
        ps4_text = "復活を妨げる者だ"
        ps2_text = "今日は天気が良いです"
        ps4 = make_mtx(b"r" + ps4_text.encode("cp932") + b"wc")
        ps2 = make_mtx(b"r" + ps2_text.encode("cp932") + b"wc")
        dc = {"keys": [key_for(ps4, ps4_text)], "values": ["Stop  my  resurrection"]}

        with self.assertRaisesRegex(StructuralImportError, "could not prove"):
            import_structural_mtx(ps2, ps4, dc)

    def test_real_dg13_02_maps_every_official_group_when_local_sources_exist(self) -> None:
        ps2_path = Path("/private/tmp/khc-ps2-assets/ADV/DG/DG13_02.MTX")
        ps4_path = Path("/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV/DG/DG13_02.MTX")
        dc_path = Path("/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV/DG/EN/DG13_02DC.json")
        if not all(path.exists() for path in (ps2_path, ps4_path, dc_path)):
            self.skipTest("Owned Kowloon local corpus is not present")

        dc = json.loads(dc_path.read_text(encoding="utf-8"))
        result = import_structural_mtx(ps2_path.read_bytes(), ps4_path.read_bytes(), dc)

        self.assertEqual(577, result.english_entries)
        self.assertEqual(result.groups_total, result.direct_groups + result.semantic_groups)
        self.assertGreater(result.direct_groups, 500)
        self.assertGreaterEqual(result.semantic_groups, 2)
        MtxFile.parse(result.data)


    def test_accepts_single_semantic_group_with_internal_line_break_when_break_count_matches(self) -> None:
        ps4_text1 = "そうなんじゃないかな、って"
        ps4_text2 = "想っていたんです。"
        ps2_text1 = "そうなんじゃないかな、って"
        ps2_text2 = "思っていたんです。"
        ps4 = make_mtx(b"r" + ps4_text1.encode("cp932") + b"r" + ps4_text2.encode("cp932") + b"wc")
        ps2 = make_mtx(b"r" + ps2_text1.encode("cp932") + b"r" + ps2_text2.encode("cp932") + b"wc")
        dc = {"keys": [key_for(ps4, ps4_text1)], "values": ["I  thought  you  might  be."]}

        result = import_structural_mtx(ps2, ps4, dc)

        self.assertEqual(1, result.semantic_groups)
        self.assertIn(encode_ps2_english("I thought you might be."), result.data)

    def test_accepts_identical_text_when_following_control_command_has_same_delimiter_but_changed_parameters(self) -> None:
        text = "奇跡は、本物だと信じるよね？"
        ps4 = make_mtx(b"r" + text.encode("cp932") + b"wc_ds01s3ci50ch00704")
        ps2 = make_mtx(b"r" + text.encode("cp932") + b"wc_ds01s3ci50")
        dc = {"keys": [key_for(ps4, text)], "values": ["Do  you  believe  in  miracles?"]}

        result = import_structural_mtx(ps2, ps4, dc)

        self.assertEqual(1, result.direct_groups)
        self.assertIn(encode_ps2_english("Do you believe in miracles?"), result.data)


    def test_semantic_similarity_ignores_ps2_ruby_markup_when_surrounding_text_matches(self) -> None:
        ps4_text = "まあ、俺だったらrもう少しフェヌグリークをr利かせて―――、"
        ps2_text = "まァ、俺だったらrもう少しフェヌグリークをrl効(き)かせて―――、"
        ps4 = make_mtx(b"r" + ps4_text.encode("cp932") + b"wc")
        ps2 = make_mtx(b"r" + ps2_text.encode("cp932") + b"wc")
        dc = {"keys": [key_for(ps4, "まあ、俺だったら")], "values": ["I  would  add  more  fenugreek."]}

        result = import_structural_mtx(ps2, ps4, dc)

        self.assertEqual(1, result.semantic_groups)
        self.assertIn(encode_ps2_english("I would add more fenugreek."), result.data)


    def test_accepts_identical_first_text_inside_long_exact_block_despite_ps2_only_control_prefix(self) -> None:
        speaker = "【皆守】"
        line = "よォ、葉佩。"
        header = struct.pack("<4H", 2, 2, 2, 2)
        ps4 = header + speaker.encode("cp932") + b"r" + line.encode("cp932") + b"wc_"
        ps2 = header + b"ds05x+000y+448w448" + speaker.encode("cp932") + b"r" + line.encode("cp932") + b"wc_"
        dc = {
            "keys": [len(header), len(header) + len(speaker.encode("cp932")) + 1],
            "values": ["【Minakami】", "Yo, Habaki."],
        }

        result = import_structural_mtx(ps2, ps4, dc)

        self.assertEqual(2, result.direct_groups)
        self.assertIn(encode_ps2_english("【Minakami】"), result.data)
        self.assertIn(encode_ps2_english("Yo, Habaki."), result.data)


if __name__ == "__main__":
    unittest.main()
