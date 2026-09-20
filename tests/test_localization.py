from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.localization import DcLocalization, encode_ps2_english
from tests.local_fixtures import require_local_fixture


ROOT = Path(__file__).parents[1] / "fixtures" / "DG00_00"
require_local_fixture(ROOT / "original.MTX")
require_local_fixture(ROOT / "en.mtxdc.json")
RAW = (ROOT / "original.MTX").read_bytes()
DC = json.loads((ROOT / "en.mtxdc.json").read_text())


class Ps2EnglishEncodingTests(unittest.TestCase):
    def test_uses_fullwidth_shift_jis_not_ascii_opcodes(self) -> None:
        encoded = encode_ps2_english("Hey,  over  here.")

        self.assertEqual("Ｈｅｙ，　ｏｖｅｒ　ｈｅｒｅ．", encoded.decode("cp932"))
        self.assertEqual(2 * len("Ｈｅｙ，　ｏｖｅｒ　ｈｅｒｅ．"), len(encoded))

    def test_encodes_apostrophe_as_jis_right_quote(self) -> None:
        encoded = encode_ps2_english("Don't")

        self.assertEqual("Ｄｏｎ’ｔ", encoded.decode("cp932"))


class DcLocalizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.localization = DcLocalization.from_json(RAW, DC)

    def test_groups_synthetic_trail_byte_key_with_real_anchor(self) -> None:
        group = self.localization.group_at(2909)

        self.assertEqual(("Go  after  them!", "Don't  lose  sight  of  them!"), group.lines)
        self.assertEqual((2910,), group.synthetic_keys)

    def test_infers_r_terminated_span(self) -> None:
        group = self.localization.group_at(107)

        self.assertEqual(127, group.replace_end)
        self.assertEqual(b"r", RAW[group.replace_end:group.replace_end + 1])

    def test_infers_wc_terminated_span_while_dropping_internal_ruby_and_breaks(self) -> None:
        group = self.localization.group_at(128)

        self.assertEqual(177, group.replace_end)
        self.assertEqual(b"wc", RAW[group.replace_end:group.replace_end + 2])

    def test_infers_title_w_command_span(self) -> None:
        group = self.localization.group_at(2829)

        self.assertEqual(2853, group.replace_end)
        self.assertEqual(b"}w60", RAW[group.replace_end:group.replace_end + 4])

    def test_synthetic_group_emits_ps2_line_break_and_preserves_wc(self) -> None:
        group = self.localization.group_at(2909)
        replacement = group.encoded_replacement()

        left, right = replacement.split(b"r", 1)
        self.assertEqual("Ｇｏ　ａｆｔｅｒ　ｔｈｅｍ！", left.decode("cp932"))
        self.assertEqual("Ｄｏｎ’ｔ　ｌｏｓｅ　ｓｉｇｈｔ　ｏｆ　ｔｈｅｍ！", right.decode("cp932"))
        self.assertEqual(b"wc", RAW[group.replace_end:group.replace_end + 2])

    def test_all_dc_entries_resolve_without_overlapping_replacement_spans(self) -> None:
        groups = self.localization.groups

        self.assertEqual(194, len(groups))
        self.assertEqual(195, sum(1 + len(group.synthetic_keys) for group in groups))
        for previous, current in zip(groups, groups[1:]):
            self.assertLessEqual(previous.replace_end, current.anchor)


if __name__ == "__main__":
    unittest.main()
