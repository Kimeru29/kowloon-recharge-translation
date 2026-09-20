from __future__ import annotations

import unittest
from pathlib import Path

from tools.elf_strings import ElfFixedStringPatch, patch_fixed_strings
from tests.local_fixtures import require_local_fixture


ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class ElfFixedStringTests(unittest.TestCase):
    def test_patches_ascii_c_string_and_zero_fills_slot(self) -> None:
        raw = bytearray(b"prefix" + "初めから".encode("cp932") + b"\x00" * 8 + b"suffix")
        patch = ElfFixedStringPatch(
            offset=6,
            capacity=16,
            expected="初めから",
            text="New Game",
        )

        result = patch_fixed_strings(bytes(raw), (patch,))

        self.assertEqual(len(raw), len(result))
        self.assertEqual(b"New Game\x00" + b"\x00" * 7, result[6:22])
        self.assertEqual(b"prefix", result[:6])
        self.assertEqual(b"suffix", result[22:])

    def test_rejects_wrong_source_version(self) -> None:
        raw = b"Wrong\x00" + b"\x00" * 10
        patch = ElfFixedStringPatch(0, 16, "初めから", "New Game")

        with self.assertRaisesRegex(ValueError, "expected source"):
            patch_fixed_strings(raw, (patch,))

    def test_rejects_replacement_without_room_for_nul(self) -> None:
        raw = "初めから".encode("cp932") + b"\x00" * 8
        patch = ElfFixedStringPatch(0, 16, "初めから", "1234567890ABCDEF")

        with self.assertRaisesRegex(ValueError, "NUL terminator"):
            patch_fixed_strings(raw, (patch,))

    def test_rejects_non_ascii_replacement(self) -> None:
        raw = "初めから".encode("cp932") + b"\x00" * 8
        patch = ElfFixedStringPatch(0, 16, "初めから", "Ｎｅｗ")

        with self.assertRaisesRegex(ValueError, "ASCII"):
            patch_fixed_strings(raw, (patch,))

    def test_real_title_and_hant_slots_match_expected_ps2_strings(self) -> None:
        patches = (
            ElfFixedStringPatch(0x5CBDE8, 16, "初めから", "New Game"),
            ElfFixedStringPatch(0x5CBDF8, 16, "続きから", "Load Game"),
            ElfFixedStringPatch(0x3BC7C8, 16, "アイテム", "Items"),
            ElfFixedStringPatch(0x3BC7D8, 16, "クエスト", "Quests"),
            ElfFixedStringPatch(0x3BC7E8, 16, "Ｈ．Ａ．Ｎ．Ｔ", "H.A.N.T"),
            ElfFixedStringPatch(0x3BC7F8, 16, "セーブ＆ロード", "Save & load"),
            ElfFixedStringPatch(0x3BC808, 16, "部屋を出る", "Leave room"),
            ElfFixedStringPatch(0x3BC818, 16, "ショップ", "Shop"),
            ElfFixedStringPatch(0x3BC828, 16, "ギルドサイト", "Guild site"),
            ElfFixedStringPatch(0x3BC838, 16, "ブロードバンド", "Broadband"),
            ElfFixedStringPatch(0x3BC848, 16, "コレクション", "Collection"),
            ElfFixedStringPatch(0x3BC868, 16, "次の話へ", "Next chapter"),
            ElfFixedStringPatch(0x3BC878, 16, "ターン終了", "End turn"),
            ElfFixedStringPatch(0x3BC898, 16, "インテリア", "Interior"),
        )

        result = patch_fixed_strings(RAW, patches)

        self.assertEqual(len(RAW), len(result))
        for patch in patches:
            encoded = patch.text.encode("ascii")
            self.assertEqual(encoded + b"\x00", result[patch.offset:patch.offset + len(encoded) + 1])


if __name__ == "__main__":
    unittest.main()
