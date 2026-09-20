from __future__ import annotations

import unittest
from pathlib import Path

from tools.early_ui import EARLY_UI_PATCHES, build_early_ui_elf
from tests.local_fixtures import require_local_fixture


ELF_PATH = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF_PATH.read_bytes()


class EarlyUiPatchTests(unittest.TestCase):
    def test_manifest_uses_official_title_and_menu_localization(self) -> None:
        actual = {(patch.offset, patch.expected): patch.text for patch in EARLY_UI_PATCHES}

        self.assertEqual("New Game", actual[(0x5CBDE8, "初めから")])
        self.assertEqual("Load Game", actual[(0x5CBDF8, "続きから")])
        self.assertEqual("Items", actual[(0x3BC7C8, "アイテム")])
        self.assertEqual("Quests", actual[(0x3BC7D8, "クエスト")])
        self.assertEqual("H.A.N.T", actual[(0x3BC7E8, "Ｈ．Ａ．Ｎ．Ｔ")])
        self.assertEqual("Save & load", actual[(0x3BC7F8, "セーブ＆ロード")])
        self.assertEqual("Leave room", actual[(0x3BC808, "部屋を出る")])
        self.assertEqual("Shop", actual[(0x3BC818, "ショップ")])
        self.assertEqual("Guild site", actual[(0x3BC828, "ギルドサイト")])
        self.assertEqual("Broadband", actual[(0x3BC838, "ブロードバンド")])
        self.assertEqual("Collection", actual[(0x3BC848, "コレクション")])
        self.assertEqual("Next chapter", actual[(0x3BC868, "次の話へ")])
        self.assertEqual("End turn", actual[(0x3BC878, "ターン終了")])
        self.assertEqual("Interior", actual[(0x3BC898, "インテリア")])
        self.assertEqual("None", actual[(0x694180, "なし")])
        self.assertEqual("Map", actual[(0x694188, "マップ")])
        self.assertEqual("Noise", actual[(0x694198, "ノイズ")])
        self.assertEqual("Battle", actual[(0x6941A0, "戦闘")])

    def test_build_changes_only_declared_fixed_slots(self) -> None:
        result = build_early_ui_elf(RAW)

        self.assertEqual(len(RAW), len(result))
        allowed = set()
        for patch in EARLY_UI_PATCHES:
            allowed.update(range(patch.offset, patch.offset + patch.capacity))

        differences = {index for index, (before, after) in enumerate(zip(RAW, result)) if before != after}
        self.assertTrue(differences)
        self.assertTrue(differences <= allowed)

    def test_unfit_or_unmapped_slots_are_intentionally_unchanged(self) -> None:
        result = build_early_ui_elf(RAW)

        # Official remaster string is 19 ASCII bytes and cannot fit this 16-byte C-string slot.
        self.assertEqual(RAW[0x3BC888:0x3BC898], result[0x3BC888:0x3BC898])
        # No matching official remaster dictionary entry was found for this PS2-only label.
        self.assertEqual(RAW[0x3BC858:0x3BC868], result[0x3BC858:0x3BC868])
        # "Report card" cannot fit the compact 8-byte runtime slot.
        self.assertEqual(RAW[0x694190:0x694198], result[0x694190:0x694198])


if __name__ == "__main__":
    unittest.main()
