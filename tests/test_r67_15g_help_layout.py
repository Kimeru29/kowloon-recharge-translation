from __future__ import annotations

import hashlib
import struct
import unicodedata
import unittest
from pathlib import Path

from tools.inspect_english_bytes import parse as parse_english
from tools.hant_ui import _HANT_BLANK_VA, _HANT_EOF_VA
from tools.r67_15g_help_layout import (
    ICON_BINDINGS,
    PAGE_OWNERS,
    PERMITTED_EXISTING_RANGES,
    apply,
    page_geometry,
)


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "local/r67-15f-item-panel-layout.elf"
CORPUS = Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
TARGETS = {"item_synthesis", "save_load", "wire_gun", "jumping"}
VIEW_ROWS = 16


def _segments(raw: bytes) -> list[tuple[int, int, int]]:
    phoff = struct.unpack_from("<I", raw, 28)[0]
    entsize, count = struct.unpack_from("<HH", raw, 42)
    return [
        (offset, address, size)
        for index in range(count)
        for kind, offset, address, _pa, size, _mem, _flags, _align in [
            struct.unpack_from("<8I", raw, phoff + index * entsize)
        ]
        if kind == 1
    ]


def _va_offset(raw: bytes, address: int) -> int:
    for offset, base, size in _segments(raw):
        if base <= address < base + size:
            return offset + address - base
    raise AssertionError(f"unmapped address {address:#x}")


def _page_rows(raw: bytes, owner: dict) -> tuple[int, list[str]]:
    descriptor = owner["descriptor_offset"]
    address = struct.unpack_from("<I", raw, descriptor)[0]
    table = _va_offset(raw, address)
    rows: list[str] = []
    for row in range(160):
        pointer = struct.unpack_from("<I", raw, table + row * 4)[0]
        if pointer == _HANT_EOF_VA:
            return table, rows
        if pointer == _HANT_BLANK_VA:
            rows.append("")
            continue
        start = _va_offset(raw, pointer)
        end = raw.find(b"\0", start, start + 384)
        if end < 0:
            raise AssertionError("unterminated Help row")
        rows.append(raw[start:end].decode("cp932"))
    raise AssertionError("Help table has no EOF")


def _canonical_content(lines: list[str]) -> str:
    return " ".join(unicodedata.normalize("NFKC", line) for line in lines if line).split()


class R6715GHelpLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base = BASE.read_bytes()
        cls.corpus_bytes = CORPUS.read_bytes()
        cls.english = parse_english(CORPUS)
        cls.output, cls.report = apply(cls.base, cls.corpus_bytes)

    def test_legacy_five_cell_layout_has_real_rectangle_collisions(self) -> None:
        old = page_geometry(self.base, legacy=True)
        self.assertEqual(TARGETS, set(old))
        collided = {
            key
            for key, geometry in old.items()
            if geometry["intersections"]
        }
        self.assertEqual(TARGETS, collided)

    def test_reflowed_full_glyph_and_sprite_rectangles_do_not_intersect(self) -> None:
        for key, geometry in page_geometry(self.output).items():
            with self.subTest(page=key):
                self.assertEqual([], geometry["intersections"])
                self.assertTrue(all(width <= 28 for width in geometry["glyph_widths"]))

    def test_complete_page_prose_and_all_official_words_are_preserved(self) -> None:
        for key, owner in PAGE_OWNERS.items():
            with self.subTest(page=key):
                _table, rows = _page_rows(self.output, owner)
                joined = _canonical_content(rows)
                original = _canonical_content(_page_rows(self.base, owner)[1])
                self.assertEqual(original, joined)
                self.assertTrue(joined)
                self.assertFalse(any(len(word) > 28 for word in joined))

        corpus_text = " ".join(text for _japanese, text, _position in self.english)
        normalized_corpus = unicodedata.normalize("NFKC", corpus_text).casefold()
        for phrase in (
            "compound", "cannot be compounded", "Rockford Adventure",
            "wire pole", "Physical Education", "mini-game",
        ):
            self.assertIn(phrase.casefold(), normalized_corpus)

    def test_controls_and_diagrams_keep_native_identity_and_instruction_pairing(self) -> None:
        for key, bindings in ICON_BINDINGS.items():
            with self.subTest(page=key):
                self.assertTrue(bindings)
                owner = PAGE_OWNERS[key]
                meta_va = struct.unpack_from("<I", self.output, owner["metadata_descriptor_offset"])[0]
                meta = _va_offset(self.output, meta_va)
                records = []
                for index in range(32):
                    value = struct.unpack_from("<4h", self.output, meta + index * 8)
                    if value == (-1, -1, -1, -1):
                        break
                    records.append(value)
                self.assertEqual(len(bindings), len(records))
                reported = self.report["pages"][key]["icons"]
                output_rows = _page_rows(self.output, owner)[1]
                for index, binding in enumerate(bindings):
                    self.assertEqual(binding["identity"], records[index][:2])
                    self.assertEqual(binding["identity"], reported[index]["identity"])
                    self.assertGreaterEqual(reported[index]["instruction_row"], 0)
                    self.assertLess(reported[index]["instruction_row"], len(_page_rows(self.output, owner)[1]))
                    start = reported[index]["instruction_row"]
                    associated = []
                    for row in output_rows[start:]:
                        if not row:
                            break
                        associated.append(unicodedata.normalize("NFKC", row))
                    self.assertIn(binding["anchor"].casefold(), " ".join(associated).casefold())

    def test_all_rows_fit_scrolling_window_and_end_is_reachable(self) -> None:
        for key, owner in PAGE_OWNERS.items():
            with self.subTest(page=key):
                _table, rows = _page_rows(self.output, owner)
                self.assertGreater(len(rows), VIEW_ROWS)
                self.assertEqual(len(rows) - VIEW_ROWS, self.report["pages"][key]["max_scroll_row"])
                self.assertEqual(unicodedata.normalize("NFKC", rows[-1]), self.report["pages"][key]["last_row"])
                self.assertTrue(self.report["pages"][key]["end_reachable"])

    def test_only_named_descriptors_and_appended_payload_change(self) -> None:
        changed = [i for i, pair in enumerate(zip(self.base, self.output)) if pair[0] != pair[1]]
        allowed = set()
        for start, end in PERMITTED_EXISTING_RANGES:
            self.assertLess(start, end)
            self.assertFalse(start < 0x68 and end > 0x64)
            allowed.update(range(start, end))
        segment_size_metadata = set(range(0x64, 0x68))
        self.assertTrue(all(offset in allowed or offset in segment_size_metadata
                            or offset >= len(self.base) for offset in changed))
        self.assertEqual(
            [[0x64, 0x68]], self.report["separately_audited_metadata_ranges"]
        )
        for key, owner in PAGE_OWNERS.items():
            old_table, _ = _page_rows(self.base, owner)
            new_table, _ = _page_rows(self.output, owner)
            self.assertNotEqual(old_table, new_table, key)
        self.assertEqual(TARGETS, set(self.report["pages"]))

    def test_unaffected_help_page_descriptors_remain_byte_identical(self) -> None:
        targeted = {owner["descriptor_offset"] for owner in PAGE_OWNERS.values()}
        targeted |= {owner["metadata_descriptor_offset"] for owner in PAGE_OWNERS.values()}
        for offset in range(0x5CBA60, 0x5CBA60 + 0x60, 4):
            if offset in targeted:
                continue
            self.assertEqual(self.base[offset:offset + 4], self.output[offset:offset + 4])

    def test_malformed_owned_preimage_fails_closed(self) -> None:
        damaged = bytearray(self.base)
        damaged[PAGE_OWNERS["wire_gun"]["descriptor_offset"]] ^= 1
        with self.assertRaisesRegex(ValueError, "preimage|owner|descriptor"):
            apply(bytes(damaged), self.corpus_bytes)

    def test_native_sprite_frame_preimage_is_pinned(self) -> None:
        damaged = bytearray(self.base)
        damaged[0x380AF0 + 3 * 8] ^= 1
        with self.assertRaisesRegex(ValueError, "sprite frame preimage"):
            apply(bytes(damaged), self.corpus_bytes)

    def test_source_english_text_preimage_is_pinned(self) -> None:
        damaged = bytearray(self.base)
        owner = PAGE_OWNERS["item_synthesis"]
        table, _rows = _page_rows(self.base, owner)
        pointer = struct.unpack_from("<I", self.base, table)[0]
        start = _va_offset(self.base, pointer)
        end = self.base.index(0, start)
        row = self.base[start:end].decode("cp932")
        altered = row.replace("Ｃ", "Ｘ", 1).encode("cp932")
        damaged[start:end] = altered
        with self.assertRaisesRegex(ValueError, "source English text preimage"):
            apply(bytes(damaged), self.corpus_bytes)

    def test_accepts_sequentially_extended_translation_segment(self) -> None:
        extended = bytearray(self.base)
        marker = b"prior-disjoint-component"
        extended.extend(marker)
        file_size_offset = 0x64
        old_size = struct.unpack_from("<I", extended, file_size_offset)[0]
        struct.pack_into("<I", extended, file_size_offset, old_size + len(marker))
        output, report = apply(bytes(extended), self.corpus_bytes)
        self.assertEqual(marker, output[len(extended) - len(marker):len(extended)])
        self.assertEqual(len(extended), report["appended_extent"][0])
        self.assertGreater(len(output), len(extended))


if __name__ == "__main__":
    unittest.main()
