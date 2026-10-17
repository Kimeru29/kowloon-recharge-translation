"""Bounded r67.15h text layout for SELECT Details and synthesis recipe names."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from tools.r67_chamber_story_text_only import Assembly, _i, _jal, _r

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = ROOT / "local/r67-15g-partial-diagnostic.elf"
BASE_SHA256 = "74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee"
APPEND_FILE_OFFSET = 0x803150
APPEND_VA = 0x902F00
APPEND_RESERVE = 0x100000
PT_LOAD_FILESIZE_OFFSET = 0x64
DETAILS_HOOK_OFFSET = 0x1520C
DETAILS_HOOK_WORD = 0x0C25D69E  # existing official-text selection helper
RECIPE_HOOKS = (0x154D8, 0x155CC, 0x1563C)
RECIPE_HOOK_WORD = 0x0C062790  # jal 0x189e40
CONSTRUCTOR_VA = 0x189E40
SETTER_VA = 0x18B120
DETAILS_HELPER_VA = 0x975A78
DETAILS_SCALE = 0.5
RECIPE_NAME_ORIGIN = 39
RECIPE_NUMERIC_ORIGIN = 177
RECIPE_REGION_WIDTH = RECIPE_NUMERIC_ORIGIN - RECIPE_NAME_ORIGIN
RECIPE_NAME_GAP = 8
RECIPE_ICON_RESERVE = 16
RECIPE_MAX_ADVANCE = RECIPE_REGION_WIDTH - RECIPE_NAME_GAP - RECIPE_ICON_RESERVE
RECIPE_SCALE_CAP = 0.5
DETAILS_FONT_HEIGHT = 18.0
DETAILS_LINE_PITCH = 9.0
DETAILS_LINE_SPACING = DETAILS_LINE_PITCH - DETAILS_FONT_HEIGHT
MAX_NODES = 256
SPACE_FULLWIDTH = 0xFF0B
SPACE_HALFWIDTH = 0xFF0A
NEWLINE = 0xFF0E
ALLOWED_SOURCE_RANGES = {
    "details_text_constructor": ((DETAILS_HOOK_OFFSET, DETAILS_HOOK_OFFSET + 4),),
    "recipe_ingredient_constructor": ((RECIPE_HOOKS[0], RECIPE_HOOKS[0] + 4),),
    "recipe_success_result_constructor": ((RECIPE_HOOKS[1], RECIPE_HOOKS[1] + 4),),
    "recipe_failure_result_constructor": ((RECIPE_HOOKS[2], RECIPE_HOOKS[2] + 4),),
}
_APPEND_METADATA_RANGE = (PT_LOAD_FILESIZE_OFFSET, PT_LOAD_FILESIZE_OFFSET + 4)


def recipe_metrics(glyph_count: int, space_count: int) -> dict:
    if glyph_count < 0 or space_count < 0:
        raise ValueError("recipe glyph and space counts must be non-negative")
    available = RECIPE_MAX_ADVANCE - 8 * space_count
    if available <= 0:
        raise ValueError("recipe spaces exceed the reserved name width")
    scale = min(RECIPE_SCALE_CAP, available / (16 * glyph_count)) if glyph_count else RECIPE_SCALE_CAP
    advance = 16 * scale * glyph_count + 8 * space_count
    return {"scale_x": scale, "advance": advance,
            "right_gap": RECIPE_REGION_WIDTH - advance,
            "budget": RECIPE_MAX_ADVANCE, "space_advance": 8}


def _float_word(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _emit_gpr_frame(m: Assembly, *, save: bool) -> None:
    opcode = 0x1F if save else 0x1E  # SQ/LQ preserve the full 128-bit EE GPR.
    for reg in (*range(1, 26), 28, 31):
        m.emit(_i(opcode, 29, reg, reg * 16))


def _emit_fpr_frame(m: Assembly, *, save: bool) -> None:
    opcode = 57 if save else 49  # SWC1/LWC1; FPRs are 32-bit on the EE.
    for reg in range(32):
        m.emit(_i(opcode, 29, reg, 0x200 + reg * 4))


def _validate_translation_load(source: bytes) -> int:
    if source[:4] != b"\x7fELF":
        raise ValueError("r67.15h source is not an ELF image")
    phoff = struct.unpack_from("<I", source, 0x1C)[0]
    entry_size, count = struct.unpack_from("<HH", source, 0x2A)
    if entry_size != 32 or phoff + count * entry_size > len(source):
        raise ValueError("r67.15h program-header table is invalid")
    for index in range(count):
        offset = phoff + index * entry_size
        kind, file_offset, virtual_address, _physical, file_size, memory_size = \
            struct.unpack_from("<6I", source, offset)
        if kind != 1 or file_offset != APPEND_FILE_OFFSET:
            continue
        if virtual_address != APPEND_VA:
            raise ValueError("r67.15h translation PT_LOAD address changed")
        if file_size != len(source) - APPEND_FILE_OFFSET or memory_size < file_size:
            raise ValueError("r67.15h translation PT_LOAD size is inconsistent")
        if file_size > APPEND_RESERVE:
            raise ValueError("r67.15h translation PT_LOAD exceeds its reservation")
        return file_size
    raise ValueError("r67.15h translation PT_LOAD was not found")


def _layout_helper(*, details: bool, helper_va: int) -> bytes:
    """Build a per-handle wrapper; no node is changed until a full valid walk."""
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x300))
    _emit_gpr_frame(m, save=True)
    if details:
        m.emit(_jal(DETAILS_HELPER_VA))
    else:
        m.emit(_jal(CONSTRUCTOR_VA))
    m.emit(0)
    _emit_fpr_frame(m, save=True)
    m.emit(_i(43, 29, 2, 0x2C0))            # keep the original text handle
    m.branch(4, 2, 0, "restore")
    m.emit(0)
    m.emit(_i(35, 2, 8, 0x3C))             # t0 = private text data
    m.branch(4, 8, 0, "restore")
    m.emit(0)
    m.emit(_i(35, 8, 10, 4))               # t2 = linked glyph-stream head
    m.emit(_i(9, 0, 11, 0))                # t3 = ordinary glyph count
    m.emit(_i(9, 0, 12, 0))                # t4 = space count
    m.emit(_i(9, 0, 13, 0))                # t5 = newline count
    m.emit(_i(9, 0, 14, 0))                # t6 = bounded walk count
    m.label("validate")
    m.branch(4, 10, 0, "validated")
    m.emit(0)
    m.emit(_i(11, 10, 15, 0x1000))          # reject pointers below EE heap window
    m.branch(5, 15, 0, "restore")
    m.emit(0)
    m.const(24, 0x02000000)
    m.emit(_i(9, 24, 24, -0x123))            # require room for node+0x120 and next pointer
    m.emit(_r(10, 24, 15, 0, 43))            # sltu t7,node,upper bound
    m.branch(4, 15, 0, "restore")
    m.emit(0)
    m.emit(_i(12, 10, 15, 3))              # reject unaligned node pointers
    m.branch(5, 15, 0, "restore")
    m.emit(0)
    m.emit(_i(9, 14, 14, 1))
    m.emit(_i(10, 14, 15, MAX_NODES + 1))
    m.branch(4, 15, 0, "restore")
    m.emit(0)
    m.emit(_i(37, 10, 15, 0))               # lhu t7,control(node)
    m.const(24, SPACE_FULLWIDTH)
    m.branch(4, 15, 24, "count_space")
    m.emit(0)
    m.const(24, SPACE_HALFWIDTH)
    m.branch(4, 15, 24, "count_space")
    m.emit(0)
    m.const(24, NEWLINE)
    m.branch(4, 15, 24, "count_newline")
    m.emit(0)
    m.emit(_r(0, 15, 24, 8, 2))              # t8 = high byte of node control
    m.emit(_i(9, 0, 25, 0xFF))
    m.branch(4, 24, 25, "invalid_control")
    m.emit(0)
    m.branch(4, 0, 0, "count_ordinary")
    m.emit(0)
    m.label("invalid_control")
    m.branch(4, 0, 0, "restore")
    m.emit(0)
    m.label("count_ordinary")
    m.emit(_i(9, 11, 11, 1))
    m.branch(4, 0, 0, "next_validate")
    m.emit(0)
    m.label("count_space")
    m.emit(_i(9, 12, 12, 1))
    m.branch(4, 0, 0, "next_validate")
    m.emit(0)
    m.label("count_newline")
    m.emit(_i(9, 13, 13, 1))
    m.label("next_validate")
    m.emit(_i(35, 10, 10, 0x120))
    m.branch(4, 0, 0, "validate")
    m.emit(0)
    m.label("validated")

    if not details:
        m.emit(_i(9, 0, 9, RECIPE_MAX_ADVANCE))  # t1 = reserved name width
        m.emit(_r(0, 12, 15, 3, 0))             # t7 = 8*S after normalization
        m.emit(_r(9, 15, 9, 0, 35))             # available = budget - 8*S
        m.emit(_i(10, 9, 15, 1))
        m.branch(5, 15, 0, "restore")
        m.emit(0)
        m.branch(4, 11, 0, "recipe_cap")
        m.emit(0)
        m.emit(_r(0, 11, 15, 3, 0))             # 8*G; ratio < 0.5 iff available < 8*G
        m.emit(_i(11, 9, 24, 0))
        m.emit(_r(9, 15, 24, 0, 43))            # sltu t8,available,8*G
        m.branch(4, 24, 0, "recipe_cap")
        m.emit(0)
        m.emit(_r(0, 11, 24, 4, 0))
        m.emit(_i(17, 4, 9, 12 << 11))          # mtc1 available,f12
        m.emit(_i(17, 4, 24, 14 << 11))         # mtc1 16*G,f14
        m.emit(0)
        m.emit((17 << 26) | (20 << 21) | (12 << 11) | (12 << 6) | 0x20)
        m.emit(0)
        m.emit((17 << 26) | (20 << 21) | (14 << 11) | (14 << 6) | 0x20)
        m.emit(0)
        m.emit((17 << 26) | (16 << 21) | (14 << 16) | (12 << 11) | (12 << 6) | 3)
        m.branch(4, 0, 0, "normalize")
        m.emit(0)
        m.label("recipe_cap")
        m.const(8, _float_word(RECIPE_SCALE_CAP))
        m.emit((17 << 26) | (4 << 21) | (8 << 16) | (12 << 11))
    else:
        m.const(8, _float_word(DETAILS_SCALE))
        m.emit((17 << 26) | (4 << 21) | (8 << 16) | (12 << 11))

    m.label("normalize")
    m.emit(_i(35, 2, 8, 0x3C))
    m.emit(_i(35, 8, 10, 4))
    m.label("normalize_loop")
    m.branch(4, 10, 0, "set_scale")
    m.emit(0)
    m.emit(_i(37, 10, 15, 0))
    m.const(24, SPACE_FULLWIDTH)
    m.branch(5, 15, 24, "normalize_next")
    m.emit(0)
    m.const(24, SPACE_HALFWIDTH)
    m.emit(_i(41, 10, 24, 0))
    m.label("normalize_next")
    m.emit(_i(35, 10, 10, 0x120))
    m.branch(4, 0, 0, "normalize_loop")
    m.emit(0)
    m.label("set_scale")
    m.emit(_i(35, 2, 8, 0x3C))
    if details:
        m.const(24, _float_word(DETAILS_LINE_SPACING))
        m.emit(_i(43, 8, 24, 0x2C))         # height 18 + spacing -9 = 9px pitch
    m.emit(_i(35, 29, 4, 0x2C0))
    m.const(8, _float_word(DETAILS_SCALE))
    m.emit((17 << 26) | (4 << 21) | (8 << 16) | (13 << 11))
    m.emit(_jal(SETTER_VA))
    m.emit(0)
    m.label("restore")
    _emit_fpr_frame(m, save=False)
    for reg in (*range(1, 26), 28, 31):
        m.emit(_i(0x1E, 29, reg, reg * 16))
    m.emit(_i(35, 29, 2, 0x2C0))            # setter clobbers v0; restore exact handle
    m.emit(_i(9, 29, 29, 0x300))
    m.emit(_r(31, 0, 0, 0, 8))
    m.emit(0)
    return m.done()


def build(source: bytes) -> tuple[bytes, dict]:
    actual_sha = hashlib.sha256(source).hexdigest()
    if actual_sha != BASE_SHA256:
        raise ValueError(f"r67.15h source ELF SHA-256 mismatch: {actual_sha}")
    if len(source) < APPEND_FILE_OFFSET:
        raise ValueError("r67.15h source ELF is truncated")
    _validate_translation_load(source)
    if struct.unpack_from("<I", source, DETAILS_HOOK_OFFSET)[0] != DETAILS_HOOK_WORD:
        raise ValueError("r67.15h Details helper hook preimage mismatch")
    if struct.unpack_from("<I", source, DETAILS_HOOK_OFFSET + 4)[0] != 0:
        raise ValueError("r67.15h Details helper delay slot changed")
    for offset in RECIPE_HOOKS:
        if struct.unpack_from("<I", source, offset)[0] != RECIPE_HOOK_WORD:
            raise ValueError(f"r67.15h recipe constructor hook preimage mismatch at {offset:#x}")
        if struct.unpack_from("<I", source, offset + 4)[0] != 0:
            raise ValueError(f"r67.15h recipe constructor delay slot changed at {offset + 4:#x}")

    candidate = bytearray(source)
    while len(candidate) & 3:
        candidate.append(0)
    details_va = APPEND_VA + len(candidate) - APPEND_FILE_OFFSET
    details_helper = _layout_helper(details=True, helper_va=details_va)
    candidate.extend(details_helper)
    while len(candidate) & 3:
        candidate.append(0)
    recipe_va = APPEND_VA + len(candidate) - APPEND_FILE_OFFSET
    recipe_helper = _layout_helper(details=False, helper_va=recipe_va)
    candidate.extend(recipe_helper)
    while len(candidate) & 3:
        candidate.append(0)
    if len(candidate) - APPEND_FILE_OFFSET > APPEND_RESERVE:
        raise ValueError("r67.15h helpers exceed the reserved translation PT_LOAD")

    details_jump = _jal(details_va)
    recipe_jump = _jal(recipe_va)
    struct.pack_into("<I", candidate, DETAILS_HOOK_OFFSET, details_jump)
    for offset in RECIPE_HOOKS:
        struct.pack_into("<I", candidate, offset, recipe_jump)
    struct.pack_into("<I", candidate, PT_LOAD_FILESIZE_OFFSET,
                     len(candidate) - APPEND_FILE_OFFSET)

    changed = {i for i, (before, after) in enumerate(zip(source, candidate[:len(source)]))
               if before != after}
    allowed = {i for spans in ALLOWED_SOURCE_RANGES.values()
                for start, end in spans for i in range(start, end)}
    allowed.update(range(*_APPEND_METADATA_RANGE))
    if changed - allowed:
        raise ValueError(f"r67.15h modified unapproved existing bytes: {sorted(changed - allowed)!r}")
    report = {
        "status": "STATIC_PATCH_BUILT_RUNTIME_UNVERIFIED",
        "source_bytes": len(source),
        "source_sha256": actual_sha,
        "result_bytes": len(candidate),
        "result_sha256": hashlib.sha256(candidate).hexdigest(),
        "details_helper_va": hex(details_va),
        "details_helper_bytes": len(details_helper),
        "recipe_helper_va": hex(recipe_va),
        "recipe_helper_bytes": len(recipe_helper),
        "details_width_budget": 220,
        "details_scale": DETAILS_SCALE,
        "details_font_height": DETAILS_FONT_HEIGHT,
        "details_line_pitch": DETAILS_LINE_PITCH,
        "details_line_spacing": DETAILS_LINE_SPACING,
        "details_origin_y_from_panel": 16,
        "details_recipe_boundary_y_from_panel": 76,
        "details_vertical_available": 60,
        "details_max_measured_rows": 6,
        "details_max_measured_ink_height": 54,
        "recipe_region_width": RECIPE_REGION_WIDTH,
        "recipe_icon_reserve": RECIPE_ICON_RESERVE,
        "recipe_numeric_origin_from_panel": RECIPE_NUMERIC_ORIGIN,
        "recipe_name_origin_from_panel": RECIPE_NAME_ORIGIN,
        "recipe_icon_left_edge_from_panel": RECIPE_NUMERIC_ORIGIN - RECIPE_ICON_RESERVE,
        "recipe_icon_boundary_evidence": "full native 16px font cell reserved before numeric origin",
        "recipe_reserved_gap": RECIPE_NAME_GAP,
        "recipe_width_budget": RECIPE_MAX_ADVANCE,
        "recipe_scale_cap": RECIPE_SCALE_CAP,
        "recipe_line_pitch": DETAILS_FONT_HEIGHT,
        "max_glyph_nodes": MAX_NODES,
        "space_controls": {hex(SPACE_FULLWIDTH): hex(SPACE_HALFWIDTH)},
        "allowed_source_ranges": {
            name: [[hex(start), hex(end)] for start, end in spans]
            for name, spans in ALLOWED_SOURCE_RANGES.items()
        },
        "changed_existing_offsets": [hex(i) for i in sorted(changed)],
        "accepted_card_hook_unchanged": candidate[0xDB44:0xDB48] == source[0xDB44:0xDB48],
        "accepted_bubble_hook_unchanged": candidate[0x14B58:0x14B5C] == source[0x14B58:0x14B5C],
        "runtime_verified": False,
        "gameplay_approved": False,
        "runtime_acceptance_outstanding": True,
        "emulator_or_release_claim": False,
    }
    return bytes(candidate), report
