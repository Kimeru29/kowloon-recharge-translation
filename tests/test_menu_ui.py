from __future__ import annotations

import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.menu_ui import MENU_LABELS, MenuLabelSpec, patch_menu_labels, relocated_menu_entries
from tools.localization import encode_ps2_english

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class MenuUiTests(unittest.TestCase):
    def test_manifest_has_unique_stable_owners_and_explicit_status(self) -> None:
        self.assertEqual(19, len(MENU_LABELS))
        self.assertTrue(all(isinstance(spec, MenuLabelSpec) for spec in MENU_LABELS))
        self.assertEqual(len(MENU_LABELS), len({spec.key for spec in MENU_LABELS}))
        self.assertEqual(len(MENU_LABELS), len({spec.source_offset for spec in MENU_LABELS}))
        self.assertTrue(all(spec.storage in {"fixed-slot", "relocated", "pristine"} for spec in MENU_LABELS))
        self.assertTrue(all(spec.status in {"proven", "unresolved", "intentionally-pristine"} for spec in MENU_LABELS))
        self.assertTrue(all(spec.evidence for spec in MENU_LABELS if spec.status == "proven"))
        self.assertTrue(all(spec.selected_english is None for spec in MENU_LABELS if spec.status == "unresolved"))

    def test_existing_fixed_menu_translations_are_preserved_semantically(self) -> None:
        actual = {spec.source_offset: spec for spec in MENU_LABELS}
        expected = {
            0x3BC7C8: (16, "アイテム", "Items"),
            0x3BC7D8: (16, "クエスト", "Quests"),
            0x3BC7E8: (16, "Ｈ．Ａ．Ｎ．Ｔ", "H.A.N.T"),
            0x3BC7F8: (16, "セーブ＆ロード", "Save & load"),
            0x3BC808: (16, "部屋を出る", "Leave room"),
            0x3BC818: (16, "ショップ", "Shop"),
            0x3BC828: (16, "ギルドサイト", "Guild site"),
            0x3BC838: (16, "ブロードバンド", "Broadband"),
            0x3BC848: (16, "コレクション", "Collection"),
            0x3BC868: (16, "次の話へ", "Next chapter"),
            0x3BC878: (16, "ターン終了", "End turn"),
            0x3BC898: (16, "インテリア", "Interior"),
            0x694180: (8, "なし", "None"),
            0x694188: (8, "マップ", "Map"),
            0x694198: (8, "ノイズ", "Noise"),
            0x6941A0: (8, "戦闘", "Battle"),
        }
        for offset, (capacity, source, english) in expected.items():
            with self.subTest(offset=hex(offset)):
                spec = actual[offset]
                self.assertEqual(capacity, spec.capacity)
                self.assertEqual(source, spec.source_text)
                self.assertEqual(english, spec.official_english)
                self.assertEqual(english, spec.selected_english)
                self.assertEqual("relocated", spec.storage)
                self.assertEqual("proven", spec.status)

    def test_unresolved_media_and_overflow_candidates_are_explicit(self) -> None:
        actual = {spec.source_offset: spec for spec in MENU_LABELS}

        media = actual[0x3BC858]
        self.assertEqual("メディア", media.source_text)
        self.assertIsNone(media.official_english)
        self.assertIsNone(media.selected_english)
        self.assertEqual("pristine", media.storage)
        self.assertEqual("unresolved", media.status)

        return_above = actual[0x3BC888]
        self.assertEqual("地上へ脱出", return_above.source_text)
        self.assertEqual("Return above ground", return_above.official_english)
        self.assertEqual("Return above ground", return_above.selected_english)
        self.assertEqual("relocated", return_above.storage)
        self.assertEqual("proven", return_above.status)
        self.assertEqual((0x3BC8F4,), return_above.pointer_offsets)

        report = actual[0x694190]
        self.assertEqual("成績表", report.source_text)
        self.assertEqual("Report card", report.official_english)
        self.assertEqual("Report card", report.selected_english)
        self.assertEqual("relocated", report.storage)
        self.assertEqual("proven", report.status)
        self.assertEqual((0x3BC8B8,), report.pointer_offsets)


    def test_every_label_records_its_exact_pointer_table_aliases(self) -> None:
        expected = {
            "none": (0x3BC8B0,),
            "map": (0x3BC8B4,),
            "report_card": (0x3BC8B8,),
            "items": (0x3BC8BC,),
            "quests": (0x3BC8C0,),
            "hant": (0x3BC8C4,),
            "save_load": (0x3BC8C8,),
            "leave_room": (0x3BC8CC, 0x3BC900),
            "shop": (0x3BC8D0,),
            "guild_site": (0x3BC8D4,),
            "broadband": (0x3BC8D8,),
            "collection": (0x3BC8DC, 0x3BC8F8),
            "media": (0x3BC8E0,),
            "noise": (0x3BC8E4,),
            "next_chapter": (0x3BC8E8,),
            "end_turn": (0x3BC8EC,),
            "battle": (0x3BC8F0,),
            "return_above_ground": (0x3BC8F4,),
            "interior": (0x3BC8FC,),
        }
        self.assertEqual(expected, {spec.key: spec.pointer_offsets for spec in MENU_LABELS})

    def test_relocated_entry_builder_uses_every_proven_label_in_wide_ps2_encoding(self) -> None:
        entries = relocated_menu_entries(RAW)
        proven = tuple(spec for spec in MENU_LABELS if spec.status == "proven")
        self.assertEqual(len(proven), len(entries))
        self.assertEqual(18, len(entries))
        self.assertEqual(
            tuple(f"menu_{spec.key}" for spec in proven),
            tuple(entry.key for entry in entries),
        )
        for spec, entry in zip(proven, entries, strict=True):
            with self.subTest(key=spec.key):
                assert spec.selected_english is not None
                self.assertEqual(
                    encode_ps2_english(spec.selected_english, collapse_spaces=False) + b"\x00",
                    entry.encoded,
                )
                self.assertEqual(spec.pointer_offsets, entry.pointer_offsets)
        self.assertNotIn("menu_media", {entry.key for entry in entries})

    def test_relocated_targets_patch_only_proven_pointer_words_and_preserve_sources(self) -> None:
        targets = {
            "return_above_ground": 0x00910000,
            "report_card": 0x00910040,
        }
        result = patch_menu_labels(RAW, targets)
        by_key = {spec.key: spec for spec in MENU_LABELS}

        for key, target in targets.items():
            spec = by_key[key]
            self.assertEqual(
                RAW[spec.source_offset:spec.source_offset + spec.capacity],
                result[spec.source_offset:spec.source_offset + spec.capacity],
            )
            for pointer_offset in spec.pointer_offsets:
                self.assertEqual(target, int.from_bytes(result[pointer_offset:pointer_offset + 4], "little"))

        media = by_key["media"]
        self.assertEqual(
            RAW[media.pointer_offsets[0]:media.pointer_offsets[0] + 4],
            result[media.pointer_offsets[0]:media.pointer_offsets[0] + 4],
        )

    def test_relocation_fails_closed_on_pointer_alias_or_unresolved_label(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x3BC8F4] ^= 1
        with self.assertRaisesRegex(ValueError, "pointer preimage mismatch"):
            patch_menu_labels(bytes(tampered), {"return_above_ground": 0x00910000})
        with self.assertRaisesRegex(ValueError, "pointer preimage mismatch"):
            relocated_menu_entries(bytes(tampered))

        with self.assertRaisesRegex(ValueError, "not relocation-owned"):
            patch_menu_labels(RAW, {"media": 0x00910000})

    def test_patch_menu_labels_without_targets_is_validation_only(self) -> None:
        result = patch_menu_labels(RAW)
        self.assertEqual(RAW, result)

    def test_all_proven_menu_sources_remain_pristine_for_relocation(self) -> None:
        result = patch_menu_labels(RAW)
        for spec in MENU_LABELS:
            with self.subTest(key=spec.key):
                self.assertEqual(
                    RAW[spec.source_offset:spec.source_offset + spec.capacity],
                    result[spec.source_offset:spec.source_offset + spec.capacity],
                )



if __name__ == "__main__":
    unittest.main()
