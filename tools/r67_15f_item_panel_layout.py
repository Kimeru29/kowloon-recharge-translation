"""r67.15f native H_Item backing geometry for Compound and Can't.

Starts from the exact diagnostic 15e ELF. The 2D action sprite is created at
VA 0x114A20 after its X coordinate has been initialized. This helper sets the
per-action horizontal scale and applies the inverse pivot displacement to the
sprite's live X field. The native 2D projection guard bypasses its X/Y rewrite,
so the position remains stable through the action's state-1 fade updates.

The shared item-title constructor receives an instance-only scale/space wrapper
that uses the native setter to rebuild geometry. Only the two approved callsite
words and translation PT_LOAD p_filesz may change in the existing image; both
helpers are append-only.
"""
from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q_MANIFEST
from tools.r67_14t_approved_ui_lock import verify_ui, MANIFEST as T_MANIFEST
from tools.r67_14y_inspection_save import validate_result
from tools.r67_14y_release import verify_save_identity
from tools.r67_history_layout_lock import read_lock, verify_bytes
from tools.r67_chamber_story_text_only import Assembly, _i, _r, _jal, _float_word


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = ROOT / "local/r67-15e-compound-bubble.elf"
SOURCE_SHA = "d1dc87b0762465f4aa653e05e07af73cc593d4e716ee2575790edc617a54972e"
BASE_SHA = SOURCE_SHA
FO = 0x803150
VA = 0x902F00
BIAS = 0xFFF80
RESERVE = 0x100000

ACTION_HOOK_SITE = 0x114AD8
ACTION_HOOK_FILE_OFFSET = 0x14B58
ACTION_HOOK_15E = 0x0825924F  # j 0x96493c
ACTION_HOOK_DELAY = 0
RESUME = 0x114B00

ACTION_OWNER_OFFSET = 0x18
SPRITE_OWNER_OFFSET = 0x00
SPRITE_X_OFFSET = 0x3C
SPRITE_Y_OFFSET = 0x40
SPRITE_SCALE_X_OFFSET = 0x60
SPRITE_SCALE_Y_OFFSET = 0x64
COMPOUND_ACTION_ID = 3
CANT_ACTION_ID = 1
COMPOUND_SCALE = 2.0
CANT_SCALE = 1.25
PIVOT_X = -29.0
COMPOUND_X_DELTA = -29.0
CANT_X_DELTA = -7.25

TITLE_HOOK_SITE = 0x10DAC4
TITLE_HOOK_FILE_OFFSET = 0xDB44
TITLE_ORIGINAL_JAL = 0x0C062790
TITLE_TEXT_CONSTRUCTOR = 0x189E40
TITLE_SETTER = 0x18B120
TITLE_LAYOUT_REBUILDER = 0x18CB50
TITLE_BUDGET = 196
TITLE_SCALE_CAP = 0.625
TITLE_SCALE_Y = 0.75
TITLE_MAX_NODES = 64
SPACE_FULLWIDTH_CONTROL = 0xFF0B
SPACE_HALFWIDTH_CONTROL = 0xFF0A

PERMITTED_EXISTING_RANGES = {
    "action_backing_creation_hook": ((0x14B58, 0x14B5C),),
    "item_card_title_constructor": ((0xDB44, 0xDB48),),
}
_INTERNAL_PERMITTED_EXISTING_RANGES = {
    **PERMITTED_EXISTING_RANGES,
    "translation_segment_filesz": ((0x64, 0x68),),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_offset(va: int) -> int:
    """Translate an address in the translation PT_LOAD to its ELF offset."""
    return FO + va - VA


def _i(op: int, rs: int, rt: int, immediate: int) -> int:
    return ((op & 0x3F) << 26) | ((rs & 0x1F) << 21) | ((rt & 0x1F) << 16) | (immediate & 0xFFFF)


def _j(va: int) -> int:
    if not 0 <= va < 0x10000000:
        raise ValueError("MIPS jump target is outside the 256 MiB region")
    return (2 << 26) | ((va >> 2) & 0x03FFFFFF)


def _beq(rs: int, rt: int, instruction_index: int, target_index: int) -> int:
    return _i(4, rs, rt, target_index - instruction_index - 1)


def title_metrics(glyph_count: int, space_count: int) -> dict:
    """Return bounded title scale and consumer advance, including native spaces."""
    if glyph_count < 0 or space_count < 0:
        raise ValueError("Title glyph and space counts must be non-negative")
    available = TITLE_BUDGET - 8 * space_count
    if available <= 0:
        raise ValueError("Native halfwidth spaces exceed the title budget")
    scale_x = min(TITLE_SCALE_CAP, available / (16 * glyph_count)) if glyph_count else TITLE_SCALE_CAP
    return {
        "scale_x": scale_x,
        "scale_y": TITLE_SCALE_Y,
        "advance": 16 * scale_x * glyph_count + 8 * space_count,
        "budget": TITLE_BUDGET,
    }


def _cop1_mtc1(rt: int, fs: int) -> int:
    return (17 << 26) | (4 << 21) | (rt << 16) | (fs << 11)


def _cop1_cvt_s_w(fd: int, fs: int) -> int:
    return (17 << 26) | (20 << 21) | (fs << 11) | (fd << 6) | 0x20


def _cop1_div_s(fd: int, fs: int, ft: int) -> int:
    return (17 << 26) | (16 << 21) | (ft << 16) | (fs << 11) | (fd << 6) | 0x03


def build_title_helper() -> bytes:
    """Wrap the shared title constructor and relayout only its generated instance."""
    m = Assembly()
    # Preserve caller frame state. Register arguments and F12/F13 remain
    # untouched until the original native constructor has consumed them.
    m.emit(_i(9, 29, 29, -0x40))
    for reg, offset in ((31, 0x38), (16, 0x30), (17, 0x28),
                        (18, 0x20), (19, 0x18), (20, 0x10)):
        m.emit(_i(63, 29, reg, offset))
    m.emit(_jal(TITLE_TEXT_CONSTRUCTOR))
    m.emit(0)
    m.emit(_r(2, 0, 16, 0, 37))               # s0 = returned title handle
    m.branch(4, 16, 0, "return")
    m.emit(0)
    m.emit(_i(35, 16, 17, 0x3C))              # s1 = handle private data
    m.branch(4, 17, 0, "return")
    m.emit(0)
    m.emit(_i(35, 17, 18, 4))                 # s2 = generated glyph-list head
    m.emit(_i(9, 0, 19, 0))                  # s3 = ordinary glyph count G
    m.emit(_i(9, 0, 20, 0))                  # s4 = fullwidth space count S
    m.emit(_i(9, 0, 13, 0))                  # t5 = bounded traversal count

    m.label("count_nodes")
    m.branch(4, 18, 0, "count_done")
    m.emit(0)
    m.emit(_i(12, 18, 8, 3))                 # reject unaligned/malformed node
    m.branch(5, 8, 0, "return")
    m.emit(0)
    m.emit(_i(9, 13, 13, 1))
    m.emit(_i(10, 13, 8, TITLE_MAX_NODES + 1))
    m.branch(4, 8, 0, "return")
    m.emit(0)
    m.emit(_i(37, 18, 8, 0))                 # lhu t0,control(node)
    m.emit(_i(13, 0, 9, SPACE_FULLWIDTH_CONTROL))
    m.branch(4, 8, 9, "count_space")
    m.emit(0)
    m.emit(_i(9, 19, 19, 1))
    m.branch(4, 0, 0, "count_next")
    m.emit(0)
    m.label("count_space")
    m.emit(_i(9, 20, 20, 1))
    m.label("count_next")
    m.emit(_i(35, 18, 18, 0x120))            # lw s2,next(node)
    m.branch(4, 0, 0, "count_nodes")
    m.emit(0)

    m.label("count_done")
    m.emit(_i(9, 0, 9, TITLE_BUDGET))       # t1 = budget - 8*S
    # Use t0 = S*8; t1 = 196 - t0; reject non-positive available width.
    m.emit(_r(0, 20, 8, 3, 0))              # sll t0,s4,3
    m.emit(_r(9, 8, 9, 0, 35))               # subu t1,t1,t0
    m.emit(_i(10, 9, 8, 1))                 # slti t0,t1,1
    m.branch(5, 8, 0, "return")              # available must be positive
    m.emit(0)
    m.branch(4, 19, 0, "scale_cap")
    m.emit(0)
    m.emit(_r(0, 19, 10, 4, 0))              # t2 = 16*G
    m.emit(_r(0, 19, 11, 3, 0))              # t3 = 8*G
    m.emit(_r(0, 19, 12, 1, 0))              # t4 = 2*G
    m.emit(_r(11, 12, 11, 0, 33))            # t3 = 10*G
    m.emit(_r(9, 11, 12, 0, 42))             # t4 = available < 10*G
    m.branch(5, 12, 0, "scale_ratio")
    m.emit(0)
    m.label("scale_cap")
    m.const(11, 0x3F200000)                 # t3 = 0.625f
    m.emit(_cop1_mtc1(11, 12))              # f12 = capped X scale
    m.branch(4, 0, 0, "normalize_spaces")
    m.emit(0)
    m.label("scale_ratio")
    m.emit(_cop1_mtc1(9, 12))                # f12 = available width
    m.emit(0)
    m.emit(_cop1_cvt_s_w(12, 12))
    m.emit(_cop1_mtc1(10, 14))               # f14 = 16*G
    m.emit(0)
    m.emit(_cop1_cvt_s_w(14, 14))
    m.emit(0)
    m.emit(_cop1_div_s(12, 12, 14))          # min ratio / cap from integer gate
    m.emit(0)

    m.label("normalize_spaces")
    m.emit(_i(35, 17, 18, 4))                # restart at list head
    m.emit(_i(9, 0, 13, 0))
    m.label("normalize_loop")
    m.branch(4, 18, 0, "set_scale")
    m.emit(0)
    m.emit(_i(37, 18, 8, 0))
    m.emit(_i(13, 0, 9, SPACE_FULLWIDTH_CONTROL))
    m.branch(5, 8, 9, "normalize_next")
    m.emit(0)
    m.emit(_i(13, 0, 9, SPACE_HALFWIDTH_CONTROL))
    m.emit(_i(41, 18, 9, 0))                 # sh halfwidth control in this title
    m.label("normalize_next")
    m.emit(_i(35, 18, 18, 0x120))
    m.emit(_i(9, 13, 13, 1))
    m.branch(4, 0, 0, "normalize_loop")
    m.emit(0)

    m.label("set_scale")
    m.emit(_r(16, 0, 4, 0, 37))              # a0 = title handle
    m.const(11, 0x3F400000)                 # f13 = 0.75f
    m.emit(_cop1_mtc1(11, 13))
    m.emit(_jal(TITLE_SETTER))               # existing setter writes +48/+4c and rebuilds
    m.emit(0)
    m.label("return")
    m.emit(_r(16, 0, 2, 0, 37))              # return original title handle in v0
    for reg, offset in ((20, 0x10), (19, 0x18), (18, 0x20),
                        (17, 0x28), (16, 0x30), (31, 0x38)):
        m.emit(_i(55, 29, reg, offset))
    m.emit(_i(9, 29, 29, 0x40))
    m.emit(_r(31, 0, 0, 0, 8))              # return to original caller
    m.emit(0)
    return m.done()


def build_helper() -> bytes:
    """Build a bounded tail helper for only native action IDs 1 and 3.

    It uses the live sprite fields instead of changing shared resource records.
    Both target scales preserve the original left edge through the native
    renderer's pivot formula; null and unrelated actions remain untouched.
    """
    words = (
        _i(35, 16, 8, ACTION_OWNER_OFFSET),   # 0 lw t0,action_id(s0)
        _i(9, 0, 9, COMPOUND_ACTION_ID),      # 1 li t1,3
        _beq(8, 9, 2, 9),                     # 2 beq t0,t1,compound
        0,                                     # 3 delay
        _i(9, 0, 9, CANT_ACTION_ID),          # 4 li t1,1
        _beq(8, 9, 5, 27),                    # 5 beq t0,t1,cant
        0,                                     # 6 delay
        _j(RESUME),                            # 7 j resume
        0,                                     # 8 delay
        _i(35, 16, 8, SPRITE_OWNER_OFFSET),   # 9 lw t0,0(s0)
        _i(4, 8, 0, -4),                      # 10 beqz t0,resume
        0,                                     # 11 delay
        _i(9, 29, 29, -8),                   # 12 addiu sp,sp,-8
        _i(57, 29, 0, 0),                    # 13 swc1 f0,0(sp)
        _i(57, 29, 2, 4),                    # 14 swc1 f2,4(sp)
        _i(15, 0, 9, 0x4000),                # 15 lui t1,0x4000 (2.0f)
        _i(43, 8, 9, SPRITE_SCALE_X_OFFSET),  # 16 sw t1,0x60(t0)
        _i(49, 8, 0, SPRITE_X_OFFSET),        # 17 lwc1 f0,0x3c(t0)
        _i(15, 0, 9, 0xC1E8),                # 18 lui t1,0xc1e8 (-29.0f)
        0x44891000,                           # 19 mtc1 t1,f2
        0x46020000,                           # 20 add.s f0,f0,f2
        _i(57, 8, 0, SPRITE_X_OFFSET),        # 21 swc1 f0,0x3c(t0)
        _i(49, 29, 0, 0),                    # 22 lwc1 f0,0(sp)
        _i(49, 29, 2, 4),                    # 23 lwc1 f2,4(sp)
        _i(9, 29, 29, 8),                    # 24 addiu sp,sp,8
        _j(RESUME),                            # 25 j resume
        0,                                     # 26 delay
        _i(35, 16, 8, SPRITE_OWNER_OFFSET),   # 27 lw t0,0(s0)
        _i(4, 8, 0, -22),                     # 28 beqz t0,resume
        0,                                     # 29 delay
        _i(9, 29, 29, -8),                   # 30 addiu sp,sp,-8
        _i(57, 29, 0, 0),                    # 31 swc1 f0,0(sp)
        _i(57, 29, 2, 4),                    # 32 swc1 f2,4(sp)
        _i(15, 0, 9, 0x3FA0),                # 33 lui t1,0x3fa0 (1.25f)
        _i(43, 8, 9, SPRITE_SCALE_X_OFFSET),  # 34 sw t1,0x60(t0)
        _i(49, 8, 0, SPRITE_X_OFFSET),        # 35 lwc1 f0,0x3c(t0)
        _i(15, 0, 9, 0xC0E8),                # 36 lui t1,0xc0e8 (-7.25f)
        0x44891000,                           # 37 mtc1 t1,f2
        0x46020000,                           # 38 add.s f0,f0,f2
        _i(57, 8, 0, SPRITE_X_OFFSET),        # 39 swc1 f0,0x3c(t0)
        _i(49, 29, 0, 0),                    # 40 lwc1 f0,0(sp)
        _i(49, 29, 2, 4),                    # 41 lwc1 f2,4(sp)
        _i(9, 29, 29, 8),                    # 42 addiu sp,sp,8
        _j(RESUME),                            # 43 j resume
        0,                                     # 44 delay
    )
    return struct.pack("<45I", *words)


def _verify_prior_approvals(result: bytes) -> dict:
    q_result = verify_approved(result, json.loads(Q_MANIFEST.read_text()))

    # 15a deliberately replaced these two accepted Lion JAL sites. Rebuild
    # their accepted values in memory for the strict t UI lock, as 15e does.
    z_path = ROOT / "local/r67-14z-storeroom-tablet.elf"
    z = z_path.read_bytes()
    expected_z_sha = "c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2"
    if sha(z) != expected_z_sha:
        raise ValueError("Accepted 14z helper source changed")
    reconstructed = bytearray(result)
    for site in (0x2A2A6C, 0x2A6060):
        offset = site - BIAS
        reconstructed[offset:offset + 4] = z[offset:offset + 4]
    t_result = verify_ui(bytes(reconstructed), json.loads(T_MANIFEST.read_text()))
    history = verify_bytes(result, read_lock())
    validate_result(result)
    save_identity = verify_save_identity(result)
    return {
        "q_lock": q_result["status"],
        "t_lock": t_result["status"],
        "history_locked_regions": history,
        "inspection_save_result": "PASS",
        "save_identity": save_identity,
    }


def apply(old: bytes) -> tuple[bytes, dict]:
    """Patch only the exact approved action/title hooks and append helpers."""
    if sha(old) != SOURCE_SHA:
        raise ValueError("Only the exact, audited r67.15e ELF preimage is accepted (SHA mismatch)")
    hook_word = struct.unpack_from("<I", old, ACTION_HOOK_FILE_OFFSET)[0]
    if hook_word != ACTION_HOOK_15E:
        raise ValueError("15e action backing hook preimage drift")
    if struct.unpack_from("<I", old, ACTION_HOOK_FILE_OFFSET + 4)[0] != ACTION_HOOK_DELAY:
        raise ValueError("15e action backing hook delay-slot drift")
    if struct.unpack_from("<I", old, 0x64)[0] != len(old) - FO:
        raise ValueError("Translation PT_LOAD p_filesz does not match the 15e source")
    if struct.unpack_from("<I", old, 0x107F8C - BIAS)[0] != 0xE640003C:
        raise ValueError("Native sprite constructor X-field store changed")
    if struct.unpack_from("<I", old, 0x1076A8 - BIAS)[0] != 0xC622003C:
        raise ValueError("Native action renderer sprite-X load changed")
    if struct.unpack_from("<I", old, 0x1076AC - BIAS)[0] != 0xC6210040:
        raise ValueError("Native action renderer sprite-Y load changed")
    if struct.unpack_from("<I", old, 0x1072B4 - BIAS)[0] != 0xC6220060:
        raise ValueError("Native pivot renderer scaleX load changed")
    if struct.unpack_from("<I", old, 0x1072B8 - BIAS)[0] != 0xC461000C:
        raise ValueError("Native pivot renderer pivotX load changed")
    if struct.unpack_from("<I", old, 0x106F08 - BIAS)[0] != 0x82230092:
        raise ValueError("Native 2D/3D projection guard changed")
    if struct.unpack_from("<I", old, 0x106F10 - BIAS)[0] != 0x1462005E:
        raise ValueError("Native projection branch target changed")
    if struct.unpack_from("<I", old, 0x107000 - BIAS)[0] != 0xE622003C or \
            struct.unpack_from("<I", old, 0x107004 - BIAS)[0] != 0xE6210040:
        raise ValueError("Native projection X/Y rewrite changed")
    if struct.unpack_from("<I", old, 0x108020 - BIAS)[0] != 0xA2400092:
        raise ValueError("Native 2D sprite flag initialization changed")
    if struct.unpack_from("<I", old, TITLE_HOOK_FILE_OFFSET)[0] != TITLE_ORIGINAL_JAL:
        raise ValueError("Shared item-card title constructor callsite changed")
    if struct.unpack_from("<I", old, TITLE_HOOK_FILE_OFFSET + 4)[0] != 0:
        raise ValueError("Shared item-card title constructor delay slot changed")

    helper = build_helper()
    data = bytearray(old)
    while len(data) & 3:
        data.append(0)
    helper_va = VA + len(data) - FO
    data.extend(helper)
    while len(data) & 3:
        data.append(0)
    title_helper = build_title_helper()
    title_helper_va = VA + len(data) - FO
    data.extend(title_helper)
    while len(data) & 3:
        data.append(0)
    if len(data) - FO > RESERVE:
        raise ValueError("Translation PT_LOAD reservation exceeded")

    jump = _j(helper_va)
    struct.pack_into("<I", data, ACTION_HOOK_FILE_OFFSET, jump)
    title_jump = _jal(title_helper_va)
    struct.pack_into("<I", data, TITLE_HOOK_FILE_OFFSET, title_jump)
    struct.pack_into("<I", data, 0x64, len(data) - FO)

    allowed = {offset for ranges in _INTERNAL_PERMITTED_EXISTING_RANGES.values()
               for start, end in ranges for offset in range(start, end)}
    existing_changes = {i for i, (before, after) in enumerate(zip(old, data))
                        if before != after}
    if not existing_changes or existing_changes - allowed:
        raise ValueError(f"Unexpected existing ELF edits: {existing_changes - allowed}")

    result = bytes(data)
    lock_result = _verify_prior_approvals(result)
    return result, {
        "status": "DIAGNOSTIC_NATIVE_ITEM_PANEL_LAYOUT",
        "source_sha256": SOURCE_SHA,
        "result_sha256": sha(result),
        "source_bytes": len(old),
        "result_bytes": len(result),
        "helper_va": hex(helper_va),
        "helper_bytes": len(helper),
        "title_helper_va": hex(title_helper_va),
        "title_helper_bytes": len(title_helper),
        "hook_site_va": hex(ACTION_HOOK_SITE),
        "hook_jump_word": hex(jump),
        "title_hook_site_va": hex(TITLE_HOOK_SITE),
        "title_hook_jump_word": hex(title_jump),
        "resume_va": hex(RESUME),
        "compound_action_id": COMPOUND_ACTION_ID,
        "compound_scale_x": COMPOUND_SCALE,
        "compound_sprite_x_delta": COMPOUND_X_DELTA,
        "cant_action_id": CANT_ACTION_ID,
        "cant_scale_x": CANT_SCALE,
        "cant_sprite_x_delta": CANT_X_DELTA,
        "native_2d_sprite_flag": "byte +0x92 is cleared; projection rewrite is bypassed",
        "state_1_fade_keeps_native_sprite_xy": True,
        "item_title_constructor_shared_by_regular_and_equipped_cards": True,
        "item_title_budget_pixels": TITLE_BUDGET,
        "item_title_scale_x_cap": TITLE_SCALE_CAP,
        "item_title_scale_y": TITLE_SCALE_Y,
        "item_title_space_control_normalized_instance_only": [
            hex(SPACE_FULLWIDTH_CONTROL), hex(SPACE_HALFWIDTH_CONTROL)],
        "item_title_setter_rebuilds_instance_geometry": hex(TITLE_SETTER),
        "item_title_layout_rebuilder": hex(TITLE_LAYOUT_REBUILDER),
        "actual_runtime_scissor_not_proven": True,
        "internal_translation_segment_filesz_range": ["0x64", "0x68"],
        "permitted_existing_ranges": {
            name: [[hex(start), hex(end)] for start, end in ranges]
            for name, ranges in PERMITTED_EXISTING_RANGES.items()
        },
        "existing_elf_changed_offsets": [hex(i) for i in sorted(existing_changes)],
        "prior_approval_locks": lock_result,
        "gameplay_approved": False,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite diagnostic files")
    patched, report = apply(args.input.read_bytes())
    args.output.write_bytes(patched)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in
                      ("result_sha256", "helper_va", "helper_bytes")}, sort_keys=True))
