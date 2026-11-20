"""Read-only static native coverage for the r67.15l Emotion Input wheel.

The report is intentionally tied to the approved r67.15k executable. It is
evidence about native ownership and dispatch, not a game-runtime emulator.
"""
from __future__ import annotations

import hashlib
import json
import struct
import argparse
from pathlib import Path

APPROVED_ELF_SHA256 = "fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d"
APPROVED_ISO_SHA256 = "ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53"
GROUP1_CONTAINER_SHA256 = "895f3d1864a653b3eb76a06eae8b8ea65b9f31cfe156fe922eb72d9eeb967942"
VA_FILE_BIAS = 0xFFF80

DIRECT_TARGETS = {
    "kanjo_input_ctor": 0x154980,
    "kanjo_sub_ctor": 0x154E60,
    "adv_emotion_task_ctor": 0x258700,
    "kanjo_shared_callback": 0x152BD0,
    "kanjo_sub_callback": 0x154D60,
    "adv_emotion_task_callback": 0x258040,
    "wheel_selection_mapper": 0x154880,
    "adv_emotion_outcome": 0x25A170,
}

SELECTION_SLOTS = (8, 1, 2, 3, 7, 5, 6, 4)
SPRITE_IDS = (21, 22, 23, 24, 29, 26, 28, 29, 30, 27, 25, 39, 31, 32, 33, 34, 42)
WHEEL_FRAME_LABELS = {
    31: {"atlas": 2, "crop": [40, 0, 80, 72], "label": "LOVE / JOY"},
    32: {"atlas": 2, "crop": [0, 0, 40, 72], "label": "COLD / ANGER"},
    33: {"atlas": 10, "crop": [160, 160, 232, 200], "label": "GRIEF / SOMBER"},
    34: {"atlas": 2, "crop": [80, 0, 152, 40], "label": "AMITY / HOT"},
}
SINGLE_LABELS = {
    53: "JOY", 54: "LOVE", 55: "AMITY", 56: "HOT",
    57: "COLD", 58: "ANGER", 59: "SOMBER", 60: "GRIEF",
}
GP001_NAMES = [f"BLBRD/GRP001/GP001_{index:02d}" for index in range(11)]
ADV_SCENARIO_CTOR_CALLERS = [
    0x15BEA4, 0x15BEC8, 0x15BF1C, 0x15BF40, 0x15BF94,
    0x15BFB8, 0x15C024, 0x15C044, 0x16FC3C, 0x16FC74,
    0x16FCAC, 0x16FCE4, 0x16FD38, 0x16FD68, 0x2483E4,
]
SELECTION_RESULT_BRANCHES = [
    # high word, command immediate, sprite resource ID, callsite
    (0x100, 0x153C10, 88, 0x153C64),
    (0x200, 0x153C78, 89, 0x153CCC),
    (0x300, 0x153CF8, 94, 0x153D40),
    (0x400, 0x153D54, 95, 0x153D9C),
    (0x500, 0x153DC8, 92, 0x153E1C),
    (0x600, 0x153E30, 93, 0x153E84),
    (0x700, 0x153EB0, 90, 0x153F04),
    (0x800, 0x153F18, 91, 0x153F6C),
]
EVENT_RESULT_BRANCHES = [
    (0x100, 0x2581E8, 0x0A, 0x2581F4),
    (0x200, 0x258250, 0x0B, 0x25825C),
    (0x300, 0x258400, 0x0C, 0x25840C),
    (0x400, 0x258438, 0x0D, 0x258444),
    (0x500, 0x258470, 0x0E, 0x25847C),
    (0x600, 0x2584A8, 0x0F, 0x2584B4),
    (0x700, 0x2584E0, 0x10, 0x2584EC),
    (0x800, 0x258518, 0x11, 0x258524),
]
INPUT_MASK_BRANCHES = [
    (0x153BF8, 0x1000), (0x153CE0, 0x8000),
    (0x153DB0, 0x4000), (0x153E98, 0x2000),
]
GLOW_LABELS_BY_SPRITE_ID = {
    88: "JOY", 89: "LOVE", 90: "AMITY", 91: "HOT",
    92: "COLD", 93: "ANGER", 94: "SOMBER", 95: "GRIEF",
}
GLOW_UV_PIXELS = {
    "JOY": [0, 0, 64, 64], "LOVE": [64, 0, 128, 64],
    "AMITY": [128, 0, 192, 64], "HOT": [192, 0, 256, 64],
    "COLD": [0, 64, 64, 128], "ANGER": [64, 64, 128, 128],
    "SOMBER": [128, 64, 192, 128], "GRIEF": [192, 64, 256, 128],
}
WHEEL_POSITION_ANCHORS = [
    (1, 0x153C18, 0x153C2C, 257, 311, "integer_to_float"),
    (2, 0x153C80, 0x153C94, 257, 281, "integer_to_float"),
    (3, 0x153D00, 0x153D08, 227, 341, "float_bits_and_integer_to_float"),
    (4, 0x153D5C, 0x153D64, 197, 341, "float_bits_and_integer_to_float"),
    (5, 0x153DD0, 0x153DE4, 257, 371, "integer_to_float"),
    (6, 0x153E38, 0x153E4C, 257, 401, "integer_to_float"),
    (7, 0x153EB8, 0x153ECC, 287, 341, "integer_to_float"),
    (8, 0x153F20, 0x153F34, 317, 341, "integer_to_float"),
]


def _va_to_offset(va: int, length: int, image_size: int) -> int:
    offset = va - VA_FILE_BIAS
    if offset < 0 or offset + length > image_size:
        raise ValueError(f"VA {va:#x} range is outside the approved ELF")
    return offset


def _direct_calls(elf: bytes) -> dict[int, list[int]]:
    calls: dict[int, list[int]] = {}
    if elf[:4] != b"\x7fELF" or elf[4:6] != b"\x01\x01":
        raise ValueError("expected ELF32 little-endian executable")
    phoff = struct.unpack_from("<I", elf, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", elf, 42)
    for index in range(phnum):
        typ, offset, va, _, filesz, _, flags, _ = struct.unpack_from(
            "<IIIIIIII", elf, phoff + index * phentsize)
        if typ != 1 or not (flags & 1):
            continue
        if offset + filesz > len(elf):
            raise ValueError("executable PT_LOAD exceeds ELF file")
        for file_offset in range(offset, offset + filesz - 3, 4):
            word = struct.unpack_from("<I", elf, file_offset)[0]
            if word >> 26 != 3:  # JAL
                continue
            pc = va + file_offset - offset
            target = ((pc + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            calls.setdefault(target, []).append(pc)
    return calls


def _group1_frames(elf: bytes) -> list[dict]:
    """Decode 146 <frames VA,count> records and every 48-byte frame."""
    registry = _va_to_offset(0x485240, 8, len(elf))
    group1_va = struct.unpack_from("<I", elf, registry + 4)[0]
    if group1_va != 0x4805E0:
        raise ValueError(f"group 1 registry target drifted: {group1_va:#x}")
    table = _va_to_offset(group1_va, 146 * 8, len(elf))
    result = []
    for resource_id in range(146):
        frames_va, count = struct.unpack_from("<II", elf, table + resource_id * 8)
        if count > 0x100 or (count and frames_va == 0):
            raise ValueError(f"invalid group 1 resource record {resource_id}")
        frames = []
        if count:
            frame_offset = _va_to_offset(frames_va, count * 48, len(elf))
            for frame_index in range(count):
                raw = elf[frame_offset + frame_index * 48:frame_offset + (frame_index + 1) * 48]
                fields = struct.unpack("<HH11f", raw)
                frames.append({
                    "index": frame_index,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "flags": fields[0], "texture_index": fields[1],
                    "width": fields[2], "height": fields[3],
                    "pivot": [fields[4], fields[5]],
                    "uv": [fields[6], fields[7], fields[8], fields[9]],
                    "angle": fields[10], "field": fields[11], "scale": fields[12],
                })
        result.append({"resource_id": resource_id, "frames_va": frames_va,
                       "frame_count": count, "frames": frames})
    return result


def _resource_binding(elf: bytes) -> dict:
    path = b"BLBRD/B_GP001.BIN\0"
    path_offset = _va_to_offset(0x4391F0, len(path), len(elf))
    if elf[path_offset:path_offset + len(path)] != path:
        raise ValueError("group 1 resource path literal changed")
    name_table = _va_to_offset(0x43A2A0, 11 * 0x20, len(elf))
    names_raw = elf[name_table:name_table + 11 * 0x20]
    names = [names_raw[i * 0x20:(i + 1) * 0x20].split(b"\0", 1)[0].decode("ascii")
             for i in range(11)]
    if names != GP001_NAMES:
        raise ValueError("group 1 texture resource name table changed")
    pointers_offset = _va_to_offset(0x43A400, 11 * 4, len(elf))
    pointers = list(struct.unpack_from("<11I", elf, pointers_offset))
    expected_pointers = [0x43A2A0 + i * 0x20 for i in range(11)]
    if pointers != expected_pointers:
        raise ValueError("group 1 texture resource pointer array changed")
    group_name_ptr_offset = _va_to_offset(0x43A034, 4, len(elf))
    group_name_ptr = struct.unpack_from("<I", elf, group_name_ptr_offset)[0]
    if group_name_ptr != 0x4391F0:
        raise ValueError(f"group 1 filename pointer changed: {group_name_ptr:#x}")
    # Pin the bounded native lookup instructions which compute table+group*4,
    # load its filename pointer and dispatch the resource loader.
    lookup_offset = _va_to_offset(0x106014, 0x20, len(elf))
    lookup_words = list(struct.unpack_from("<8I", elf, lookup_offset))
    expected_words = [0x00041880, 0x3C020044, 0x2442A030, 0x00431021,
                      0x8C440000, 0x24050001, 0x0C040CC4, 0]
    if lookup_words != expected_words:
        raise ValueError("native group resource lookup sequence changed")
    return {
        "loader_va": "0x105fe0",
        "group_index_table_va": "0x43a030",
        "group1_filename_pointer_va": "0x43a034",
        "group1_filename_va": "0x4391f0",
        "group1_filename": path[:-1].decode("ascii"),
        "filename_literal_sha256": hashlib.sha256(path).hexdigest(),
        "resource_names_va": "0x43a2a0",
        "resource_names_sha256": hashlib.sha256(names_raw).hexdigest(),
        "resource_pointer_array_va": "0x43a400",
        "resource_pointer_array_sha256": hashlib.sha256(elf[pointers_offset:pointers_offset + 44]).hexdigest(),
        "resource_names": names,
        "bounded_lookup_words": [f"0x{word:08x}" for word in lookup_words],
        "disc_inventory": {"path": "BLBRD/B_GP001.BIN", "absolute_iso_offset": "0x2ed7a800",
                           "size_bytes": 603520, "matching_group_files": 116,
                           "source_iso_sha256": APPROVED_ISO_SHA256,
                           "source_container_sha256": GROUP1_CONTAINER_SHA256,
                           "evidence_source": "approved r67.15k ISO byte-range lock; checked by regression test"},
    }


def _adv_creation_route(elf: bytes, calls: dict[int, list[int]]) -> dict:
    table_va = 0x785CF0
    table_offset = _va_to_offset(table_va, 6 * 4, len(elf))
    state_targets = list(struct.unpack_from("<6I", elf, table_offset))
    expected_targets = [0x25A4C8, 0x25A6B0, 0x25A6D4, 0x25A8E0, 0x25A8E8, 0x25A8E8]
    if state_targets != expected_targets:
        raise ValueError("ADV emotion task handler state table changed")
    create_call_va = 0x25A58C
    word = struct.unpack_from("<I", elf, _va_to_offset(create_call_va, 4, len(elf)))[0]
    create_target = ((create_call_va + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
    if word >> 26 != 3 or create_target != DIRECT_TARGETS["adv_emotion_task_ctor"]:
        raise ValueError("ADV state-zero task construction call changed")

    def address_from_pair(lui_va: int, addiu_va: int, register: int) -> int:
        lui = struct.unpack_from("<I", elf, _va_to_offset(lui_va, 4, len(elf)))[0]
        addiu = struct.unpack_from("<I", elf, _va_to_offset(addiu_va, 4, len(elf)))[0]
        if lui >> 26 != 15 or ((lui >> 16) & 31) != register:
            raise ValueError(f"expected LUI address part at {lui_va:#x}")
        if addiu >> 26 != 9 or ((addiu >> 21) & 31) != register or ((addiu >> 16) & 31) != register:
            raise ValueError(f"expected ADDIU address part at {addiu_va:#x}")
        low = addiu & 0xFFFF
        return (((lui & 0xFFFF) << 16) + (low if low < 0x8000 else low - 0x10000)) & 0xFFFFFFFF

    callback_va = address_from_pair(0x25875C, 0x258760, 7)
    destructor_va = address_from_pair(0x258764, 0x258768, 8)
    name_va = address_from_pair(0x258754, 0x258758, 6)
    registration_va = 0x258770
    registration = struct.unpack_from("<I", elf, _va_to_offset(registration_va, 4, len(elf)))[0]
    registration_target = ((registration_va + 4) & 0xF0000000) | ((registration & 0x03FFFFFF) << 2)
    if registration >> 26 != 3 or registration_target != 0x1A1190:
        raise ValueError("ADV task callback registration call changed")
    name_offset = _va_to_offset(name_va, 18, len(elf))
    name = elf[name_offset:name_offset + 18].split(b"\0", 1)[0].decode("ascii")
    if (callback_va, destructor_va, name) != (0x258040, 0x2586D0, "adv emotion task"):
        raise ValueError("ADV emotion task registration tuple changed")

    scenario_registrations = []
    for role, name_pair, callback_pair, destructor_pair, callsite, expected_name, expected_callback, expected_destructor in (
        ("adv scenario proc", (0x25A9A4, 0x25A9A8), (0x25A9AC, 0x25A9B0),
         (0x25A9B4, 0x25A9B8), 0x25A9C0, 0x678780, 0x25A340, 0x25A450),
        ("adv scenario draw", (0x25AA34, 0x25AA38), (0x25AA3C, 0x25AA40),
         (0x25AA44, 0x25AA48), 0x25AA50, 0x6787A0, 0x25A480, 0x25A910),
    ):
        resolved_name = address_from_pair(*name_pair, 6)
        resolved_callback = address_from_pair(*callback_pair, 7)
        resolved_destructor = address_from_pair(*destructor_pair, 8)
        if (resolved_name, resolved_callback, resolved_destructor) != (
            expected_name, expected_callback, expected_destructor
        ):
            raise ValueError(f"{role} split-pointer registration tuple changed")
        call = struct.unpack_from("<I", elf, _va_to_offset(callsite, 4, len(elf)))[0]
        target = ((callsite + 4) & 0xF0000000) | ((call & 0x03FFFFFF) << 2)
        if call >> 26 != 3 or target != 0x1A1190:
            raise ValueError(f"{role} registration call changed")
        name_bytes = elf[_va_to_offset(resolved_name, 24, len(elf)):]
        resolved_name_text = name_bytes[:24].split(b"\0", 1)[0].decode("ascii")
        if resolved_name_text != role:
            raise ValueError(f"{role} registered name changed")
        scenario_registrations.append({
            "role": role,
            "name_pointer_split": {"lui_va": hex(name_pair[0]), "addiu_va": hex(name_pair[1]),
                                   "resolved_va": hex(resolved_name)},
            "callback_split_pointer": {"lui_va": hex(callback_pair[0]),
                                       "addiu_va": hex(callback_pair[1]),
                                       "resolved_va": hex(resolved_callback)},
            "destructor_split_pointer": {"lui_va": hex(destructor_pair[0]),
                                         "addiu_va": hex(destructor_pair[1]),
                                         "resolved_va": hex(resolved_destructor)},
            "register_callsite_va": hex(callsite),
            "register_target_va": hex(target),
            "name": resolved_name_text,
        })
    scenario_callers = calls.get(0x25A940, [])
    if scenario_callers != ADV_SCENARIO_CTOR_CALLERS:
        raise ValueError("ADV scenario constructor direct-call census changed")
    source_va = 0x678770
    source_bytes = elf[_va_to_offset(source_va, 16, len(elf)):][:16]
    source_name = source_bytes.split(b"\0", 1)[0].decode("ascii")
    if source_name != "y_AdvMain.c":
        raise ValueError("ADV scenario source-name anchor changed")
    return {
        "handler_va": "0x25a480",
        "handler_direct_jal_callers": [hex(x) for x in calls.get(0x25A480, [])],
        "state_table_va": hex(table_va),
        "state_targets": [hex(value) for value in state_targets],
        "state_zero_task_create_callsite_va": hex(create_call_va),
        "state_zero_task_create_target_va": hex(create_target),
        "state_zero_registry_slot_gp_offset": "-0x1d68",
        "state_zero_registry_store_offsets": ["+0x04", "+0x08"],
        "task_registration": {"register_call_va": hex(registration_va),
                               "register_target_va": hex(registration_target),
                               "callback_va": hex(callback_va),
                               "destructor_va": hex(destructor_va),
                               "name_va": hex(name_va), "name": name},
        "scenario_constructor_va": "0x25a940",
        "scenario_constructor_direct_callers": [hex(x) for x in calls.get(0x25A940, [])],
        "scenario_source": {"name_va": hex(source_va), "name": source_name},
        "scenario_constructor_registrations": scenario_registrations,
        "scenario_registration_chain": (
            "The 15 direct callers invoke constructor 0x25a940, which registers the "
            "scenario proc and draw callbacks through 0x1a1190. Separately, handler "
            "0x25a480 state zero calls task constructor 0x258700; script/opcode entry "
            "to that handler remains unresolved."
        ),
        "callback_address_note": (
            "The draw callback LUI/ADDIU pair resolves byte-for-byte to 0x25a480, "
            "the state handler address; signed ADDIU low-immediate semantics are required."
        ),
        "script_opcode_origin": "unresolved: no complete ADV opcode/scene parser or incoming indirect handler registration was established",
    }


def _mode_branches(elf: bytes) -> list[dict]:
    branches = [
        (0x100, 0x2581E8, 0x2581FC, 0x258200, 0x678110),
        (0x200, 0x258250, 0x258264, 0x258268, 0x678120),
        (0x300, 0x258400, 0x258414, 0x258418, 0x678130),
        (0x400, 0x258438, 0x25844C, 0x258450, 0x678140),
        (0x500, 0x258470, 0x258484, 0x258488, 0x678150),
        (0x600, 0x2584A8, 0x2584BC, 0x2584C0, 0x678160),
        (0x700, 0x2584E0, 0x2584F4, 0x2584F8, 0x678170),
        (0x800, 0x258518, 0x25852C, 0x258530, 0x678180),
    ]
    result = []
    for mode, branch_va, lui_va, addiu_va, string_va in branches:
        lui = struct.unpack_from("<I", elf, _va_to_offset(lui_va, 4, len(elf)))[0]
        addiu = struct.unpack_from("<I", elf, _va_to_offset(addiu_va, 4, len(elf)))[0]
        call_va = addiu_va + 4
        call = struct.unpack_from("<I", elf, _va_to_offset(call_va, 4, len(elf)))[0]
        if (lui >> 26, (lui >> 16) & 31, addiu >> 26,
            (addiu >> 21) & 31, (addiu >> 16) & 31) != (15, 4, 9, 4, 4):
            raise ValueError(f"native mood-label address construction changed at {branch_va:#x}")
        high = (lui & 0xFFFF) << 16
        low = addiu & 0xFFFF
        resolved = (high + (low if low < 0x8000 else low - 0x10000)) & 0xFFFFFFFF
        if resolved != string_va:
            raise ValueError(f"native mood-label string pointer changed at {branch_va:#x}")
        if call >> 26 != 3:
            raise ValueError(f"native mood-label helper call changed at {call_va:#x}")
        target = ((call_va + 4) & 0xF0000000) | ((call & 0x03FFFFFF) << 2)
        if target != 0x39D7D8:
            raise ValueError(f"native mood-label consumer changed at {call_va:#x}")
        text_offset = _va_to_offset(string_va, 16, len(elf))
        label_format = elf[text_offset:text_offset + 16].split(b"\0", 1)[0].decode("ascii")
        result.append({"command": hex(mode), "task_branch_va": hex(branch_va),
                       "native_label_string_va": hex(string_va),
                       "native_label_format": label_format,
                       "label_semantic_join": "reported as native key only; not equated to sprite IDs without a direct code/data join"})
    return result


def _native_selection_crosswalk(elf: bytes, frames: list[dict], slot_values: list[int],
                                calls: dict[int, list[int]]) -> dict:
    positions = _wheel_position_coordinates(elf)
    result_slots = []
    for result_index, (command, command_va, sprite_id, call_va) in enumerate(
        SELECTION_RESULT_BRANCHES, start=1
    ):
        command_word = struct.unpack_from("<I", elf, _va_to_offset(command_va, 4, len(elf)))[0]
        command_store = struct.unpack_from("<I", elf, _va_to_offset(command_va + 4, 4, len(elf)))[0]
        sprite_arg_va = call_va - 0x0C
        sprite_arg = struct.unpack_from("<I", elf, _va_to_offset(sprite_arg_va, 4, len(elf)))[0]
        call_word = struct.unpack_from("<I", elf, _va_to_offset(call_va, 4, len(elf)))[0]
        if command_word != (0x24020000 | command) or command_store != 0xA602009E:
            raise ValueError(f"selection result command store changed at {command_va:#x}")
        if sprite_arg != (0x24050000 | sprite_id):
            raise ValueError(f"selection result sprite ID changed at {sprite_arg_va:#x}")
        target = ((call_va + 4) & 0xF0000000) | ((call_word & 0x03FFFFFF) << 2)
        if call_word >> 26 != 3 or target != 0x107D60:
            raise ValueError(f"selection result sprite initializer call changed at {call_va:#x}")

        descriptor = frames[sprite_id]
        label = GLOW_LABELS_BY_SPRITE_ID[sprite_id]
        first = descriptor["frames"][0]
        uv_pixels = [round(value * 256) for value in first["uv"]]
        if (descriptor["frame_count"] != 41 or first["texture_index"] != 8
                or first["width"] != 64 or first["height"] != 64
                or uv_pixels != GLOW_UV_PIXELS[label]):
            raise ValueError(f"glow sprite descriptor {sprite_id} no longer maps to {label}")
        result_slots.append({
            "result_slot": result_index,
            "result_highword": hex(command),
            "command_store_va": hex(command_va),
            "command_store_gp_offset": "+0x9e",
            "sprite_id_argument_va": hex(sprite_arg_va),
            "sprite_id": sprite_id,
            "sprite_initializer_call_va": hex(call_va),
            "sprite_initializer_target_va": "0x107d60",
            "descriptor_frame_count": descriptor["frame_count"],
            "descriptor_texture_index": first["texture_index"],
            "label": label,
            "uv_pixels": uv_pixels,
            "default_event_slot_value": slot_values[result_index - 1],
            "wheel_position": result_index,
            "wheel_position_xy": positions[result_index - 1]["xy"],
        })

    event_routes = []
    for mode, branch_va, slot_offset, store_va in EVENT_RESULT_BRANCHES:
        load_va = branch_va + 4
        load_word = struct.unpack_from("<I", elf, _va_to_offset(load_va, 4, len(elf)))[0]
        store_word = struct.unpack_from("<I", elf, _va_to_offset(store_va, 4, len(elf)))[0]
        if load_word != (0x80430000 | slot_offset) or store_word != 0xA043327E:
            raise ValueError(f"event result-slot load/store changed at {branch_va:#x}")
        event_routes.append({"result_highword": hex(mode), "branch_va": hex(branch_va),
                             "event_slot_load_va": hex(load_va),
                             "event_slot_offset": hex(slot_offset),
                             "result_field_store_va": hex(store_va),
                             "result_field_offset": "+0x327e"})

    outcome_calls = [hex(x) for x in calls.get(DIRECT_TARGETS["adv_emotion_outcome"], [])]
    return {
        "scope": "ordinary/default mode; forced scenario modes preserve caller-owned event slots",
        "result_slots": result_slots,
        "event_result_routes": event_routes,
        "shared_outcome_target_va": hex(DIRECT_TARGETS["adv_emotion_outcome"]),
        "shared_outcome_direct_callers": outcome_calls,
        "input_masks": _input_mask_proof(elf),
        "wheel_positions": positions,
    }


def _wheel_position_coordinates(elf: bytes) -> list[dict]:
    positions = []
    for position_id, x_va, y_va, x, y, representation in WHEEL_POSITION_ANCHORS:
        x_word = struct.unpack_from("<I", elf, _va_to_offset(x_va, 4, len(elf)))[0]
        y_word = struct.unpack_from("<I", elf, _va_to_offset(y_va, 4, len(elf)))[0]
        if representation == "integer_to_float":
            expected_x, expected_y = 0x24020000 | x, 0x24020000 | y
        else:
            expected_x, expected_y = 0x3C020000 | (0x4363 if x == 227 else 0x4345), 0x24020000 | y
        if x_word != expected_x or y_word != expected_y:
            raise ValueError(f"wheel position coordinate setup changed for position {position_id}")
        positions.append({"position_id": position_id, "xy": [x, y],
                          "x_setup_va": hex(x_va), "y_setup_va": hex(y_va),
                          "encoding": representation})
    return positions


def _input_mask_proof(elf: bytes) -> dict:
    masks = []
    for address, mask in INPUT_MASK_BRANCHES:
        word = struct.unpack_from("<I", elf, _va_to_offset(address, 4, len(elf)))[0]
        if word != (0x30620000 | mask):
            raise ValueError(f"wheel input mask changed at {address:#x}")
        masks.append({"instruction_va": hex(address), "mask": hex(mask)})
    if struct.unpack_from("<I", elf, _va_to_offset(0x153BE8, 4, len(elf)))[0] != 0x86040096:
        raise ValueError("wheel input strength private-field read changed")
    threshold_sites = (0x153C04, 0x153CEC, 0x153DBC, 0x153EA4)
    for address in threshold_sites:
        if struct.unpack_from("<I", elf, _va_to_offset(address, 4, len(elf)))[0] != 0x28810005:
            raise ValueError(f"wheel input strength threshold changed at {address:#x}")
    return {"mask_comparisons": masks,
            "direction_labels": "unassigned; masks are reported as native bit values",
            "strength_private_offset": "+0x96",
            "strength_threshold": "private value < 5",
            "strength_read_va": "0x153be8",
            "threshold_instruction_vas": [hex(address) for address in threshold_sites]}


def _scenario_event_slot_initialization(elf: bytes, slot_values: list[int]) -> dict:
    mode_load = struct.unpack_from("<I", elf, _va_to_offset(0x258098, 4, len(elf)))[0]
    branch = struct.unpack_from("<I", elf, _va_to_offset(0x25809C, 4, len(elf)))[0]
    if mode_load != 0x80450009 or branch >> 26 != 5:
        raise ValueError("scenario mode load/branch changed")
    branch_target = 0x2580A0 + (((branch & 0xFFFF) ^ 0x8000) - 0x8000) * 4
    if branch_target != 0x258120:
        raise ValueError("nonzero scenario mode no longer bypasses default event-slot initialization")
    ctor_call = struct.unpack_from("<I", elf, _va_to_offset(0x258120, 4, len(elf)))[0]
    target = ((0x258120 + 4) & 0xF0000000) | ((ctor_call & 0x03FFFFFF) << 2)
    if ctor_call >> 26 != 3 or target != 0x154980:
        raise ValueError("nonzero scenario mode wheel-owner constructor call changed")
    initialized = []
    for index, expected in enumerate(slot_values):
        value_va = 0x2580B8 + index * 12
        store_va = value_va + 8
        value_word = struct.unpack_from("<I", elf, _va_to_offset(value_va, 4, len(elf)))[0]
        store_word = struct.unpack_from("<I", elf, _va_to_offset(store_va, 4, len(elf)))[0]
        if value_word != (0x24030000 | expected) or store_word != (0xA043000A + index):
            raise ValueError(f"default scenario event-slot initialization changed at {value_va:#x}")
        initialized.append(expected)
    return {"scenario_mode_load_va": "0x258098", "scenario_mode_private_offset": "+0x09",
            "nonzero_mode_branch_target_va": hex(branch_target),
            "nonzero_mode_wheel_owner_ctor_va": hex(target),
            "nonzero_mode_preserves_caller_event_slots": True,
            "mode_zero_default_event_slot_values": initialized,
            "default_slot_initialization_start_va": "0x2580b8"}


def _wheel_variant_routing(elf: bytes, frames: list[dict]) -> dict:
    def word(va: int) -> int:
        return struct.unpack_from("<I", elf, _va_to_offset(va, 4, len(elf)))[0]

    if word(0x153334) != 0x860400F6 or word(0x153338) != 0x10800007:
        raise ValueError("wheel initialization mode read/zero branch changed")
    if word(0x153340) != 0x2862000C or word(0x153344) != 0x14400004:
        raise ValueError("ordinary wheel resource index lower bound changed")
    if word(0x15334C) != 0x28610010 or word(0x153350) != 0x14200014:
        raise ValueError("ordinary wheel resource index upper bound changed")
    if word(0x1533A4) != 0x00061080 or word(0x1533AC) != 0x2482FFFF:
        raise ValueError("forced-mode resource index arithmetic changed")
    if word(0x1533B0) != 0x00021080 or word(0x1533B4) != 0x2443006D:
        raise ValueError("forced-mode resource base arithmetic changed")
    if word(0x1533B8) != 0x24C2FFF4 or word(0x1533BC) != 0x00432821:
        raise ValueError("forced-mode resource ID formula changed")
    if word(0x1533D8) != 0x0C041F58:
        raise ValueError("forced-mode sprite initializer call changed")
    if word(0x153FEC) != 0x860200F6 or word(0x153FF0) != 0x24450057:
        raise ValueError("completion glow resource override changed")
    if word(0x154014) != 0x0C041F58:
        raise ValueError("completion glow initializer call changed")

    forced_modes = []
    for mode in range(1, 9):
        resource_ids = [0x6D + 4 * (mode - 1) + (index - 12) for index in range(12, 16)]
        if resource_ids != list(range(109 + (mode - 1) * 4, 113 + (mode - 1) * 4)):
            raise ValueError(f"forced-mode resource IDs changed for mode {mode}")
        for resource_id in resource_ids:
            record = frames[resource_id]
            if record["frame_count"] != 1 or record["frames"][0]["texture_index"] not in (2, 10):
                raise ValueError(f"forced-mode paired plaque descriptor changed: {resource_id}")
        forced_modes.append({"mode": mode, "resource_ids_by_init_index": resource_ids})

    glow_override = [{"mode": mode, "resource_id": mode + 87} for mode in range(1, 9)]
    return {
        "mode_read_va": "0x153334", "mode_private_offset": "+0xf6",
        "ordinary_mode_zero": {"index_bounds": [12, 16], "resource_ids": [31, 32, 33, 34]},
        "forced_mode_formula": "0x6d + 4 * (mode - 1) + (init_index - 12)",
        "forced_modes": forced_modes,
        "forced_mode_resource_family": "paired plaque descriptors on textures 2 and 10",
        "completion_mode_read_va": "0x153fec",
        "completion_glow_resource_formula": "mode + 0x57",
        "completion_glow_resource_ids": glow_override,
        "completion_glow_descriptor_labels": [GLOW_LABELS_BY_SPRITE_ID[mode + 87]
                                               for mode in range(1, 9)],
    }


def execute_selection_mapper(elf: bytes, cases=None) -> dict:
    """Execute the bounded native mode-to-command mapper in Unicorn.

    This is a small function-level proof only. It does not emulate task polling,
    the event scheduler, asset rendering, or full game state.
    """
    if hashlib.sha256(elf).hexdigest() != APPROVED_ELF_SHA256:
        raise ValueError("native mapper execution requires the approved r67.15k ELF")
    try:
        from unicorn import (Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN,
                             UC_MODE_MIPS32)
        from unicorn.mips_const import (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_PC,
                                        UC_MIPS_REG_RA, UC_MIPS_REG_SP, UC_MIPS_REG_V0)
    except ImportError as error:
        raise RuntimeError("execute_selection_mapper requires the optional unicorn package") from error

    phoff = struct.unpack_from("<I", elf, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", elf, 42)
    loads = []
    for index in range(phnum):
        typ, offset, va, _, filesz, _, flags, _ = struct.unpack_from(
            "<IIIIIIII", elf, phoff + index * phentsize)
        if typ == 1:
            loads.append((offset, va, filesz, flags))
    start = min(va for _, va, _, _ in loads) & ~0xFFF
    end = max(va + size for _, va, size, _ in loads)
    end = (end + 0xFFF) & ~0xFFF
    emu = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    emu.mem_map(start, end - start)
    for offset, va, size, _ in loads:
        emu.mem_write(va, elf[offset:offset + size])
    object_va, private_va, output_va, stack_va, return_va = (
        0x50000000, 0x50001000, 0x50002000, 0x50003000, 0x50004000)
    for address in (object_va, private_va, output_va, stack_va, return_va):
        emu.mem_map(address, 0x1000)
    # This ELF uses one MIPS III DADDU (v0,zero,zero) in its not-ready return
    # block. Unicorn's MIPS32 core rejects it, so emulate that exact instruction
    # at its pinned address; all selector/table/branch/store/return code runs
    # from the untouched ELF bytes.
    not_ready_va = 0x154954
    not_ready_word = struct.unpack_from("<I", elf, _va_to_offset(not_ready_va, 4, len(elf)))[0]
    if not_ready_word != 0x0000102D:
        raise ValueError("native mapper not-ready return instruction changed")

    def emulate_daddu_zero(uc, address, _size, _user_data):
        if address == not_ready_va:
            uc.reg_write(UC_MIPS_REG_V0, 0)
            uc.reg_write(UC_MIPS_REG_PC, address + 4)

    emu.hook_add(UC_HOOK_CODE, emulate_daddu_zero)
    emu.mem_write(object_va + 0x3C, struct.pack("<I", private_va))
    cases = cases or [
        *({"state": 0x13, "mode": mode} for mode in range(9)),
        {"state": 0x13, "mode": 9}, {"state": 0x13, "mode": -1},
        {"state": 0x12, "mode": 3}, {"state": 0x14, "mode": 3},
    ]
    emu.mem_write(private_va + 0x9E, struct.pack("<H", 0x3456))
    results = []
    for case in cases:
        state, mode = case["state"], case["mode"]
        emu.mem_write(private_va + 0x90, struct.pack("<h", state))
        emu.mem_write(private_va + 0xF6, struct.pack("<h", mode))
        initial_output = 0xBEEF
        emu.mem_write(output_va, struct.pack("<H", initial_output))
        emu.reg_write(UC_MIPS_REG_A0, object_va)
        emu.reg_write(UC_MIPS_REG_A1, output_va)
        emu.reg_write(UC_MIPS_REG_SP, stack_va + 0x800)
        emu.reg_write(UC_MIPS_REG_RA, return_va)
        emu.reg_write(UC_MIPS_REG_PC, 0x154880)
        try:
            emu.emu_start(0x154880, return_va, count=100)
        except Exception as error:
            raise RuntimeError(f"bounded MIPS execution failed for state={state:#x}, mode={mode} at PC {emu.reg_read(UC_MIPS_REG_PC):#x}") from error
        output = struct.unpack("<H", emu.mem_read(output_va, 2))[0]
        expected = mode << 8 if 1 <= mode <= 8 else 0x3456
        if state != 0x13:
            expected = 0xBEEF
        results.append({"state": state, "mode": mode, "command": output,
                        "return_value": emu.reg_read(UC_MIPS_REG_V0),
                        "expected_command": expected,
                        "output_unchanged": output == initial_output,
                        "expected_return": int(state == 0x13)})
    return {"execution_kind": "bounded_unicorn_function", "function_va": "0x154880",
            "jump_table_va": "0x77c260",
            "compatibility_shim": {"va": hex(not_ready_va), "raw_word": hex(not_ready_word),
                                    "semantics": "DADDU v0,zero,zero; Unicorn MIPS32 hook sets v0=0 and advances PC"},
            "results": results, "full_runtime": False}


def verify(elf: bytes) -> dict:
    """Return a fail-closed native static coverage proof for approved r67.15k."""
    digest = hashlib.sha256(elf).hexdigest()
    if digest != APPROVED_ELF_SHA256:
        raise ValueError(f"native coverage requires approved r67.15k ELF; got {digest}")
    calls = _direct_calls(elf)
    direct_names = ("kanjo_input_ctor", "kanjo_sub_ctor", "adv_emotion_task_ctor",
                    "wheel_selection_mapper", "adv_emotion_outcome")
    missing = [name for name in direct_names if not calls.get(DIRECT_TARGETS[name])]
    if missing:
        raise ValueError(f"native direct-call anchors missing: {', '.join(missing)}")

    # Verify the explicit eight default slot writes in the task's short,
    # bounded instruction window. Each pair is ADDIU a3,zero,value; SB a3,...
    task = _va_to_offset(0x2580B8, 8 * 12, len(elf))
    slot_values = []
    for index in range(8):
        immediate = struct.unpack_from("<I", elf, task + index * 12)[0]
        store = struct.unpack_from("<I", elf, task + index * 12 + 8)[0]
        if immediate >> 26 != 9 or (immediate >> 21) & 31 != 0:
            raise ValueError("default selection immediate sequence changed")
        if store >> 26 != 40:
            raise ValueError("default selection slot store sequence changed")
        slot_values.append(immediate & 0xFFFF)
    if tuple(slot_values) != SELECTION_SLOTS:
        raise ValueError(f"default selection slots changed: {slot_values}")

    mapper_call_va = 0x258144
    mapper_call = struct.unpack_from("<I", elf, _va_to_offset(mapper_call_va, 4, len(elf)))[0]
    if mapper_call >> 26 != 3:
        raise ValueError("ADV phase-2 mapper callsite is no longer a JAL")
    mapper_target = ((mapper_call_va + 4) & 0xF0000000) | ((mapper_call & 0x03FFFFFF) << 2)
    if mapper_target != DIRECT_TARGETS["wheel_selection_mapper"]:
        raise ValueError(f"ADV phase-2 mapper target changed: {mapper_target:#x}")
    mapper_table_offset = _va_to_offset(0x77C260, 9 * 4, len(elf))
    mapper_table_words = list(struct.unpack_from("<9I", elf, mapper_table_offset))
    expected_mapper_table = [0x154940, 0x1548C0, 0x1548D0, 0x1548E0,
                             0x1548F0, 0x154900, 0x154910, 0x154920, 0x154930]
    if mapper_table_words != expected_mapper_table:
        raise ValueError("native selector jump table changed")

    frames = _group1_frames(elf)
    if len(frames) != 146:
        raise ValueError("group 1 frame table is not the expected 146 records")
    return {
        "release": "r67.15l",
        "evidence_kind": "native_static_coverage",
        "elf_sha256": digest,
        "va_file_bias": hex(VA_FILE_BIAS),
        "direct_call_census": {
            name: {"target_va": hex(target), "callsite_vas": [hex(x) for x in calls[target]],
                   "count": len(calls[target])}
            for name, target in DIRECT_TARGETS.items() if calls.get(target)
        },
        "callback_pointer_words": {
            name: {"callback_va": hex(DIRECT_TARGETS[name]),
                   "aligned_pointer_word_offsets": [hex(pos) for pos in range(0, len(elf) - 3, 4)
                                                     if struct.unpack_from("<I", elf, pos)[0] == DIRECT_TARGETS[name]]}
            for name in ("kanjo_shared_callback", "kanjo_sub_callback", "adv_emotion_task_callback")
        },
        "owners": {
            "kanjo_input": {"constructor_va": "0x154980", "callback_va": "0x152bd0",
                            "destructor_va": "0x1546f0", "private_bytes": 248,
                            "mode_byte_offset": 246},
            "kanjo_sub": {"constructor_va": "0x154e60", "callback_va": "0x154d60",
                          "destructor_va": "0x154e10", "private_bytes": 24},
            "adv_emotion_task": {"constructor_va": "0x258700", "callback_va": "0x258040",
                                 "destructor_va": "0x2586d0", "private_name_va": "0x678190"},
        },
        "selection": {
            "default_slot_values": slot_values,
            "position_to_native_selection_id": [
                {"wheel_position": position, "selection_id": value,
                 "native_mapper_mode": position + 1,
                 "mapper_command": hex((position + 1) << 8)}
                for position, value in enumerate(slot_values)],
            "mode_to_command": [{"mode": mode, "command": hex(mode << 8)}
                                 for mode in range(1, 9)],
            "fallback_modes": [0, 9, -1],
            "fallback_output": "private halfword +0x9e",
            "unfinished_states": [0x12, 0x14],
            "jump_table_va": "0x77c260",
            "jump_table_words": [hex(x) for x in mapper_table_words],
            "jump_table_sha256": hashlib.sha256(elf[mapper_table_offset:mapper_table_offset + 36]).hexdigest(),
            "phase2_mapper_callsite_va": hex(mapper_call_va),
            "mapper_target_va": hex(mapper_target),
            "default_selection_count": 8,
            "no_selection_behavior": "zero high byte exits without issuing a command",
            "sprite_initialization_sequence": list(SPRITE_IDS),
            "outcome_field_offset": "0x327e",
            "official_label_crosswalk": "resolved for ordinary/default mode by the native result highword branches, sprite initializer IDs, and glow descriptor UVs; nonzero forced scenario modes retain their caller-owned event slots",
        },
        "selection_label_crosswalk": _native_selection_crosswalk(elf, frames, slot_values, calls),
        "scenario_slot_initialization": _scenario_event_slot_initialization(elf, slot_values),
        "wheel_variant_routing": _wheel_variant_routing(elf, frames),
        "resource_binding": _resource_binding(elf),
        "adv_task_creation_route": _adv_creation_route(elf, calls),
        "task_command_label_branches": _mode_branches(elf),
        "group1": {"registry_va": "0x485240", "group1_va": "0x4805e0",
                   "resource_records": frames, "resource_count": len(frames),
                   "total_frames": sum(r["frame_count"] for r in frames),
                   "wheel_frame_labels": WHEEL_FRAME_LABELS,
                   "single_label_resources": SINGLE_LABELS,
                   "variant_observations": {"atlas_08": "same eight glow resources",
                                            "atlas_10": "paired label variants"}},
        "coverage_limits": {
            "direct_calls": "Word-aligned JAL targets across the ELF; this is not proof of all indirect callers.",
            "indirect_event_routes": "Not closed: runtime callback/actor registration and dynamic event selection remain indirect.",
            "execution": "Optional bounded Unicorn function execution covers selector modes, fallback, and unfinished states only; it does not emulate graphics, task scheduling, or full game runtime.",
            "textures": "Frame descriptors are covered; source texture pixel coverage belongs to the art-owned patch/tests.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elf", type=Path, default=Path(__file__).resolve().parents[1] /
                        "local/r67-15k-description-word-wrap.elf")
    parser.add_argument("--output", type=Path, required=True,
                        help="write the deterministic JSON evidence snapshot")
    args = parser.parse_args()
    proof = verify(args.elf.read_bytes())
    args.output.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
