from __future__ import annotations

from dataclasses import dataclass
import struct

from tools.companion_hud_data import COMPANION_ACTION_DATA, COMPANION_COMMENT_DATA
from tools.executable_text import ExecutableTextResult, RelocatedText
from tools.localization import encode_ps2_english


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_MAX_STRING_BYTES = 512

# r31-r37 presentation owners for the persistent companion action caption.
# r35 proved the accepted one-line 224x48 down-tail presentation. r36 added
# generic wrapping, while r37 corrects the runtime selector to use the game's
# real action-id getter instead of misreading HUD+0x2D0 (the companion-slot
# index). The original two-slot X/Y table remains pristine and still positions
# the bubble independently for companion slot 1 or 2.
COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET = 0x380E30
COMPANION_ACTION_BUBBLE_METADATA_VA = 0x00450AC0
COMPANION_ACTION_BUBBLE_WIDTH_OFFSET = 0x350B44
COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET = 0x350B48
COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET = 0x350B4C
COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET = 0x350B50
COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY = (288.0, 80.0, 67.0, 77.0)
COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY = (224.0, 48.0, 52.0, 45.0)
COMPANION_SLOT_POSITION_TABLE_OFFSET = 0x3F8E80
COMPANION_SLOT_POSITIONS = ((172.0, 407.0), (230.0, 407.0))
COMPANION_ACTION_ID_GETTER_VA = 0x0012FEE0
COMPANION_ACTION_ID_KEY = 0x8000
COMPANION_ACTION_MAX_CELLS = 17
COMPANION_ACTION_MAX_LINES = 4
COMPANION_ACTION_LINE_STEP = 16.0
COMPANION_ACTION_LAYOUT_TABLE_KEY = "companion_action_layout_table"
COMPANION_ACTION_RUNTIME_STATE_KEY = "companion_action_runtime_text_y"
COMPANION_ACTION_RUNTIME_HOOK_KEY = "companion_action_layout_hook"
COMPANION_ACTION_RUNTIME_HOOK_SIZE = 132

# Static owners that are independent of the current action id. The resource
# selection and text-Y load are patched after translation allocation because
# they need addresses inside the relocated executable segment.
COMPANION_ACTION_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x666F0, 0x3C024140, 0x3C024080),  # tail-tip X: +12.0 -> +4.0
    (0x66708, 0x3C02C1E8, 0x3C02C274),  # tail-tip Y: -29.0 -> -61.0
    (0x66804, 0x3C024244, 0x3C02C210),  # text X: +49.0 -> -36.0
    (0x6686C, 0x0000282D, 0x24050001),  # style 0 (16px) -> style 1 (12px)
)
COMPANION_ACTION_RUNTIME_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x66724, 0x24040002),  # li a0,2
    (0x66728, 0x24050018),  # li a1,0x18
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


def _runtime_hook_bytes(*, table_va: int, state_va: int) -> bytes:
    table_hi, table_lo = _split_address(table_va)
    state_hi, state_lo = _split_address(state_va)

    # The pristine renderer proves HUD+0x2D0 is only the 0/1 companion-slot
    # index: it scales that value by eight and indexes the two-entry position
    # table at 0x4F8E00. The actual action id comes from the same read-only
    # getter used later by the original caption renderer: getter(0x8000), then
    # low-16 normalization via ANDI/XORI 0x8000 before indexing the 31 pointers.
    # Preserve ra across the nested JAL and restore a0=2/a1=0x68 for the
    # original group-2 bubble constructor after returning from this hook.
    words = (
        _mips_i(0x09, 29, 29, -16),         # addiu sp,sp,-16
        _mips_i(0x2B, 29, 31, 12),          # sw ra,12(sp)
        _mips_i(0x0D, 0, 4, COMPANION_ACTION_ID_KEY),  # ori a0,zero,0x8000
        _jal_word(COMPANION_ACTION_ID_GETTER_VA),       # jal action-id getter
        0x00000000,                         # nop
        _mips_i(0x0C, 2, 2, 0xFFFF),        # andi v0,v0,0xffff
        _mips_i(0x0E, 2, 2, COMPANION_ACTION_ID_KEY),  # xori v0,v0,0x8000
        _mips_i(0x0B, 2, 3, len(COMPANION_ACTION_LAYOUTS)),  # sltiu v1,v0,31
        _mips_i(0x05, 3, 0, 2),            # bne v1,zero,valid
        0x00000000,                         # nop
        _mips_r(0, 0, 2, 0, 0x21),         # addu v0,zero,zero (fallback id 0)
        _mips_r(0, 2, 3, 3, 0x00),         # sll v1,v0,3
        _mips_r(0, 2, 8, 2, 0x00),         # sll t0,v0,2
        _mips_r(3, 8, 3, 0, 0x21),         # addu v1,v1,t0 (id * 12)
        _mips_i(0x0F, 0, 8, table_hi),      # lui t0,hi(table)
        _mips_i(0x09, 8, 8, table_lo),      # addiu t0,t0,lo(table)
        _mips_r(8, 3, 8, 0, 0x21),         # addu t0,t0,v1
        _mips_i(0x0F, 0, 9, 0x0045),       # lui t1,0x45
        _mips_i(0x09, 9, 9, 0x0AC8),       # addiu t1,t1,0xac8 (height)
        _mips_i(0x23, 8, 10, 0),            # lw t2,0(t0) height
        _mips_i(0x2B, 9, 10, 0),            # sw t2,0(t1)
        _mips_i(0x23, 8, 10, 4),            # lw t2,4(t0) pivot_y
        _mips_i(0x2B, 9, 10, 8),            # sw t2,8(t1)
        _mips_i(0x23, 8, 10, 8),            # lw t2,8(t0) text_y
        _mips_i(0x0F, 0, 9, state_hi),      # lui t1,hi(state)
        _mips_i(0x09, 9, 9, state_lo),      # addiu t1,t1,lo(state)
        _mips_i(0x2B, 9, 10, 0),            # sw t2,0(t1)
        _mips_i(0x23, 29, 31, 12),          # lw ra,12(sp)
        _mips_i(0x09, 29, 29, 16),          # addiu sp,sp,16
        _mips_i(0x09, 0, 4, 2),             # li a0,2
        _mips_i(0x09, 0, 5, 0x0068),        # li a1,0x68
        _mips_r(31, 0, 0, 0, 0x08),         # jr ra
        0x00000000,                         # nop
    )
    code = b"".join(struct.pack("<I", word) for word in words)
    if len(code) != COMPANION_ACTION_RUNTIME_HOOK_SIZE:
        raise AssertionError(f"companion runtime hook size drifted: {len(code)}")
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


def validate_companion_hud_source(raw: bytes) -> None:
    if len(COMPANION_COMMENT_LINES) != 1650:
        raise ValueError(f"companion comment corpus size drifted: {len(COMPANION_COMMENT_LINES)}")
    if sum(len(spec.pointer_offsets) for spec in COMPANION_COMMENT_LINES) != 1784:
        raise ValueError("companion comment pointer-alias count drifted")
    if len(COMPANION_ACTION_LABELS) != 31:
        raise ValueError(f"companion action corpus size drifted: {len(COMPANION_ACTION_LABELS)}")

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


def patch_companion_action_layout(raw: bytes) -> bytes:
    """Apply the static portion of the generic r37 companion-action layout."""

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

    bubble_metadata_va, bubble_record_count = struct.unpack_from(
        "<II", raw, COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET
    )
    if (bubble_metadata_va, bubble_record_count) != (COMPANION_ACTION_BUBBLE_METADATA_VA, 1):
        raise ValueError(
            "companion action bubble resource-table drifted: "
            f"expected ({COMPANION_ACTION_BUBBLE_METADATA_VA:#010x}, 1), "
            f"got ({bubble_metadata_va:#010x}, {bubble_record_count})"
        )

    bubble_geometry = (
        struct.unpack_from("<f", raw, COMPANION_ACTION_BUBBLE_WIDTH_OFFSET)[0],
        struct.unpack_from("<f", raw, COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET)[0],
        struct.unpack_from("<f", raw, COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET)[0],
        struct.unpack_from("<f", raw, COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET)[0],
    )
    if bubble_geometry != COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY:
        raise ValueError(
            "companion action bubble geometry drifted: "
            f"expected {COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY!r}, got {bubble_geometry!r}"
        )

    for offset, expected in COMPANION_ACTION_RUNTIME_PREIMAGES:
        if offset < 0 or offset + 4 > len(raw):
            raise ValueError(f"companion action runtime owner is outside executable: {offset:#x}")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                "companion action runtime preimage mismatch: "
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

    # Install the accepted one-line geometry as the deterministic startup/default
    # state. The runtime hook updates height and pivot-Y before every callout.
    for offset, value in zip(
        (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
        ),
        COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
        strict=True,
    ):
        struct.pack_into("<f", out, offset, value)
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
    except KeyError as exc:
        raise ValueError(f"companion action runtime payload is missing: {exc.args[0]}") from exc

    if table_va & 3 or state_va & 3 or hook_va & 3:
        raise ValueError(
            "companion action runtime payload lost word alignment: "
            f"table={table_va:#x} state={state_va:#x} hook={hook_va:#x}"
        )

    hook = _runtime_hook_bytes(table_va=table_va, state_va=state_va)
    hook_file = installed.info.file_offset + (hook_va - installed.info.segment_vaddr)
    if hook_file < 0 or hook_file + len(hook) > len(result):
        raise ValueError("companion action runtime hook is outside translated executable")
    if result[hook_file:hook_file + len(hook)] != b"\x00" * len(hook):
        raise ValueError("companion action runtime hook placeholder drifted")
    result[hook_file:hook_file + len(hook)] = hook

    for offset, expected in COMPANION_ACTION_RUNTIME_PREIMAGES:
        actual = struct.unpack_from("<I", result, offset)[0]
        if actual != expected:
            raise ValueError(
                "companion action runtime finalizer preimage mismatch: "
                f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
            )

    # Replace the fixed group-2 resource selection with a call into the generic
    # layout selector. Keep li a0,2 in the JAL delay slot.
    struct.pack_into("<I", result, 0x66724, _jal_word(hook_va))
    struct.pack_into("<I", result, 0x66728, 0x24040002)

    # The selector stores the current per-action text-Y float in relocated RWX
    # state. Replace the old immediate-float construction with a direct load.
    state_hi, state_lo = _split_address(state_va)
    struct.pack_into("<I", result, 0x6681C, _mips_i(0x0F, 0, 2, state_hi))
    struct.pack_into("<I", result, 0x66820, _mips_i(0x31, 2, 0, state_lo))
    struct.pack_into("<I", result, 0x66824, 0x00000000)
    # 0x66828 remains the pristine add.s f0,f1,f0.


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
                encoded=struct.pack("<f", COMPANION_ACTION_LAYOUTS[0].text_y),
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
    return tuple(entries)
