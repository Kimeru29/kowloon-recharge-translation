from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import struct

from tools.elf_translation_segment import TranslationSegmentInfo
from tools.executable_text import RelocatedText, install_executable_text
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells, wrap_hant_text
from tools.localization import encode_ps2_english
from tools.memory_card_ui import relocated_memory_card_entries
from tools.startup_ui import (
    NAME_BLANK_STRING_OFFSET,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_READING_PROMPT_SOURCE_OFFSETS,
)


HANT_POINTER_TABLE_OFFSET = 0x5C8C70
# Resolver VA 0x2A9FE0 indexes the mode/page/subpage hierarchy rooted at
# VA 0x006CBAC0. Tuple (4,2,0) resolves through this descriptor slot to the
# pristine tutorial row-pointer table at VA 0x006C8BF0.
HANT_TUTORIAL_DESCRIPTOR_OFFSET = 0x5CBAB0
# Parallel resolver VA 0x2A9FA0 resolves tuple (4,2,0) to the page-specific
# controller metadata list at VA 0x006C8A20 through this independent leaf.
HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET = 0x5CBA60
HANT_CONTROLLER_METADATA_OFFSET = 0x5C8AA0
# The Help UI has three sibling topic pointer tables. This descriptor vector is
# static ownership evidence independent of any one runtime screenshot:
#   [ADV topics, ruins/exploration topics, H.A.N.T/system topics].
# r5 translated only the third table, which explains why deeper Help pages still
# appeared in Japanese at runtime even though the H.A.N.T-specific list was done.
HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET = 0x587890
_HANT_HELP_CATEGORY_TABLE_OFFSETS = (0x587430, 0x587690, 0x587840)
# Separate three-label tab/category table consumed directly by the live Help
# renderer at VA 0x28C798..0x28C7BC. This is presentation chrome, not Help body
# text, so it has its own owner/preimage rather than being inferred from the
# topic-table descriptor above.
HANT_HELP_CATEGORY_LABEL_TABLE_OFFSET = 0x587288
_HANT_HELP_CATEGORY_RENDERER_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x18C818, 0x3C030068),  # lui v1,0x68
    (0x18C81C, 0x24637208),  # addiu v1,v1,0x7208 -> VA 0x00687208
    (0x18C820, 0x00711821),  # addu v1,v1,s1 -> indexed slot
    (0x18C828, 0x8C650000),  # lw a1,0(v1) -> category label pointer
    (0x18C82C, 0x0C062820),  # jal 0x18A080 -> text writer
    (0x18C838, 0x2A620003),  # slti v0,s3,3 -> exactly three labels
)
# Mode-4 tutorial row constructor at VA 0x2908E8. Pristine style 0 is 16x18;
# existing style 1 is 12x12 and reduces English glyph advance without a global
# font change or injected call path.
HANT_TUTORIAL_FONT_STYLE_OFFSET = 0x190968
_HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD = 0x0000282D  # move a1,zero
_HANT_TUTORIAL_FONT_STYLE_ENGLISH_WORD = 0x24050001   # addiu a1,zero,1
# VA 0x2907E4 materializes the page-local float stride used by
# Y = 131 + stride * row. r4 runtime proved 21px still exceeds the visible
# tutorial budget. r7 keeps the runtime-good 12px font and tightens only this page to 16px.
HANT_TUTORIAL_ROW_SPACING_OFFSET = 0x190864
_HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD = 0x3C0241A8  # lui v0,0x41A8 => 21.0f
_HANT_TUTORIAL_ROW_SPACING_ENGLISH_WORD = 0x3C024180   # lui v0,0x4180 => 16.0f

_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_HANT_BLANK_STRING_OFFSET = 0x696038
_HANT_EOF_STRING_OFFSET = 0x69603C
_HANT_METADATA_SCREEN_X_BASE = 73
_HANT_METADATA_SCREEN_Y_BASE = 119
_HANT_TEXT_ORIGIN_Y = 131


@dataclass(frozen=True)
class HantChromeLabel:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str


@dataclass(frozen=True)
class HantHelpTopic:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str = "semantic"


@dataclass(frozen=True)
class HantHelpBody:
    key: str
    mode: int
    category_index: int
    topic_index: int
    descriptor_offset: int
    source_table_offset: int
    metadata_descriptor_offset: int
    metadata_offset: int
    source_rows: tuple[tuple[int, int, str], ...]
    english_rows: tuple[str, ...]
    provenance: str = "semantic"


@dataclass(frozen=True)
class HantConfigLabel:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str = "semantic"


@dataclass(frozen=True)
class HantHelpCategoryLabel:
    key: str
    source_offset: int
    pointer_offset: int
    source_text: str
    english: str
    provenance: str = "semantic"


# Runtime ownership is proven independently of translation provenance: the seven
# pointers at file 0x586D20 are indexed by the live H.A.N.T. chrome renderer at
# VA 0x2881B0/0x2881C0. The owned remaster extraction does not expose the
# localized TextAsset that would establish exact official wording, so these are
# deliberately classified as semantic translations rather than official text.
# Preserve the original corner-bracket chrome while translating the labels.
HANT_CHROME_LABELS: tuple[HantChromeLabel, ...] = (
    HantChromeLabel("main_menu", 0x586CB0, 0x586D20, "【メインメニュー】", "【Main Menu】", "semantic"),
    HantChromeLabel("mail", 0x586CC8, 0x586D24, "【メール】", "【Mail】", "semantic"),
    HantChromeLabel("dictionary", 0x586CD8, 0x586D28, "【用語辞典】", "【Dictionary】", "semantic"),
    HantChromeLabel("enemy", 0x695888, 0x586D2C, "【敵】", "【Enemy】", "semantic"),
    HantChromeLabel("memo", 0x586CE8, 0x586D30, "【睡院メモ】", "【Memo】", "semantic"),
    HantChromeLabel("help", 0x586CF8, 0x586D34, "【ヘルプ】", "【Help】", "semantic"),
    HantChromeLabel("config", 0x586D08, 0x586D38, "【コンフィグ】", "【Config】", "semantic"),
)


# Config ownership is direct executable evidence, not adjacency: VA 0x28BC24
# materializes 0x00686E70 (file 0x586EF0), indexes it by the loop byte offset,
# loads the pointed label, and passes it to the generic text writer. The loop at
# VA 0x28BC44 is bounded to exactly nine entries. Two labels live in the shared
# high data arena; the other seven are adjacent to the pointer table. No owned
# localized PS4 corpus is currently available, so wording is semantic.
HANT_CONFIG_POINTER_TABLE_OFFSET = 0x586EF0
_HANT_CONFIG_RENDERER_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x18BCA4, 0x3C030068),  # lui v1,0x68
    (0x18BCA8, 0x24636E70),  # addiu v1,v1,0x6e70 -> table VA 0x00686E70
    (0x18BCAC, 0x00711821),  # addu v1,v1,s1 -> indexed slot
    (0x18BCB4, 0x8C650000),  # lw a1,0(v1) -> label pointer
    (0x18BCB8, 0x0C062820),  # jal 0x18A080 -> text writer
    (0x18BCC4, 0x2A420009),  # slti v0,s2,9 -> exactly nine rows
)
HANT_CONFIG_LABELS: tuple[HantConfigLabel, ...] = (
    HantConfigLabel("voice_sfx_volume", 0x586E30, 0x586EF0, "声・効果音の音量", "Voice/SFX Volume"),
    HantConfigLabel("bgm_volume", 0x586E48, 0x586EF4, "ＢＧＭの音量", "BGM Volume"),
    HantConfigLabel("emotion_speed", 0x586E60, 0x586EF8, "感情入力の変化速度", "Emotion Speed"),
    HantConfigLabel("walk_camera", 0x586E80, 0x586EFC, "歩行時のカメラ演出", "Walk Camera"),
    HantConfigLabel("vibration", 0x586EA0, 0x586F00, "コントローラの振動", "Vibration"),
    HantConfigLabel("audio", 0x695898, 0x586F04, "音響", "Audio"),
    HantConfigLabel("message_icon", 0x586EC0, 0x586F08, "メッセージアイコン", "Message Icon"),
    HantConfigLabel("voice_nav", 0x586ED8, 0x586F0C, "ボイスナビ", "Voice Nav"),
    HantConfigLabel("ringtone", 0x6958A0, 0x586F10, "着メロ", "Ringtone"),
)


# The Help category renderer owns these three tabs independently from the three
# topic pointer tables. The owned remaster extraction does not expose localized
# source text for this PS2-only owner, so these concise labels are semantic.
HANT_HELP_CATEGORY_LABELS: tuple[HantHelpCategoryLabel, ...] = (
    HantHelpCategoryLabel("adv", 0x695908, 0x587288, "ＡＤＶ", "ADV"),
    HantHelpCategoryLabel("exploration", 0x587278, 0x58728C, "遺跡探索", "Ruins"),
    HantHelpCategoryLabel("other", 0x695910, 0x587290, "その他", "Other"),
)


# The Help root owns three sibling topic lists through the contiguous descriptor
# vector at 0x587890. The owned PS4 extraction does not currently contain the
# localized TextAsset/English.bytes corpus, so every newly promoted label below
# is explicitly semantic rather than claimed as official-remaster wording.
HANT_ADV_HELP_TOPICS: tuple[HantHelpTopic, ...] = (
    HantHelpTopic("adv_controls", 0x5872A0, 0x587430, "ＡＤＶでの基本操作", "ADV Controls"),
    HantHelpTopic("adv_auto_advance", 0x5872C0, 0x587434, "メッセージの自動送り", "Auto-Advance Messages"),
    HantHelpTopic("adv_message_log", 0x5872E0, 0x587438, "メッセージログの閲覧", "Message Log"),
    HantHelpTopic("adv_emotion_system", 0x587300, 0x58743C, "感情入力システムとは", "Emotion Input System"),
    HantHelpTopic("adv_emotion_controls", 0x587320, 0x587440, "感情入力画面での操作", "Emotion Input Controls"),
    HantHelpTopic("adv_06", 0x587338, 0x587444, "ＡＤＶ０６", "ADV 06"),
    HantHelpTopic("adv_07", 0x587348, 0x587448, "ＡＤＶ０７", "ADV 07"),
    HantHelpTopic("adv_08", 0x587358, 0x58744C, "ＡＤＶ０８", "ADV 08"),
    HantHelpTopic("adv_09", 0x587368, 0x587450, "ＡＤＶ０９", "ADV 09"),
    HantHelpTopic("adv_10", 0x587378, 0x587454, "ＡＤＶ１０", "ADV 10"),
    HantHelpTopic("adv_11", 0x587388, 0x587458, "ＡＤＶ１１", "ADV 11"),
    HantHelpTopic("adv_12", 0x587398, 0x58745C, "ＡＤＶ１２", "ADV 12"),
    HantHelpTopic("adv_13", 0x5873A8, 0x587460, "ＡＤＶ１３", "ADV 13"),
    HantHelpTopic("adv_14", 0x5873B8, 0x587464, "ＡＤＶ１４", "ADV 14"),
    HantHelpTopic("adv_15", 0x5873C8, 0x587468, "ＡＤＶ１５", "ADV 15"),
    HantHelpTopic("adv_16", 0x5873D8, 0x58746C, "ＡＤＶ１６", "ADV 16"),
    HantHelpTopic("adv_17", 0x5873E8, 0x587470, "ＡＤＶ１７", "ADV 17"),
    HantHelpTopic("adv_18", 0x5873F8, 0x587474, "ＡＤＶ１８", "ADV 18"),
    HantHelpTopic("adv_19", 0x587408, 0x587478, "ＡＤＶ１９", "ADV 19"),
    HantHelpTopic("adv_20", 0x587418, 0x58747C, "ＡＤＶ２０", "ADV 20"),
)

HANT_EXPLORATION_HELP_TOPICS: tuple[HantHelpTopic, ...] = (
    HantHelpTopic("exploration_controls", 0x587480, 0x587690, "遺跡内探索時の操作", "Exploration Controls"),
    HantHelpTopic("moving_in_ruins", 0x587498, 0x587694, "遺跡内での移動", "Moving in Ruins"),
    HantHelpTopic("reading_display", 0x5874B0, 0x587698, "ディスプレイの見方", "Reading the Display"),
    HantHelpTopic("opening_doors", 0x5874C8, 0x58769C, "扉の開き方", "Opening Doors"),
    HantHelpTopic("opening_containers", 0x5874D8, 0x5876A0, "箱や壷の開き方", "Opening Boxes/Jars"),
    HantHelpTopic("unlocking_locks", 0x5874E8, 0x5876A4, "鍵の外し方", "Unlocking Locks"),
    HantHelpTopic("moving_objects", 0x587500, 0x5876A8, "設置物の動かし方", "Moving Objects"),
    HantHelpTopic("operating_switches", 0x587520, 0x5876AC, "スイッチの動かし方", "Operating Switches"),
    HantHelpTopic("command_palette", 0x587540, 0x5876B0, "コマンドパレット", "Command Palette"),
    HantHelpTopic("radar_icons", 0x587560, 0x5876B4, "レーダーアイコン", "Radar Icons"),
    HantHelpTopic("enemy_icons", 0x587580, 0x5876B8, "エネミーアイコン", "Enemy Icons"),
    HantHelpTopic("entering_battle", 0x587598, 0x5876BC, "探索から戦闘へ", "Entering Battle"),
    HantHelpTopic("turn_based_combat", 0x5875B0, 0x5876C0, "ターン制について", "Turn-Based Combat"),
    HantHelpTopic("basic_attack", 0x5875D0, 0x5876C4, "基本的な攻撃手順", "Basic Attack"),
    HantHelpTopic("battle_tips", 0x5875E8, 0x5876C8, "戦闘のコツ", "Battle Tips"),
    HantHelpTopic("jumping", 0x587600, 0x5876CC, "ジャンプについて", "Jumping"),
    HantHelpTopic("wire_gun", 0x587620, 0x5876D0, "ワイヤーガンの操作", "Wire Gun Controls"),
    HantHelpTopic("buddies", 0x587638, 0x5876D4, "バディについて", "Buddies"),
    HantHelpTopic("status_effects", 0x587650, 0x5876D8, "状態変化効果について", "Status Effects"),
    HantHelpTopic("enemy_status_effects", 0x587670, 0x5876DC, "敵の状態変化について", "Enemy Status Effects"),
)

# r5 already translated the third, H.A.N.T/system-specific Help list. Preserve
# those accepted semantic labels while extending coverage to its two siblings.
HANT_HELP_TOPICS: tuple[HantHelpTopic, ...] = (
    HantHelpTopic("hant_functions", 0x5876E0, 0x587840, "Ｈ．Ａ．Ｎ．Ｔの機能", "H.A.N.T Functions"),
    HantHelpTopic("command_thumbnails", 0x587700, 0x587844, "コマンドサムネイル", "Command Thumbnails"),
    HantHelpTopic("your_room", 0x587718, 0x587848, "自室について", "About Your Room"),
    HantHelpTopic("shopping_site", 0x587730, 0x58784C, "ショッピングサイト", "Shopping Site"),
    HantHelpTopic("guild_site", 0x587748, 0x587850, "ギルドサイト", "Guild Site"),
    HantHelpTopic("shop", 0x587758, 0x587854, "売店について", "About the Shop"),
    HantHelpTopic("item_screen", 0x587770, 0x587858, "アイテム画面について", "Item Screen"),
    HantHelpTopic("using_items", 0x587790, 0x58785C, "アイテムの使い方", "Using Items"),
    HantHelpTopic("carrying_items", 0x5877A8, 0x587860, "アイテムの携行", "Carrying Items"),
    HantHelpTopic("equipping_items", 0x5877B8, 0x587864, "アイテムの装備", "Equipping Items"),
    HantHelpTopic("recycling", 0x5877D0, 0x587868, "リサイクルについて", "Recycling"),
    HantHelpTopic("item_synthesis", 0x5877E8, 0x58786C, "アイテムの調合", "Item Synthesis"),
    HantHelpTopic("ammunition", 0x5877F8, 0x587870, "弾薬について", "Ammunition"),
    HantHelpTopic("level_up", 0x587810, 0x587874, "レベルアップしたら", "When You Level Up"),
    HantHelpTopic("save_load", 0x587828, 0x587878, "セーブ＆ロード", "Save & Load"),
)

HANT_ALL_HELP_TOPICS: tuple[HantHelpTopic, ...] = (
    *HANT_ADV_HELP_TOPICS,
    *HANT_EXPLORATION_HELP_TOPICS,
    *HANT_HELP_TOPICS,
)


# Selected Help-topic bodies are a separate ownership class from the menu labels
# above. The live Help handler at VA 0x28D210..0x28D24C passes
# (mode=4, category, topic) to the generic page constructor; resolver VA 0x2A9FE0
# then indexes the text hierarchy rooted at VA 0x006CBAC0. Tuple (4,2,0) is the
# already-accepted H.A.N.T Functions/tutorial body. The first newly promoted body
# deliberately uses (4,2,5): it has a short seven-row table and its parallel
# metadata leaf is an immediate negative sentinel, so no icon geometry changes
# are required. English.bytes is absent locally, therefore wording is semantic.
HANT_HELP_BODIES: tuple[HantHelpBody, ...] = (
    HantHelpBody(
        key="shop",
        mode=4,
        category_index=2,
        topic_index=5,
        descriptor_offset=0x5CBAC4,
        source_table_offset=0x5C9B80,
        metadata_descriptor_offset=0x5CBA74,
        metadata_offset=0x698968,
        source_rows=(
            (0, 0x5C9AE0, "\u3000\u3000\u3000\u3000\u3000\u3000＜売店について＞"),
            (2, 0x5C9B00, "昼休みの自由移動で「売店」へ行くと、"),
            (3, 0x5C9B30, "食品や学用品などの"),
            (4, 0x5C9B50, "アイテムを購入することができます。"),
        ),
        english_rows=(
            "       About the Shop",
            "",
            "During lunch, visit the Shop",
            "You can buy food, supplies,",
            "and other useful items.",
            "",
            "",
        ),
    ),
)


def _elf_va(file_offset: int) -> int:
    return _ELF_MAIN_VADDR + file_offset - _ELF_MAIN_FILE_OFFSET


_HANT_PRISTINE_TABLE_VA = _elf_va(HANT_POINTER_TABLE_OFFSET)
_HANT_PRISTINE_CONTROLLER_METADATA_VA = _elf_va(HANT_CONTROLLER_METADATA_OFFSET)
_HANT_BLANK_VA = _elf_va(_HANT_BLANK_STRING_OFFSET)
_HANT_EOF_VA = _elf_va(_HANT_EOF_STRING_OFFSET)


# Exact source records in the PS2 H.A.N.T startup tutorial. This English was
# already accepted by the pre-v11 project from the official remaster corpus;
# Task 6 intentionally did not promote any newly discovered H.A.N.T candidate
# while English.bytes was absent. v11 changes only presentation of this proven
# tutorial wording and keeps all newly discovered unresolved owners pristine.
_HANT_SOURCES: dict[int, tuple[int, str]] = {
    0: (0x5C8AC0, "　　　＜Ｈ．Ａ．Ｎ．Ｔについて＞"),
    2: (0x5C8AF0, "Ｈ．Ａ．Ｎ．Ｔは、"),
    3: (0x5C8B10, "探索をサポートする小型情報端末です。"),
    4: (0x5C8B40, "≪操作方法≫や≪情報≫の確認ができます。"),
    7: (0x5C8B70, "　　　Ｈ．Ａ．Ｎ．Ｔの起動方法"),
    8: (0x5C8B90, "　　　￣￣￣￣￣￣￣￣￣￣￣￣"),
    9: (0x5C8BB0, "　ＳＥＬＥＣＴボタンを押して"),
    10: (0x5C8BD0, "コマンドサムネイルを呼び出します。"),
    12: (0x5C8C00, "次に、　方向キーで"),
    13: (0x5C8C20, "「Ｈ．Ａ．Ｎ．Ｔ」を選択し"),
    14: (0x5C8C40, "　ボタンを押すと起動させることができます。"),
}

# Preserve the established public mapping/provenance. Runtime no longer points
# these strings one-for-one at the original Japanese rows; HANT_WRAPPED_LINES is
# derived from this wording and installed as a separate EOF-terminated table.
HANT_ENGLISH_LINES: dict[int, str] = {
    0: "                           H.A.N.T",
    2: "The H.A.N.T is a mini info device designed",
    3: "to support exploration. You can review",
    4: "game controls and other info here.",
    7: "     Booting Up the H.A.N.T",
    8: "     -----------------------------",
    9: "Press the      button to bring up the",
    10: "command thumbnails.",
    12: "Next,      press the directional buttons",
    13: "to select the H.A.N.T",
    14: "Press the      button to boot it up.",
}

# The official strings use six consecutive spaces at each controller insertion:
# one ordinary word separator plus five cells reserved for the icon. Keep the
# semantic five-cell span explicit instead of treating an arbitrary run of spaces
# as an icon placeholder.
_HANT_CONTROLLER_SOURCE_SPANS: dict[int, tuple[int, int]] = {
    9: (10, 15),
    12: (6, 11),
    14: (10, 15),
}


def _wrap_section(text: str, reserved_spans: tuple[tuple[int, int], ...] = ()) -> tuple[str, ...]:
    return wrap_hant_text(text, HANT_LAYOUT_PROFILE.max_cells, reserved_spans)


def _build_wrapped_hant_lines() -> tuple[tuple[str, ...], dict[int, tuple[int, int]]]:
    body = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (2, 3, 4))
    instruction_1 = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (9, 10))
    instruction_2 = " ".join(HANT_ENGLISH_LINES[index].strip() for index in (12, 13))
    instruction_3 = HANT_ENGLISH_LINES[14].strip()

    body_lines = _wrap_section(body)
    boot_heading_lines = _wrap_section(HANT_ENGLISH_LINES[7].strip())
    instruction_1_lines = _wrap_section(instruction_1, (_HANT_CONTROLLER_SOURCE_SPANS[9],))
    instruction_2_lines = _wrap_section(instruction_2, (_HANT_CONTROLLER_SOURCE_SPANS[12],))
    instruction_3_lines = _wrap_section(instruction_3, (_HANT_CONTROLLER_SOURCE_SPANS[14],))

    if tuple(map(len, (body_lines, boot_heading_lines, instruction_1_lines, instruction_2_lines, instruction_3_lines))) != (5, 1, 3, 3, 2):
        raise ValueError("H.A.N.T wrapping no longer matches the 12px/28-cell tutorial profile")

    # Keep all accepted instructional wording while dropping only the redundant
    # standalone H.A.N.T heading and decorative separator. The existing 12px font
    # style fits the text in 14 rows, leaving two rows of headroom under the
    # renderer's hard 16-row cap instead of clipping the final instruction.
    lines = (
        *body_lines,
        *boot_heading_lines,
        *instruction_1_lines,
        *instruction_2_lines,
        *instruction_3_lines,
    )
    if len(lines) != 14 or len(lines) > HANT_LAYOUT_PROFILE.max_rows:
        raise ValueError(f"wrapped H.A.N.T tutorial must materialize 14 rows, got {len(lines)}")

    controller_spans = {
        6: _HANT_CONTROLLER_SOURCE_SPANS[9],
        9: _HANT_CONTROLLER_SOURCE_SPANS[12],
        12: _HANT_CONTROLLER_SOURCE_SPANS[14],
    }
    gap = " " * HANT_LAYOUT_PROFILE.controller_gap_cells
    for row, (start, end) in controller_spans.items():
        if end - start != HANT_LAYOUT_PROFILE.controller_gap_cells or lines[row][start:end] != gap:
            raise ValueError(f"H.A.N.T controller placeholder was not preserved on row {row}")
    return lines, controller_spans


HANT_WRAPPED_LINES, HANT_CONTROLLER_SPANS_BY_ROW = _build_wrapped_hant_lines()


# The page's parallel metadata list has three 8-byte records and a negative
# sentinel. Fields 2/3 are relative coordinates: screen X = 73 + field2 and
# screen Y = 119 + field3. These pristine records align the icons to Japanese
# gaps at rows/columns (9,0), (12,3), (14,0).
HANT_PRISTINE_CONTROLLER_METADATA_RECORDS: tuple[tuple[int, int, int, int], ...] = (
    (0, 5, 10, 201),
    (38, 1, 54, 263),
    (0, 0, 9, 305),
    (-1, -1, -1, -1),
)
_HANT_SOURCE_ICON_POSITIONS = ((9, 0), (12, 3), (14, 0))
_HANT_TARGET_ICON_POSITIONS = ((6, 10), (9, 6), (12, 10))
_HANT_PRISTINE_GLYPH_ADVANCE = 16.0
_HANT_PRISTINE_LINE_SPACING = 21.0


def _relocated_controller_metadata() -> tuple[tuple[int, int, int, int], ...]:
    records: list[tuple[int, int, int, int]] = []
    target_advance = HANT_LAYOUT_PROFILE.glyph_advance
    spacing = HANT_LAYOUT_PROFILE.line_spacing
    origin_x = 85.0

    for record, source, target in zip(
        HANT_PRISTINE_CONTROLLER_METADATA_RECORDS[:3],
        _HANT_SOURCE_ICON_POSITIONS,
        _HANT_TARGET_ICON_POSITIONS,
        strict=True,
    ):
        kind, variant, source_field_x, source_field_y = record
        source_row, source_column = source
        target_row, target_column = target

        source_icon_x = _HANT_METADATA_SCREEN_X_BASE + source_field_x
        source_icon_y = _HANT_METADATA_SCREEN_Y_BASE + source_field_y
        source_gap_x = origin_x + source_column * _HANT_PRISTINE_GLYPH_ADVANCE
        source_row_y = _HANT_TEXT_ORIGIN_Y + source_row * _HANT_PRISTINE_LINE_SPACING
        delta_x = source_icon_x - source_gap_x
        delta_y = source_icon_y - source_row_y

        target_icon_x = origin_x + target_column * target_advance + delta_x
        target_icon_y = _HANT_TEXT_ORIGIN_Y + target_row * spacing + delta_y
        target_field_x = int(round(target_icon_x - _HANT_METADATA_SCREEN_X_BASE))
        target_field_y = int(round(target_icon_y - _HANT_METADATA_SCREEN_Y_BASE))
        records.append((kind, variant, target_field_x, target_field_y))

    records.append(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS[-1])
    return tuple(records)


HANT_CONTROLLER_METADATA_RECORDS = _relocated_controller_metadata()


def _expected_hant_pointer_table() -> tuple[int, ...]:
    values: list[int] = []
    for index in range(17):
        if index in _HANT_SOURCES:
            values.append(_elf_va(_HANT_SOURCES[index][0]))
        elif index == 16:
            values.append(_HANT_EOF_VA)
        else:
            values.append(_HANT_BLANK_VA)
    return tuple(values)


def _expected_help_body_table(spec: HantHelpBody) -> tuple[int, ...]:
    source_by_index = {index: offset for index, offset, _text in spec.source_rows}
    values = [
        _elf_va(source_by_index[index]) if index in source_by_index else _HANT_BLANK_VA
        for index in range(len(spec.english_rows))
    ]
    values.append(_HANT_EOF_VA)
    return tuple(values)


def _read_metadata_records(raw: bytes, offset: int) -> tuple[tuple[int, int, int, int], ...]:
    size = len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS) * 8
    if offset + size > len(raw):
        raise ValueError("H.A.N.T controller metadata is outside executable")
    return tuple(
        struct.unpack_from("<hhhh", raw, offset + index * 8)
        for index in range(len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS))
    )


def _validate_source(raw: bytes) -> None:
    if HANT_TUTORIAL_ROW_SPACING_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T renderer spacing preimage is outside executable")
    actual_spacing = struct.unpack_from("<I", raw, HANT_TUTORIAL_ROW_SPACING_OFFSET)[0]
    if actual_spacing != _HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD:
        raise ValueError(
            "H.A.N.T renderer spacing preimage mismatch: "
            f"expected {_HANT_TUTORIAL_ROW_SPACING_PRISTINE_WORD:#010x}, got {actual_spacing:#010x}"
        )

    if HANT_TUTORIAL_FONT_STYLE_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T renderer style preimage is outside executable")
    actual_style = struct.unpack_from("<I", raw, HANT_TUTORIAL_FONT_STYLE_OFFSET)[0]
    if actual_style != _HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD:
        raise ValueError(
            "H.A.N.T renderer style preimage mismatch: "
            f"expected {_HANT_TUTORIAL_FONT_STYLE_PRISTINE_WORD:#010x}, got {actual_style:#010x}"
        )

    for spec in HANT_CHROME_LABELS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T chrome source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T chrome pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T chrome pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

    for offset, expected in _HANT_CONFIG_RENDERER_PREIMAGES:
        if offset + 4 > len(raw):
            raise ValueError("H.A.N.T config renderer preimage is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"H.A.N.T config renderer preimage mismatch at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )

    for spec in HANT_CONFIG_LABELS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T config source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T config pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T config pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

    for offset, expected in _HANT_HELP_CATEGORY_RENDERER_PREIMAGES:
        if offset + 4 > len(raw):
            raise ValueError("H.A.N.T help category renderer preimage is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"H.A.N.T help category renderer preimage mismatch at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )

    for spec in HANT_HELP_CATEGORY_LABELS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T help-category source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T help-category pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T help-category pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

    descriptor_size = len(_HANT_HELP_CATEGORY_TABLE_OFFSETS) * 4
    if HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET + descriptor_size > len(raw):
        raise ValueError("H.A.N.T help category descriptor is outside executable")
    actual_help_tables = struct.unpack_from(
        f"<{len(_HANT_HELP_CATEGORY_TABLE_OFFSETS)}I",
        raw,
        HANT_HELP_CATEGORY_DESCRIPTOR_OFFSET,
    )
    expected_help_tables = tuple(_elf_va(offset) for offset in _HANT_HELP_CATEGORY_TABLE_OFFSETS)
    if actual_help_tables != expected_help_tables:
        raise ValueError(
            "H.A.N.T help category descriptor preimage mismatch: "
            f"expected {expected_help_tables!r}, got {actual_help_tables!r}"
        )

    for spec in HANT_ALL_HELP_TOPICS:
        encoded = spec.source_text.encode("cp932")
        if (
            spec.source_offset + len(encoded) >= len(raw)
            or raw[spec.source_offset:spec.source_offset + len(encoded)] != encoded
            or raw[spec.source_offset + len(encoded)] != 0
        ):
            raise ValueError(f"H.A.N.T help-topic source preimage mismatch: {spec.key}")
        if spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T help-topic pointer is outside executable: {spec.key}")
        expected_va = _elf_va(spec.source_offset)
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if actual_va != expected_va:
            raise ValueError(
                f"H.A.N.T help-topic pointer preimage mismatch for {spec.key}: "
                f"expected {expected_va:#x}, got {actual_va:#x}"
            )

    for spec in HANT_HELP_BODIES:
        if spec.descriptor_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T help-body descriptor is outside executable: {spec.key}")
        expected_table_va = _elf_va(spec.source_table_offset)
        actual_table_va = struct.unpack_from("<I", raw, spec.descriptor_offset)[0]
        if actual_table_va != expected_table_va:
            raise ValueError(
                f"H.A.N.T help-body descriptor preimage mismatch for {spec.key}: "
                f"expected {expected_table_va:#x}, got {actual_table_va:#x}"
            )

        table_words = len(spec.english_rows) + 1
        table_size = table_words * 4
        if spec.source_table_offset + table_size > len(raw):
            raise ValueError(f"H.A.N.T help-body source table is outside executable: {spec.key}")
        actual_table = struct.unpack_from(f"<{table_words}I", raw, spec.source_table_offset)
        expected_table = _expected_help_body_table(spec)
        if actual_table != expected_table:
            raise ValueError(f"H.A.N.T help-body table preimage mismatch for {spec.key}")

        for row_index, source_offset, source_text in spec.source_rows:
            if row_index >= len(spec.english_rows):
                raise ValueError(f"H.A.N.T help-body source row index is invalid: {spec.key}/{row_index}")
            encoded = source_text.encode("cp932")
            if (
                source_offset + len(encoded) >= len(raw)
                or raw[source_offset:source_offset + len(encoded)] != encoded
                or raw[source_offset + len(encoded)] != 0
            ):
                raise ValueError(f"H.A.N.T help-body source preimage mismatch: {spec.key}/{row_index}")

        for row_index, english in enumerate(spec.english_rows):
            if measured_hant_cells(english) > HANT_LAYOUT_PROFILE.max_cells:
                raise ValueError(f"H.A.N.T help-body row exceeds visible width: {spec.key}/{row_index}")

        if spec.metadata_descriptor_offset + 4 > len(raw):
            raise ValueError(f"H.A.N.T help-body metadata descriptor is outside executable: {spec.key}")
        expected_metadata_va = _elf_va(spec.metadata_offset)
        actual_metadata_va = struct.unpack_from("<I", raw, spec.metadata_descriptor_offset)[0]
        if actual_metadata_va != expected_metadata_va:
            raise ValueError(
                f"H.A.N.T help-body metadata descriptor preimage mismatch for {spec.key}: "
                f"expected {expected_metadata_va:#x}, got {actual_metadata_va:#x}"
            )
        if spec.metadata_offset + 8 > len(raw):
            raise ValueError(f"H.A.N.T help-body metadata is outside executable: {spec.key}")
        if struct.unpack_from("<hhhh", raw, spec.metadata_offset) != (-1, -1, -1, -1):
            raise ValueError(f"H.A.N.T help-body metadata is not empty: {spec.key}")

    for index, (offset, source) in _HANT_SOURCES.items():
        encoded = source.encode("cp932")
        if raw[offset:offset + len(encoded)] != encoded or raw[offset + len(encoded)] != 0:
            raise ValueError(f"H.A.N.T source preimage mismatch for line {index}")

    table_end = HANT_POINTER_TABLE_OFFSET + 17 * 4
    if table_end > len(raw):
        raise ValueError("H.A.N.T pointer table is outside executable")
    actual_table = struct.unpack_from("<17I", raw, HANT_POINTER_TABLE_OFFSET)
    expected_table = _expected_hant_pointer_table()
    if actual_table != expected_table:
        for index, (actual, expected) in enumerate(zip(actual_table, expected_table, strict=True)):
            if actual != expected:
                raise ValueError(
                    f"H.A.N.T pointer preimage mismatch for line {index}: "
                    f"expected {expected:#x}, got {actual:#x}"
                )
        raise ValueError("H.A.N.T pointer table preimage mismatch")

    if HANT_TUTORIAL_DESCRIPTOR_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T tutorial descriptor is outside executable")
    descriptor = struct.unpack_from("<I", raw, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
    if descriptor != _HANT_PRISTINE_TABLE_VA:
        raise ValueError(
            "H.A.N.T tutorial descriptor preimage mismatch: "
            f"expected {_HANT_PRISTINE_TABLE_VA:#x}, got {descriptor:#x}"
        )

    metadata_records = _read_metadata_records(raw, HANT_CONTROLLER_METADATA_OFFSET)
    if metadata_records != HANT_PRISTINE_CONTROLLER_METADATA_RECORDS:
        raise ValueError("H.A.N.T controller metadata preimage mismatch")

    if HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET + 4 > len(raw):
        raise ValueError("H.A.N.T controller metadata descriptor is outside executable")
    metadata_descriptor = struct.unpack_from("<I", raw, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0]
    if metadata_descriptor != _HANT_PRISTINE_CONTROLLER_METADATA_VA:
        raise ValueError(
            "H.A.N.T controller metadata descriptor preimage mismatch: "
            f"expected {_HANT_PRISTINE_CONTROLLER_METADATA_VA:#x}, got {metadata_descriptor:#x}"
        )


_NAME_READING_PROMPT_INDICES = (2, 3)


def _encoded_wide(text: str) -> bytes:
    return encode_ps2_english(text, collapse_spaces=False) + b"\x00"


def _controller_metadata_bytes() -> bytes:
    return b"".join(struct.pack("<hhhh", *record) for record in HANT_CONTROLLER_METADATA_RECORDS)


def _packed_payload_size(entries: Sequence[RelocatedText]) -> int:
    cursor = 0
    for entry in entries:
        if cursor & 1:
            cursor += 1
        cursor += len(entry.encoded)
    return cursor


def _base_relocated_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    entries: list[RelocatedText] = []
    for index in _NAME_READING_PROMPT_INDICES:
        entries.append(
            RelocatedText(
                key=f"name_prompt_{index}",
                encoded=_encoded_wide(NAME_PROMPT_TEXTS[index]),
                pointer_offsets=(NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4,),
            )
        )

    entries.extend(
        RelocatedText(f"hant_row_{index}", _encoded_wide(text), ())
        for index, text in enumerate(HANT_WRAPPED_LINES)
    )
    # The translated pointer table itself requires 4-byte alignment, while the
    # shared allocator intentionally guarantees only 2-byte string alignment.
    # Keep one explicit H.A.N.T.-owned 2-byte pad before the structured table;
    # the translated string payload is only 2-byte aligned while this table must
    # remain 4-byte aligned. The fail-closed
    # alignment check below still guards future row-shape drift.
    entries.append(RelocatedText("hant_table_alignment", b"\x00\x00", ()))
    entries.append(
        RelocatedText(
            "hant_table",
            b"\x00" * ((len(HANT_WRAPPED_LINES) + 1) * 4),
            (HANT_TUTORIAL_DESCRIPTOR_OFFSET,),
        )
    )
    entries.append(
        RelocatedText(
            "hant_controller_metadata",
            _controller_metadata_bytes(),
            (HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,),
        )
    )
    entries.extend(
        RelocatedText(
            key=f"hant_chrome_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_CHROME_LABELS
    )
    entries.extend(
        RelocatedText(
            key=f"hant_config_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_CONFIG_LABELS
    )
    entries.extend(
        RelocatedText(
            key=f"hant_help_category_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_HELP_CATEGORY_LABELS
    )
    entries.extend(
        RelocatedText(
            key=f"hant_help_{spec.key}",
            encoded=_encoded_wide(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in HANT_ALL_HELP_TOPICS
    )

    for spec in HANT_HELP_BODIES:
        for row_index, english in enumerate(spec.english_rows):
            if not english:
                continue
            entries.append(
                RelocatedText(
                    key=f"hant_help_body_{spec.key}_row_{row_index}",
                    encoded=_encoded_wide(english),
                    pointer_offsets=(),
                )
            )

        # ``install_executable_text`` aligns entries to two bytes. Help body
        # pointer tables are consumed with ``lw`` and must be word-aligned, so
        # add a body-owned two-byte pad only when the next packed entry would
        # otherwise begin at address +2 mod 4.
        next_offset = (_packed_payload_size(entries) + 1) & ~1
        if next_offset & 3:
            entries.append(RelocatedText(f"hant_help_body_{spec.key}_alignment", b"\x00\x00", ()))
        entries.append(
            RelocatedText(
                key=f"hant_help_body_{spec.key}_table",
                encoded=b"\x00" * ((len(spec.english_rows) + 1) * 4),
                pointer_offsets=(spec.descriptor_offset,),
            )
        )

    entries.extend(relocated_memory_card_entries(raw))
    return tuple(entries)


def _validate_name_prompt_preimages(raw: bytes) -> None:
    blank_va = _elf_va(NAME_BLANK_STRING_OFFSET)
    for index in _NAME_READING_PROMPT_INDICES:
        pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
        if pointer_offset + 4 > len(raw):
            raise ValueError("Name-reading prompt pointer table is outside executable")
        actual = struct.unpack_from("<I", raw, pointer_offset)[0]
        pristine_va = _elf_va(NAME_READING_PROMPT_SOURCE_OFFSETS[index])
        if actual not in (pristine_va, blank_va):
            raise ValueError(
                f"Name-reading prompt {index} preimage mismatch: "
                f"expected pristine/staged pointer {pristine_va:#x}/{blank_va:#x}, got {actual:#x}"
            )


def patch_hant_tutorial(
    raw: bytes,
    *,
    reserve_size: int = 0x100000,
    extra_entries: Sequence[RelocatedText] = (),
) -> tuple[bytes, TranslationSegmentInfo]:
    """Install all proven shared executable text through one translation PT_LOAD.

    ``extra_entries`` lets the composite early-UI build append independently
    validated relocation classes (currently long command-menu labels) without a
    second translation-segment installation. The base payload includes the
    accepted name/H.A.N.T./memory-card classes plus the separately owned semantic
    H.A.N.T. chrome labels.
    """

    _validate_source(raw)
    _validate_name_prompt_preimages(raw)

    entries = (*_base_relocated_entries(raw), *tuple(extra_entries))
    installed = install_executable_text(raw, entries, reserve_size=reserve_size)

    table_va = installed.target_vas["hant_table"]
    metadata_va = installed.target_vas["hant_controller_metadata"]
    if table_va & 3 or metadata_va & 3:
        raise ValueError("H.A.N.T structured translation payload lost word alignment")

    result = bytearray(installed.raw)
    struct.pack_into(
        "<I",
        result,
        HANT_TUTORIAL_ROW_SPACING_OFFSET,
        _HANT_TUTORIAL_ROW_SPACING_ENGLISH_WORD,
    )
    struct.pack_into(
        "<I",
        result,
        HANT_TUTORIAL_FONT_STYLE_OFFSET,
        _HANT_TUTORIAL_FONT_STYLE_ENGLISH_WORD,
    )
    table_file = installed.info.file_offset + (table_va - installed.info.segment_vaddr)
    for index in range(len(HANT_WRAPPED_LINES)):
        struct.pack_into("<I", result, table_file + index * 4, installed.target_vas[f"hant_row_{index}"])
    struct.pack_into("<I", result, table_file + len(HANT_WRAPPED_LINES) * 4, _HANT_EOF_VA)

    for spec in HANT_HELP_BODIES:
        body_table_va = installed.target_vas[f"hant_help_body_{spec.key}_table"]
        if body_table_va & 3:
            raise ValueError(f"H.A.N.T help-body translation table lost word alignment: {spec.key}")
        body_table_file = installed.info.file_offset + (body_table_va - installed.info.segment_vaddr)
        for row_index, english in enumerate(spec.english_rows):
            target_va = (
                installed.target_vas[f"hant_help_body_{spec.key}_row_{row_index}"]
                if english
                else _HANT_BLANK_VA
            )
            struct.pack_into("<I", result, body_table_file + row_index * 4, target_va)
        struct.pack_into(
            "<I",
            result,
            body_table_file + len(spec.english_rows) * 4,
            _HANT_EOF_VA,
        )

    return bytes(result), installed.info
