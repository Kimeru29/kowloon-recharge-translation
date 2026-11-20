from __future__ import annotations

import struct
import unittest

from tools.exact_import import ExactImportError, import_exact_mtx
from tools.mtx import MtxFile


def synthetic_mtx() -> bytes:
    header = struct.pack("<4H", 2, 4, 0, 0)
    region1 = "あ".encode("cp932") + b"wc___\x00"
    region2 = "い".encode("cp932") + b"wc___\x00"
    assert len(region1) == 8 and len(region2) == 8
    return header + region1 + region2


class ExactMtxImportTests(unittest.TestCase):
    def test_imports_identical_direct_mtx_and_rebuilds_pointers(self) -> None:
        raw = synthetic_mtx()
        dc = {"keys": [8, 16], "values": ["Hello", "World"]}

        result = import_exact_mtx(raw, raw, dc)

        parsed = MtxFile.parse(result)
        self.assertIn("Ｈｅｌｌｏ".encode("cp932"), result)
        self.assertIn("Ｗｏｒｌｄ".encode("cp932"), result)
        self.assertNotIn("あ".encode("cp932"), result)
        self.assertEqual(8, parsed.header_size)
        self.assertTrue(all(offset % 4 == 0 for offset in parsed.pointer_offsets if offset))

    def test_rejects_non_identical_ps2_ps4_sources(self) -> None:
        raw = synthetic_mtx()
        changed = raw[:-1] + b"X"

        with self.assertRaisesRegex(ExactImportError, "byte-identical"):
            import_exact_mtx(raw, changed, {"keys": [8], "values": ["Hello"]})

    def test_rejects_duplicate_or_indirect_dc_key_instead_of_guessing(self) -> None:
        raw = synthetic_mtx()
        dc = {"keys": [8, 8], "values": ["First", "Second"]}

        with self.assertRaises(ExactImportError):
            import_exact_mtx(raw, raw, dc)


def _mtx_with_single_byte_prefix() -> bytes:
    """Build an MTX whose first DC anchor is a single-byte control prefix.

    Layout: header(8) | region1(8): l + あいwc_ | region2(8): えwc___
    DC keys 8 and 9 both land on CP932 boundaries but 9 is a continuation.
    """
    header = struct.pack("<4H", 2, 4, 0, 0)
    region1 = b"l" + "あい".encode("cp932") + b"wc_"  # 8 bytes
    region2 = "え".encode("cp932") + b"wc___\x00"  # 8 bytes
    assert len(region1) == 8 and len(region2) == 8
    return header + region1 + region2


def _mtx_with_two_byte_prefix() -> bytes:
    """Build an MTX whose first DC anchor is a two-byte CP932 character.

    Layout: header(8) | region1(8): あいwc__ | region2(8): えwc___
    DC keys 8 and 10 both land on CP932 boundaries but 10 is a continuation.
    """
    header = struct.pack("<4H", 2, 4, 0, 0)
    region1 = "あい".encode("cp932") + b"wc__"  # 8 bytes
    region2 = "え".encode("cp932") + b"wc___\x00"  # 8 bytes
    assert len(region1) == 8 and len(region2) == 8
    return header + region1 + region2


class AdjacentDcKeyMergeTests(unittest.TestCase):
    """Verify that adjacent DC keys separated by exactly one CP932 character
    are merged into a single group instead of creating a tiny broken group."""

    def test_merges_single_byte_control_prefix_with_following_key(self) -> None:
        raw = _mtx_with_single_byte_prefix()
        # Keys at 8 (the 'l' prefix) and 9 (text start at next boundary), plus region2 at 16
        dc = {"keys": [8, 9, 16], "values": ["Line one", "Line two", "Other"]}

        result = import_exact_mtx(raw, raw, dc)

        parsed = MtxFile.parse(result)
        compiled = parsed.compile()
        self.assertIn("Ｌｉｎｅ　ｏｎｅ".encode("cp932"), compiled)
        self.assertIn("Ｌｉｎｅ　ｔｗｏ".encode("cp932"), compiled)
        self.assertIn("Ｏｔｈｅｒ".encode("cp932"), compiled)

    def test_merges_two_byte_cp932_prefix_with_following_key(self) -> None:
        raw = _mtx_with_two_byte_prefix()
        # Actual synthetic keys enumerate English lines at anchor + 1, + 2;
        # a two-byte source glyph does not justify skipping a synthetic index.
        dc = {"keys": [8, 9, 10, 16], "values": ["Line one", "Line two", "Line three", "Other"]}

        result = import_exact_mtx(raw, raw, dc)

        parsed = MtxFile.parse(result)
        compiled = parsed.compile()
        self.assertIn("Ｌｉｎｅ　ｏｎｅ".encode("cp932"), compiled)
        self.assertIn("Ｌｉｎｅ　ｔｗｏ".encode("cp932"), compiled)
        self.assertIn("Ｏｔｈｅｒ".encode("cp932"), compiled)

    def test_rejects_when_merge_causes_wrong_terminator_position(self) -> None:
        """Ensure the merge doesn't blindly accept; the terminator must exist."""
        header = struct.pack("<4H", 2, 4, 0, 0)
        # region with no known terminator
        region1 = b"l" + "あ".encode("cp932") + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        region2 = "え".encode("cp932") + b"wc___\x00"
        raw = header + region1 + region2
        dc = {"keys": [8, 9], "values": ["Line one", "Line two"]}

        with self.assertRaises(ExactImportError):
            import_exact_mtx(raw, raw, dc)


if __name__ == "__main__":
    unittest.main()
