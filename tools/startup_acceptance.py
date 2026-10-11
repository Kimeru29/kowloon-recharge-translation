from __future__ import annotations

import struct
from typing import Any
from hashlib import sha256

from tools.adv_layout import ADV_DG_LAYOUT_PATCHES, ADV_SPEAKER_LAYOUT_PATCHES
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells
from tools.hant_dictionary_definitions import DICTIONARY_DEFINITION_MAX_CELLS, definition_source_fingerprint
from tools.hant_ui import (
    HANT_ALL_HELP_TOPICS,
    HANT_CHROME_LABELS,
    HANT_CONFIG_LABELS,
    HANT_CONTENT_LABELS,
    HANT_DICTIONARY_DEFINITIONS,
    HANT_DICTIONARY_TABS,
    HANT_DICTIONARY_TERMS,
    HANT_HELP_BODIES,
    HANT_MAIL_COUNT_LABEL,
    HANT_RUNTIME_LAYOUT_PATCHES,
    HANT_RINGTONES,
    HANT_HELP_CATEGORY_LABELS,
    HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,
    HANT_CONTROLLER_METADATA_OFFSET,
    HANT_CONTROLLER_METADATA_RECORDS,
    HANT_POINTER_TABLE_OFFSET,
    HANT_PRISTINE_CONTROLLER_METADATA_RECORDS,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_TUTORIAL_FONT_STYLE_OFFSET,
    HANT_TUTORIAL_SINGLETON_STYLE_OFFSET,
    HANT_TUTORIAL_SINGLETON_STYLE_PRISTINE_WORD,
    HANT_TUTORIAL_ROW_SPACING_OFFSET,
    HANT_WRAPPED_LINES,
)
from tools.localization import encode_ps2_english
from tools.companion_afk_data import COMPANION_AFK_TRANSLATIONS
from tools.companion_hud import (
    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_BUBBLE_METADATA_VA,
    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT_RESOURCES,
    COMPANION_ACTION_SLOT_TEXT_X,
    COMPANION_ACTION_ID_GETTER_VA,
    COMPANION_ACTION_ID_KEY,
    COMPANION_ACTION_ID_REFERENCE_PREIMAGES,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUTS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_HOOK_SIZE,
    COMPANION_ACTION_RUNTIME_PATCH_OFFSETS,
    COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE,
    COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE,
    COMPANION_ACTION_VISIBILITY_HOOK_SIZE,
    COMPANION_ACTION_VISIBILITY_PATCH_OFFSETS,
    COMPANION_AFK_PANEL_FRAME_COUNT,
    COMPANION_AFK_PANEL_FRAME_STRIDE,
    COMPANION_AFK_PANEL_METADATA_OFFSET,
    COMPANION_AFK_PANEL_METADATA_VA,
    COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
    COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET,
    COMPANION_AFK_PANEL_TARGET_GEOMETRIES,
    COMPANION_AFK_PANEL_TARGET_PLACEMENTS,
    COMPANION_AFK_GREEN_PLACEMENT_OFFSETS,
    COMPANION_AFK_GREEN_TARGET_PLACEMENTS,
    COMPANION_AFK_EMPTY_VA,
    COMPANION_AFK_EXPECTED_LIVE_FIELDS,
    COMPANION_AFK_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_SCALE_HOOK_SIZE,
    COMPANION_AFK_TEXT_SAFE_CELLS,
    COMPANION_AFK_TEXT_SCALES,
    COMPANION_AFK_LAYOUTS,
    COMPANION_AFK_WRAP_CELLS,
    COMPANION_AFK_LINE_STEP,
    COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION,
    COMPANION_AFK_GREEN_BASE_HEIGHT,
    COMPANION_AFK_GREEN_BASE_PIVOT_Y,
    COMPANION_AFK_BLUE_BASE_HEIGHT,
    COMPANION_AFK_R55_MULTILINE_BLUE_BOTTOM_TRIM,
    COMPANION_AFK_R57_FOUR_ROW_EXTRA_BOTTOM_TRIM,
    COMPANION_AFK_R59_FOUR_ROW_BLUE_BOTTOM_TRIM,
    COMPANION_AFK_R59_FOUR_ROW_TEXT_TOP_PADDING,
    COMPANION_AFK_ANCHOR_Y,
    COMPANION_ACTION_R59_BLUE_RESOURCE_ID,
    COMPANION_ACTION_R59_BLUE_METADATA_VA,
    COMPANION_ACTION_R59_BLUE_FRAME_STRIDE,
    COMPANION_ACTION_R59_BLUE_PRISTINE,
    COMPANION_AFK_R56_SECOND_OBJECT_GAP_CORRECTION,
    COMPANION_AFK_BLUE_BASE_PIVOT_Y,
    COMPANION_AFK_TEXT1_BASE_Y,
    COMPANION_AFK_WRAP_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_WRAP_TEXT_HOOK_SIZE,
    COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_R52_PRETEXT_HOOK_SIZE,
    COMPANION_ACTION_R53_BLUE_CREATE_SIZE,
    COMPANION_ACTION_R53_ALPHA_HOOK_SIZE,
    COMPANION_ACTION_R53_SHOW_SITE,
    COMPANION_ACTION_R53_HIDE_SITES,
    _afk_r52_pretext_hook_bytes,
    _action_r53_blue_create_bytes,
    _action_r53_blue_alpha_bytes,
    COMPANION_ACTION_R60_PRECONSTRUCT_SIZE,
    COMPANION_ACTION_R60_NATIVE_CONSTRUCTOR_RETURN_VA,
    _action_r60_preconstruct_bytes,
    _action_r62_inset_layout_table_bytes,
    COMPANION_ACTION_R62_INSET_X,
    COMPANION_ACTION_R62_INSET_TOP,
    COMPANION_ACTION_R62_INSET_BOTTOM,
    COMPANION_ACTION_R62_INSET_WIDTH,
    COMPANION_ACTION_R61_LIVE_OFFSET_SIZE,
    COMPANION_ACTION_R61_BLUE_SHIFT_X,
    COMPANION_ACTION_R61_BLUE_SHIFT_Y,
    _action_r61_live_blue_xy_bytes,
    COMPANION_ACTION_R58_POSITION_SIZE,
    COMPANION_AFK_R58_RESTORE_SIZE,
    COMPANION_ACTION_R58_PLACEMENT_X_VA,
    _action_r58_blue_placement_bytes,
    _afk_r58_restore_placement_bytes,
    COMPANION_AFK_RECORD_COUNT,
    COMPANION_AFK_RECORD_STRIDE,
    COMPANION_AFK_RECORDS_PER_COMPANION,
    COMPANION_AFK_TABLE_OFFSET,
    COMPANION_SLOT_INDEX_PREIMAGES,
    COMPANION_SLOT_POSITIONS,
    COMPANION_SLOT_POSITION_TABLE_OFFSET,
    COMPANION_COMMENT_LINES,
    encode_companion_action,
    encode_companion_afk_text,
    wrap_companion_afk_text,
)
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.menu_ui import MENU_LABELS
from tools.memory_card_ui import (
    MEMORY_CARD_MESSAGES,
    MEMORY_CARD_POINTER_ALIASES,
    MEMORY_CARD_POINTER_TABLE_OFFSET,
    encode_memory_card_english,
)
from tools.startup_ui import (
    KEYBOARD_ROW_PATCHES,
    NAME_CONFIRMATION_FOCUS_PATCHES,
    NAME_DEFAULT_POINTER_OFFSETS,
    NAME_PROMPT_LAYOUT_PATCHES,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_RUNTIME_POINTER_OFFSETS,
    NAME_FLOW_STATE9_FLAG_OFFSET,
    TITLE_LOAD_POINTER_OFFSET,
    TITLE_LOAD_START,
    TITLE_NEW_GAME_START,
    TITLE_POINTER_TABLE_OFFSET,
)
from tools.title_layout import TITLE_LABEL_BACKING_PATCHES

STARTUP_GRAPHICS_PATHS: tuple[str, ...] = (
    "BLBRD/B_GP019.BIN",
    "BLBRD/B_GP020.BIN",
    "BLBRD/B_GP088.BIN",
    *(f"BLBRD/INIT_MES/TR{index:03d}.TMX" for index in range(29)),
)

_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_SECOND_PH_OFFSET = 0x54
_TRANSLATION_VADDR = 0x00902F00
_RUNTIME_HEAP_BREAK_OFFSET = 0x650014
_EXPECTED_RUNTIME_HEAP_START = 0x00A02F00
_VISIBLE_PROMPT_INDICES = tuple(range(len(NAME_PROMPT_TEXTS)))
_HANT_POINTER_TABLE_SHA256 = "2282baed9b810c5dc9de2ea6a57bb7e8308154279f2efe9b57ea5b3d761205a0"
_HANT_BLANK_VA = 0x00795FB8
_HANT_EOF_VA = 0x00795FBC
# Task-6 unresolved H.A.N.T. candidates. 0x3BC7E8 is cross-owned by the
# separately proven main-menu fixed patch, so its pointer is pinned here while
# its source bytes are intentionally allowed to change under that owner.
_HANT_UNRESOLVED_SIGNATURES: tuple[tuple[int, tuple[int, ...], str | None], ...] = (
    (0x3BC7E8, (0x3BC8C4,), None),
    (0x575240, (0x694C10,), "　の情報を\n\nＨ．Ａ．Ｎ．Ｔに記録しました。\n"),
    (0x5860F0, (0x586374,), "　　　Ｈ．Ａ．Ｎ．Ｔ（Ｈｕｎｔｅｒ"),
    (0x588410, (0x58856C,), "Ｈ．Ａ．Ｎ．Ｔ"),
    (0x5975F0, (0x597678, 0x5A3958), "このＨ．Ａ．Ｎ．Ｔに転送される。"),
    (0x599390, (0x5994BC,), "ルを貴方のＨ．Ａ．Ｎ．Ｔに転送するサービ"),
    (
        0x5A2E00,
        (
            0x5A2E74, 0x5A2EB4, 0x5A2EF4, 0x5A2F34, 0x5A2F74,
            0x5A2FB4, 0x5A2FF4, 0x5A3034, 0x5A3074, 0x5A30B4,
            0x5A30F4, 0x5A3634, 0x5A3674, 0x5A36B4, 0x5A36F4,
            0x5A3734, 0x5A3774, 0x5A37B4, 0x5A37F4, 0x5A3834,
        ),
        "自動的に、このＨ．Ａ．Ｎ．Ｔに",
    ),
    (0x5B70A0, (0x5B7140,), "●Ｈ．Ａ．Ｎ．Ｔ（ハント）"),
    (0x5BD200, (0x5BD2F4,), "　各地に支部があり、『Ｈ．Ａ．Ｎ．Ｔ』の"),
)


def _check(name: str, ok: bool, detail: str | None = None) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": None if ok else detail}


def _main_va_to_file(va: int) -> int:
    return va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET


def _read_wide_at_va(raw: bytes, va: int, expected: str) -> bool:
    payload = encode_ps2_english(expected, collapse_spaces=False) + b"\x00"

    main_offset = _main_va_to_file(va)
    if 0 <= main_offset <= len(raw) - len(payload):
        if raw[main_offset:main_offset + len(payload)] == payload:
            return True

    segment = _translation_segment(raw)
    if segment is None:
        return False
    p_offset, p_vaddr, p_filesz, _p_memsz = segment
    relative = va - p_vaddr
    if relative < 0 or relative + len(payload) > p_filesz:
        return False
    target_file = p_offset + relative
    return raw[target_file:target_file + len(payload)] == payload


def _menu_source_slot(spec) -> bytes:
    encoded = spec.source_text.encode("cp932")
    return encoded + b"\x00" * (spec.capacity - len(encoded))


def _menu_source_va(spec) -> int:
    return _ELF_MAIN_VADDR + spec.source_offset - _ELF_MAIN_FILE_OFFSET


def _verify_menu_semantics(
    raw: bytes,
    segment: tuple[int, int, int, int] | None,
) -> tuple[bool, bool, bool]:
    fixed_ok = True
    relocated_ok = segment is not None
    pristine_ok = True

    for spec in MENU_LABELS:
        source_end = spec.source_offset + spec.capacity
        if source_end > len(raw):
            if spec.storage == "fixed-slot":
                fixed_ok = False
            elif spec.storage == "relocated":
                relocated_ok = False
            else:
                pristine_ok = False
            continue

        source_va = _menu_source_va(spec)
        aliases_in_bounds = all(offset + 4 <= len(raw) for offset in spec.pointer_offsets)

        if spec.storage == "fixed-slot":
            if spec.selected_english is None:
                fixed_ok = False
                continue
            replacement = spec.selected_english.encode("ascii")
            expected_slot = replacement + b"\x00" * (spec.capacity - len(replacement))
            aliases_ok = aliases_in_bounds and all(
                struct.unpack_from("<I", raw, offset)[0] == source_va
                for offset in spec.pointer_offsets
            )
            if raw[spec.source_offset:source_end] != expected_slot or not aliases_ok:
                fixed_ok = False
            continue

        if spec.storage == "relocated":
            if raw[spec.source_offset:source_end] != _menu_source_slot(spec):
                relocated_ok = False
                continue
            if spec.selected_english is None or not aliases_in_bounds or not spec.pointer_offsets:
                relocated_ok = False
                continue
            targets = {struct.unpack_from("<I", raw, offset)[0] for offset in spec.pointer_offsets}
            if len(targets) != 1 or segment is None:
                relocated_ok = False
                continue
            target_va = targets.pop()
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            expected = encode_ps2_english(spec.selected_english, collapse_spaces=False) + b"\x00"
            relative = target_va - p_vaddr
            if relative < 0 or relative + len(expected) > p_filesz:
                relocated_ok = False
                continue
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                relocated_ok = False
            continue

        aliases_ok = aliases_in_bounds and all(
            struct.unpack_from("<I", raw, offset)[0] == source_va
            for offset in spec.pointer_offsets
        )
        if raw[spec.source_offset:source_end] != _menu_source_slot(spec) or not aliases_ok:
            pristine_ok = False

    return fixed_ok, relocated_ok, pristine_ok


def _decode_lui_addiu_target(raw: bytes, lui_offset: int, addiu_offset: int) -> int | None:
    if lui_offset + 4 > len(raw) or addiu_offset + 4 > len(raw):
        return None
    lui_word = struct.unpack_from("<I", raw, lui_offset)[0]
    addiu_word = struct.unpack_from("<I", raw, addiu_offset)[0]
    if lui_word & 0xFFFF0000 != 0x3C060000 or addiu_word & 0xFFFF0000 != 0x24C60000:
        return None
    hi = lui_word & 0xFFFF
    lo = addiu_word & 0xFFFF
    signed_lo = lo if lo < 0x8000 else lo - 0x10000
    return ((hi << 16) + signed_lo) & 0xFFFFFFFF


def _segment_has_wide_text(
    raw: bytes,
    segment: tuple[int, int, int, int] | None,
    target_va: int,
    english: str,
) -> bool:
    if segment is None:
        return False
    p_offset, p_vaddr, p_filesz, _p_memsz = segment
    expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
    relative = target_va - p_vaddr
    if relative < 0 or relative + len(expected) > p_filesz:
        return False
    target_file = p_offset + relative
    return raw[target_file:target_file + len(expected)] == expected


def _verify_dungeon_semantics(
    raw: bytes,
    segment: tuple[int, int, int, int] | None,
) -> tuple[bool, bool]:
    action_ok = segment is not None
    for spec in DUNGEON_ACTION_LABELS:
        source = spec.source_text.encode("cp932") + b"\x00"
        if raw[spec.source_offset:spec.source_offset + len(source)] != source:
            action_ok = False
            break
        target_va = _decode_lui_addiu_target(
            raw,
            spec.code_reference.lui_offset,
            spec.code_reference.addiu_offset,
        )
        if target_va is None or not _segment_has_wide_text(raw, segment, target_va, spec.english):
            action_ok = False
            break

    item_ok = segment is not None and len(DUNGEON_ITEM_NAMES) == 446
    for spec in DUNGEON_ITEM_NAMES:
        if not item_ok:
            break
        source = spec.source_text.encode("cp932") + b"\x00"
        if raw[spec.source_offset:spec.source_offset + len(source)] != source:
            item_ok = False
            break
        if spec.pointer_offset + 4 > len(raw):
            item_ok = False
            break
        target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if not _segment_has_wide_text(raw, segment, target_va, spec.english):
            item_ok = False
            break

    return action_ok, item_ok


def _verify_companion_hud_semantics(
    raw: bytes,
    segment: tuple[int, int, int, int] | None,
) -> tuple[bool, bool]:
    comments_ok = segment is not None and len(COMPANION_COMMENT_LINES) == 1650
    for spec in COMPANION_COMMENT_LINES:
        if not comments_ok:
            break
        source = spec.source_text.encode("cp932") + b"\x00"
        if raw[spec.source_offset:spec.source_offset + len(source)] != source:
            comments_ok = False
            break
        for pointer_offset in spec.pointer_offsets:
            if pointer_offset + 4 > len(raw):
                comments_ok = False
                break
            target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            # Gameplay r67: this 22-cell story comment visibly exceeded its
            # native speech bubble. Keep the exact official PS4 wording valid
            # for r66, and accept only the 17-cell semantic compression in a
            # later candidate. AFK and L1 code/translation owners are frozen.
            allowed_texts = (spec.display_english,)
            if spec.source_offset == 0x3C1A50 and spec.display_english == "What an eerie place...":
                allowed_texts += ("An eerie place...", "Eerie place.", "  Eerie place.")
            if spec.source_offset == 0x3C1F38 and spec.display_english == "Good. The door should be":
                allowed_texts += ("Door's ready.",)
            if not any(
                _segment_has_wide_text(raw, segment, target_va, text)
                for text in allowed_texts
            ):
                comments_ok = False
                break

    actions_ok = segment is not None and len(COMPANION_ACTION_LABELS) == 31
    for spec in COMPANION_ACTION_LABELS:
        if not actions_ok:
            break
        source = spec.source_text.encode("cp932") + b"\x00"
        if raw[spec.source_offset:spec.source_offset + len(source)] != source:
            actions_ok = False
            break
        if spec.pointer_offset + 4 > len(raw):
            actions_ok = False
            break
        target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        if spec.english is None:
            source_va = _ELF_MAIN_VADDR + spec.source_offset - _ELF_MAIN_FILE_OFFSET
            if target_va != source_va:
                actions_ok = False
                break
        else:
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            relative = target_va - p_vaddr
            payload = encode_companion_action(spec.english)
            if relative < 0 or relative + len(payload) > p_filesz:
                actions_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(payload)] != payload:
                actions_ok = False
                break

    return comments_ok, actions_ok


def _verify_companion_afk_semantics(
    raw: bytes,
    segment: tuple[int, int, int, int] | None,
) -> bool:
    """Verify every translated Re:charge free-talk owner in the final ELF."""

    if segment is None or len(COMPANION_AFK_TRANSLATIONS) != COMPANION_AFK_RECORD_COUNT:
        return False

    live_fields = 0
    for record_index, (english_line1, english_line2) in enumerate(COMPANION_AFK_TRANSLATIONS):
        record_offset = COMPANION_AFK_TABLE_OFFSET + (
            record_index * COMPANION_AFK_RECORD_STRIDE
        )
        if record_offset + 16 > len(raw):
            return False
        enabled, companion_id, line1_va, line2_va = struct.unpack_from(
            "<IIII", raw, record_offset
        )
        expected_companion_id = (
            record_index // COMPANION_AFK_RECORDS_PER_COMPANION
        ) + 1
        if (enabled, companion_id) != (1, expected_companion_id):
            return False

        for target_va, english in (
            (line1_va, english_line1),
            (line2_va, english_line2),
        ):
            if not english:
                if target_va != COMPANION_AFK_EMPTY_VA:
                    return False
                continue
            if target_va == COMPANION_AFK_EMPTY_VA:
                return False
            live_fields += 1
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            payload = encode_companion_afk_text(english)
            relative = target_va - p_vaddr
            if relative < 0 or relative + len(payload) > p_filesz:
                return False
            target_file = p_offset + relative
            if raw[target_file:target_file + len(payload)] != payload:
                return False

    return live_fields == COMPANION_AFK_EXPECTED_LIVE_FIELDS


def _verify_companion_hud_layout(raw: bytes) -> bool:
    # r38 keeps the game's pristine 0/1 companion anchors but uses sibling
    # group-2 speech bubbles whose pivots place the body almost stationary while
    # the tail tracks the active slot.
    if COMPANION_SLOT_POSITION_TABLE_OFFSET + 16 > len(raw):
        return False
    expected_slot_positions = tuple(
        component for position in COMPANION_SLOT_POSITIONS for component in position
    )
    if struct.unpack_from("<ffff", raw, COMPANION_SLOT_POSITION_TABLE_OFFSET) != expected_slot_positions:
        return False
    if not all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == expected
        for offset, expected in (*COMPANION_SLOT_INDEX_PREIMAGES, *COMPANION_ACTION_ID_REFERENCE_PREIMAGES)
    ):
        return False

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
    for record_offset, metadata_va, offsets, geometry in bubble_specs:
        if record_offset + 8 > len(raw) or max(offsets) + 4 > len(raw):
            return False
        if struct.unpack_from("<II", raw, record_offset) != (metadata_va, 1):
            return False
        if tuple(struct.unpack_from("<f", raw, offset)[0] for offset in offsets) != geometry:
            return False

    # r46 preserves AFK's native blue 0x6A resource exactly after r45's
    # compacted geometry made that panel disappear at runtime. These checks are
    # validation-only: resource record, all three native animation frames and
    # both native slot placements must remain pristine.
    if (
        COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET + 8 > len(raw)
        or struct.unpack_from("<II", raw, COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET)
        != (COMPANION_AFK_PANEL_METADATA_VA, COMPANION_AFK_PANEL_FRAME_COUNT)
    ):
        return False
    for frame_index, target in enumerate(COMPANION_AFK_PANEL_TARGET_GEOMETRIES):
        frame_offset = (
            COMPANION_AFK_PANEL_METADATA_OFFSET
            + frame_index * COMPANION_AFK_PANEL_FRAME_STRIDE
        )
        if frame_offset + 0x14 > len(raw):
            return False
        if struct.unpack_from("<ffff", raw, frame_offset + 4) != target:
            return False
    for offsets, targets in (
        (COMPANION_AFK_GREEN_PLACEMENT_OFFSETS, COMPANION_AFK_GREEN_TARGET_PLACEMENTS),
        (COMPANION_AFK_PANEL_PLACEMENT_OFFSETS, COMPANION_AFK_PANEL_TARGET_PLACEMENTS),
    ):
        for placement_offset, target in zip(offsets, targets, strict=True):
            if placement_offset + 20 > len(raw):
                return False
            if struct.unpack_from("<IIfff", raw, placement_offset) != target:
                return False

    # Both resources are the proven sibling pair and produce only a 13px body
    # shift while the companion anchors themselves remain 58px apart.
    if COMPANION_ACTION_SLOT_RESOURCES != (0x68, 0x69):
        return False
    slot_body_left = (
        COMPANION_SLOT_POSITIONS[0][0] - COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY[2],
        COMPANION_SLOT_POSITIONS[1][0] - COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY[2],
    )
    slot_text_left = (
        COMPANION_SLOT_POSITIONS[0][0] + COMPANION_ACTION_SLOT_TEXT_X[0],
        COMPANION_SLOT_POSITIONS[1][0] + COMPANION_ACTION_SLOT_TEXT_X[1],
    )
    if slot_body_left[1] - slot_body_left[0] != 13.0 or slot_text_left[1] - slot_text_left[0] != 13.0:
        return False

    if not all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
        for offset, _expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES
    ):
        return False

    segment = _translation_segment(raw)
    if segment is None:
        return False
    p_offset, p_vaddr, p_filesz, _p_memsz = segment
    p_flags = struct.unpack_from("<I", raw, _SECOND_PH_OFFSET + 24)[0]
    if p_flags != 7:
        return False

    jal = struct.unpack_from("<I", raw, 0x66724)[0]
    if jal >> 26 != 0x03 or struct.unpack_from("<I", raw, 0x66728)[0] != 0x24040002:
        return False
    hook_va = (jal & 0x03FFFFFF) << 2
    hook_rel = hook_va - p_vaddr
    if hook_rel < 0 or hook_rel + COMPANION_ACTION_RUNTIME_HOOK_SIZE > p_filesz:
        return False
    hook_file = p_offset + hook_rel
    hook_words = struct.unpack_from(
        f"<{COMPANION_ACTION_RUNTIME_HOOK_SIZE // 4}I", raw, hook_file
    )
    getter_jal = 0x0C000000 | ((COMPANION_ACTION_ID_GETTER_VA >> 2) & 0x03FFFFFF)
    if (
        hook_words[0] != 0x27BDFFF0
        or hook_words[1] != 0xAFBF000C
        or hook_words[2] != (0x34040000 | COMPANION_ACTION_ID_KEY)
        or hook_words[3] != getter_jal
        or hook_words[4] != 0
        or hook_words[5] != 0x3042FFFF
        or hook_words[6] != (0x38420000 | COMPANION_ACTION_ID_KEY)
        or hook_words[7] != 0x2C43001F
        or 0x860D02D0 not in hook_words
        or hook_words[-6] != 0x25A50068
        or hook_words[-5] >> 26 != 0x02
        or hook_words[-4:] != (0, 0, 0, 0)
    ):
        return False

    action_geometry_va = (hook_words[-5] & 0x03FFFFFF) << 2
    action_geometry_rel = action_geometry_va - p_vaddr
    if (
        action_geometry_rel < 0
        or action_geometry_rel + COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE > p_filesz
    ):
        return False
    action_geometry_file = p_offset + action_geometry_rel
    if struct.unpack_from(
        f"<{COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE // 4}I",
        raw,
        action_geometry_file,
    ) != (
        0x000D7100, 0x000D7940, 0x01CF7021,
        0x3C0F0045, 0x25EF0AC4, 0x01EE7821,
        0x3C0E4360, 0xADEE0000,
        0x3C0E4250, 0x11A00002, 0x00000000,
        0x3C0E42C2, 0xADEE0008,
        0x3C0F0045, 0x25EF13F4, 0x3C0C4360,
        0, 0, 0, 0, 0, 0,  # late 0x78 blue writes retired by r62
        0, 0, 0, 0, 0, 0,
        0x8FBF000C, 0x27BD0010, 0x24040002,
        struct.unpack_from("<I", raw, action_geometry_file + 31*4)[0],
        0x00000000, 0x00000000,
    ):
        return False

    # r45 keeps the same whole-callout skip target, but binds it to the
    # task's native AFK-visible lifecycle: free-talk record >= 601 and state
    # 11..13 (constructed, visible, teardown). This replaces r44's indirect
    # render-handle inference.
    visibility_jal = struct.unpack_from("<I", raw, 0x666BC)[0]
    if (
        visibility_jal >> 26 != 0x03
        or struct.unpack_from("<I", raw, 0x666C0)[0] != 0
        or struct.unpack_from("<I", raw, 0x666C4)[0] != 0x10400073
    ):
        return False
    visibility_va = (visibility_jal & 0x03FFFFFF) << 2
    visibility_rel = visibility_va - p_vaddr
    if (
        visibility_rel < 0
        or visibility_rel + COMPANION_ACTION_VISIBILITY_HOOK_SIZE > p_filesz
    ):
        return False
    visibility_file = p_offset + visibility_rel
    visibility_words = struct.unpack_from(
        f"<{COMPANION_ACTION_VISIBILITY_HOOK_SIZE // 4}I",
        raw,
        visibility_file,
    )
    if visibility_words != (
        0x8E0202C8,
        0x1040000C,
        0x00000000,
        0x86080004,
        0x2D090259,
        0x15200008,
        0x00000000,
        0x86080002,
        0x2508FFF5,
        0x2D090003,
        0x11200003,
        0x00000000,
        0x00001021,
        0x00000000,
        0x03E00008,
        0x00000000,
        0x00000000,
        0x00000000,
        0x00000000,
    ):
        return False

    def _materialized_va(lui_word: int, low_word: int) -> int:
        hi = lui_word & 0xFFFF
        lo = low_word & 0xFFFF
        if lo & 0x8000:
            lo -= 0x10000
        return ((hi << 16) + lo) & 0xFFFFFFFF

    # r50 keeps AFK width fixed at 288 but makes the blue layer slot-aware.
    # Green and all three blue frames receive the same record-specific height
    # growth; both layers remain anchored in the safe L1 vertical band.
    afk_geometry_jal = struct.unpack_from("<I", raw, 0x66050)[0]
    if (
        afk_geometry_jal >> 26 != 0x03
        or struct.unpack_from("<I", raw, 0x66054)[0] != 0x000219C0
    ):
        return False
    afk_geometry_va = (afk_geometry_jal & 0x03FFFFFF) << 2
    afk_geometry_rel = afk_geometry_va - p_vaddr
    if (
        afk_geometry_rel < 0
        or afk_geometry_rel + COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE > p_filesz
    ):
        return False
    geometry_words = struct.unpack_from(
        f"<{COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE // 4}I",
        raw,
        p_offset + afk_geometry_rel,
    )
    if (
        geometry_words[:10] != (
            0x86020004, 0x2448FDA7, 0x2D090258, 0x1120002D, 0,
            0x860A02F8, 0x2D490002, 0x11200029, 0, 0x00085940,
        )
        or geometry_words[10] & 0xFFFF0000 != 0x3C0C0000
        or geometry_words[11] & 0xFFFF0000 != 0x258C0000
        or geometry_words[12:] != (
            0x018B6021, 0x000A6900, 0x000A7140, 0x01AE6821,
            0x3C0E0045, 0x25CE0AC4, 0x01CD7021,
            0x3C0F4390, 0xADCF0000,
            0x8D8F0000, 0xADCF0004,
            0x8D8F0004, 0xADCF000C,
            0x3C0F4286, 0x11400002, 0, 0x3C0F42FA, 0xADCF0008,
            0x3C0E0045, 0x25CE0B24,
            0x3C0D438D, 0xADCD0000, 0xADCD0030, 0xADCD0060,
            0x8D8D0008, 0xADCD0004, 0xADCD0034, 0xADCD0064,
            0xADCF0008, 0xADCF0038, 0xADCF0068,
            0x8D8D000C, 0xADCD000C,
            0x8D8D0010, 0xADCD003C,
            0x8D8D0014, 0xADCD006C,
            0x86020004, 0x000219C0, geometry_words[-2], 0,
        )
    ):
        return False
    afk_layout_table_va = _materialized_va(geometry_words[10], geometry_words[11])
    afk_layout_table_rel = afk_layout_table_va - p_vaddr
    expected_afk_layout_table = b"".join(
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
    if (
        afk_layout_table_rel < 0
        or afk_layout_table_rel + len(expected_afk_layout_table) > p_filesz
        or raw[
            p_offset + afk_layout_table_rel:
            p_offset + afk_layout_table_rel + len(expected_afk_layout_table)
        ] != expected_afk_layout_table
    ):
        return False

    # Constructor f16 is alpha, proven at runtime in r48; it remains exactly 1.0.
    for lui_offset, mtc1_offset in (
        (0x6621C, 0x66220),
        (0x6625C, 0x66260),
        (0x662EC, 0x662F0),
        (0x6632C, 0x66330),
    ):
        if (
            struct.unpack_from("<I", raw, lui_offset)[0] != 0x3C023F80
            or struct.unpack_from("<I", raw, mtc1_offset)[0] != 0x44828000
        ):
            return False

    # r49 text is never horizontally squeezed. The post-construction hook writes
    # 1.0 to object +0x48 and uses only object +0x18 for record-specific Y.
    text_jal_1 = struct.unpack_from("<I", raw, 0x66284)[0]
    text_jal_2 = struct.unpack_from("<I", raw, 0x66354)[0]
    if (
        text_jal_1 != text_jal_2
        or text_jal_1 >> 26 != 0x03
        or struct.unpack_from("<I", raw, 0x66288)[0] != 0xAE020028
        or struct.unpack_from("<I", raw, 0x6628C)[0] != 0x00022900
        or struct.unpack_from("<I", raw, 0x66358)[0] != 0xAE02002C
        or struct.unpack_from("<I", raw, 0x6635C)[0] != 0xA6020008
    ):
        return False
    text_hook_va = (text_jal_1 & 0x03FFFFFF) << 2
    text_hook_rel = text_hook_va - p_vaddr
    if text_hook_rel < 0 or text_hook_rel + COMPANION_AFK_WRAP_TEXT_HOOK_SIZE > p_filesz:
        return False
    text_words = struct.unpack_from(
        f"<{COMPANION_AFK_WRAP_TEXT_HOOK_SIZE // 4}I",
        raw,
        p_offset + text_hook_rel,
    )
    if (
        text_words[:11] != (
            0x00405821, 0x3C0F3F80, 0xAD6F0048,
            0x3C0E0016, 0x35CE620C,
            0x86080004, 0x2508FDA7, 0x2D090258, 0x1120000C, 0, 0x00084140,
        )
        or text_words[11] & 0xFFFF0000 != 0x3C090000
        or text_words[12] & 0xFFFF0000 != 0x25290000
        or text_words[13:] != (
            0x01284821, 0x17EE0004, 0,
            0x8D2A0018, 0x10000002, 0, 0x8D2A001C, 0xAD6A0018,
            0x17EE0004, 0x24020078, 0x8602000A, 0x03E00008, 0,
            0x03E00008, 0,
        )
        or _materialized_va(text_words[11], text_words[12]) != afk_layout_table_va
    ):
        return False


    # r53: constructor must preserve t0-t3. 0x1950A0 saves these live
    # arguments (particularly t1, the text pointer) before text conversion.
    # r51/r52 overwrote them and made AFK text disappear.
    pretext_jal_1 = struct.unpack_from("<I", raw, 0x66250)[0]
    pretext_jal_2 = struct.unpack_from("<I", raw, 0x66320)[0]
    if (
        pretext_jal_1 != pretext_jal_2
        or pretext_jal_1 >> 26 != 3
        or struct.unpack_from("<I", raw, 0x66254)[0] != 0x3C024375
        or struct.unpack_from("<I", raw, 0x66324)[0] != 0x3C024375
    ):
        return False
    pretext_va = (pretext_jal_1 & 0x03FFFFFF) << 2
    pretext_rel = pretext_va - p_vaddr
    if pretext_rel < 0 or pretext_rel + COMPANION_AFK_R52_PRETEXT_HOOK_SIZE > p_filesz:
        return False
    pretext_bytes = raw[
        p_offset + pretext_rel:p_offset + pretext_rel + COMPANION_AFK_R52_PRETEXT_HOOK_SIZE
    ]
    if (
        pretext_bytes != _afk_r52_pretext_hook_bytes(table_va=afk_layout_table_va)
        or struct.unpack_from("<I", pretext_bytes, 18 * 4)[0] != 0xE7AD01A4
    ):
        return False
    # Reject any regression that writes or destroys the special constructor
    # argument registers t0/t1/t2/t3 in this hook.
    for w in struct.unpack("<21I", pretext_bytes):
        op, rt, rd = w >> 26, (w >> 16) & 31, (w >> 11) & 31
        if op in (0x09, 0x0D, 0x0F, 0x21, 0x23) and 8 <= rt <= 11:
            return False
        if op == 0 and (w & 0x3F) in (0x00, 0x21) and 8 <= rd <= 11:
            return False

    # The r51 independent blue sprite was never faded or hidden with green.
    # r53 initializes all four vertex alphas to zero, mirrors the green
    # show/hide writes at the original three native sites and destroys the
    # resource on both L1 exit paths.
    if (
        any(struct.unpack_from("<I", raw, site)[0] != 0x0C06850C
            for site in (0x66668, 0x66DD4))
        or struct.unpack_from("<I", raw, 0x66744)[0] != 0x3C024371
        or 0x0C041F58 in struct.unpack_from("<39I", raw,
            p_offset + (((struct.unpack_from("<I", raw, 0x66740)[0]
                          & 0x03FFFFFF) << 2) - p_vaddr))
    ):
        return False
    create_site = struct.unpack_from("<I", raw, 0x66740)[0]
    if create_site >> 26 != 3:
        return False
    create_va = (create_site & 0x03FFFFFF) << 2
    scanner_file = p_offset + create_va - p_vaddr
    if scanner_file < 0 or scanner_file + COMPANION_ACTION_R53_BLUE_CREATE_SIZE > len(raw):
        return False
    scanner_tail = struct.unpack_from("<I", raw, scanner_file + 36*4)[0]
    if scanner_tail >> 26 != 2 or struct.unpack_from("<I", raw, scanner_file + 37*4)[0] != 0:
        return False
    preconstruct_va = (scanner_tail & 0x03FFFFFF) << 2
    preconstruct_file = p_offset + preconstruct_va - p_vaddr
    if (
        preconstruct_file < 0
        or preconstruct_file + COMPANION_ACTION_R60_PRECONSTRUCT_SIZE > p_offset + p_filesz
        or preconstruct_file + COMPANION_ACTION_R60_PRECONSTRUCT_SIZE > len(raw)
    ):
        return False
    # The accepted action layout table is already resolved later by r38's
    # independent full layout check. Resolve its own r38 hook for this gate.
    action_select = struct.unpack_from("<I", raw, 0x66724)[0]
    if action_select >> 26 != 3:
        return False
    selector_file = p_offset + (((action_select & 0x03FFFFFF) << 2) - p_vaddr)
    # Runtime-approved r66 action selector is now an immutable owner.
    # Without an independent snapshot, changing non-layout branch words can
    # silently pass the generated self-consistency checks below.
    if (
        selector_file < p_offset
        or selector_file + 188 > p_offset + p_filesz
        or sha256(raw[selector_file:selector_file + 188]).hexdigest()
        != "5703e08e842ffab5a8c4d2f65a094c9b19c94ebfbf9d624a9f90f7c70bc1ae97"
    ):
        return False
    select_hi, select_lo = struct.unpack_from("<2I", raw, selector_file + 14*4)
    action_table_va = ((select_hi & 0xFFFF) << 16) + (
        (select_lo & 0xFFFF) - (0x10000 if select_lo & 0x8000 else 0)
    )
    preconstruct_words = struct.unpack_from("<55I", raw, preconstruct_file)
    blue_table_va = ((preconstruct_words[18] & 0xFFFF) << 16) + (
        (preconstruct_words[19] & 0xFFFF) - (0x10000 if preconstruct_words[19] & 0x8000 else 0)
    )
    blue_table_off = p_offset + blue_table_va - p_vaddr
    expected_inset_table = _action_r62_inset_layout_table_bytes()
    if (
        action_table_va == blue_table_va
        or blue_table_off < p_offset
        or blue_table_off + len(expected_inset_table) > p_offset + p_filesz
        or raw[blue_table_off:blue_table_off+len(expected_inset_table)] != expected_inset_table
        or raw[preconstruct_file:preconstruct_file + COMPANION_ACTION_R60_PRECONSTRUCT_SIZE]
           != _action_r60_preconstruct_bytes(table_va=blue_table_va)
        or COMPANION_ACTION_R60_NATIVE_CONSTRUCTOR_RETURN_VA != 0x001666C8
        or COMPANION_ACTION_R62_INSET_X != -4.0
        or COMPANION_ACTION_R62_INSET_TOP != 0.0
        or COMPANION_ACTION_R62_INSET_BOTTOM != 6.0
        or COMPANION_ACTION_R62_INSET_WIDTH != 226.0
    ):
        return False
    for site, size, payload in (
        (0x66740, COMPANION_ACTION_R53_BLUE_CREATE_SIZE,
         _action_r53_blue_create_bytes(hook_va=create_va, preconstruct_va=preconstruct_va)),
        (COMPANION_ACTION_R53_SHOW_SITE, COMPANION_ACTION_R53_ALPHA_HOOK_SIZE,
         _action_r53_blue_alpha_bytes(visible=True, create_va=create_va)),
        *((site, COMPANION_ACTION_R53_ALPHA_HOOK_SIZE,
           _action_r53_blue_alpha_bytes(visible=False, create_va=create_va))
          for site in COMPANION_ACTION_R53_HIDE_SITES),
    ):
        jal = struct.unpack_from("<I", raw, site)[0]
        if jal >> 26 != 3:
            return False
        va = (jal & 0x03FFFFFF) << 2
        rel = va - p_vaddr
        if rel < 0 or rel + size > p_filesz:
            return False
        if raw[p_offset + rel:p_offset + rel + size] != payload:
            return False
        if site in (
            COMPANION_ACTION_R53_SHOW_SITE,
            *COMPANION_ACTION_R53_HIDE_SITES,
        ) and struct.unpack_from("<I", raw, site + 4)[0] != 0x8E0402DC:
            return False

    # r58: the native 0x6A compositor placement, NOT the pool object fields,
    # is changed during L1 and restored on the AFK construction path. Verify
    # both dynamic tail-call edges and every instruction of the two new hooks.
    def resolve_j(word: int) -> int:
        if word >> 26 != 2:
            return -1
        return (word & 0x03FFFFFF) << 2

    afk_geometry_site = struct.unpack_from("<I", raw, 0x66050)[0]
    if afk_geometry_site >> 26 != 3:
        return False
    afk_geometry_va = (afk_geometry_site & 0x03FFFFFF) << 2
    afk_geometry_file = p_offset + afk_geometry_va - p_vaddr
    afk_tail = struct.unpack_from("<I", raw, afk_geometry_file + COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE - 8)[0]
    afk_restore_va = resolve_j(afk_tail)

    action_runtime_site = struct.unpack_from("<I", raw, 0x66724)[0]
    if action_runtime_site >> 26 != 3:
        return False
    action_runtime_va = (action_runtime_site & 0x03FFFFFF) << 2
    action_runtime_file = p_offset + action_runtime_va - p_vaddr
    action_words = struct.unpack_from(f"<{COMPANION_ACTION_RUNTIME_HOOK_SIZE//4}I", raw, action_runtime_file)
    ext_candidates = [resolve_j(word) for word in action_words if word >> 26 == 2]
    if len(ext_candidates) != 1:
        return False
    action_ext_file = p_offset + ext_candidates[0] - p_vaddr
    action_ext_words = struct.unpack_from(
        f"<{COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE//4}I", raw, action_ext_file
    )
    action_placement_va = resolve_j(action_ext_words[-3])
    if (
        afk_restore_va < p_vaddr or action_placement_va < p_vaddr
        or afk_restore_va + COMPANION_AFK_R58_RESTORE_SIZE > p_vaddr + p_filesz
        or action_placement_va + COMPANION_ACTION_R58_POSITION_SIZE > p_vaddr + p_filesz
        or action_ext_words[-4] != 0x24040002  # li a0,2
        or struct.unpack_from("<I", raw, afk_geometry_file + COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE - 4)[0] != 0
    ):
        return False
    placement_file = p_offset + action_placement_va - p_vaddr
    placement_tail = struct.unpack_from("<I", raw, placement_file + 13*4)[0]
    if placement_tail != 0x03E00008 or struct.unpack_from("<I",raw,placement_file+14*4)[0] != 0:
        return False
    # r62: the r61 live XY patch has been retired, because it takes effect
    # AFTER native sprite construction and r61 screenshots showed no improvement.
    # The accepted preconstructor geometry is the sole active blue owner.
    if action_ext_words[16:28] != (0,) * 12:
        return False
    for va, expected in (
        (afk_restore_va, _afk_r58_restore_placement_bytes()),
        (action_placement_va, _action_r58_blue_placement_bytes(tail_va=0)),
    ):
        off = p_offset + va - p_vaddr
        if raw[off:off + len(expected)] != expected:
            return False

    # Complete-corpus generic invariant: every wrapped visual row is <=16 cells,
    # width never grows, and vertical growth preserves the native bottom anchors.
    if len(COMPANION_AFK_LAYOUTS) != COMPANION_AFK_RECORD_COUNT:
        return False
    for source_lines, layout in zip(
        COMPANION_AFK_TRANSLATIONS, COMPANION_AFK_LAYOUTS, strict=True
    ):
        rows = (*layout.line1_rows, *layout.line2_rows)
        if not rows or any(len(row) > COMPANION_AFK_WRAP_CELLS for row in rows):
            return False
        total_rows = len(rows)
        delta = COMPANION_AFK_LINE_STEP * max(0, total_rows - 2)
        if (
            layout.green_height != COMPANION_AFK_GREEN_BASE_HEIGHT + delta
            or layout.green_pivot_y != COMPANION_AFK_GREEN_BASE_PIVOT_Y + delta
            or layout.blue_height != (
                COMPANION_AFK_BLUE_BASE_HEIGHT + delta
                - (COMPANION_AFK_R55_MULTILINE_BLUE_BOTTOM_TRIM if total_rows > 2 else 0.0)
                - (COMPANION_AFK_R57_FOUR_ROW_EXTRA_BOTTOM_TRIM if total_rows >= 4 else 0.0)
                - (COMPANION_AFK_R59_FOUR_ROW_BLUE_BOTTOM_TRIM if total_rows >= 4 else 0.0)
            )
            or layout.text1_y != (
                COMPANION_AFK_ANCHOR_Y - layout.green_pivot_y
                + COMPANION_AFK_TEXT1_BASE_Y
                - (COMPANION_AFK_ANCHOR_Y - COMPANION_AFK_GREEN_BASE_PIVOT_Y)
                + (COMPANION_AFK_R59_FOUR_ROW_TEXT_TOP_PADDING if total_rows >= 4 else 0.0)
            )
            or layout.text2_y != (
                layout.text1_y
                + COMPANION_AFK_LINE_STEP * len(layout.line1_rows)
                - COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION
                * max(0, len(layout.line2_rows) - 1)
                - COMPANION_AFK_R56_SECOND_OBJECT_GAP_CORRECTION
                * max(0, len(layout.line1_rows) - 1)
                * int(bool(layout.line2_rows))
            )
            or layout.green_height - layout.green_pivot_y != 3.0
        ):
            return False
        for base, pivot in zip(
            COMPANION_AFK_BLUE_BASE_PIVOT_Y, layout.blue_pivot_y, strict=True
        ):
            if (
                pivot != base + delta
                or layout.blue_height - pivot != (
                    COMPANION_AFK_BLUE_BASE_HEIGHT - base
                    - (COMPANION_AFK_R55_MULTILINE_BLUE_BOTTOM_TRIM if total_rows > 2 else 0.0)
                    - (COMPANION_AFK_R57_FOUR_ROW_EXTRA_BOTTOM_TRIM if total_rows >= 4 else 0.0)
                    - (COMPANION_AFK_R59_FOUR_ROW_BLUE_BOTTOM_TRIM if total_rows >= 4 else 0.0)
                )
            ):
                return False
        for source in source_lines:
            if source and wrap_companion_afk_text(source) == ():
                return False

    table_va = _materialized_va(hook_words[14], hook_words[15])
    table_rel = table_va - p_vaddr
    expected_table = b"".join(
        struct.pack("<fff", layout.height, layout.pivot_y, layout.text_y)
        for layout in COMPANION_ACTION_LAYOUTS
    )
    if table_rel < 0 or table_rel + len(expected_table) > p_filesz:
        return False
    if raw[p_offset + table_rel:p_offset + table_rel + len(expected_table)] != expected_table:
        return False

    # r38 state is two floats: slot-aware text X, then per-action text Y.
    text_x_lui = struct.unpack_from("<I", raw, 0x66804)[0]
    text_x_lwc1 = struct.unpack_from("<I", raw, 0x66808)[0]
    text_y_lui = struct.unpack_from("<I", raw, 0x6681C)[0]
    text_y_lwc1 = struct.unpack_from("<I", raw, 0x66820)[0]
    if text_x_lui & 0xFFFF0000 != 0x3C020000 or text_x_lwc1 & 0xFFFF0000 != 0xC4400000:
        return False
    if text_y_lui & 0xFFFF0000 != 0x3C020000 or text_y_lwc1 & 0xFFFF0000 != 0xC4400000:
        return False
    state_va = _materialized_va(text_x_lui, text_x_lwc1)
    if _materialized_va(text_y_lui, text_y_lwc1) != state_va + 4:
        return False
    hook_state_va = _materialized_va(hook_words[33], hook_words[34])
    if hook_state_va != state_va:
        return False
    state_rel = state_va - p_vaddr
    if state_rel < 0 or state_rel + 8 > p_filesz:
        return False
    if struct.unpack_from("<ff", raw, p_offset + state_rel) != (
        COMPANION_ACTION_SLOT_TEXT_X[0],
        COMPANION_ACTION_LAYOUTS[0].text_y,
    ):
        return False
    if (
        struct.unpack_from("<I", raw, 0x6680C)[0] != 0
        or struct.unpack_from("<I", raw, 0x66810)[0] != 0x46000800
        or struct.unpack_from("<I", raw, 0x66824)[0] != 0
        or struct.unpack_from("<I", raw, 0x66828)[0] != 0x46000800
    ):
        return False

    return True


def _translation_segment(raw: bytes) -> tuple[int, int, int, int] | None:
    if len(raw) < _SECOND_PH_OFFSET + 32:
        return None
    p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, _p_align = struct.unpack_from(
        "<IIIIIIII", raw, _SECOND_PH_OFFSET
    )
    if (
        p_type != 1
        or p_vaddr != _TRANSLATION_VADDR
        or p_filesz <= 0
        or p_memsz < p_filesz
        or p_flags not in (6, 7)
        or p_offset + p_filesz > len(raw)
    ):
        return None
    return p_offset, p_vaddr, p_filesz, p_memsz


def verify_startup_elf(raw: bytes) -> list[dict[str, Any]]:
    """Verify translated startup renderer classes in a finished SLPM-66511 ELF.

    This intentionally checks runtime indirections rather than merely searching
    for English bytes.  It is usable both on the standalone translated ELF and
    the ELF extracted from the final ISO.
    """

    checks: list[dict[str, Any]] = []
    checks.append(_check("serial", b"SLPM-66511" in raw, "serial missing"))
    checks.append(_check("save_namespace", b"BISLPM-66511Save" in raw, "save namespace missing"))

    new_game = encode_ps2_english("New Game", collapse_spaces=False) + b"\x00"
    load_game = encode_ps2_english("Load Game", collapse_spaces=False) + b"\x00"
    checks.append(
        _check(
            "title_new_game",
            raw[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)] == new_game,
            "New Game wide text missing",
        )
    )
    checks.append(
        _check(
            "title_load_game",
            raw[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)] == load_game,
            "Load Game wide text missing",
        )
    )
    if len(raw) >= TITLE_POINTER_TABLE_OFFSET + 8:
        new_ptr, load_ptr = struct.unpack_from("<II", raw, TITLE_POINTER_TABLE_OFFSET)
        checks.append(
            _check(
                "title_new_pointer",
                new_ptr == _ELF_MAIN_VADDR + TITLE_NEW_GAME_START - _ELF_MAIN_FILE_OFFSET,
                f"unexpected New Game pointer {new_ptr:#x}",
            )
        )
        checks.append(
            _check(
                "title_load_pointer",
                load_ptr == _ELF_MAIN_VADDR + TITLE_LOAD_START - _ELF_MAIN_FILE_OFFSET,
                f"unexpected Load Game pointer {load_ptr:#x}",
            )
        )
    else:
        checks.extend((
            _check("title_new_pointer", False, "title pointer table outside ELF"),
            _check("title_load_pointer", False, "title pointer table outside ELF"),
        ))

    title_geometry_ok = False
    title_geometry_detail = "title English label/backing geometry or preservation invariants are missing/stale"
    if (
        len(raw) >= 0x6989C8
        and len(raw) >= 0x1AC604
        and len(raw) >= 0x1ABF88
        and len(raw) >= 0x3787C0
        and len(raw) >= 0x5CBFB4
        and len(raw) >= TITLE_POINTER_TABLE_OFFSET + 8
    ):
        new_ptr, load_ptr = struct.unpack_from("<II", raw, TITLE_POINTER_TABLE_OFFSET)
        new_anchor_word = struct.unpack_from("<I", raw, 0x1ABF64)[0]
        load_anchor_word = struct.unpack_from("<I", raw, 0x1ABF84)[0]
        backing_words = tuple(struct.unpack_from("<I", raw, offset)[0] for offset, _, _ in TITLE_LABEL_BACKING_PATCHES)
        backing_scale_target = struct.unpack_from("<ff", raw, 0x6989C0)
        third_call = struct.unpack_from("<I", raw, 0x1AC600)[0]
        # r11 intentionally recenters the two backing records inside this table.
        # Normalize only those exact fields back to pristine before hashing so
        # unrelated title-state bytes remain covered by the historical checksum.
        normalized_title_records = bytearray(raw[0x5CBE60:0x5CBFB4])
        for offset, pristine, _replacement in TITLE_LABEL_BACKING_PATCHES:
            if 0x5CBE60 <= offset < 0x5CBFB4:
                struct.pack_into("<I", normalized_title_records, offset - 0x5CBE60, pristine)
        title_records_hash = sha256(normalized_title_records).hexdigest()
        generic_text_offsets_pristine = (
            struct.unpack_from("<I", raw, 0x19AB38)[0] == 0x3C024280
            and struct.unpack_from("<I", raw, 0x19ABD8)[0] == 0x3C024280
        )
        title_geometry_ok = (
            raw[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)] == new_game
            and raw[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)] == load_game
            and new_ptr == _ELF_MAIN_VADDR + TITLE_NEW_GAME_START - _ELF_MAIN_FILE_OFFSET
            and load_ptr == _ELF_MAIN_VADDR + TITLE_LOAD_START - _ELF_MAIN_FILE_OFFSET
            and new_anchor_word == 0x3C024210
            and load_anchor_word == 0x3C0243AA
            and backing_words == tuple(replacement for _, _, replacement in TITLE_LABEL_BACKING_PATCHES)
            and backing_scale_target == (1.0, 1.0)
            and third_call == 0x2787D750
            and generic_text_offsets_pristine
            and title_records_hash == "fbb685e638f950a844c169bec567f7102943e4a9b7ef1916f02b2b0dcb530422"
        )
    checks.append(
        _check(
            "title_english_label_geometry",
            title_geometry_ok,
            title_geometry_detail,
        )
    )

    for index in _VISIBLE_PROMPT_INDICES:
        pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
        ok = False
        detail = "prompt pointer outside ELF"
        if pointer_offset + 4 <= len(raw):
            target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            ok = _read_wide_at_va(raw, target_va, NAME_PROMPT_TEXTS[index])
            detail = f"prompt {index} does not resolve to wide {NAME_PROMPT_TEXTS[index]!r}"
        checks.append(_check(f"name_prompt_{index}", ok, detail))

    for name, pointer_offsets in NAME_DEFAULT_POINTER_OFFSETS.items():
        ok = all(
            offset + 4 <= len(raw)
            and _read_wide_at_va(raw, struct.unpack_from("<I", raw, offset)[0], name)
            for offset in pointer_offsets
        )
        checks.append(_check(f"default_name_{name}", ok, f"default {name} pointer does not resolve to wide text"))
    for name, pointer_offsets in NAME_RUNTIME_POINTER_OFFSETS.items():
        ok = all(
            offset + 4 <= len(raw)
            and _read_wide_at_va(raw, struct.unpack_from("<I", raw, offset)[0], name)
            for offset in pointer_offsets
        )
        checks.append(_check(f"runtime_name_{name}", ok, f"runtime {name} pointer does not resolve to wide text"))

    keyboard_ok = True
    for patch in KEYBOARD_ROW_PATCHES:
        expected = encode_ps2_english(patch.text, collapse_spaces=False)
        if raw[patch.offset:patch.offset + len(expected)] != expected:
            keyboard_ok = False
            break
    checks.append(_check("latin_name_keyboard", keyboard_ok, "one or more keyboard rows are not wide Latin"))

    name_flow_ok = (
        NAME_FLOW_STATE9_FLAG_OFFSET + 8 <= len(raw)
        and struct.unpack_from("<I", raw, NAME_FLOW_STATE9_FLAG_OFFSET)[0] == 0x24050001
        and struct.unpack_from("<I", raw, NAME_FLOW_STATE9_FLAG_OFFSET + 4)[0] == 0x0C0A1788
        and 0x186A94 <= len(raw)
        and struct.unpack_from("<I", raw, 0x186A8C)[0] == 0x24050001
        and struct.unpack_from("<I", raw, 0x186A90)[0] == 0x0C0A1788
    )
    checks.append(
        _check(
            "name_flow_skip_reading",
            name_flow_ok,
            "state 9 does not reuse the post-reading flag-1 transition",
        )
    )

    name_prompt_layout_ok = all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
        for offset, _expected, replacement in NAME_PROMPT_LAYOUT_PATCHES
    )
    checks.append(
        _check(
            "name_prompt_centered_layout",
            name_prompt_layout_ok,
            "M_Name prompt X owners are not using the centered English geometry",
        )
    )

    name_confirmation_focus_ok = (
        all(
            offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
            for offset, _expected, replacement in NAME_CONFIRMATION_FOCUS_PATCHES
        )
        and 0x181DCC <= len(raw)
        and struct.unpack_from("<I", raw, 0x181DC8)[0] == 0x3C024388
    )
    checks.append(
        _check(
            "name_confirmation_focus_layout",
            name_confirmation_focus_ok,
            "selected Yes geometry/color ownership is stale or accepted No focus changed",
        )
    )

    adv_ok = all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
        for offset, _expected, replacement in ADV_DG_LAYOUT_PATCHES
    )
    checks.append(
        _check(
            "adv_dg_horizontal_layout",
            adv_ok,
            "proven DG coordinate-output swap is missing or stale",
        )
    )
    adv_speaker_ok = all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
        for offset, _expected, replacement in ADV_SPEAKER_LAYOUT_PATCHES
    )
    checks.append(
        _check(
            "adv_speaker_horizontal_layout",
            adv_speaker_ok,
            "separate ADV speaker-name canvas is not using horizontal advance",
        )
    )

    segment = _translation_segment(raw)
    checks.append(_check("translation_segment", segment is not None, "translation PT_LOAD is not active/valid"))

    _menu_fixed_ok, menu_relocated_ok, menu_pristine_ok = _verify_menu_semantics(raw, segment)
    checks.append(
        _check(
            "menu_relocated_labels",
            menu_relocated_ok,
            "one or more proven command labels do not resolve as wide PS2 text through their semantic aliases",
        )
    )
    checks.append(
        _check(
            "menu_unresolved_pristine",
            menu_pristine_ok,
            "one or more unresolved/pristine command labels or pointer aliases changed",
        )
    )

    dungeon_actions_ok, dungeon_items_ok = _verify_dungeon_semantics(raw, segment)
    checks.append(
        _check(
            "dungeon_action_labels",
            dungeon_actions_ok,
            "exploration action-palette labels do not resolve through their proven direct-code owners",
        )
    )
    checks.append(
        _check(
            "dungeon_item_names",
            dungeon_items_ok,
            "one or more battle/L1 item-name pointers do not resolve to exact official wide English",
        )
    )

    companion_comments_ok, companion_actions_ok = _verify_companion_hud_semantics(raw, segment)
    checks.append(
        _check(
            "companion_hud_comments",
            companion_comments_ok,
            "one or more companion HUD comment aliases do not resolve to the exact PS4 English line",
        )
    )
    checks.append(
        _check(
            "companion_hud_actions",
            companion_actions_ok,
            "one or more companion HUD action labels drifted from their translated/pristine owner",
        )
    )
    checks.append(
        _check(
            "companion_afk_free_talk",
            _verify_companion_afk_semantics(raw, segment),
            "one or more Re:charge free-talk owners do not resolve through the bounded 30x20 AFK table",
        )
    )
    checks.append(
        _check(
            "companion_hud_layout",
            _verify_companion_hud_layout(raw),
            "companion action/AFK shared bubble is not using the r50 anchored multiline and consumer-specific blue-panel runtime",
        )
    )
    heap_break_ok = (
        _RUNTIME_HEAP_BREAK_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, _RUNTIME_HEAP_BREAK_OFFSET)[0] == _EXPECTED_RUNTIME_HEAP_START
    )
    checks.append(
        _check(
            "runtime_heap_break",
            heap_break_ok,
            "libkernel heap break still overlaps the translation PT_LOAD",
        )
    )
    hant_inventory_ok = False
    hant_wrapped_ok = False
    hant_unresolved_ok = True

    if HANT_POINTER_TABLE_OFFSET + 17 * 4 > len(raw):
        hant_unresolved_ok = False
    else:
        table_hash = sha256(raw[HANT_POINTER_TABLE_OFFSET:HANT_POINTER_TABLE_OFFSET + 17 * 4]).hexdigest()
        table_pristine = table_hash == _HANT_POINTER_TABLE_SHA256
        metadata_size = len(HANT_PRISTINE_CONTROLLER_METADATA_RECORDS) * 8
        expected_pristine_metadata = b"".join(
            struct.pack("<hhhh", *record) for record in HANT_PRISTINE_CONTROLLER_METADATA_RECORDS
        )
        metadata_pristine = (
            HANT_CONTROLLER_METADATA_OFFSET + metadata_size <= len(raw)
            and raw[HANT_CONTROLLER_METADATA_OFFSET:HANT_CONTROLLER_METADATA_OFFSET + metadata_size]
            == expected_pristine_metadata
        )

        text_descriptor_in_segment = False
        metadata_descriptor_in_segment = False
        text_payload_ok = False
        metadata_payload_ok = False
        if segment is not None:
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            if HANT_TUTORIAL_DESCRIPTOR_OFFSET + 4 <= len(raw):
                table_va = struct.unpack_from("<I", raw, HANT_TUTORIAL_DESCRIPTOR_OFFSET)[0]
                text_descriptor_in_segment = p_vaddr <= table_va < p_vaddr + p_filesz
                if text_descriptor_in_segment:
                    table_file = p_offset + (table_va - p_vaddr)
                    table_bytes = (len(HANT_WRAPPED_LINES) + 1) * 4
                    if table_file + table_bytes <= p_offset + p_filesz:
                        text_payload_ok = True
                        for row_index, english in enumerate(HANT_WRAPPED_LINES):
                            if measured_hant_cells(english) > HANT_LAYOUT_PROFILE.max_cells:
                                text_payload_ok = False
                                break
                            target_va = struct.unpack_from("<I", raw, table_file + row_index * 4)[0]
                            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
                            relative = target_va - p_vaddr
                            if relative < 0 or relative + len(expected) > p_filesz:
                                text_payload_ok = False
                                break
                            target_file = p_offset + relative
                            if raw[target_file:target_file + len(expected)] != expected:
                                text_payload_ok = False
                                break
                        if text_payload_ok:
                            eof_va = struct.unpack_from(
                                "<I", raw, table_file + len(HANT_WRAPPED_LINES) * 4
                            )[0]
                            text_payload_ok = eof_va == _HANT_EOF_VA

            if HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET + 4 <= len(raw):
                metadata_va = struct.unpack_from("<I", raw, HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET)[0]
                metadata_descriptor_in_segment = p_vaddr <= metadata_va < p_vaddr + p_filesz
                if metadata_descriptor_in_segment:
                    metadata_file = p_offset + (metadata_va - p_vaddr)
                    expected_metadata = b"".join(
                        struct.pack("<hhhh", *record) for record in HANT_CONTROLLER_METADATA_RECORDS
                    )
                    metadata_payload_ok = (
                        metadata_file + len(expected_metadata) <= p_offset + p_filesz
                        and raw[metadata_file:metadata_file + len(expected_metadata)] == expected_metadata
                    )

        hant_inventory_ok = (
            table_pristine
            and metadata_pristine
            and text_descriptor_in_segment
            and metadata_descriptor_in_segment
        )
        hant_wrapped_ok = text_payload_ok and metadata_payload_ok

    hant_style_ok = (
        HANT_TUTORIAL_FONT_STYLE_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, HANT_TUTORIAL_FONT_STYLE_OFFSET)[0] == 0x24050001
        and HANT_TUTORIAL_SINGLETON_STYLE_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, HANT_TUTORIAL_SINGLETON_STYLE_OFFSET)[0]
        == HANT_TUTORIAL_SINGLETON_STYLE_PRISTINE_WORD
    )
    hant_spacing_ok = (
        HANT_TUTORIAL_ROW_SPACING_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, HANT_TUTORIAL_ROW_SPACING_OFFSET)[0] == 0x3C024180
    )

    hant_chrome_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_CHROME_LABELS:
            source = spec.source_text.encode("cp932") + b"\x00"
            if raw[spec.source_offset:spec.source_offset + len(source)] != source:
                hant_chrome_ok = False
                break
            if spec.pointer_offset + 4 > len(raw):
                hant_chrome_ok = False
                break
            target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
            relative = target_va - p_vaddr
            expected = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
            if relative < 0 or relative + len(expected) > p_filesz:
                hant_chrome_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                hant_chrome_ok = False
                break

    hant_config_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_CONFIG_LABELS:
            source = spec.source_text.encode("cp932") + b"\x00"
            if raw[spec.source_offset:spec.source_offset + len(source)] != source:
                hant_config_ok = False
                break
            if spec.pointer_offset + 4 > len(raw):
                hant_config_ok = False
                break
            target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
            relative = target_va - p_vaddr
            expected = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
            if relative < 0 or relative + len(expected) > p_filesz:
                hant_config_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                hant_config_ok = False
                break

    hant_help_category_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_HELP_CATEGORY_LABELS:
            source = spec.source_text.encode("cp932") + b"\x00"
            if raw[spec.source_offset:spec.source_offset + len(source)] != source:
                hant_help_category_ok = False
                break
            if spec.pointer_offset + 4 > len(raw):
                hant_help_category_ok = False
                break
            target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
            relative = target_va - p_vaddr
            expected = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
            if relative < 0 or relative + len(expected) > p_filesz:
                hant_help_category_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                hant_help_category_ok = False
                break

    hant_help_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_ALL_HELP_TOPICS:
            source = spec.source_text.encode("cp932") + b"\x00"
            if raw[spec.source_offset:spec.source_offset + len(source)] != source:
                hant_help_ok = False
                break
            if spec.pointer_offset + 4 > len(raw):
                hant_help_ok = False
                break
            target_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
            relative = target_va - p_vaddr
            expected = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
            if relative < 0 or relative + len(expected) > p_filesz:
                hant_help_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                hant_help_ok = False
                break

    # Selected Help pages are not owned by the topic-label tables above. The
    # Help handler resolves a separate mode/category/topic body tree. Verify the
    # newly promoted body leaves independently so English menu labels cannot
    # mask a Japanese/stale selected-page payload.
    hant_help_bodies_ok = segment is not None
    for spec in HANT_HELP_BODIES:
        if not hant_help_bodies_ok:
            break

        source_by_index = {index: offset for index, offset, _text in spec.source_rows}
        expected_source_table = tuple(
            _ELF_MAIN_VADDR + source_by_index[index] - _ELF_MAIN_FILE_OFFSET
            if index in source_by_index
            else _HANT_BLANK_VA
            for index in range(len(spec.english_rows))
        ) + (_HANT_EOF_VA,)
        source_table_size = len(expected_source_table) * 4
        if spec.source_table_offset + source_table_size > len(raw):
            hant_help_bodies_ok = False
            break
        actual_source_table = struct.unpack_from(
            f"<{len(expected_source_table)}I",
            raw,
            spec.source_table_offset,
        )
        if actual_source_table != expected_source_table:
            hant_help_bodies_ok = False
            break

        for _row_index, source_offset, source_text in spec.source_rows:
            source = source_text.encode("cp932") + b"\x00"
            if raw[source_offset:source_offset + len(source)] != source:
                hant_help_bodies_ok = False
                break
        if not hant_help_bodies_ok:
            break

        if spec.descriptor_offset + 4 > len(raw):
            hant_help_bodies_ok = False
            break
        target_table_va = struct.unpack_from("<I", raw, spec.descriptor_offset)[0]
        if target_table_va & 3:
            hant_help_bodies_ok = False
            break
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        table_relative = target_table_va - p_vaddr
        translated_table_size = (len(spec.english_rows) + 1) * 4
        if table_relative < 0 or table_relative + translated_table_size > p_filesz:
            hant_help_bodies_ok = False
            break
        target_table_file = p_offset + table_relative

        for row_index, english in enumerate(spec.english_rows):
            row_va = struct.unpack_from("<I", raw, target_table_file + row_index * 4)[0]
            if not english:
                if row_va != _HANT_BLANK_VA:
                    hant_help_bodies_ok = False
                    break
                continue
            if measured_hant_cells(english) > HANT_LAYOUT_PROFILE.max_cells:
                hant_help_bodies_ok = False
                break
            if not _read_wide_at_va(raw, row_va, english):
                hant_help_bodies_ok = False
                break
        if not hant_help_bodies_ok:
            break
        if struct.unpack_from("<I", raw, target_table_file + len(spec.english_rows) * 4)[0] != _HANT_EOF_VA:
            hant_help_bodies_ok = False
            break

    def expected_english_help_metadata(spec) -> tuple[tuple[int, int, int, int], ...]:
        records: list[tuple[int, int, int, int]] = []
        for record_index, (kind, variant, field_x, field_y) in enumerate(spec.metadata_records):
            source_x = 73 + field_x
            source_y = 119 + field_y
            source_column = round((source_x - 85) / 16)
            source_row = round((source_y - 131) / 21)
            delta_x = source_x - (85 + source_column * 16)
            delta_y = source_y - (131 + source_row * 21)
            target_x = 85 + source_column * HANT_LAYOUT_PROFILE.glyph_advance + delta_x
            target_y = 131 + source_row * HANT_LAYOUT_PROFILE.line_spacing + delta_y
            if spec.key == "exploration_controls" and record_index == len(spec.metadata_records) - 1:
                target_x -= 6
            records.append((kind, variant, int(round(target_x - 73)), int(round(target_y - 119))))
        records.append((-1, -1, -1, -1))
        return tuple(records)

    hant_help_body_metadata_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_HELP_BODIES:
            source_metadata = (*spec.metadata_records, (-1, -1, -1, -1))
            metadata_size = len(source_metadata) * 8
            if spec.metadata_offset + metadata_size > len(raw):
                hant_help_body_metadata_ok = False
                break
            if tuple(
                struct.unpack_from("<hhhh", raw, spec.metadata_offset + index * 8)
                for index in range(len(source_metadata))
            ) != source_metadata:
                hant_help_body_metadata_ok = False
                break
            if spec.metadata_descriptor_offset + 4 > len(raw):
                hant_help_body_metadata_ok = False
                break
            metadata_va = struct.unpack_from("<I", raw, spec.metadata_descriptor_offset)[0]
            if not spec.metadata_records:
                expected_source_va = _ELF_MAIN_VADDR + spec.metadata_offset - _ELF_MAIN_FILE_OFFSET
                if metadata_va != expected_source_va:
                    hant_help_body_metadata_ok = False
                    break
                continue
            relative = metadata_va - p_vaddr
            expected_metadata = expected_english_help_metadata(spec)
            expected_size = len(expected_metadata) * 8
            if metadata_va & 3 or relative < 0 or relative + expected_size > p_filesz:
                hant_help_body_metadata_ok = False
                break
            target_file = p_offset + relative
            actual_metadata = tuple(
                struct.unpack_from("<hhhh", raw, target_file + index * 8)
                for index in range(len(expected_metadata))
            )
            if actual_metadata != expected_metadata:
                hant_help_body_metadata_ok = False
                break

    hant_runtime_layout_ok = all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == replacement
        for offset, _expected, replacement in HANT_RUNTIME_LAYOUT_PATCHES
    )

    hant_mail_chrome_ok = segment is not None
    if segment is not None:
        source = HANT_MAIL_COUNT_LABEL.source_text.encode("cp932") + b"\x00"
        if raw[HANT_MAIL_COUNT_LABEL.source_offset:HANT_MAIL_COUNT_LABEL.source_offset + len(source)] != source:
            hant_mail_chrome_ok = False
        elif HANT_MAIL_COUNT_LABEL.addiu_offset + 4 > len(raw):
            hant_mail_chrome_ok = False
        else:
            lui_word = struct.unpack_from("<I", raw, HANT_MAIL_COUNT_LABEL.lui_offset)[0]
            addiu_word = struct.unpack_from("<I", raw, HANT_MAIL_COUNT_LABEL.addiu_offset)[0]
            if lui_word & 0xFFFF0000 != 0x3C050000 or addiu_word & 0xFFFF0000 != 0x24A50000:
                hant_mail_chrome_ok = False
            else:
                hi = lui_word & 0xFFFF
                lo = addiu_word & 0xFFFF
                signed_lo = lo if lo < 0x8000 else lo - 0x10000
                target_va = ((hi << 16) + signed_lo) & 0xFFFFFFFF
                p_offset, p_vaddr, p_filesz, _p_memsz = segment
                relative = target_va - p_vaddr
                expected = encode_ps2_english(HANT_MAIL_COUNT_LABEL.english, collapse_spaces=False) + b"\x00"
                if relative < 0 or relative + len(expected) > p_filesz:
                    hant_mail_chrome_ok = False
                elif raw[p_offset + relative:p_offset + relative + len(expected)] != expected:
                    hant_mail_chrome_ok = False

    hant_dictionary_definitions_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in HANT_DICTIONARY_DEFINITIONS:
            try:
                source_ok = (
                    definition_source_fingerprint(raw, spec.source_table_offset, spec.source_row_count)
                    == spec.source_sha256
                )
            except ValueError:
                source_ok = False
            if not source_ok:
                hant_dictionary_definitions_ok = False
                break
            if spec.descriptor_offset + 4 > len(raw):
                hant_dictionary_definitions_ok = False
                break
            table_va = struct.unpack_from("<I", raw, spec.descriptor_offset)[0]
            relative = table_va - p_vaddr
            table_size = (len(spec.english_rows) + 1) * 4
            if table_va & 3 or relative < 0 or relative + table_size > p_filesz:
                hant_dictionary_definitions_ok = False
                break
            table_file = p_offset + relative
            for row_index, english in enumerate(spec.english_rows):
                row_va = struct.unpack_from("<I", raw, table_file + row_index * 4)[0]
                if not english:
                    if row_va != _HANT_BLANK_VA:
                        hant_dictionary_definitions_ok = False
                        break
                elif measured_hant_cells(english) > DICTIONARY_DEFINITION_MAX_CELLS or not _read_wide_at_va(raw, row_va, english):
                    hant_dictionary_definitions_ok = False
                    break
            if not hant_dictionary_definitions_ok:
                break
            if struct.unpack_from("<I", raw, table_file + len(spec.english_rows) * 4)[0] != _HANT_EOF_VA:
                hant_dictionary_definitions_ok = False
                break

    def verify_relocated_hant_content(specs, *, hashed: bool) -> bool:
        if segment is None:
            return False
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for spec in specs:
            if hashed:
                end = raw.find(b"\x00", spec.source_offset, min(len(raw), spec.source_offset + 256))
                if end < 0 or sha256(raw[spec.source_offset:end + 1]).hexdigest() != spec.source_sha256:
                    return False
            else:
                source = spec.source_text.encode("cp932") + b"\x00"
                if raw[spec.source_offset:spec.source_offset + len(source)] != source:
                    return False
            if not spec.pointer_offsets:
                return False
            targets = set()
            for pointer_offset in spec.pointer_offsets:
                if pointer_offset + 4 > len(raw):
                    return False
                targets.add(struct.unpack_from("<I", raw, pointer_offset)[0])
            if len(targets) != 1:
                return False
            target_va = targets.pop()
            expected = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
            relative = target_va - p_vaddr
            if relative < 0 or relative + len(expected) > p_filesz:
                return False
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                return False
        return True

    hant_content_values_ok = verify_relocated_hant_content(HANT_CONTENT_LABELS, hashed=False)
    hant_ringtones_ok = verify_relocated_hant_content(HANT_RINGTONES, hashed=True)
    hant_dictionary_tabs_ok = verify_relocated_hant_content(HANT_DICTIONARY_TABS, hashed=True)
    hant_dictionary_terms_ok = verify_relocated_hant_content(HANT_DICTIONARY_TERMS, hashed=True)

    promoted_hant_sources = {
        *(spec.source_offset for spec in HANT_CONTENT_LABELS),
        *(spec.source_offset for spec in HANT_RINGTONES),
        *(spec.source_offset for spec in HANT_DICTIONARY_TABS),
        *(spec.source_offset for spec in HANT_DICTIONARY_TERMS),
    }
    promoted_menu_sources = {
        spec.source_offset for spec in MENU_LABELS if spec.status == "proven"
    }
    for source_offset, pointer_offsets, source_text in _HANT_UNRESOLVED_SIGNATURES:
        if source_offset in promoted_hant_sources or source_offset in promoted_menu_sources:
            continue
        expected_va = _ELF_MAIN_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET
        if source_text is not None:
            encoded = source_text.encode("cp932") + b"\x00"
            if raw[source_offset:source_offset + len(encoded)] != encoded:
                hant_unresolved_ok = False
                break
        if any(
            pointer_offset + 4 > len(raw)
            or struct.unpack_from("<I", raw, pointer_offset)[0] != expected_va
            for pointer_offset in pointer_offsets
        ):
            hant_unresolved_ok = False
            break

    checks.append(
        _check(
            "hant_inventory_proven_targets",
            hant_inventory_ok,
            "pristine tutorial table or translated descriptor target is missing/stale",
        )
    )
    checks.append(
        _check(
            "hant_wrapped_layout_payload",
            hant_wrapped_ok,
            "wrapped H.A.N.T rows/icon metadata do not match the page-local 12px/28-cell profile",
        )
    )
    checks.append(
        _check(
            "hant_tutorial_font_style",
            hant_style_ok,
            "H.A.N.T tutorial row style or singleton-constructor preservation is stale",
        )
    )
    checks.append(
        _check(
            "hant_tutorial_row_spacing",
            hant_spacing_ok,
            "H.A.N.T tutorial rows are not using the page-local 16px stride",
        )
    )
    checks.append(
        _check(
            "hant_chrome_labels",
            hant_chrome_ok,
            "one or more H.A.N.T chrome labels do not resolve through the proven seven-entry owner table",
        )
    )
    checks.append(
        _check(
            "hant_config_labels",
            hant_config_ok,
            "one or more H.A.N.T Config labels do not resolve through the proven nine-entry live renderer table",
        )
    )
    checks.append(
        _check(
            "hant_help_category_labels",
            hant_help_category_ok,
            "one or more H.A.N.T Help category labels do not resolve through the proven three-entry live renderer table",
        )
    )
    checks.append(
        _check(
            "hant_help_topics",
            hant_help_ok,
            "one or more H.A.N.T Help topic labels do not resolve through the proven three-list 55-entry owner set",
        )
    )
    checks.append(
        _check(
            "hant_help_bodies",
            hant_help_bodies_ok,
            "one or more selected H.A.N.T Help bodies do not resolve through the proven mode/category/topic body owner",
        )
    )
    checks.append(_check("hant_help_body_metadata", hant_help_body_metadata_ok, "one or more selected Help-body icon records do not follow the English 12px/16px geometry"))
    checks.append(_check("hant_runtime_layout", hant_runtime_layout_ok, "Config/Dictionary/Help/Enemy H.A.N.T renderer geometry is stale"))
    checks.append(_check("hant_mail_chrome", hant_mail_chrome_ok, "Mail count/status chrome does not resolve to its translated direct-code owner"))
    checks.append(_check("hant_dictionary_definitions", hant_dictionary_definitions_ok, "one or more observed Dictionary definition pages are stale or unresolved"))
    checks.append(_check("hant_content_values", hant_content_values_ok, "Mail/Config/Dictionary/Enemy H.A.N.T content values are stale or unresolved"))
    checks.append(_check("hant_ringtones", hant_ringtones_ok, "one or more H.A.N.T ringtone titles are stale or unresolved"))
    checks.append(_check("hant_dictionary_tabs", hant_dictionary_tabs_ok, "one or more H.A.N.T Dictionary tabs are stale or unresolved"))
    checks.append(_check("hant_dictionary_terms", hant_dictionary_terms_ok, "one or more H.A.N.T Dictionary terms are stale or unresolved"))
    checks.append(
        _check(
            "hant_unresolved_pristine",
            hant_unresolved_ok,
            "one or more unresolved H.A.N.T owners changed outside an explicit owner",
        )
    )
    checks.append(
        _check(
            "hant_tutorial",
            hant_inventory_ok and hant_wrapped_ok and hant_style_ok and hant_spacing_ok and hant_unresolved_ok,
            "H.A.N.T tutorial relocation/layout invariant failed",
        )
    )

    for index, (_source_offset, _source, english) in MEMORY_CARD_MESSAGES.items():
        ok = segment is not None
        detail = f"memory-card entry {index} does not resolve to official English"
        if segment is not None:
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            pointer_offset = MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4
            if pointer_offset + 4 > len(raw):
                ok = False
            else:
                target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
                relative = target_va - p_vaddr
                expected = encode_memory_card_english(english) + b"\x00"
                if relative < 0 or relative + len(expected) > p_filesz:
                    ok = False
                else:
                    target_file = p_offset + relative
                    ok = raw[target_file:target_file + len(expected)] == expected
        checks.append(_check(f"memory_card_{index}", ok, detail))

    alias_ok = segment is not None
    alias_detail = "boot memory-card aliases do not resolve to relocated entry 1 English"
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        primary_offset = MEMORY_CARD_POINTER_TABLE_OFFSET + 4
        if primary_offset + 4 > len(raw):
            alias_ok = False
        else:
            primary_va = struct.unpack_from("<I", raw, primary_offset)[0]
            expected = encode_memory_card_english(MEMORY_CARD_MESSAGES[1][2]) + b"\x00"
            relative = primary_va - p_vaddr
            if relative < 0 or relative + len(expected) > p_filesz:
                alias_ok = False
            elif raw[p_offset + relative:p_offset + relative + len(expected)] != expected:
                alias_ok = False
            else:
                alias_ok = all(
                    alias_offset + 4 <= len(raw)
                    and struct.unpack_from("<I", raw, alias_offset)[0] == primary_va
                    for alias_offset in MEMORY_CARD_POINTER_ALIASES.get(1, ())
                )
    checks.append(_check("memory_card_1_boot_aliases", alias_ok, alias_detail))
    return checks


def _sha256_file(path) -> str:
    digest = sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_startup_candidate(candidate, startup_graphics_root) -> dict[str, Any]:
    """Verify the startup acceptance slice from the final ISO bytes."""
    import mmap
    from pathlib import Path

    from tools.cvm import HEADER_SIZE
    from tools.elf_rofs import find_rofs_record
    from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso

    candidate = Path(candidate)
    startup_graphics_root = Path(startup_graphics_root)
    checks: list[dict[str, Any]] = []

    with candidate.open("rb") as handle:
        image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            _, outer_records = index_iso(image)
            elf_record = find_record(outer_records, "SLPM_665.11")
            elf = bytes(
                image[
                    elf_record.extent * SECTOR_SIZE:
                    elf_record.extent * SECTOR_SIZE + elf_record.size
                ]
            )
            checks.extend(verify_startup_elf(elf))

            cvm = find_record(outer_records, "DATA.CVM")
            embedded_base = cvm.extent * SECTOR_SIZE + HEADER_SIZE
            _, embedded_records = index_iso(image, embedded_base)

            graphics_found = 0
            for rel in STARTUP_GRAPHICS_PATHS:
                expected_path = startup_graphics_root / rel
                ok = expected_path.is_file()
                detail = f"missing expected startup overlay {expected_path}"
                if ok:
                    expected = expected_path.read_bytes()
                    try:
                        record = find_record(embedded_records, rel)
                    except ValueError as exc:
                        ok = False
                        detail = str(exc)
                    else:
                        actual = bytes(
                            image[
                                embedded_base + record.extent * SECTOR_SIZE:
                                embedded_base + record.extent * SECTOR_SIZE + record.size
                            ]
                        )
                        ok = actual == expected
                        detail = f"finished payload differs for {rel}"
                        if ok:
                            graphics_found += 1
                        try:
                            find_rofs_record(elf, rel, record.size, record.extent)
                        except ValueError as exc:
                            checks.append(_check(f"rofs_{rel}", False, str(exc)))
                        else:
                            checks.append(_check(f"rofs_{rel}", True))
                checks.append(_check(f"graphics_{rel}", ok, detail))
            checks.append(
                _check(
                    "startup_graphics_count",
                    graphics_found == len(STARTUP_GRAPHICS_PATHS),
                    f"resolved {graphics_found}/{len(STARTUP_GRAPHICS_PATHS)} startup graphics",
                )
            )

            # Keep the structurally repacked title atlas independently visible in
            # acceptance reports even though the whole B_GP088 container is also
            # compared byte-for-byte above.
            from tools.tmx import find_tmx_entry

            gp088_expected_path = startup_graphics_root / "BLBRD/B_GP088.BIN"
            packed_ok = gp088_expected_path.is_file()
            packed_detail = f"missing expected GP088 container {gp088_expected_path}"
            if packed_ok:
                expected_gp088 = gp088_expected_path.read_bytes()
                gp088_record = find_record(embedded_records, "BLBRD/B_GP088.BIN")
                actual_gp088 = bytes(
                    image[
                        embedded_base + gp088_record.extent * SECTOR_SIZE:
                        embedded_base + gp088_record.extent * SECTOR_SIZE + gp088_record.size
                    ]
                )
                try:
                    expected_entry = find_tmx_entry(expected_gp088, "GRP088/GP088_12.TMX")
                    actual_entry = find_tmx_entry(actual_gp088, "GRP088/GP088_12.TMX")
                except ValueError as exc:
                    packed_ok = False
                    packed_detail = str(exc)
                else:
                    expected_chunk = expected_gp088[
                        expected_entry.base_offset:expected_entry.base_offset + expected_entry.chunk_size
                    ]
                    actual_chunk = actual_gp088[
                        actual_entry.base_offset:actual_entry.base_offset + actual_entry.chunk_size
                    ]
                    packed_ok = actual_chunk == expected_chunk
                    packed_detail = "finished GP088_12 packed title differs from generated English atlas"
            checks.append(_check("graphics_gp088_12_packed_title", packed_ok, packed_detail))

            dg00_mtx_record = find_record(embedded_records, "ADV/DG/DG00_00.MTX")
            dg00_mtx = bytes(
                image[
                    embedded_base + dg00_mtx_record.extent * SECTOR_SIZE:
                    embedded_base + dg00_mtx_record.extent * SECTOR_SIZE + dg00_mtx_record.size
                ]
            )
            for text in (
                "Old man's voice",
                "Hey, over here.",
                "Old merchant Salah",
                "This is the Heracleion temple.",
                "First, it would be a good idea to",
                "check H.A.N.T.",
            ):
                encoded = encode_ps2_english(text)
                checks.append(_check(f"dg00_{text}", encoded in dg00_mtx, f"missing DG00 English {text!r}"))
            for japanese in ("老人の声", "おい、こっちだ。"):
                encoded = japanese.encode("cp932")
                checks.append(
                    _check(
                        f"dg00_removed_{japanese}",
                        encoded not in dg00_mtx,
                        f"Japanese DG00 source still present: {japanese}",
                    )
                )
            try:
                find_rofs_record(elf, "ADV/DG/DG00_00.MTX", dg00_mtx_record.size, dg00_mtx_record.extent)
            except ValueError as exc:
                checks.append(_check("rofs_ADV/DG/DG00_00.MTX", False, str(exc)))
            else:
                checks.append(_check("rofs_ADV/DG/DG00_00.MTX", True))

            dg00_ksf_record = find_record(embedded_records, "ADV/DG/DG00_00.KSF")
            dg00_ksf = bytes(
                image[
                    embedded_base + dg00_ksf_record.extent * SECTOR_SIZE:
                    embedded_base + dg00_ksf_record.extent * SECTOR_SIZE + dg00_ksf_record.size
                ]
            )
            for text in ("Look around the area", "Stand here", "Pick up device on the ground", "Say no"):
                checks.append(_check(f"ksf_{text}", text.encode("ascii") in dg00_ksf, f"missing KSF English {text!r}"))

        finally:
            image.close()

    passed = sum(1 for check in checks if check["ok"])
    return {
        "schema_version": 2,
        "candidate": str(candidate),
        "sha256": _sha256_file(candidate),
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks": checks,
    }


def main() -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Verify Kowloon startup translation from final ISO bytes")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--startup-graphics-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify_startup_candidate(args.candidate, args.startup_graphics_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, sort_keys=True))
    failures = [check for check in report["checks"] if not check["ok"]]
    for failure in failures:
        print(f"FAIL {failure['name']}: {failure['detail']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
