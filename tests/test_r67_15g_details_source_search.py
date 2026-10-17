from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import unittest

from tools.r67_15g_details_source_search import (
    find_exact_keys,
    main,
    scan_raw_assets,
)


class DetailsSourceSearchTests(unittest.TestCase):
    def test_raw_scan_finds_full_paragraphs_and_line_keys_in_synthetic_assets(self) -> None:
        owners = {
            b"line-key": {(500, "line_key")},
            b"whole japanese paragraph": {(501, "full_paragraph")},
        }
        line_hits, paragraph_hits, byte_count = scan_raw_assets(
            [("asset-a.bytes", b"prefix line-key suffix"),
             ("asset-b.map", b"whole japanese paragraph")],
            owners,
        )

        self.assertEqual(line_hits, {500: {"asset-a.bytes"}})
        self.assertEqual(paragraph_hits, {501})
        self.assertEqual(byte_count, 46)

    def test_exact_key_matching_does_not_promote_substrings_or_partial_rows(self) -> None:
        unresolved_keys = {
            500: {"Japanese row A＠改行", "Japanese row B＠改行"},
            501: {"Japanese row C＠改行"},
        }

        self.assertEqual(
            find_exact_keys(unresolved_keys, {"Japanese row A＠改行", "prefix Japanese row C＠改行"}),
            {500: ["Japanese row A＠改行"]},
        )

    def test_automaton_rejects_empty_patterns(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty raw-search pattern"):
            scan_raw_assets([], {b"": {(500, "line_key")}})

    def test_cli_help_exits_without_opening_search_inputs(self) -> None:
        output = StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--help"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("--asset-root", output.getvalue())
        self.assertIn("--corpus", output.getvalue())


if __name__ == "__main__":
    unittest.main()
