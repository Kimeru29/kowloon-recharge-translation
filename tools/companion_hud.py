from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct

from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud_data import COMPANION_ACTION_DATA, COMPANION_COMMENT_DATA
from tools.executable_text import ExecutableTextResult, RelocatedText
from tools.localization import encode_ps2_english


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_MAX_STRING_BYTES = 512

# Re:charge-only free-talk / AFK corpus. This is a structurally bounded table
# immediately following h_buddy: 30 companions x 20 records, 0x80 bytes each.
# Only the live +8/+0xC text-pointer fields are translation owners. In
# particular, empty +0xC fields keep the shared 0x00794150 sentinel untouched.
COMPANION_AFK_TABLE_OFFSET = 0x3E5FA0
COMPANION_AFK_RECORDS_PER_COMPANION = 20
COMPANION_AFK_COMPANION_COUNT = 30
COMPANION_AFK_RECORD_COUNT = COMPANION_AFK_COMPANION_COUNT * COMPANION_AFK_RECORDS_PER_COMPANION
COMPANION_AFK_RECORD_STRIDE = 0x80
COMPANION_AFK_EMPTY_VA = 0x00794150
COMPANION_AFK_EXPECTED_LIVE_FIELDS = 999
COMPANION_AFK_EXPECTED_UNIQUE_SOURCE_POINTERS = 952
COMPANION_AFK_MAX_CHARS = 38
COMPANION_AFK_TABLE_SHA256 = "5c1f0c9348502012fd0f51d0160f5fe9a903006c317519b20ad75af60369020a"
COMPANION_AFK_SOURCE_SHA256 = "eaeb3bd7b6dab806aaa894f5458d13b1f0a29e7221ba0d5f4b9dc04f846d0641"

# Native Re:charge free-talk composition. AFK creates two layers: the
# slot-specific green 0x68/0x69 speech pointer plus a blue group-2/resource
# 0x6A panel. r45's attempt to compact 0x6A made the blue panel disappear at
# runtime, so r46 treats the native 0x6A geometry/placements as immutable and
# validates them fail-closed without writing them. The exact two structured
# placement owners and three animation frames remain documented below.
COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET = 0x380E40
COMPANION_AFK_PANEL_METADATA_VA = 0x00450B20
COMPANION_AFK_PANEL_METADATA_OFFSET = 0x350BA0
COMPANION_AFK_PANEL_FRAME_STRIDE = 0x30
COMPANION_AFK_PANEL_FRAME_COUNT = 3
COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES = (
    (288.0, 56.0, 67.0, 74.0),
    (288.0, 56.0, 67.0, 75.0),
    (288.0, 56.0, 67.0, 76.0),
)
COMPANION_AFK_PANEL_TARGET_GEOMETRIES = COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES
COMPANION_AFK_PANEL_PLACEMENT_OFFSETS = (0x3F8E44, 0x3F8E58)
COMPANION_AFK_PANEL_PRISTINE_PLACEMENTS = (
    (2, 0x6A, 246.0, 172.0, 381.0),
    (2, 0x6A, 246.0, 172.0, 381.0),
)
# r50 moves both AFK slots to the accepted L1 vertical anchor. Slot 1's blue
# placement also follows the slot-1 X anchor; runtime pivot-X then keeps the
# blue body aligned with the matching green 0x68/0x69 consumer.
COMPANION_AFK_ANCHOR_Y = 346.0
# r53: 3px inset on both sides keeps blue tint behind the green frame.
COMPANION_AFK_R53_BLUE_INSET_X = 3.0
COMPANION_AFK_R53_BLUE_WIDTH = 282.0
COMPANION_AFK_PANEL_TARGET_PLACEMENTS = (
    (2, 0x6A, 246.0, 175.0, COMPANION_AFK_ANCHOR_Y),
    (2, 0x6A, 246.0, 233.0, COMPANION_AFK_ANCHOR_Y),
)
COMPANION_AFK_GREEN_PLACEMENT_OFFSETS = (0x3F8E1C, 0x3F8E30)
COMPANION_AFK_GREEN_PRISTINE_PLACEMENTS = (
    (2, 0x68, 249.0, 172.0, 381.0),
    (2, 0x69, 249.0, 230.0, 381.0),
)
COMPANION_AFK_GREEN_TARGET_PLACEMENTS = (
    (2, 0x68, 249.0, 172.0, COMPANION_AFK_ANCHOR_Y),
    (2, 0x69, 249.0, 230.0, COMPANION_AFK_ANCHOR_Y),
)
# Exact dword owners modified by the r50 placement patch: green Y for both
# slots, blue Y for both slots, plus slot-1 blue X.
COMPANION_AFK_PANEL_LAYOUT_PATCH_OFFSETS: tuple[int, ...] = (
    0x3F8E2C,
    0x3F8E40,
    0x3F8E50,
    0x3F8E54,
    0x3F8E64,
    0x3F8E68,
)
COMPANION_AFK_PANEL_VALIDATION_OFFSETS = (
    COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET,
    0x350BA4, 0x350BAC, 0x350BB0,
    0x350BD4, 0x350BDC, 0x350BE0,
    0x350C04, 0x350C0C, 0x350C10,
    *COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
)
COMPANION_AFK_VISIBLE_STATE_FIRST = 11
COMPANION_AFK_VISIBLE_STATE_LAST = 13

# r31-r38 presentation owners for the persistent companion action caption.
# r35 proved the accepted one-line 224x48 down-tail presentation, r36 made
# height/wrapping generic, and r37 separated action id from HUD+0x2D0's 0/1
# companion-slot index. r38 now uses the two pristine sibling speech bubbles:
# group-2 0x68 points its tail at slot 1, while 0x69 has the same body/UVs with
# the tail shifted right for slot 2. Their different pivots keep the body almost
# stationary (13px shift) even though the companion anchors are 58px apart.
COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET = 0x380E30
COMPANION_ACTION_BUBBLE_METADATA_VA = 0x00450AC0
COMPANION_ACTION_BUBBLE_WIDTH_OFFSET = 0x350B44
COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET = 0x350B48
COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET = 0x350B4C
COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET = 0x350B50
COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY = (288.0, 80.0, 67.0, 77.0)
COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY = (224.0, 48.0, 52.0, 45.0)
COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET = 0x380E38
COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA = 0x00450AF0
COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET = 0x350B74
COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET = 0x350B78
COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET = 0x350B7C
COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET = 0x350B80
COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY = (288.0, 80.0, 125.0, 77.0)
COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY = (224.0, 48.0, 97.0, 45.0)
COMPANION_ACTION_SLOT_RESOURCES = (0x68, 0x69)
COMPANION_ACTION_SLOT_TEXT_X = (-36.0, -81.0)
COMPANION_SLOT_POSITION_TABLE_OFFSET = 0x3F8E80
COMPANION_SLOT_POSITIONS = ((172.0, 407.0), (230.0, 407.0))
COMPANION_ACTION_ID_GETTER_VA = 0x0012FEE0
COMPANION_ACTION_ID_KEY = 0x8000
COMPANION_ACTION_MAX_CELLS = 17
COMPANION_ACTION_MAX_LINES = 4
COMPANION_ACTION_LINE_STEP = 16.0
COMPANION_ACTION_LAYOUT_TABLE_KEY = "companion_action_layout_table"
COMPANION_ACTION_RUNTIME_STATE_KEY = "companion_action_runtime_text_xy"
COMPANION_ACTION_RUNTIME_HOOK_KEY = "companion_action_layout_hook"
COMPANION_ACTION_RUNTIME_HOOK_SIZE = 188
COMPANION_ACTION_VISIBILITY_HOOK_KEY = "companion_action_afk_visibility_hook"
COMPANION_ACTION_VISIBILITY_HOOK_SIZE = 76
# r47 appends all new payloads after the r46 visibility hook so every existing
# translated VA remains stable.
COMPANION_ACTION_GEOMETRY_EXTENSION_KEY = "companion_action_geometry_extension"
COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE = 72
COMPANION_AFK_SCALE_TABLE_KEY = "companion_afk_text_scale_table"
COMPANION_AFK_SCALE_HOOK_KEY = "companion_afk_text_scale_hook"
COMPANION_AFK_SCALE_HOOK_SIZE = 64
COMPANION_AFK_GEOMETRY_HOOK_KEY = "companion_afk_native_geometry_hook"
COMPANION_AFK_GEOMETRY_HOOK_SIZE = 112
# r49 appends a fixed-width multiline layout after every r48 payload. Keeping
# the older scale/geometry owners allocated preserves all previously translated
# VAs even though the r49 callsites no longer jump to them.
COMPANION_AFK_WRAP_LAYOUT_TABLE_KEY = "companion_afk_wrap_layout_table"
COMPANION_AFK_WRAP_GEOMETRY_HOOK_KEY = "companion_afk_wrap_geometry_hook"
COMPANION_AFK_WRAP_GEOMETRY_HOOK_SIZE = 184
COMPANION_AFK_WRAP_TEXT_HOOK_KEY = "companion_afk_wrap_text_hook"
COMPANION_AFK_WRAP_TEXT_HOOK_SIZE = 112
# r50 appends complete consumer-specific geometry owners. The r49 hooks remain
# allocated at their historical VAs for binary stability.
COMPANION_AFK_R50_GEOMETRY_HOOK_KEY = "companion_afk_r50_geometry_hook"
COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE = 212
COMPANION_ACTION_R50_PANEL_EXTENSION_KEY = "companion_action_r50_panel_extension"
COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE = 136
# r52 replaces both r51 runtime hooks with one AFK-only constructor fix.

# r53: L1 blue object uses the existing unused task+0x2F4 sprite slot,
# but unlike r51 its opacity tracks every native green action transition.
COMPANION_ACTION_R53_BLUE_CREATE_KEY = "companion_action_r53_blue_create"
COMPANION_ACTION_R53_BLUE_CREATE_SIZE = 156
COMPANION_ACTION_R53_SHOW_KEY = "companion_action_r53_blue_show"
COMPANION_ACTION_R53_HIDE_KEY = "companion_action_r53_blue_hide"
COMPANION_ACTION_R53_ALPHA_HOOK_SIZE = 48
COMPANION_ACTION_R53_BLUE_OFFSET = 0x02F4
COMPANION_ACTION_R53_SHOW_SITE = 0x65A88
COMPANION_ACTION_R53_HIDE_SITES = (0x65B40, 0x65C5C)
COMPANION_ACTION_R53_BLUE_PREIMAGES = (
    (0x66668, 0x0C06850C),   # task reset cleanup sprite destructor
    (0x66DD4, 0x0C06850C),   # terminal cleanup sprite destructor
    (0x66740, 0x3C024371),   # action constructor next-resource f12
    (0x66744, 0x44826000),
    (0x65A88, 0xA0450023),   # green show vertex alpha
    (0x65B40, 0xA0400023),   # green hide vertex alpha
    (0x65C5C, 0xA0400023),   # green hide after task fade
)
COMPANION_AFK_R52_PRETEXT_HOOK_KEY = "companion_afk_r52_pretext_hook"
COMPANION_AFK_R52_PRETEXT_HOOK_SIZE = 84
COMPANION_AFK_R52_PRETEXT_PREIMAGES = (
    (0x66250, 0x44807000), (0x66254, 0x3C024375),
    (0x66320, 0x44807000), (0x66324, 0x3C024375),
)
COMPANION_AFK_R52_PRETEXT_PATCH_OFFSETS = (0x66250, 0x66320)
COMPANION_AFK_FIRST_RECORD_INDEX = 0x259
COMPANION_AFK_TEXT_STYLE_CELL_WIDTH = 16.0
COMPANION_AFK_TEXT_BODY_WIDTH = 288.0
COMPANION_AFK_TEXT_LEFT_INSET = 12.0
COMPANION_AFK_TEXT_RIGHT_INSET = 12.0
COMPANION_AFK_TEXT_SAFE_WIDTH = (
    COMPANION_AFK_TEXT_BODY_WIDTH
    - COMPANION_AFK_TEXT_LEFT_INSET
    - COMPANION_AFK_TEXT_RIGHT_INSET
)
COMPANION_AFK_TEXT_SAFE_CELLS = (
    COMPANION_AFK_TEXT_SAFE_WIDTH / COMPANION_AFK_TEXT_STYLE_CELL_WIDTH
)
# r49 never grows AFK horizontally. 16 cells = 256px, safely inside the proven
# 264px text body. Native line spacing is 18px (Y=313 then Y=331). Additional
# wrapped rows grow both bubble layers upward while their bottom/tail anchors
# stay fixed.
COMPANION_AFK_WRAP_CELLS = 16
# r49 used the 18px distance between the two *separate* native AFK objects as
# the newline advance. Runtime proves embedded 0xFF0E rows use a 32px visual
# advance. r50 sizes every row with that renderer-owned step.
COMPANION_AFK_LINE_STEP = 32.0
COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION = 18.0
COMPANION_AFK_GREEN_BASE_HEIGHT = 80.0
COMPANION_AFK_GREEN_BASE_PIVOT_Y = 77.0
COMPANION_AFK_BLUE_BASE_HEIGHT = 56.0
COMPANION_AFK_BLUE_BASE_PIVOT_Y = (74.0, 75.0, 76.0)
# Move text with the 381 -> 346 resource-anchor correction. The first row sits
# at 278 and a second row at 310; extra rows extend upward only.
COMPANION_AFK_TEXT1_BASE_Y = 278.0
COMPANION_AFK_TEXT2_BASE_Y = 310.0
# 0x1950A0 rejects converted strings whose source length is >=0x1FE. The
# current corpus is far below this, but keep generic wrapping fail-closed at the
# engine's own hard capacity instead of silently overflowing its 0x1FE buffer.
COMPANION_AFK_SOURCE_MAX_BYTES = 0x1FD
# The AFK task restores shared 0x68/0x69 to native geometry before constructing
# free-talk. The normal action renderer re-applies compact geometry every draw.
COMPANION_AFK_GEOMETRY_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66050, 0x86020004),  # lh v0,4(s0): current talk record
    (0x66054, 0x000219C0),  # sll v1,v0,7 (kept as JAL delay slot)
)
# r47 incorrectly treated f16 as X scale. Runtime + constructor tracing proves
# f16 is the fourth clamped RGBA component (alpha), so r48 freezes it at 1.0.
COMPANION_AFK_ALPHA_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x6625C, 0x3C023F80),  # line 1: lui v0,1.0
    (0x66260, 0x44828000),  # mtc1 v0,f16 (alpha)
    (0x6632C, 0x3C023F80),  # line 2: lui v0,1.0
    (0x66330, 0x44828000),  # mtc1 v0,f16 (alpha)
)
# The real horizontal transform is object +0x48. Apply it only after the
# specialized AFK text constructor returns, preserving the native continuation
# in each JAL delay slot/helper return value.
COMPANION_AFK_SCALE_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66284, 0xAE020028),  # line 1: sw v0,0x28(s0)
    (0x66288, 0x8602000A),  # lh v0,0x0a(s0)
    (0x66354, 0xAE02002C),  # line 2: sw v0,0x2c(s0)
    (0x66358, 0x24020078),  # li v0,0x78
)
COMPANION_AFK_RUNTIME_PATCH_OFFSETS = (
    0x66050,
    0x66284,
    0x66288,
    0x66354,
    0x66358,
)
# Existing H_TalkBuddyTask owner that skips the complete L1 callout when zero.
# r44 introduced the relocated predicate; r45 refined it to native AFK states
# 11..13. r46 preserves that hook byte-for-byte and only restores native 0x6A.
COMPANION_ACTION_VISIBILITY_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x666BC, 0x8E0202C8),  # lw v0,0x2c8(s0): original action-callout guard
    (0x666C0, 0x10400074),  # beq v0,zero,0x166814
    (0x666C4, 0x00000000),  # nop
)
COMPANION_ACTION_VISIBILITY_PATCH_OFFSETS = tuple(
    offset for offset, _expected in COMPANION_ACTION_VISIBILITY_PREIMAGES
)

# Static owners that are independent of the current action id. The resource
# selection and text-Y load are patched after translation allocation because
# they need addresses inside the relocated executable segment.
COMPANION_ACTION_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x666F0, 0x3C024140, 0x3C024080),  # tail-tip X: +12.0 -> +4.0
    (0x66708, 0x3C02C1E8, 0x3C02C274),  # tail-tip Y: -29.0 -> -61.0
    (0x6686C, 0x0000282D, 0x24050001),  # style 0 (16px) -> style 1 (12px)
)
COMPANION_ACTION_RUNTIME_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66724, 0x24040002),  # li a0,2
    (0x66728, 0x24050018),  # li a1,0x18
    (0x66804, 0x3C024244),  # static text-X float immediate
    (0x66808, 0x44820000),  # mtc1 v0,f0
    (0x6680C, 0x00000000),
    (0x66810, 0x46000800),  # add.s f0,f1,f0
    (0x6681C, 0x3C02C1B0),  # static text-Y float immediate
    (0x66820, 0x44820000),  # mtc1 v0,f0
    (0x66824, 0x00000000),
    (0x66828, 0x46000800),  # add.s f0,f1,f0
)
# Pristine slot selection: HUD+0x2D0 is scaled by eight and indexes the two
# (x,y) pairs at VA 0x4F8E00 / file 0x3F8E80.
COMPANION_SLOT_INDEX_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66674, 0x860202D0),  # lh v0,0x2d0(s0)
    (0x66678, 0x000218C0),  # sll v1,v0,3
    (0x6667C, 0x3C020050),  # lui v0,0x50
    (0x66680, 0x24428E00),  # addiu v0,v0,-0x7200 -> 0x4f8e00
    (0x66684, 0x00431021),  # addu v0,v0,v1
)
# Pristine action lookup later in the same renderer. r37 reuses this exact
# read-only getter contract before constructing the bubble.
COMPANION_ACTION_ID_REFERENCE_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66830, 0x34048000),  # ori a0,zero,0x8000
    (0x66834, 0x0C04BFB8),  # jal 0x0012fee0
    (0x66838, 0x00000000),
    (0x6683C, 0x3042FFFF),  # andi v0,v0,0xffff
    (0x66840, 0x38428000),  # xori v0,v0,0x8000
)
COMPANION_ACTION_RUNTIME_PATCH_OFFSETS = tuple(offset for offset, _ in COMPANION_ACTION_RUNTIME_PREIMAGES)


@dataclass(frozen=True)
class CompanionCommentLine:
    source_offset: int
    source_text: str
    official_english: str
    remaster_offset: int
    pointer_offsets: tuple[int, ...]

    @property
    def display_english(self) -> str:
        # English.bytes uses @D to delete a PS4 line after its content was merged
        # into the previous localized line. An empty C-string preserves that
        # exact presentation semantic in the PS2 two-line HUD table.
        return "" if self.official_english == "@D" else self.official_english


@dataclass(frozen=True)
class CompanionActionLabel:
    action_id: int
    pointer_offset: int
    source_offset: int
    source_text: str
    english: str | None
    remaster_offset: int | None
    provenance: str


COMPANION_COMMENT_LINES: tuple[CompanionCommentLine, ...] = tuple(
    CompanionCommentLine(*record) for record in COMPANION_COMMENT_DATA
)
COMPANION_ACTION_LABELS: tuple[CompanionActionLabel, ...] = tuple(
    CompanionActionLabel(*record) for record in COMPANION_ACTION_DATA
)


@dataclass(frozen=True)
class CompanionActionLayout:
    lines: tuple[str, ...]
    height: float
    pivot_y: float
    text_y: float


def wrap_companion_action_text(
    text: str,
    *,
    max_cells: int = COMPANION_ACTION_MAX_CELLS,
) -> tuple[str, ...]:
    """Word-wrap a companion action into deterministic 12px-cell rows."""

    if max_cells <= 0:
        raise ValueError("companion action max_cells must be positive")
    words = text.split()
    if not words:
        return ("",)

    lines: list[str] = []
    current = ""
    for word in words:
        while len(word) > max_cells:
            if current:
                lines.append(current)
                current = ""
            lines.append(word[:max_cells])
            word = word[max_cells:]
        if not word:
            continue
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_cells:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    if len(lines) > COMPANION_ACTION_MAX_LINES:
        raise ValueError(
            f"companion action requires {len(lines)} lines, exceeds safe HUD budget "
            f"of {COMPANION_ACTION_MAX_LINES}: {text!r}"
        )
    return tuple(lines)


def companion_action_layout(text: str | None) -> CompanionActionLayout:
    lines = wrap_companion_action_text(text or "")
    line_count = len(lines)
    height = 48.0 + COMPANION_ACTION_LINE_STEP * (line_count - 1)
    pivot_y = height - 3.0
    # Tail-tip anchor stays Y=-61; 7px text inset from the resized body top.
    text_y = -61.0 - pivot_y + 7.0
    return CompanionActionLayout(lines, height, pivot_y, text_y)


COMPANION_ACTION_LAYOUTS: tuple[CompanionActionLayout, ...] = tuple(
    companion_action_layout(spec.english) for spec in COMPANION_ACTION_LABELS
)


def encode_companion_action(text: str) -> bytes:
    lines = wrap_companion_action_text(text)
    return b"\x0a".join(
        encode_ps2_english(line, collapse_spaces=False) for line in lines
    ) + b"\x00"


def _layout_table_bytes() -> bytes:
    return b"".join(
        struct.pack("<fff", layout.height, layout.pivot_y, layout.text_y)
        for layout in COMPANION_ACTION_LAYOUTS
    )


@dataclass(frozen=True)
class CompanionAfkLayout:
    line1_rows: tuple[str, ...]
    line2_rows: tuple[str, ...]
    green_height: float
    green_pivot_y: float
    blue_height: float
    blue_pivot_y: tuple[float, float, float]
    text1_y: float
    text2_y: float


def wrap_companion_afk_text(
    text: str,
    *,
    max_cells: int = COMPANION_AFK_WRAP_CELLS,
) -> tuple[str, ...]:
    """Word-wrap one AFK field into fixed-width native style-0 rows.

    Long tokens are hard-split so no row can ever exceed the horizontal body
    budget. There is intentionally no artificial line-count ceiling: vertical
    capacity is derived from the resulting row count.
    """

    if max_cells <= 0:
        raise ValueError("companion AFK max_cells must be positive")
    words = text.split()
    if not words:
        return ()

    rows: list[str] = []
    current = ""
    for word in words:
        while len(word) > max_cells:
            if current:
                rows.append(current)
                current = ""
            rows.append(word[:max_cells])
            word = word[max_cells:]
        if not word:
            continue
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_cells:
            current = candidate
        else:
            rows.append(current)
            current = word
    if current:
        rows.append(current)
    return tuple(rows)


def encode_companion_afk_text(text: str) -> bytes:
    """Encode AFK English with native raw-newline controls.

    0x195960 converts raw 0x0A into internal control 0xFF0E. For the current
    corpus every break replaces a source space, so padding after the first NUL
    keeps each r48 relocation allocation exactly the same size and therefore
    keeps all later r48 payload VAs stable. Future harder splits remain generic
    and may grow the allocation if necessary.
    """

    rows = wrap_companion_afk_text(text)
    payload = b"\x0a".join(
        encode_ps2_english(row, collapse_spaces=False) for row in rows
    ) + b"\x00"
    source_bytes = len(payload) - 1
    if source_bytes > COMPANION_AFK_SOURCE_MAX_BYTES:
        raise ValueError(
            f"companion AFK wrapped source exceeds engine capacity: {source_bytes} bytes"
        )

    old_allocation = len(encode_ps2_english(text, collapse_spaces=False)) + 1
    if len(payload) < old_allocation:
        payload += b"\x00" * (old_allocation - len(payload))
    return payload


def companion_afk_layout(lines: tuple[str, str]) -> CompanionAfkLayout:
    line1_rows = wrap_companion_afk_text(lines[0])
    line2_rows = wrap_companion_afk_text(lines[1])
    if not line1_rows:
        raise ValueError("companion AFK record unexpectedly has no primary text row")

    total_rows = len(line1_rows) + len(line2_rows)
    extra_height = COMPANION_AFK_LINE_STEP * max(0, total_rows - 2)
    text1_y = COMPANION_AFK_TEXT1_BASE_Y - extra_height
    # The first and second native text objects are independent, and embedded
    # newlines advance at ~18 game units on the tested four-row AFK callout.
    # r50's 32-unit conservative BUBBLE budget remains unchanged, but applying
    # it again to the final text object's internal rows pushes the last word
    # ("age.") below the green bottom edge. Correct only that second baseline.
    text2_y = (
        text1_y
        + COMPANION_AFK_LINE_STEP * len(line1_rows)
        - COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION * max(0, len(line2_rows) - 1)
    )
    return CompanionAfkLayout(
        line1_rows=line1_rows,
        line2_rows=line2_rows,
        green_height=COMPANION_AFK_GREEN_BASE_HEIGHT + extra_height,
        green_pivot_y=COMPANION_AFK_GREEN_BASE_PIVOT_Y + extra_height,
        blue_height=COMPANION_AFK_BLUE_BASE_HEIGHT + extra_height,
        blue_pivot_y=tuple(
            value + extra_height for value in COMPANION_AFK_BLUE_BASE_PIVOT_Y
        ),
        text1_y=text1_y,
        text2_y=text2_y,
    )


COMPANION_AFK_LAYOUTS: tuple[CompanionAfkLayout, ...] = tuple(
    companion_afk_layout(lines) for lines in COMPANION_AFK_TRANSLATIONS
)


def _afk_wrap_layout_table_bytes() -> bytes:
    return b"".join(
        struct.pack(
            "<8f",
            layout.green_height,
            layout.green_pivot_y,
            layout.blue_height,
            *layout.blue_pivot_y,
            layout.text1_y,
            layout.text2_y,
        )
        for layout in COMPANION_AFK_LAYOUTS
    )


def companion_afk_text_scale(lines: tuple[str, str]) -> float:
    """Return the record-wide X scale that keeps both AFK rows inside 288px."""

    longest_cells = max((len(line) for line in lines if line), default=0)
    if longest_cells <= 0:
        return 1.0
    return min(
        1.0,
        COMPANION_AFK_TEXT_SAFE_CELLS / float(longest_cells),
    )


COMPANION_AFK_TEXT_SCALES: tuple[float, ...] = tuple(
    companion_afk_text_scale(lines) for lines in COMPANION_AFK_TRANSLATIONS
)


def _afk_scale_table_bytes() -> bytes:
    return struct.pack(
        f"<{len(COMPANION_AFK_TEXT_SCALES)}f",
        *COMPANION_AFK_TEXT_SCALES,
    )


def _split_address(value: int) -> tuple[int, int]:
    return ((value + 0x8000) >> 16) & 0xFFFF, value & 0xFFFF


def _mips_i(op: int, rs: int, rt: int, imm: int) -> int:
    return ((op & 0x3F) << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | (imm & 0xFFFF)


def _mips_r(rs: int, rt: int, rd: int, shamt: int, funct: int) -> int:
    return (
        ((rs & 0x1F) << 21)
        | ((rt & 0x1F) << 16)
        | ((rd & 0x1F) << 11)
        | ((shamt & 0x1F) << 6)
        | (funct & 0x3F)
    )


def _mips_mtc1(rt: int, fs: int) -> int:
    return (
        (0x11 << 26)
        | (0x04 << 21)
        | ((rt & 0x1F) << 16)
        | ((fs & 0x1F) << 11)
    )


def _j_word(target_va: int) -> int:
    if target_va & 3:
        raise ValueError(f"companion runtime target is not word-aligned: {target_va:#x}")
    return 0x08000000 | ((target_va >> 2) & 0x03FFFFFF)


def _action_geometry_extension_bytes() -> bytes:
    """Write complete compact 0x68/0x69 body geometry for the normal L1 callout."""

    words = (
        _mips_r(0, 13, 14, 4, 0x00),        # sll t6,t5,4
        _mips_r(0, 13, 15, 5, 0x00),        # sll t7,t5,5
        _mips_r(14, 15, 14, 0, 0x21),       # addu t6,t6,t7 = slot*48
        _mips_i(0x0F, 0, 15, 0x0045),       # lui t7,0x45
        _mips_i(0x09, 15, 15, 0x0AC4),      # addiu t7,t7,0xac4 (slot0 width)
        _mips_r(15, 14, 15, 0, 0x21),       # addu t7,t7,t6
        _mips_i(0x0F, 0, 14, 0x4360),       # lui t6,224.0
        _mips_i(0x2B, 15, 14, 0),            # sw t6,0(t7) width
        _mips_i(0x0F, 0, 14, 0x4250),       # lui t6,52.0 slot0 pivot-X
        _mips_i(0x04, 13, 0, 2),            # beq t5,zero,pivot_ready
        0x00000000,                          # nop
        _mips_i(0x0F, 0, 14, 0x42C2),       # lui t6,97.0 slot1 pivot-X
        _mips_i(0x2B, 15, 14, 8),            # sw t6,8(t7) pivot-X
        _mips_i(0x23, 29, 31, 12),           # lw ra,12(sp)
        _mips_i(0x09, 29, 29, 16),           # addiu sp,sp,16
        _mips_i(0x09, 0, 4, 2),              # li a0,2
        _mips_r(31, 0, 0, 0, 0x08),         # jr ra
        0x00000000,                          # nop
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE:
        raise AssertionError(f"companion action geometry extension drifted: {len(code)}")
    return code


def _afk_scale_hook_bytes(*, table_va: int) -> bytes:
    """Apply record-wide X scale to the constructed AFK text object.

    The specialized constructor returns the text object in v0. Runtime tracing
    proves object +0x48 is the horizontal transform; caller f16 is alpha and
    must remain the native 1.0. The two post-constructor callsites have different
    continuation values, so RA selects the value to restore in v0 before return.
    """

    table_hi, table_lo = _split_address(table_va)
    line1_return_va = 0x0016620C
    words = (
        _mips_r(2, 0, 11, 0, 0x21),         # addu t3,v0,zero: text object
        _mips_i(0x21, 16, 8, 0x0004),       # lh t0,4(s0): AFK record index
        _mips_i(0x09, 8, 8, -COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_r(0, 8, 8, 2, 0x00),          # sll t0,t0,2
        _mips_i(0x0F, 0, 9, table_hi),       # lui t1,hi(scale table)
        _mips_r(9, 8, 9, 0, 0x21),          # addu t1,t1,t0
        _mips_i(0x23, 9, 8, table_lo),       # lw t0,lo(scale table)(t1)
        _mips_i(0x2B, 11, 8, 0x0048),       # sw t0,0x48(t3): horizontal scale
        _mips_i(0x0F, 0, 8, line1_return_va >> 16),
        _mips_i(0x0D, 8, 8, line1_return_va & 0xFFFF),
        _mips_i(0x05, 31, 8, 2),            # bne ra,t0,line2_return
        _mips_i(0x09, 0, 2, 0x0078),        # delay: line2 needs v0=0x78
        _mips_i(0x21, 16, 2, 0x000A),       # line1: lh v0,0x0a(s0)
        _mips_r(31, 0, 0, 0, 0x08),         # jr ra
        0x00000000,                          # nop
        0x00000000,                          # stable 64-byte payload size
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_SCALE_HOOK_SIZE:
        raise AssertionError(f"companion AFK scale hook drifted: {len(code)}")
    return code


def _afk_geometry_hook_bytes() -> bytes:
    """Restore native 288x80 0x68/0x69 geometry for the selected AFK slot."""

    words = (
        _mips_i(0x21, 16, 2, 0x0004),       # lh v0,4(s0), preserve owner result
        _mips_i(0x0B, 2, 9, COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_i(0x05, 9, 0, 22),            # bne t1,zero,return
        0x00000000,                          # nop
        _mips_i(0x21, 16, 8, 0x02F8),       # lh t0,0x2f8(s0) AFK slot
        _mips_i(0x0B, 8, 9, 2),             # sltiu t1,t0,2
        _mips_i(0x04, 9, 0, 18),            # beq t1,zero,return
        0x00000000,                          # nop
        _mips_r(0, 8, 9, 4, 0x00),          # sll t1,t0,4
        _mips_r(0, 8, 10, 5, 0x00),         # sll t2,t0,5
        _mips_r(9, 10, 9, 0, 0x21),         # addu t1,t1,t2 = slot*48
        _mips_i(0x0F, 0, 10, 0x0045),       # lui t2,0x45
        _mips_i(0x09, 10, 10, 0x0AC4),      # addiu t2,t2,0xac4 width field
        _mips_r(10, 9, 10, 0, 0x21),        # addu t2,t2,t1
        _mips_i(0x0F, 0, 9, 0x4390),        # 288.0
        _mips_i(0x2B, 10, 9, 0),             # width
        _mips_i(0x0F, 0, 9, 0x42A0),        # 80.0
        _mips_i(0x2B, 10, 9, 4),             # height
        _mips_i(0x0F, 0, 9, 0x429A),        # 77.0
        _mips_i(0x2B, 10, 9, 12),            # pivot-Y
        _mips_i(0x0F, 0, 9, 0x4286),        # 67.0 slot0 pivot-X
        _mips_i(0x04, 8, 0, 2),             # beq t0,zero,pivot_ready
        0x00000000,                          # nop
        _mips_i(0x0F, 0, 9, 0x42FA),        # 125.0 slot1 pivot-X
        _mips_i(0x2B, 10, 9, 8),             # pivot-X
        _mips_r(0, 2, 3, 7, 0x00),          # return: sll v1,v0,7
        _mips_r(31, 0, 0, 0, 0x08),         # jr ra
        0x00000000,                          # nop
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_GEOMETRY_HOOK_SIZE:
        raise AssertionError(f"companion AFK geometry hook drifted: {len(code)}")
    return code


def _afk_wrap_geometry_hook_bytes(*, table_va: int) -> bytes:
    """Apply record-specific fixed-width AFK geometry before construction.

    Width and X pivots remain native. Height and Y pivots grow together, so the
    green tail/bottom anchor and blue-panel bottom stay fixed while extra rows
    extend upward. The selected green slot and all three blue animation frames
    receive the same per-record vertical delta.
    """

    table_hi, table_lo = _split_address(table_va)
    words = (
        _mips_i(0x21, 16, 2, 0x0004),       # lh v0,4(s0): record index
        _mips_i(0x09, 2, 8, -COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_i(0x0B, 8, 9, COMPANION_AFK_RECORD_COUNT),
        _mips_i(0x04, 9, 0, 38),            # invalid record -> return
        0x00000000,
        _mips_i(0x21, 16, 10, 0x02F8),      # lh t2,0x2f8(s0): slot 0/1
        _mips_i(0x0B, 10, 9, 2),
        _mips_i(0x04, 9, 0, 34),            # invalid slot -> return
        0x00000000,
        _mips_r(0, 8, 11, 5, 0x00),         # sll t3,t0,5: layout * 32
        _mips_i(0x0F, 0, 12, table_hi),
        _mips_i(0x09, 12, 12, table_lo),
        _mips_r(12, 11, 12, 0, 0x21),       # t4 = layout record
        _mips_r(0, 10, 13, 4, 0x00),        # slot*16
        _mips_r(0, 10, 14, 5, 0x00),        # slot*32
        _mips_r(13, 14, 13, 0, 0x21),       # t5 = slot*48
        _mips_i(0x0F, 0, 14, 0x0045),
        _mips_i(0x09, 14, 14, 0x0AC4),      # t6 = green slot0 width field
        _mips_r(14, 13, 14, 0, 0x21),
        _mips_i(0x0F, 0, 15, 0x4390),       # native width 288
        _mips_i(0x2B, 14, 15, 0),
        _mips_i(0x23, 12, 15, 0),            # dynamic green height
        _mips_i(0x2B, 14, 15, 4),
        _mips_i(0x23, 12, 15, 4),            # dynamic green pivot-Y
        _mips_i(0x2B, 14, 15, 12),
        _mips_i(0x0F, 0, 15, 0x4286),       # slot0 pivot-X 67
        _mips_i(0x04, 10, 0, 2),
        0x00000000,
        _mips_i(0x0F, 0, 15, 0x42FA),       # slot1 pivot-X 125
        _mips_i(0x2B, 14, 15, 8),
        _mips_i(0x0F, 0, 14, 0x0045),
        _mips_i(0x09, 14, 14, 0x0B28),      # blue frame0 height field
        _mips_i(0x23, 12, 15, 8),            # dynamic blue height
        _mips_i(0x2B, 14, 15, 0),
        _mips_i(0x2B, 14, 15, 0x30),
        _mips_i(0x2B, 14, 15, 0x60),
        _mips_i(0x23, 12, 15, 12),           # frame0 pivot-Y
        _mips_i(0x2B, 14, 15, 8),
        _mips_i(0x23, 12, 15, 16),           # frame1 pivot-Y
        _mips_i(0x2B, 14, 15, 0x38),
        _mips_i(0x23, 12, 15, 20),           # frame2 pivot-Y
        _mips_i(0x2B, 14, 15, 0x68),
        _mips_i(0x21, 16, 2, 0x0004),       # return: restore pristine results
        _mips_r(0, 2, 3, 7, 0x00),          # sll v1,v0,7
        _mips_r(31, 0, 0, 0, 0x08),
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_WRAP_GEOMETRY_HOOK_SIZE:
        raise AssertionError(f"companion AFK wrap geometry hook drifted: {len(code)}")
    return code


def _afk_wrap_text_hook_bytes(*, table_va: int) -> bytes:
    """Place wrapped AFK text vertically and keep horizontal scale at 1.0."""

    table_hi, table_lo = _split_address(table_va)
    line1_return_va = 0x0016620C
    words = (
        _mips_r(2, 0, 11, 0, 0x21),         # t3 = returned text object
        _mips_i(0x0F, 0, 15, 0x3F80),       # 1.0
        _mips_i(0x2B, 11, 15, 0x0048),      # X scale = native 1.0
        _mips_i(0x0F, 0, 14, line1_return_va >> 16),
        _mips_i(0x0D, 14, 14, line1_return_va & 0xFFFF),
        _mips_i(0x21, 16, 8, 0x0004),       # record index
        _mips_i(0x09, 8, 8, -COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_i(0x0B, 8, 9, COMPANION_AFK_RECORD_COUNT),
        _mips_i(0x04, 9, 0, 12),            # invalid -> continuation only
        0x00000000,
        _mips_r(0, 8, 8, 5, 0x00),          # layout * 32
        _mips_i(0x0F, 0, 9, table_hi),
        _mips_i(0x09, 9, 9, table_lo),
        _mips_r(9, 8, 9, 0, 0x21),
        _mips_i(0x05, 31, 14, 4),           # line2 -> +28
        0x00000000,
        _mips_i(0x23, 9, 10, 24),           # line1 Y
        _mips_i(0x04, 0, 0, 2),             # -> store Y
        0x00000000,
        _mips_i(0x23, 9, 10, 28),           # line2 Y
        _mips_i(0x2B, 11, 10, 0x0018),      # object Y
        _mips_i(0x05, 31, 14, 4),           # line2 continuation
        _mips_i(0x09, 0, 2, 0x0078),        # delay: line2 v0=0x78
        _mips_i(0x21, 16, 2, 0x000A),       # line1 continuation
        _mips_r(31, 0, 0, 0, 0x08),
        0x00000000,
        _mips_r(31, 0, 0, 0, 0x08),         # line2 return
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_WRAP_TEXT_HOOK_SIZE:
        raise AssertionError(f"companion AFK wrap text hook drifted: {len(code)}")
    return code


def _afk_r50_geometry_hook_bytes(*, table_va: int) -> bytes:
    """Apply r50 AFK geometry for the active record and companion slot.

    The green 0x68/0x69 layer and all three blue 0x6A animation frames receive
    the same record-specific height growth. Width stays 288. Blue pivot-X now
    follows the active slot (67/125), matching the r50 slot-aware placement.
    """

    table_hi, table_lo = _split_address(table_va)
    words = (
        _mips_i(0x21, 16, 2, 0x0004),       # lh v0,4(s0): record index
        _mips_i(0x09, 2, 8, -COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_i(0x0B, 8, 9, COMPANION_AFK_RECORD_COUNT),
        _mips_i(0x04, 9, 0, 45),            # invalid record -> return
        0x00000000,
        _mips_i(0x21, 16, 10, 0x02F8),      # lh t2,0x2f8(s0): slot 0/1
        _mips_i(0x0B, 10, 9, 2),
        _mips_i(0x04, 9, 0, 41),            # invalid slot -> return
        0x00000000,
        _mips_r(0, 8, 11, 5, 0x00),         # sll t3,t0,5: layout * 32
        _mips_i(0x0F, 0, 12, table_hi),
        _mips_i(0x09, 12, 12, table_lo),
        _mips_r(12, 11, 12, 0, 0x21),       # t4 = layout record
        _mips_r(0, 10, 13, 4, 0x00),        # slot*16
        _mips_r(0, 10, 14, 5, 0x00),        # slot*32
        _mips_r(13, 14, 13, 0, 0x21),       # t5 = slot*48
        _mips_i(0x0F, 0, 14, 0x0045),
        _mips_i(0x09, 14, 14, 0x0AC4),      # green slot0 width field
        _mips_r(14, 13, 14, 0, 0x21),
        _mips_i(0x0F, 0, 15, 0x4390),       # 288.0
        _mips_i(0x2B, 14, 15, 0),           # green width
        _mips_i(0x23, 12, 15, 0),           # green height
        _mips_i(0x2B, 14, 15, 4),
        _mips_i(0x23, 12, 15, 4),           # green pivot-Y
        _mips_i(0x2B, 14, 15, 12),
        _mips_i(0x0F, 0, 15, 0x4286),       # slot0 pivot-X 67
        _mips_i(0x04, 10, 0, 2),
        0x00000000,
        _mips_i(0x0F, 0, 15, 0x42FA),       # slot1 pivot-X 125
        _mips_i(0x2B, 14, 15, 8),           # green pivot-X
        _mips_i(0x0F, 0, 14, 0x0045),
        _mips_i(0x09, 14, 14, 0x0B24),      # blue frame0 width field
        _mips_i(0x0F, 0, 13, 0x438D),       # r53 AFK blue 282.0, green stays 288
        _mips_i(0x2B, 14, 13, 0x00),
        _mips_i(0x2B, 14, 13, 0x30),
        _mips_i(0x2B, 14, 13, 0x60),
        _mips_i(0x23, 12, 13, 8),            # blue height
        _mips_i(0x2B, 14, 13, 0x04),
        _mips_i(0x2B, 14, 13, 0x34),
        _mips_i(0x2B, 14, 13, 0x64),
        _mips_i(0x2B, 14, 15, 0x08),         # blue pivot-X slot-aware
        _mips_i(0x2B, 14, 15, 0x38),
        _mips_i(0x2B, 14, 15, 0x68),
        _mips_i(0x23, 12, 13, 12),           # blue frame0 pivot-Y
        _mips_i(0x2B, 14, 13, 0x0C),
        _mips_i(0x23, 12, 13, 16),           # blue frame1 pivot-Y
        _mips_i(0x2B, 14, 13, 0x3C),
        _mips_i(0x23, 12, 13, 20),           # blue frame2 pivot-Y
        _mips_i(0x2B, 14, 13, 0x6C),
        _mips_i(0x21, 16, 2, 0x0004),       # return: restore owner results
        _mips_r(0, 2, 3, 7, 0x00),
        _mips_r(31, 0, 0, 0, 0x08),
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE:
        raise AssertionError(f"companion AFK r50 geometry hook drifted: {len(code)}")
    return code


def _action_r50_panel_extension_bytes() -> bytes:
    """Apply compact L1 geometry to green and blue speech layers together."""

    words = (
        _mips_r(0, 13, 14, 4, 0x00),        # slot*16
        _mips_r(0, 13, 15, 5, 0x00),        # slot*32
        _mips_r(14, 15, 14, 0, 0x21),       # t6 = slot*48
        _mips_i(0x0F, 0, 15, 0x0045),
        _mips_i(0x09, 15, 15, 0x0AC4),      # green slot0 width
        _mips_r(15, 14, 15, 0, 0x21),
        _mips_i(0x0F, 0, 14, 0x4360),       # 224.0
        _mips_i(0x2B, 15, 14, 0),           # green width
        _mips_i(0x0F, 0, 14, 0x4250),       # slot0 pivot-X 52
        _mips_i(0x04, 13, 0, 2),
        0x00000000,
        _mips_i(0x0F, 0, 14, 0x42C2),       # slot1 pivot-X 97
        _mips_i(0x2B, 15, 14, 8),           # green pivot-X
        _mips_i(0x0F, 0, 15, 0x0045),
        _mips_i(0x09, 15, 15, 0x0B24),      # blue frame0 width
        _mips_i(0x0F, 0, 12, 0x4360),       # 224.0
        _mips_i(0x2B, 15, 12, 0x00),
        _mips_i(0x2B, 15, 12, 0x30),
        _mips_i(0x2B, 15, 12, 0x60),
        _mips_i(0x2B, 15, 10, 0x04),         # action-specific height
        _mips_i(0x2B, 15, 10, 0x34),
        _mips_i(0x2B, 15, 10, 0x64),
        _mips_i(0x2B, 15, 14, 0x08),         # slot-aware pivot-X
        _mips_i(0x2B, 15, 14, 0x38),
        _mips_i(0x2B, 15, 14, 0x68),
        _mips_i(0x2B, 15, 11, 0x0C),         # action-specific pivot-Y
        _mips_i(0x2B, 15, 11, 0x3C),
        _mips_i(0x2B, 15, 11, 0x6C),
        _mips_i(0x23, 29, 31, 12),           # restore caller
        _mips_i(0x09, 29, 29, 16),
        _mips_i(0x09, 0, 4, 2),              # li a0,2
        _mips_r(31, 0, 0, 0, 0x08),
        0x00000000,
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE:
        raise AssertionError(f"companion action r50 panel extension drifted: {len(code)}")
    return code



def _afk_r52_pretext_hook_bytes(*, table_va: int) -> bytes:
    """Bind AFK Y to both native constructor inputs before text creation.

    Unlike r51/r52, preserve t0-t3: the specialized constructor saves t1 as
    a native text argument before generating glyphs. Only t4-t6 are scratch;
    caller stack-spilled f13 (sp+0x1a4) remains synchronized.
    All non-AFK records continue with the original value. This never creates
    an independent group-2 sprite or alters L1 ownership/lifecycle.
    """

    table_hi, table_lo = _split_address(table_va)
    line1_return_va = 0x001661D8
    words = (
        _mips_mtc1(0, 14),                    # displaced mtc1 zero,f14
        _mips_i(0x21, 16, 12, 0x0004),        # lh t4,4(s0): AFK record
        _mips_i(0x09, 12, 12, -COMPANION_AFK_FIRST_RECORD_INDEX),
        _mips_i(0x0B, 12, 13, COMPANION_AFK_RECORD_COUNT),
        _mips_i(0x04, 13, 0, 14),            # non-AFK -> return, no stack change
        0x00000000,
        _mips_r(0, 12, 12, 5, 0x00),          # t4 index * 32
        _mips_i(0x0F, 0, 13, table_hi),
        _mips_i(0x09, 13, 13, table_lo),
        _mips_r(13, 12, 13, 0, 0x21),
        _mips_i(0x0F, 0, 14, line1_return_va >> 16),
        _mips_i(0x0D, 14, 14, line1_return_va & 0xFFFF),
        _mips_i(0x05, 31, 14, 4),           # line2 -> +28
        0x00000000,
        _mips_i(0x31, 13, 13, 24),           # lwc1 f13,line1_y
        _mips_i(0x04, 0, 0, 2),             # join spill/return
        0x00000000,
        _mips_i(0x31, 13, 13, 28),           # lwc1 f13,line2_y
        _mips_i(0x39, 29, 13, 0x01A4),     # swc1 f13,0x1a4(sp): native spill
        _mips_r(31, 0, 0, 0, 0x08),         # jr ra
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_AFK_R52_PRETEXT_HOOK_SIZE:
        raise AssertionError(f"companion AFK r52 pretext hook drifted: {len(code)}")
    return code



def _action_r53_blue_create_bytes() -> bytes:
    """One L1 blue: match live green position, hide stale AFK blue sibling.

    Both sprite constructors initially use stack+0x178. Crucially, this alone
    failed visually in r53. The native resource owner at 0x107F88-0x107F94
    stores the actual post-construction sprite X/Y at +0x3C/+0x40, so copy
    those fields from the ALREADY-CREATED L1 green +0x2D8 sprite. The older
    AFK 0x6A at task+0x5C is separately created and left at its old anchor;
    zero its four vertex-alpha bytes during L1 and let AFK rebuild it during
    the subsequent native AFK lifecycle. Never allocate a SECOND blue object.
    """
    words = (
        _mips_i(0x37, 29, 6, 0x0178),       # ld a2,0x178(sp): native caller XY
        _mips_i(0x09, 29, 29, -16),
        _mips_i(0x2B, 29, 31, 12),
        _mips_i(0x0F, 0, 2, 0x4372),        # 242.5 behind green 243
        _mips_i(0x0D, 2, 2, 0x8000),
        _mips_mtc1(2, 12),
        _mips_i(0x09, 0, 4, 2),
        _mips_i(0x09, 0, 5, 0x006A),
        _mips_r(0, 0, 7, 0, 0x21),
        _jal_word(0x00107D60),
        0,
        _mips_i(0x2B, 16, 2, COMPANION_ACTION_R53_BLUE_OFFSET),
        _mips_i(0x23, 16, 12, COMPANION_ACTION_R53_BLUE_OFFSET), # t4=new L1 blue
        _mips_i(0x04, 12, 0, 19),          # no sprite -> preserve old
        0,
        _mips_i(0x28, 12, 0, 0x23),        # four initially hidden vertices
        _mips_i(0x28, 12, 0, 0x27),
        _mips_i(0x28, 12, 0, 0x2B),
        _mips_i(0x28, 12, 0, 0x2F),
        _mips_i(0x23, 16, 13, 0x02D8),   # t5=green live object
        _mips_i(0x04, 13, 0, 5),          # no green -> preserve copied XY
        0,
        _mips_i(0x31, 13, 0, 0x003C),    # lwc1 f0,green actual X
        _mips_i(0x39, 12, 0, 0x003C),    # swc1 f0,blue actual X
        _mips_i(0x31, 13, 1, 0x0040),    # lwc1 f1,green actual Y
        _mips_i(0x39, 12, 1, 0x0040),    # swc1 f1,blue actual Y
        _mips_i(0x23, 16, 13, 0x005C),   # t5=stale AFK blue at lower anchor
        _mips_i(0x04, 13, 0, 5),          # only hide old AFK sprite if present
        0,
        _mips_i(0x28, 13, 0, 0x23),        # r54 suppress redundant lower panel
        _mips_i(0x28, 13, 0, 0x27),
        _mips_i(0x28, 13, 0, 0x2B),
        _mips_i(0x28, 13, 0, 0x2F),
        _mips_i(0x23, 29, 31, 12),       # return / native next resource setup
        _mips_i(0x09, 29, 29, 16),
        _mips_i(0x0F, 0, 2, 0x4371),
        _mips_mtc1(2, 12),
        _mips_r(31, 0, 0, 0, 0x08),
        0,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_R53_BLUE_CREATE_SIZE:
        raise AssertionError(f"L1 r54 single-blue constructor size drift: {len(code)}")
    return code


def _action_r53_blue_alpha_bytes(*, visible: bool) -> bytes:
    """Mirror L1 green alpha to its sole blue, keep old AFK blue hidden.

    The native AFK 0x6A may be animated independently while a normal action
    is visible. Suppress its per-vertex alpha on EACH green show/hide pass, not
    only at new-blue creation, avoiding the two-window r53 regression.
    """
    source = 5 if visible else 0
    words = (
        _mips_i(0x28, 2, source, 0x23),       # displaced green sb
        _mips_i(0x23, 16, 12, COMPANION_ACTION_R53_BLUE_OFFSET), # new sibling
        _mips_i(0x04, 12, 0, 3),            # skip mirroring if absent
        _mips_r(0, 3, 13, 2, 0x00),         # t5 = frame*4; delay slot
        _mips_r(12, 13, 12, 0, 0x21),
        _mips_i(0x28, 12, source, 0x23),   # mirror native green alpha
        _mips_i(0x23, 16, 14, 0x005C),     # existing AFK 0x6A sprite
        _mips_i(0x04, 14, 0, 2),           # skip if absent
        _mips_r(14, 13, 14, 0, 0x21),       # old AFK frame*4
        _mips_i(0x28, 14, 0, 0x23),        # old native blue alpha always zero
        _mips_r(31, 0, 0, 0, 0x08),
        0,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_R53_ALPHA_HOOK_SIZE:
        raise AssertionError(f"L1 r54 single-blue alpha hook size drift: {len(code)}")
    return code


def _runtime_hook_bytes(
    *,
    table_va: int,
    state_va: int,
    geometry_extension_va: int,
) -> bytes:
    table_hi, table_lo = _split_address(table_va)
    state_hi, state_lo = _split_address(state_va)

    # Action id and companion slot are independent. The action getter selects
    # height/pivot-Y/text-Y from the 31-entry table. HUD+0x2D0 selects one of the
    # two sibling down-tail bubbles and a matching text-X inset. Slot 2 therefore
    # moves the body only 13px right while its tail moves 58px to the slot-2
    # anchor. Invalid slot/action ids fail safely to zero.
    words = (
        _mips_i(0x09, 29, 29, -16),         # addiu sp,sp,-16
        _mips_i(0x2B, 29, 31, 12),          # sw ra,12(sp)
        _mips_i(0x0D, 0, 4, COMPANION_ACTION_ID_KEY),  # ori a0,zero,0x8000
        _jal_word(COMPANION_ACTION_ID_GETTER_VA),       # jal action-id getter
        0x00000000,                         # nop
        _mips_i(0x0C, 2, 2, 0xFFFF),        # andi v0,v0,0xffff
        _mips_i(0x0E, 2, 2, COMPANION_ACTION_ID_KEY),  # xori v0,v0,0x8000
        _mips_i(0x0B, 2, 3, len(COMPANION_ACTION_LAYOUTS)),  # sltiu v1,v0,31
        _mips_i(0x05, 3, 0, 2),             # bne v1,zero,action_valid
        0x00000000,                          # nop
        _mips_r(0, 0, 2, 0, 0x21),          # addu v0,zero,zero (fallback id 0)
        _mips_r(0, 2, 3, 3, 0x00),          # sll v1,v0,3
        _mips_r(0, 2, 8, 2, 0x00),          # sll t0,v0,2
        _mips_r(3, 8, 3, 0, 0x21),          # addu v1,v1,t0 (id * 12)
        _mips_i(0x0F, 0, 8, table_hi),       # lui t0,hi(action table)
        _mips_i(0x09, 8, 8, table_lo),       # addiu t0,t0,lo(action table)
        _mips_r(8, 3, 8, 0, 0x21),          # addu t0,t0,v1
        _mips_i(0x23, 8, 10, 0),             # lw t2,0(t0) height
        _mips_i(0x23, 8, 11, 4),             # lw t3,4(t0) pivot_y
        _mips_i(0x23, 8, 12, 8),             # lw t4,8(t0) text_y
        _mips_i(0x21, 16, 13, 0x02D0),       # lh t5,0x2d0(s0) slot
        _mips_i(0x0B, 13, 14, 2),            # sltiu t6,t5,2
        _mips_i(0x05, 14, 0, 2),             # bne t6,zero,slot_valid
        0x00000000,                          # nop
        _mips_r(0, 0, 13, 0, 0x21),         # addu t5,zero,zero (fallback slot 0)
        _mips_r(0, 13, 14, 4, 0x00),         # sll t6,t5,4  (slot*16)
        _mips_r(0, 13, 15, 5, 0x00),         # sll t7,t5,5  (slot*32)
        _mips_r(14, 15, 14, 0, 0x21),        # addu t6,t6,t7 (slot*48)
        _mips_i(0x0F, 0, 15, 0x0045),        # lui t7,0x45
        _mips_i(0x09, 15, 15, 0x0AC8),       # addiu t7,t7,0xac8 (slot0 height)
        _mips_r(15, 14, 15, 0, 0x21),        # addu t7,t7,t6
        _mips_i(0x2B, 15, 10, 0),            # sw t2,0(t7) height
        _mips_i(0x2B, 15, 11, 8),            # sw t3,8(t7) pivot_y
        _mips_i(0x0F, 0, 15, state_hi),      # lui t7,hi(state)
        _mips_i(0x09, 15, 15, state_lo),     # addiu t7,t7,lo(state)
        _mips_i(0x0F, 0, 10, 0xC210),        # lui t2,0xc210 (-36.0 slot 0)
        _mips_i(0x04, 13, 0, 2),             # beq t5,zero,text_x_ready
        0x00000000,                          # nop
        _mips_i(0x0F, 0, 10, 0xC2A2),        # lui t2,0xc2a2 (-81.0 slot 1)
        _mips_i(0x2B, 15, 10, 0),            # sw t2,0(t7) text_x
        _mips_i(0x2B, 15, 12, 4),            # sw t4,4(t7) text_y
        _mips_i(0x09, 13, 5, 0x0068),        # addiu a1,t5,0x68 (0x68/0x69)
        _j_word(geometry_extension_va),       # tail-jump: complete compact geometry
        0x00000000,                          # nop
        0x00000000,                          # keep 188-byte owner stable
        0x00000000,
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_RUNTIME_HOOK_SIZE:
        raise AssertionError(f"companion runtime hook size drifted: {len(code)}")
    return code


def _visibility_hook_bytes() -> bytes:
    """Return the r45 L1-callout visibility predicate.

    Preserve the original s0+0x2C8 callout guard first. Re:charge free-talk is
    selected by record index >= 0x259, then the native task enters state 11
    immediately after constructing the AFK panel/text and tears it down through
    states 12 and 13 before returning to state 8. Suppress the independent L1
    action callout only for that exact native AFK-visible lifecycle.
    """

    words = (
        _mips_i(0x23, 16, 2, 0x02C8),       # lw v0,0x2c8(s0): original guard
        _mips_i(0x04, 2, 0, 12),            # beq v0,zero,return
        0x00000000,                          # nop
        _mips_i(0x21, 16, 8, 0x0004),       # lh t0,4(s0): current record index
        _mips_i(0x0B, 8, 9, COMPANION_AFK_FIRST_RECORD_INDEX),  # sltiu t1,t0,0x259
        _mips_i(0x05, 9, 0, 8),             # bne t1,zero,return (normal h_buddy)
        0x00000000,                          # nop
        _mips_i(0x21, 16, 8, 0x0002),       # lh t0,2(s0): H_TalkBuddyTask state
        _mips_i(0x09, 8, 8, -COMPANION_AFK_VISIBLE_STATE_FIRST), # addiu t0,t0,-11
        _mips_i(
            0x0B,
            8,
            9,
            COMPANION_AFK_VISIBLE_STATE_LAST - COMPANION_AFK_VISIBLE_STATE_FIRST + 1,
        ),                                   # sltiu t1,t0,3 => states 11..13
        _mips_i(0x04, 9, 0, 3),             # beq t1,zero,return
        0x00000000,                          # nop
        _mips_r(0, 0, 2, 0, 0x21),          # addu v0,zero,zero: hide L1 callout
        0x00000000,                          # alignment / fallthrough padding
        _mips_r(31, 0, 0, 0, 0x08),         # return: jr ra
        0x00000000,                          # nop
        0x00000000,
        0x00000000,
        0x00000000,
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_VISIBILITY_HOOK_SIZE:
        raise AssertionError(f"companion visibility hook size drifted: {len(code)}")
    return code


def _jal_word(target_va: int) -> int:
    if target_va & 3:
        raise ValueError(f"companion action hook is not word-aligned: {target_va:#x}")
    return 0x0C000000 | ((target_va >> 2) & 0x03FFFFFF)


def _source_va(source_offset: int) -> int:
    return _ELF_MAIN_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET


def _validate_source_text(raw: bytes, *, owner: str, source_offset: int, source_text: str) -> None:
    expected = source_text.encode("cp932") + b"\x00"
    if source_offset < 0 or source_offset + len(expected) > len(raw):
        raise ValueError(f"{owner} source is outside executable: {source_offset:#x}")
    if raw[source_offset:source_offset + len(expected)] != expected:
        raise ValueError(f"{owner} source preimage mismatch: {source_offset:#x}")


def validate_companion_afk_source(raw: bytes) -> None:
    """Validate the exact Re:charge free-talk owner table and source strings."""

    if len(COMPANION_AFK_TRANSLATIONS) != COMPANION_AFK_RECORD_COUNT:
        raise ValueError(
            "companion AFK translation corpus size drifted: "
            f"{len(COMPANION_AFK_TRANSLATIONS)}"
        )

    table_end = COMPANION_AFK_TABLE_OFFSET + (
        COMPANION_AFK_RECORD_COUNT * COMPANION_AFK_RECORD_STRIDE
    )
    if table_end > len(raw):
        raise ValueError("companion AFK table is outside executable")
    table_digest = hashlib.sha256(raw[COMPANION_AFK_TABLE_OFFSET:table_end]).hexdigest()
    if table_digest != COMPANION_AFK_TABLE_SHA256:
        raise ValueError(
            "companion AFK table preimage drifted: "
            f"expected {COMPANION_AFK_TABLE_SHA256}, got {table_digest}"
        )

    source_digest = hashlib.sha256()
    live_fields = 0
    unique_source_pointers: set[int] = set()
    english_by_source_va: dict[int, str] = {}

    for record_index, (english_line1, english_line2) in enumerate(COMPANION_AFK_TRANSLATIONS):
        companion_id = (record_index // COMPANION_AFK_RECORDS_PER_COMPANION) + 1
        record_offset = COMPANION_AFK_TABLE_OFFSET + (
            record_index * COMPANION_AFK_RECORD_STRIDE
        )
        enabled, actual_companion_id, line1_va, line2_va = struct.unpack_from(
            "<IIII", raw, record_offset
        )
        if (enabled, actual_companion_id) != (1, companion_id):
            raise ValueError(
                "companion AFK record owner drifted: "
                f"{record_offset:#x}: expected (1, {companion_id}), "
                f"got ({enabled}, {actual_companion_id})"
            )

        source_digest.update(
            struct.pack(
                "<IIIII",
                record_index,
                record_offset,
                enabled,
                actual_companion_id,
                line1_va,
            )
        )
        source_digest.update(struct.pack("<I", line2_va))

        for line_number, (source_va, english) in enumerate(
            ((line1_va, english_line1), (line2_va, english_line2)),
            start=1,
        ):
            if source_va == COMPANION_AFK_EMPTY_VA:
                source_digest.update(b"<EMPTY>")
                if english:
                    raise ValueError(
                        "companion AFK translation adds text to a pristine empty field: "
                        f"id={companion_id} index={record_index % 20} line={line_number}"
                    )
                continue

            if not english:
                raise ValueError(
                    "companion AFK translation is missing for a live field: "
                    f"id={companion_id} index={record_index % 20} line={line_number}"
                )
            if len(english) > COMPANION_AFK_MAX_CHARS:
                raise ValueError(
                    "companion AFK English exceeds the safe field budget: "
                    f"id={companion_id} index={record_index % 20} "
                    f"line={line_number} chars={len(english)}"
                )
            # A reused Japanese source pointer must keep one English rendering.
            # This mirrors the game's own string sharing and prevents context-only
            # rewrites from silently diverging for the same source text.
            previous_english = english_by_source_va.setdefault(source_va, english)
            if previous_english != english:
                raise ValueError(
                    "companion AFK reused source has conflicting English: "
                    f"{source_va:#x}: {previous_english!r} != {english!r}"
                )

            # Reject unsupported glyphs before allocation.
            encode_ps2_english(english, collapse_spaces=False)

            source_offset = _ELF_MAIN_FILE_OFFSET + source_va - _ELF_MAIN_VADDR
            if source_offset < 0 or source_offset >= len(raw):
                raise ValueError(
                    "companion AFK source pointer is outside executable: "
                    f"{source_va:#x}"
                )
            terminator = raw.find(
                b"\x00",
                source_offset,
                min(len(raw), source_offset + _MAX_STRING_BYTES),
            )
            if terminator < 0:
                raise ValueError(
                    f"companion AFK source is unterminated: {source_offset:#x}"
                )
            source_bytes = raw[source_offset:terminator]
            try:
                source_bytes.decode("cp932")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"companion AFK source is not CP932 text: {source_offset:#x}"
                ) from exc

            live_fields += 1
            unique_source_pointers.add(source_va)
            source_digest.update(struct.pack("<I", source_va))
            source_digest.update(source_bytes)
            source_digest.update(b"\x00")

    if live_fields != COMPANION_AFK_EXPECTED_LIVE_FIELDS:
        raise ValueError(
            "companion AFK live-field count drifted: "
            f"expected {COMPANION_AFK_EXPECTED_LIVE_FIELDS}, got {live_fields}"
        )
    if len(unique_source_pointers) != COMPANION_AFK_EXPECTED_UNIQUE_SOURCE_POINTERS:
        raise ValueError(
            "companion AFK unique-source count drifted: "
            f"expected {COMPANION_AFK_EXPECTED_UNIQUE_SOURCE_POINTERS}, "
            f"got {len(unique_source_pointers)}"
        )
    actual_source_digest = source_digest.hexdigest()
    if actual_source_digest != COMPANION_AFK_SOURCE_SHA256:
        raise ValueError(
            "companion AFK source corpus drifted: "
            f"expected {COMPANION_AFK_SOURCE_SHA256}, got {actual_source_digest}"
        )


def _relocated_companion_afk_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    entries: list[RelocatedText] = []
    for record_index, (english_line1, english_line2) in enumerate(COMPANION_AFK_TRANSLATIONS):
        companion_id = (record_index // COMPANION_AFK_RECORDS_PER_COMPANION) + 1
        companion_line = record_index % COMPANION_AFK_RECORDS_PER_COMPANION
        record_offset = COMPANION_AFK_TABLE_OFFSET + (
            record_index * COMPANION_AFK_RECORD_STRIDE
        )
        _, _, line1_va, line2_va = struct.unpack_from("<IIII", raw, record_offset)
        for line_number, source_va, english, pointer_offset in (
            (1, line1_va, english_line1, record_offset + 8),
            (2, line2_va, english_line2, record_offset + 12),
        ):
            if source_va == COMPANION_AFK_EMPTY_VA:
                continue
            entries.append(
                RelocatedText(
                    key=(
                        f"companion_afk_{companion_id:02d}_"
                        f"{companion_line:02d}_{line_number}"
                    ),
                    encoded=encode_companion_afk_text(english),
                    pointer_offsets=(pointer_offset,),
                )
            )
    return tuple(entries)


def validate_companion_hud_source(raw: bytes) -> None:
    if len(COMPANION_COMMENT_LINES) != 1650:
        raise ValueError(f"companion comment corpus size drifted: {len(COMPANION_COMMENT_LINES)}")
    if sum(len(spec.pointer_offsets) for spec in COMPANION_COMMENT_LINES) != 1784:
        raise ValueError("companion comment pointer-alias count drifted")
    if len(COMPANION_ACTION_LABELS) != 31:
        raise ValueError(f"companion action corpus size drifted: {len(COMPANION_ACTION_LABELS)}")

    validate_companion_afk_source(raw)

    owned_pointers: set[int] = set()
    for spec in COMPANION_COMMENT_LINES:
        _validate_source_text(
            raw,
            owner="companion comment",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        expected_va = _source_va(spec.source_offset)
        for pointer_offset in spec.pointer_offsets:
            if pointer_offset in owned_pointers:
                raise ValueError(f"duplicate companion comment pointer owner: {pointer_offset:#x}")
            owned_pointers.add(pointer_offset)
            if pointer_offset < 0 or pointer_offset + 4 > len(raw):
                raise ValueError(f"companion comment pointer is outside executable: {pointer_offset:#x}")
            actual_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            if actual_va != expected_va:
                raise ValueError(
                    "companion comment pointer preimage mismatch: "
                    f"{pointer_offset:#x}: expected {expected_va:#x}, got {actual_va:#x}"
                )

    for expected_id, spec in enumerate(COMPANION_ACTION_LABELS):
        if spec.action_id != expected_id:
            raise ValueError(
                f"companion action table order drifted: expected {expected_id}, got {spec.action_id}"
            )
        _validate_source_text(
            raw,
            owner="companion action",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        if spec.pointer_offset < 0 or spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"companion action pointer is outside executable: {spec.action_id}")
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        expected_va = _source_va(spec.source_offset)
        if actual_va != expected_va:
            raise ValueError(
                "companion action pointer preimage mismatch: "
                f"id={spec.action_id}, expected {expected_va:#x}, got {actual_va:#x}"
            )


def patch_companion_afk_layout(raw: bytes) -> bytes:
    """Validate AFK speech placement ownership and move the composition upward."""

    metadata_va, metadata_count = struct.unpack_from(
        "<II", raw, COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET
    )
    if (metadata_va, metadata_count) != (
        COMPANION_AFK_PANEL_METADATA_VA,
        COMPANION_AFK_PANEL_FRAME_COUNT,
    ):
        raise ValueError(
            "companion AFK panel resource-table drifted: "
            f"expected ({COMPANION_AFK_PANEL_METADATA_VA:#010x}, "
            f"{COMPANION_AFK_PANEL_FRAME_COUNT}), got "
            f"({metadata_va:#010x}, {metadata_count})"
        )

    # The only structured group-2/resource-0x6A owners are the two AFK slot
    # placement records. This is intentionally stricter than scanning arbitrary
    # words for the integer 0x6A.
    owner_bytes = struct.pack("<II", 2, 0x6A)
    structured_owners = tuple(
        offset
        for offset in range(0, len(raw) - len(owner_bytes) + 1, 4)
        if raw[offset:offset + len(owner_bytes)] == owner_bytes
    )
    if structured_owners != COMPANION_AFK_PANEL_PLACEMENT_OFFSETS:
        raise ValueError(
            "companion AFK panel structured-owner drifted: "
            f"expected {[hex(x) for x in COMPANION_AFK_PANEL_PLACEMENT_OFFSETS]}, "
            f"got {[hex(x) for x in structured_owners]}"
        )

    for frame_index, expected in enumerate(COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES):
        frame_offset = (
            COMPANION_AFK_PANEL_METADATA_OFFSET
            + frame_index * COMPANION_AFK_PANEL_FRAME_STRIDE
        )
        actual = struct.unpack_from("<ffff", raw, frame_offset + 4)
        if actual != expected:
            raise ValueError(
                "companion AFK panel metadata drifted: "
                f"frame={frame_index}, expected {expected!r}, got {actual!r}"
            )

    placement_specs = (
        (
            COMPANION_AFK_GREEN_PLACEMENT_OFFSETS,
            COMPANION_AFK_GREEN_PRISTINE_PLACEMENTS,
            COMPANION_AFK_GREEN_TARGET_PLACEMENTS,
            "green",
        ),
        (
            COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
            COMPANION_AFK_PANEL_PRISTINE_PLACEMENTS,
            COMPANION_AFK_PANEL_TARGET_PLACEMENTS,
            "blue",
        ),
    )
    out = bytearray(raw)
    for offsets, pristine, targets, owner in placement_specs:
        for placement_offset, expected, replacement in zip(
            offsets, pristine, targets, strict=True
        ):
            actual = struct.unpack_from("<IIfff", raw, placement_offset)
            if actual != expected:
                raise ValueError(
                    f"companion AFK {owner} placement drifted: "
                    f"{placement_offset:#x}: expected {expected!r}, got {actual!r}"
                )
            struct.pack_into("<IIfff", out, placement_offset, *replacement)

    # r50 changes only the four structured placement records here. Geometry is
    # still runtime consumer-specific: AFK restores native-width blue/green
    # metadata, while the L1 path applies compact geometry immediately before
    # drawing its callout.
    return bytes(out)


def patch_companion_action_layout(raw: bytes) -> bytes:
    """Apply the static portion of the generic, slot-aware r38 companion-action layout."""

    expected_slot_positions = tuple(
        component for position in COMPANION_SLOT_POSITIONS for component in position
    )
    actual_slot_positions = struct.unpack_from("<ffff", raw, COMPANION_SLOT_POSITION_TABLE_OFFSET)
    if actual_slot_positions != expected_slot_positions:
        raise ValueError(
            "companion slot position table drifted: "
            f"expected {expected_slot_positions!r}, got {actual_slot_positions!r}"
        )

    for offset, expected in (*COMPANION_SLOT_INDEX_PREIMAGES, *COMPANION_ACTION_ID_REFERENCE_PREIMAGES):
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                "companion slot/action-id owner drifted: "
                f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
            )

    bubble_specs = (
        (
            COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
            COMPANION_ACTION_BUBBLE_METADATA_VA,
            (
                COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
            ),
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
        ),
        (
            COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
            COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
            (
                COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
            ),
            COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
        ),
    )
    for record_offset, expected_metadata_va, geometry_offsets, expected_geometry in bubble_specs:
        bubble_metadata_va, bubble_record_count = struct.unpack_from("<II", raw, record_offset)
        if (bubble_metadata_va, bubble_record_count) != (expected_metadata_va, 1):
            raise ValueError(
                "companion action bubble resource-table drifted: "
                f"{record_offset:#x}: expected ({expected_metadata_va:#010x}, 1), "
                f"got ({bubble_metadata_va:#010x}, {bubble_record_count})"
            )
        bubble_geometry = tuple(struct.unpack_from("<f", raw, offset)[0] for offset in geometry_offsets)
        if bubble_geometry != expected_geometry:
            raise ValueError(
                "companion action bubble geometry drifted: "
                f"{record_offset:#x}: expected {expected_geometry!r}, got {bubble_geometry!r}"
            )

    for owner, preimages in (
        ("runtime", COMPANION_ACTION_RUNTIME_PREIMAGES),
        ("visibility", COMPANION_ACTION_VISIBILITY_PREIMAGES),
    ):
        for offset, expected in preimages:
            if offset < 0 or offset + 4 > len(raw):
                raise ValueError(
                    f"companion action {owner} owner is outside executable: {offset:#x}"
                )
            actual = struct.unpack_from("<I", raw, offset)[0]
            if actual != expected:
                raise ValueError(
                    f"companion action {owner} preimage mismatch: "
                    f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
                )

    out = bytearray(raw)
    for offset, expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES:
        if offset < 0 or offset + 4 > len(out):
            raise ValueError(f"companion action layout owner is outside executable: {offset:#x}")
        actual = struct.unpack_from("<I", out, offset)[0]
        if actual != expected:
            raise ValueError(
                "companion action layout preimage mismatch: "
                f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
            )
        struct.pack_into("<I", out, offset, replacement)

    # r47 leaves the shared 0x68/0x69 metadata pristine in the static ELF.
    # AFK therefore starts from its native 288x80 outer bubble. The normal L1
    # runtime selector writes its complete compact geometry immediately before
    # constructing an action callout, eliminating the global-resource conflict.
    return bytes(out)


def finalize_companion_action_runtime_layout(
    result: bytearray,
    installed: ExecutableTextResult,
) -> None:
    """Bind the r37 per-action layout table and executable runtime hook."""

    try:
        table_va = installed.target_vas[COMPANION_ACTION_LAYOUT_TABLE_KEY]
        state_va = installed.target_vas[COMPANION_ACTION_RUNTIME_STATE_KEY]
        hook_va = installed.target_vas[COMPANION_ACTION_RUNTIME_HOOK_KEY]
        visibility_hook_va = installed.target_vas[COMPANION_ACTION_VISIBILITY_HOOK_KEY]
        scale_table_va = installed.target_vas[COMPANION_AFK_SCALE_TABLE_KEY]
        scale_hook_va = installed.target_vas[COMPANION_AFK_SCALE_HOOK_KEY]
        afk_geometry_hook_va = installed.target_vas[COMPANION_AFK_GEOMETRY_HOOK_KEY]
        afk_wrap_table_va = installed.target_vas[COMPANION_AFK_WRAP_LAYOUT_TABLE_KEY]
        afk_wrap_geometry_hook_va = installed.target_vas[COMPANION_AFK_WRAP_GEOMETRY_HOOK_KEY]
        afk_wrap_text_hook_va = installed.target_vas[COMPANION_AFK_WRAP_TEXT_HOOK_KEY]
        afk_r50_geometry_hook_va = installed.target_vas[COMPANION_AFK_R50_GEOMETRY_HOOK_KEY]
        afk_r52_pretext_hook_va = installed.target_vas[COMPANION_AFK_R52_PRETEXT_HOOK_KEY]
        blue_create_va = installed.target_vas[COMPANION_ACTION_R53_BLUE_CREATE_KEY]
        blue_show_va = installed.target_vas[COMPANION_ACTION_R53_SHOW_KEY]
        blue_hide_va = installed.target_vas[COMPANION_ACTION_R53_HIDE_KEY]
        action_geometry_extension_va = installed.target_vas[
            COMPANION_ACTION_GEOMETRY_EXTENSION_KEY
        ]
        action_r50_panel_extension_va = installed.target_vas[
            COMPANION_ACTION_R50_PANEL_EXTENSION_KEY
        ]
    except KeyError as exc:
        raise ValueError(f"companion action runtime payload is missing: {exc.args[0]}") from exc

    runtime_vas = (
        table_va,
        state_va,
        hook_va,
        visibility_hook_va,
        scale_table_va,
        scale_hook_va,
        afk_geometry_hook_va,
        afk_wrap_table_va,
        afk_wrap_geometry_hook_va,
        afk_wrap_text_hook_va,
        afk_r50_geometry_hook_va,
        afk_r52_pretext_hook_va,
        blue_create_va,
        blue_show_va,
        blue_hide_va,
        action_geometry_extension_va,
        action_r50_panel_extension_va,
    )
    if any(value & 3 for value in runtime_vas):
        raise ValueError(
            "companion runtime payload lost word alignment: "
            + ", ".join(f"{value:#x}" for value in runtime_vas)
        )

    hook = _runtime_hook_bytes(
        table_va=table_va,
        state_va=state_va,
        geometry_extension_va=action_r50_panel_extension_va,
    )
    hook_file = installed.info.file_offset + (hook_va - installed.info.segment_vaddr)
    if hook_file < 0 or hook_file + len(hook) > len(result):
        raise ValueError("companion action runtime hook is outside translated executable")
    if result[hook_file:hook_file + len(hook)] != b"\x00" * len(hook):
        raise ValueError("companion action runtime hook placeholder drifted")
    result[hook_file:hook_file + len(hook)] = hook

    visibility_hook = _visibility_hook_bytes()
    visibility_hook_file = installed.info.file_offset + (
        visibility_hook_va - installed.info.segment_vaddr
    )
    if (
        visibility_hook_file < 0
        or visibility_hook_file + len(visibility_hook) > len(result)
    ):
        raise ValueError("companion action visibility hook is outside translated executable")
    if (
        result[visibility_hook_file:visibility_hook_file + len(visibility_hook)]
        != b"\x00" * len(visibility_hook)
    ):
        raise ValueError("companion action visibility hook placeholder drifted")
    result[visibility_hook_file:visibility_hook_file + len(visibility_hook)] = visibility_hook

    runtime_payloads = (
        (
            action_geometry_extension_va,
            _action_geometry_extension_bytes(),
            "companion action geometry extension",
        ),
        (
            scale_hook_va,
            _afk_scale_hook_bytes(table_va=scale_table_va),
            "companion AFK scale hook",
        ),
        (
            afk_geometry_hook_va,
            _afk_geometry_hook_bytes(),
            "companion AFK native-geometry hook",
        ),
        (
            afk_wrap_geometry_hook_va,
            _afk_wrap_geometry_hook_bytes(table_va=afk_wrap_table_va),
            "companion AFK wrap geometry hook",
        ),
        (
            afk_wrap_text_hook_va,
            _afk_wrap_text_hook_bytes(table_va=afk_wrap_table_va),
            "companion AFK wrap text hook",
        ),
        (
            afk_r50_geometry_hook_va,
            _afk_r50_geometry_hook_bytes(table_va=afk_wrap_table_va),
            "companion AFK r50 geometry hook",
        ),
        (
            action_r50_panel_extension_va,
            _action_r50_panel_extension_bytes(),
            "companion action r50 panel extension",
        ),
        (
            afk_r52_pretext_hook_va,
            _afk_r52_pretext_hook_bytes(table_va=afk_wrap_table_va),
            "companion AFK r53 preserved-text-args Y and stack spill",
        ),
        (blue_create_va, _action_r53_blue_create_bytes(), "L1 r53 blue constructor"),
        (blue_show_va, _action_r53_blue_alpha_bytes(visible=True), "L1 r53 blue show"),
        (blue_hide_va, _action_r53_blue_alpha_bytes(visible=False), "L1 r53 blue hide"),
    )
    for payload_va, payload, owner in runtime_payloads:
        payload_file = installed.info.file_offset + (
            payload_va - installed.info.segment_vaddr
        )
        if payload_file < 0 or payload_file + len(payload) > len(result):
            raise ValueError(f"{owner} is outside translated executable")
        if result[payload_file:payload_file + len(payload)] != b"\x00" * len(payload):
            raise ValueError(f"{owner} placeholder drifted")
        result[payload_file:payload_file + len(payload)] = payload

    for owner, preimages in (
        ("runtime", COMPANION_ACTION_RUNTIME_PREIMAGES),
        ("visibility", COMPANION_ACTION_VISIBILITY_PREIMAGES),
        ("AFK geometry", COMPANION_AFK_GEOMETRY_PREIMAGES),
        ("AFK alpha", COMPANION_AFK_ALPHA_PREIMAGES),
        ("AFK scale", COMPANION_AFK_SCALE_PREIMAGES),
        ("AFK r52 pretext", COMPANION_AFK_R52_PRETEXT_PREIMAGES),
        ("L1 r53 blue", COMPANION_ACTION_R53_BLUE_PREIMAGES),
    ):
        for offset, expected in preimages:
            actual = struct.unpack_from("<I", result, offset)[0]
            if actual != expected:
                raise ValueError(
                    f"companion action {owner} finalizer preimage mismatch: "
                    f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
                )

    # r50 owns AFK geometry per record and slot. Width remains native 288px;
    # height follows the 32px multiline budget and blue pivot-X now follows the
    # speaking slot. Preserve the original sll v1,v0,7 in the JAL delay slot.
    struct.pack_into("<I", result, 0x66050, _jal_word(afk_r50_geometry_hook_va))

    # r52 supplies record Y through BOTH f13 and the native stack argument.
    # r51 did not update sp+0x1a4 and independently created a persistent blue
    # sprite; neither r51 L1 callsite nor its destructor change is retained.
    struct.pack_into("<I", result, 0x66250, _jal_word(afk_r52_pretext_hook_va))
    struct.pack_into("<I", result, 0x66320, _jal_word(afk_r52_pretext_hook_va))

    # r53 blue is a sibling L1 object, not a permanent independent overlay.
    # Both cleanup paths must use the sprite destructor, and all three native
    # vertex-alpha animation loops must update it whenever green changes.
    for site in (0x66668, 0x66DD4):
        struct.pack_into("<I", result, site, _jal_word(0x00108650))
    struct.pack_into("<I", result, 0x66740, _jal_word(blue_create_va))
    struct.pack_into("<I", result, 0x66744, 0x3C024371)
    struct.pack_into("<I", result, COMPANION_ACTION_R53_SHOW_SITE, _jal_word(blue_show_va))
    for site in COMPANION_ACTION_R53_HIDE_SITES:
        struct.pack_into("<I", result, site, _jal_word(blue_hide_va))

    # Keep constructor alpha at native 1.0. After each AFK text object is
    # created, place it at the record-specific Y and force horizontal scale to
    # 1.0; wrapping rather than squeezing now guarantees the fixed-width bound.
    struct.pack_into("<I", result, 0x66284, _jal_word(afk_wrap_text_hook_va))
    struct.pack_into("<I", result, 0x66288, 0xAE020028)  # sw v0,0x28(s0)
    struct.pack_into("<I", result, 0x66354, _jal_word(afk_wrap_text_hook_va))
    struct.pack_into("<I", result, 0x66358, 0xAE02002C)  # sw v0,0x2c(s0)

    # Use the existing "skip complete L1 callout" branch, but compute its guard
    # from H_TalkBuddyTask's own state. The JAL occupies the old guard load,
    # 0x666C0 is its delay-slot NOP, and the original branch moves one word
    # later while preserving the same 0x166814 target.
    struct.pack_into("<I", result, 0x666BC, _jal_word(visibility_hook_va))
    struct.pack_into("<I", result, 0x666C0, 0x00000000)
    struct.pack_into("<I", result, 0x666C4, _mips_i(0x04, 2, 0, 0x73))

    # Replace the fixed group-2 resource selection with a call into the generic
    # layout selector. Keep li a0,2 in the JAL delay slot.
    struct.pack_into("<I", result, 0x66724, _jal_word(hook_va))
    struct.pack_into("<I", result, 0x66728, 0x24040002)

    # The selector stores slot-aware text-X and per-action text-Y floats in
    # relocated RWX state. Replace both old immediate-float constructions with
    # direct loads; the pristine add.s owners remain untouched.
    state_hi, state_lo = _split_address(state_va)
    struct.pack_into("<I", result, 0x66804, _mips_i(0x0F, 0, 2, state_hi))
    struct.pack_into("<I", result, 0x66808, _mips_i(0x31, 2, 0, state_lo))
    struct.pack_into("<I", result, 0x6680C, 0x00000000)
    struct.pack_into("<I", result, 0x6681C, _mips_i(0x0F, 0, 2, state_hi))
    struct.pack_into("<I", result, 0x66820, _mips_i(0x31, 2, 0, state_lo + 4))
    struct.pack_into("<I", result, 0x66824, 0x00000000)
    # 0x66810 and 0x66828 remain the pristine add.s f0,f1,f0.


def relocated_companion_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    """Return translated companion text plus generic action-layout runtime data.

    Transient comments remain exact CUSA27034 English.bytes matches. Action
    labels preserve their official/remaster-first wording but are word-wrapped
    algorithmically at 17 12px cells per line. Literal 0x0A is the game's
    existing multiline control byte; no per-action layout special cases exist.
    """

    validate_companion_hud_source(raw)
    entries = [
        RelocatedText(
            key=f"companion_comment_{spec.source_offset:06x}",
            encoded=encode_ps2_english(spec.display_english, collapse_spaces=False) + b"\x00",
            pointer_offsets=spec.pointer_offsets,
        )
        for spec in COMPANION_COMMENT_LINES
    ]
    entries.extend(
        RelocatedText(
            key=f"companion_action_{spec.action_id:02d}",
            encoded=encode_companion_action(spec.english),
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in COMPANION_ACTION_LABELS
        if spec.english is not None
    )

    # These data/code owners have no external pointer aliases. Four-byte
    # alignment is explicit because the runtime selector consumes them as words.
    entries.extend(
        (
            RelocatedText(
                key=COMPANION_ACTION_LAYOUT_TABLE_KEY,
                encoded=_layout_table_bytes(),
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_ACTION_RUNTIME_STATE_KEY,
                encoded=struct.pack(
                    "<ff",
                    COMPANION_ACTION_SLOT_TEXT_X[0],
                    COMPANION_ACTION_LAYOUTS[0].text_y,
                ),
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_ACTION_RUNTIME_HOOK_KEY,
                encoded=b"\x00" * COMPANION_ACTION_RUNTIME_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
        )
    )
    # Keep all r43 translation payload VAs stable: append the Re:charge-only
    # AFK strings first, then add the r44-only visibility predicate at the end.
    entries.extend(_relocated_companion_afk_entries(raw))
    entries.append(
        RelocatedText(
            key=COMPANION_ACTION_VISIBILITY_HOOK_KEY,
            encoded=b"\x00" * COMPANION_ACTION_VISIBILITY_HOOK_SIZE,
            pointer_offsets=(),
            alignment=4,
        )
    )
    # r47 extras append strictly after every r46 owner so all prior translated
    # addresses remain stable.
    entries.extend(
        (
            RelocatedText(
                key=COMPANION_AFK_SCALE_TABLE_KEY,
                encoded=_afk_scale_table_bytes(),
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_AFK_SCALE_HOOK_KEY,
                encoded=b"\x00" * COMPANION_AFK_SCALE_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_AFK_GEOMETRY_HOOK_KEY,
                encoded=b"\x00" * COMPANION_AFK_GEOMETRY_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_ACTION_GEOMETRY_EXTENSION_KEY,
                encoded=b"\x00" * COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
        )
    )
    # r49 appends its multiline layout strictly after every r48 payload. The
    # wrapped AFK strings preserve their old allocation sizes for the current
    # corpus, so all historical target VAs above remain stable.
    entries.extend(
        (
            RelocatedText(
                key=COMPANION_AFK_WRAP_LAYOUT_TABLE_KEY,
                encoded=_afk_wrap_layout_table_bytes(),
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_AFK_WRAP_GEOMETRY_HOOK_KEY,
                encoded=b"\x00" * COMPANION_AFK_WRAP_GEOMETRY_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_AFK_WRAP_TEXT_HOOK_KEY,
                encoded=b"\x00" * COMPANION_AFK_WRAP_TEXT_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
        )
    )
    # r50 remains append-only relative to r49. These complete consumer-specific
    # geometry helpers replace only runtime call targets; every historical
    # translated payload keeps its r49 VA.
    entries.extend(
        (
            RelocatedText(
                key=COMPANION_AFK_R50_GEOMETRY_HOOK_KEY,
                encoded=b"\x00" * COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
            RelocatedText(
                key=COMPANION_ACTION_R50_PANEL_EXTENSION_KEY,
                encoded=b"\x00" * COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE,
                pointer_offsets=(),
                alignment=4,
            ),
        )
    )
    # r52 is append-only after the complete r50 payload. Never instantiate
    # L1 resource 0x6A until its native visibility owner has been proven.
    entries.append(
        RelocatedText(
            key=COMPANION_AFK_R52_PRETEXT_HOOK_KEY,
            encoded=b"\x00" * COMPANION_AFK_R52_PRETEXT_HOOK_SIZE,
            pointer_offsets=(),
            alignment=4,
        )
    )
    # r53 adds only sibling creation/opacity helpers. Existing translations,
    # r50 geometry and the r52 AFK helper VA remain stable.
    entries.extend(
        RelocatedText(key=key, encoded=b"\x00" * size, pointer_offsets=(), alignment=4)
        for key, size in (
            (COMPANION_ACTION_R53_BLUE_CREATE_KEY, COMPANION_ACTION_R53_BLUE_CREATE_SIZE),
            (COMPANION_ACTION_R53_SHOW_KEY, COMPANION_ACTION_R53_ALPHA_HOOK_SIZE),
            (COMPANION_ACTION_R53_HIDE_KEY, COMPANION_ACTION_R53_ALPHA_HOOK_SIZE),
        )
    )
    return tuple(entries)
