from __future__ import annotations

import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.inspect_english_bytes import parse
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_15j_action_labels import (
    ALLOWED_SOURCE_RANGES,
    CORPUS_PATH,
    CORPUS_SHA256,
    DUNGEON_ACTIONS,
    H_ITEM_ACTIONS,
    build,
)
from tools import r67_15j_action_labels as action_labels


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-15i-hant-text-item-details.elf"


class ActionLabelPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not SOURCE.is_file():
            raise unittest.SkipTest("Requires the local staged r67.15i ELF")
        if not CORPUS_PATH.is_file():
            raise unittest.SkipTest("Requires the owned official English.bytes corpus")
        cls.source = SOURCE.read_bytes()
        cls.result, cls.report = build(cls.source)

    def test_every_h_item_japanese_action_is_replaced_by_its_official_match(self) -> None:
        self.assertEqual(16, len(H_ITEM_ACTIONS))
        self.assertEqual(16, len({spec.owner for spec in H_ITEM_ACTIONS}))
        for spec in H_ITEM_ACTIONS:
            with self.subTest(owner=hex(spec.owner)):
                original = struct.unpack_from("<I", self.source, spec.owner)[0]
                current = read_string(self.source, original).decode("cp932")
                if spec.patch:
                    self.assertNotEqual(spec.english_native, current, spec.key)
                else:
                    self.assertEqual(spec.existing_native_english, current, spec.key)
                pointer = struct.unpack_from("<I", self.result, spec.owner)[0]
                self.assertEqual(spec.english_native,
                                 read_string(self.result, pointer).decode("cp932"))

    def test_dungeon_action_owner_inventory_includes_aliases_and_both_sentinels(self) -> None:
        self.assertEqual(13, len(DUNGEON_ACTIONS))
        self.assertEqual(
            {0x594F84, 0x594F88, 0x594F8C, 0x594F90, 0x594F94,
             0x594F98, 0x594FA0, 0x594FA4, 0x594FA8, 0x594FAC,
             0x594FB0, 0x594FB4, 0x594FBC},
            {spec.owner for spec in DUNGEON_ACTIONS},
        )
        self.assertEqual({0x594F80: 0x795B9C, 0x594F9C: 0x795B9C},
                         action_labels.SENTINELS)

    def test_take_and_place_regressions_are_covered(self) -> None:
        owners = {spec.owner: spec for spec in H_ITEM_ACTIONS}
        for owner, source, english, corpus_offset in (
            (0x38635C, "置く", "Place", 0x46318),
        ):
            spec = owners[owner]
            self.assertEqual((source, english, corpus_offset),
                             (spec.source_japanese, spec.english, spec.official_offset))
            before = struct.unpack_from("<I", self.source, owner)[0]
            after = struct.unpack_from("<I", self.result, owner)[0]
            self.assertEqual(source, read_string(self.source, before).decode("cp932"))
            self.assertEqual(spec.english_native,
                             read_string(self.result, after).decode("cp932"))

        take = next(spec for spec in DUNGEON_ACTIONS if spec.owner == 0x594F8C)
        self.assertEqual(("取る", "Take", 0xD0B57),
                         (take.source_japanese, take.english, take.official_offset))
        before = struct.unpack_from("<I", self.source, take.owner)[0]
        after = struct.unpack_from("<I", self.result, take.owner)[0]
        self.assertEqual("取る", read_string(self.source, before).decode("cp932"))
        self.assertEqual(take.english_native,
                         read_string(self.result, after).decode("cp932"))

    def test_existing_h_item_english_ids_and_empty_dungeon_slot_are_preserved(self) -> None:
        for owner, expected in ((0x386324, "Ｃａｎ’ｔ"), (0x38632C, "Ｃｏｍｐｏｕｎｄ")):
            self.assertEqual(self.source[owner:owner + 4], self.result[owner:owner + 4])
            pointer = struct.unpack_from("<I", self.result, owner)[0]
            self.assertEqual(expected, read_string(self.result, pointer).decode("cp932"))
        for spec in DUNGEON_ACTIONS:
            if not spec.patch:
                self.assertEqual(self.source[spec.owner:spec.owner + 4],
                                 self.result[spec.owner:spec.owner + 4], spec.key)
        self.assertEqual(0x795B9C, struct.unpack_from("<I", self.result, 0x594F9C)[0])
        self.assertEqual(self.source[0x594F9C:0x594FA0], self.result[0x594F9C:0x594FA0])
        self.assertEqual(0x795B9C, struct.unpack_from("<I", self.result, 0x594F80)[0])
        self.assertEqual(self.source[0x594F50:0x594F7A], self.result[0x594F50:0x594F7A])
        enter = next(spec for spec in DUNGEON_ACTIONS if spec.owner == 0x594FBC)
        self.assertIsNone(enter.english)
        self.assertFalse(enter.patch)
        pointer = struct.unpack_from("<I", self.result, enter.owner)[0]
        self.assertEqual("入る", read_string(self.result, pointer).decode("cp932"))

    def test_official_rows_are_unique_and_pinned_to_owned_corpus(self) -> None:
        self.assertEqual(CORPUS_SHA256,
                         hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest())
        rows = parse(CORPUS_PATH)
        by_offset = {offset: (key, value) for key, value, offset in rows}
        for spec in (*H_ITEM_ACTIONS, *DUNGEON_ACTIONS):
            with self.subTest(owner=hex(spec.owner)):
                matches = [(key, value, offset) for key, value, offset in rows
                           if key == spec.source_japanese]
                if spec.english is None:
                    self.assertEqual([], matches)
                else:
                    self.assertEqual([(spec.source_japanese, spec.english, spec.official_offset)],
                                     matches)
                    self.assertEqual((spec.source_japanese, spec.english),
                                     by_offset[spec.official_offset])

    def test_rejects_changed_official_corpus_even_when_rows_parse(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "English.bytes"
            altered.write_bytes(CORPUS_PATH.read_bytes() + b"\0")
            with patch.object(action_labels, "CORPUS_PATH", altered):
                with self.assertRaisesRegex(ValueError, "corpus hash mismatch"):
                    build(self.source)

    def test_source_change_contract_is_narrow_and_excludes_filesz_metadata(self) -> None:
        expected = {f"h_item_action_{spec.key}": ((spec.owner, spec.owner + 4),)
                    for spec in H_ITEM_ACTIONS if spec.patch}
        expected.update({f"dungeon_action_{spec.key}": ((spec.owner, spec.owner + 4),)
                         for spec in DUNGEON_ACTIONS if spec.patch})
        self.assertEqual(expected, ALLOWED_SOURCE_RANGES)
        allowed = {offset for ranges in ALLOWED_SOURCE_RANGES.values()
                   for start, end in ranges for offset in range(start, end)}
        allowed.update(range(0x64, 0x68))
        changed = {offset for offset, (old, new) in
                   enumerate(zip(self.source, self.result)) if old != new}
        self.assertTrue(changed)
        self.assertFalse(changed - allowed)
        self.assertEqual(len(self.source), len(self.result[:len(self.source)]))
        self.assertEqual(self.report["source_bytes_appended"],
                         len(self.result) - len(self.source))

    def test_rejects_changed_japanese_pointer_preimage(self) -> None:
        changed = bytearray(self.source)
        changed[0x38635C] ^= 1
        with self.assertRaisesRegex(ValueError, "preimage"):
            build(bytes(changed))

    def test_rejects_changed_empty_slot_and_unowned_pointer(self) -> None:
        changed = bytearray(self.source)
        struct.pack_into("<I", changed, 0x594F9C, 0x795EC8)
        with self.assertRaisesRegex(ValueError, "sentinel"):
            build(bytes(changed))

        changed = bytearray(self.source)
        struct.pack_into("<I", changed, 0x594FBC, 0x795EC8)
        with self.assertRaisesRegex(ValueError, "preimage"):
            build(bytes(changed))

    def test_composes_over_unowned_source_changes_without_overwriting_them(self) -> None:
        changed = bytearray(self.source)
        changed[0x200000] ^= 1
        result, _report = build(bytes(changed))
        self.assertEqual(changed[0x200000], result[0x200000])
        allowed = {offset for spans in ALLOWED_SOURCE_RANGES.values()
                   for start, end in spans for offset in range(start, end)}
        allowed.update(range(0x64, 0x68))
        actual = {offset for offset, (old, new) in
                  enumerate(zip(changed, result)) if old != new}
        self.assertFalse(actual - allowed)


if __name__ == "__main__":
    unittest.main()
