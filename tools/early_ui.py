from __future__ import annotations

from tools.elf_strings import ElfFixedStringPatch, patch_fixed_strings
from tools.startup_ui import STARTUP_FIXED_PATCHES, patch_title_labels


# Official remaster localization values for executable-resident fixed strings.
# Startup/name/location strings are kept in tools.startup_ui so the boot-to-DG00
# acceptance slice is independently testable.  These are the remaining menu/UI
# labels that already fit their PS2 fixed slots.
MENU_UI_PATCHES: tuple[ElfFixedStringPatch, ...] = (
    # Command thumbnail / H.A.N.T.-adjacent menu table.
    ElfFixedStringPatch(0x3BC7C8, 16, "アイテム", "Items"),
    ElfFixedStringPatch(0x3BC7D8, 16, "クエスト", "Quests"),
    ElfFixedStringPatch(0x3BC7E8, 16, "Ｈ．Ａ．Ｎ．Ｔ", "H.A.N.T"),
    ElfFixedStringPatch(0x3BC7F8, 16, "セーブ＆ロード", "Save & load"),
    ElfFixedStringPatch(0x3BC808, 16, "部屋を出る", "Leave room"),
    ElfFixedStringPatch(0x3BC818, 16, "ショップ", "Shop"),
    ElfFixedStringPatch(0x3BC828, 16, "ギルドサイト", "Guild site"),
    ElfFixedStringPatch(0x3BC838, 16, "ブロードバンド", "Broadband"),
    ElfFixedStringPatch(0x3BC848, 16, "コレクション", "Collection"),
    # 0x3BC858 メディア is intentionally left unchanged: no exact official
    # remaster dictionary entry was found for this PS2 label.
    ElfFixedStringPatch(0x3BC868, 16, "次の話へ", "Next chapter"),
    ElfFixedStringPatch(0x3BC878, 16, "ターン終了", "End turn"),
    # 0x3BC888 地上へ脱出 -> "Return above ground" is 19 ASCII bytes and cannot
    # fit safely in the existing 16-byte C-string slot.
    ElfFixedStringPatch(0x3BC898, 16, "インテリア", "Interior"),
    # Compact runtime labels used by command/H.A.N.T.-adjacent screens.
    ElfFixedStringPatch(0x694180, 8, "なし", "None"),
    ElfFixedStringPatch(0x694188, 8, "マップ", "Map"),
    # 0x694190 成績表 -> "Report card" does not fit this 8-byte C-string slot.
    ElfFixedStringPatch(0x694198, 8, "ノイズ", "Noise"),
    ElfFixedStringPatch(0x6941A0, 8, "戦闘", "Battle"),
)

# Backwards-compatible name used by the artifact builder/tests.  It now means
# every fixed-slot executable patch; the relocated title strings are handled by
# patch_title_labels and therefore intentionally are not members of this tuple.
EARLY_UI_PATCHES: tuple[ElfFixedStringPatch, ...] = STARTUP_FIXED_PATCHES + MENU_UI_PATCHES


def build_early_ui_elf(raw: bytes) -> bytes:
    return patch_fixed_strings(patch_title_labels(raw), EARLY_UI_PATCHES)
