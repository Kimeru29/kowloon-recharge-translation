from __future__ import annotations

import struct
from typing import Any
from hashlib import sha256

from tools.adv_layout import ADV_DG_LAYOUT_PATCHES, ADV_SPEAKER_LAYOUT_PATCHES
from tools.hant_layout import HANT_LAYOUT_PROFILE, measured_hant_cells
from tools.hant_ui import (
    HANT_ALL_HELP_TOPICS,
    HANT_CHROME_LABELS,
    HANT_CONFIG_LABELS,
    HANT_HELP_CATEGORY_LABELS,
    HANT_CONTROLLER_METADATA_DESCRIPTOR_OFFSET,
    HANT_CONTROLLER_METADATA_OFFSET,
    HANT_CONTROLLER_METADATA_RECORDS,
    HANT_POINTER_TABLE_OFFSET,
    HANT_PRISTINE_CONTROLLER_METADATA_RECORDS,
    HANT_TUTORIAL_DESCRIPTOR_OFFSET,
    HANT_TUTORIAL_FONT_STYLE_OFFSET,
    HANT_TUTORIAL_ROW_SPACING_OFFSET,
    HANT_WRAPPED_LINES,
)
from tools.localization import encode_ps2_english
from tools.menu_ui import MENU_LABELS
from tools.memory_card_ui import (
    MEMORY_CARD_MESSAGES,
    MEMORY_CARD_POINTER_ALIASES,
    MEMORY_CARD_POINTER_TABLE_OFFSET,
    encode_memory_card_english,
)
from tools.startup_ui import (
    KEYBOARD_ROW_PATCHES,
    NAME_DEFAULT_POINTER_OFFSETS,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_RUNTIME_POINTER_OFFSETS,
    NAME_FLOW_STATE9_FLAG_OFFSET,
    TITLE_LOAD_POINTER_OFFSET,
    TITLE_LOAD_START,
    TITLE_NEW_GAME_START,
    TITLE_POINTER_TABLE_OFFSET,
)

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
            expected = spec.selected_english.encode("ascii") + b"\x00"
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
        or p_flags != 6
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
    title_geometry_detail = "title English label geometry or packed title-art invariants are missing/stale"
    if (
        len(raw) >= 0x6989C8
        and len(raw) >= 0x1AC604
        and len(raw) >= 0x1ABF88
        and len(raw) >= 0x5CBFB4
        and len(raw) >= TITLE_POINTER_TABLE_OFFSET + 8
    ):
        new_ptr, load_ptr = struct.unpack_from("<II", raw, TITLE_POINTER_TABLE_OFFSET)
        new_anchor_word = struct.unpack_from("<I", raw, 0x1ABF64)[0]
        load_anchor_word = struct.unpack_from("<I", raw, 0x1ABF84)[0]
        packed_art_scale = struct.unpack_from("<ff", raw, 0x6989C0)
        third_call = struct.unpack_from("<I", raw, 0x1AC600)[0]
        title_records_hash = sha256(raw[0x5CBE60:0x5CBFB4]).hexdigest()
        title_geometry_ok = (
            raw[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)] == new_game
            and raw[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)] == load_game
            and new_ptr == _ELF_MAIN_VADDR + TITLE_NEW_GAME_START - _ELF_MAIN_FILE_OFFSET
            and load_ptr == _ELF_MAIN_VADDR + TITLE_LOAD_START - _ELF_MAIN_FILE_OFFSET
            and new_anchor_word == 0x3C024210
            and load_anchor_word == 0x3C0243AA
            and packed_art_scale == (1.0, 1.0)
            and third_call == 0x2787D750
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

    menu_fixed_ok, menu_relocated_ok, menu_pristine_ok = _verify_menu_semantics(raw, segment)
    checks.append(
        _check(
            "menu_semantic_fixed_labels",
            menu_fixed_ok,
            "one or more fixed command labels or their semantic pointer aliases are stale",
        )
    )
    checks.append(
        _check(
            "menu_relocated_labels",
            menu_relocated_ok,
            "one or more long command labels do not resolve through all proven aliases into the translation segment",
        )
    )
    checks.append(
        _check(
            "menu_unresolved_pristine",
            menu_pristine_ok,
            "one or more unresolved/pristine command labels or pointer aliases changed",
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
    )
    hant_spacing_ok = (
        HANT_TUTORIAL_ROW_SPACING_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, HANT_TUTORIAL_ROW_SPACING_OFFSET)[0] == 0x3C024190
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

    for source_offset, pointer_offsets, source_text in _HANT_UNRESOLVED_SIGNATURES:
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
            "H.A.N.T tutorial rows are not using the page-local 12px style",
        )
    )
    checks.append(
        _check(
            "hant_tutorial_row_spacing",
            hant_spacing_ok,
            "H.A.N.T tutorial rows are not using the page-local 18px stride",
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
