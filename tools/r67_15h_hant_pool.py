"""Relocate the native H.A.N.T. text-handle pool and enforce its row bounds."""
from __future__ import annotations

import hashlib
import struct

from tools.r67_chamber_story_text_only import Assembly, _i, _jal


ELF_BIAS = 0xFFF80
TRANSLATION_FO = 0x803150
TRANSLATION_VA = 0x902F00
TRANSLATION_RESERVE = 0x100000
SOURCE_SHA256 = "74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee"

OLD_POOL_BASE = 0x17A0
POOL_BASE = 0x1A94
POOL_CAPACITY = 19
OLD_ALLOCATION_SIZE = 0x1A94
ALLOCATION_SIZE = 0x1AE0
ROW_CAPACITY = 80
VISIBLE_MIN_Y = 89
VISIBLE_MAX_Y = 383
SUPPORTED_ROW_PITCHES = (16, 21)

# Named half-open ranges in the existing ELF. These are the only existing
# instruction words this transform owns; offsets are ELF file offsets.
ALLOWED_SOURCE_RANGES = {
    "reset_pool_base_addiu": ((0x28FD9C - ELF_BIAS, 0x28FDA0 - ELF_BIAS),),
    "reset_pool_base_load": ((0x28FDA0 - ELF_BIAS, 0x28FDA4 - ELF_BIAS),),
    "reset_pool_capacity": ((0x28FDC8 - ELF_BIAS, 0x28FDCC - ELF_BIAS),),
    "visible_pool_base_addiu": ((0x28FE94 - ELF_BIAS, 0x28FE98 - ELF_BIAS),),
    "visible_pool_base_load": ((0x28FE98 - ELF_BIAS, 0x28FE9C - ELF_BIAS),),
    "visible_pool_capacity": ((0x28FE3C - ELF_BIAS, 0x28FE40 - ELF_BIAS),),
    "visible_pool_null_guard": ((0x28FE9C - ELF_BIAS, 0x28FEA0 - ELF_BIAS),),
    "visible_x_position_load": ((0x28FEA0 - ELF_BIAS, 0x28FEA4 - ELF_BIAS),),
    "visible_x_setter_call": ((0x28FEA4 - ELF_BIAS, 0x28FEA8 - ELF_BIAS),),
    "visible_capacity_guard": ((0x28FE48 - ELF_BIAS, 0x28FE50 - ELF_BIAS),),
    "row_count_load": ((0x28FDD4 - ELF_BIAS, 0x28FDD8 - ELF_BIAS),),
    "row_count_limit": ((0x28FDD8 - ELF_BIAS, 0x28FDDC - ELF_BIAS),),
    "row_count_branch": ((0x28FDDC - ELF_BIAS, 0x28FDE0 - ELF_BIAS),),
    "row_capacity_branch": ((0x28FE60 - ELF_BIAS, 0x28FE64 - ELF_BIAS),),
    "row_capacity_guard": ((0x28FE64 - ELF_BIAS, 0x28FE70 - ELF_BIAS),),
    "allocate_count_compare": ((0x290884 - ELF_BIAS, 0x290888 - ELF_BIAS),),
    "allocate_count_cap": ((0x290890 - ELF_BIAS, 0x290894 - ELF_BIAS),),
    "allocate_pool_store": ((0x290914 - ELF_BIAS, 0x290918 - ELF_BIAS),),
    "fade_pool_base_addiu": ((0x290EE4 - ELF_BIAS, 0x290EE8 - ELF_BIAS),),
    "fade_pool_base_load": ((0x290EE8 - ELF_BIAS, 0x290EEC - ELF_BIAS),),
    "fade_pool_capacity": ((0x290F10 - ELF_BIAS, 0x290F14 - ELF_BIAS),),
    "owner_allocation_size": ((0x291DE0 - ELF_BIAS, 0x291DE4 - ELF_BIAS),),
    "owner_allocation_success_branch": ((0x291E00 - ELF_BIAS, 0x291E04 - ELF_BIAS),),
    "owner_pool_clear_call": ((0x291E08 - ELF_BIAS, 0x291E0C - ELF_BIAS),),
    "owner_pool_clear_delay": ((0x291E0C - ELF_BIAS, 0x291E10 - ELF_BIAS),),
}
_PT_LOAD_FILESZ_RANGE = (0x64, 0x68)

_PREIMAGES = {
    0x28FD9C: 0x245217A0,
    0x28FDA0: 0x8C4417A0,
    0x28FDC8: 0x2A230010,
    0x28FE3C: 0x2AA20010,
    0x28FE48: 0x3C040069,
    0x28FE4C: 0x24848C18,
    0x28FDD4: 0x0000A82D,
    0x28FDD8: 0x0000A02D,
    0x28FDDC: 0x1000003C,
    0x28FE5C: 0x2A820050,
    0x28FE60: 0x14400006,
    0x28FE64: 0x00000000,
    0x28FE68: 0x3C040069,
    0x28FE6C: 0x24848C18,
    0x28FE94: 0x245217A0,
    0x28FE98: 0x8C4417A0,
    0x28FE9C: 0xC62C0120,
    0x28FEA0: 0x0C062AAC,
    0x28FEA4: 0x00000000,
    0x28FEA8: 0x8E440000,
    0x28FEAC: 0xC62C0124,
    0x28FEB0: 0x0C062AB8,
    0x28FEB4: 0x00000000,
    0x28FEB8: 0x8E440000,
    0x28FEBC: 0x26250128,
    0x28FEC0: 0x0C062820,
    0x28FEC4: 0x00000000,
    0x290884: 0x2A020010,
    0x290890: 0x24100010,
    0x290914: 0xAC6217A0,
    0x290EE4: 0x245317A0,
    0x290EE8: 0x8C4417A0,
    0x290F10: 0x2A220010,
    0x291DE0: 0x24051A94,
    0x291E00: 0x16000004,
    0x291E04: 0x00000000,
    0x291E08: 0x0000102D,
    0x291E0C: 0x10000091,
}
_PITCH_PREIMAGES = {
    0x2903B0: 0x3C0341A8,
    0x2904A0: 0x3C0241A8,
    0x290578: 0x3C0341A8,
    0x29063C: 0x3C0241A8,
    0x29073C: 0x3C0241A8,
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clear_tail_helper() -> bytes:
    m = Assembly()
    m.emit(_i(9, 16, 8, POOL_BASE))       # t0 = allocated owner + relocated pool
    m.emit(_i(9, 0, 9, POOL_CAPACITY))    # t1 = 19 slots
    m.label("clear")
    m.emit(_i(43, 8, 0, 0))               # sw zero,0(t0)
    m.emit(_i(9, 8, 8, 4))                # addiu t0,t0,4
    m.emit(_i(9, 9, 9, -1))               # addiu t1,t1,-1
    m.branch(5, 9, 0, "clear")
    m.emit(0)
    m.emit(0x03E00008)                    # jr ra
    m.emit(0)
    return m.done()


def _segments(source: bytes) -> tuple[int, int, int, int, int]:
    if len(source) < 0x80 or source[:4] != b"\x7fELF":
        raise ValueError("r67.15h H.A.N.T. pool ELF is malformed")
    phoff = struct.unpack_from("<I", source, 28)[0]
    phentsize, phnum = struct.unpack_from("<HH", source, 42)
    if phentsize != 32 or phoff + phentsize * phnum > len(source):
        raise ValueError("translation PT_LOAD program-header table is malformed")
    candidates = [
        struct.unpack_from("<8I", source, phoff + index * phentsize)
        for index in range(phnum)
    ]
    matches = [entry for entry in candidates if entry[0] == 1 and entry[2] == TRANSLATION_VA]
    if len(matches) != 1:
        raise ValueError("translation PT_LOAD identity changed")
    _kind, p_offset, p_vaddr, _paddr, p_filesz, p_memsz, p_flags, _align = matches[0]
    if (p_offset, p_vaddr, p_filesz, p_memsz, p_flags) != (
        TRANSLATION_FO, TRANSLATION_VA, len(source) - TRANSLATION_FO,
        TRANSLATION_RESERVE, 7,
    ):
        raise ValueError("translation PT_LOAD geometry or source extent changed")
    return p_offset, p_vaddr, p_filesz, p_memsz, p_flags


def _check_preimages(source: bytes) -> None:
    _segments(source)
    for address, expected in _PREIMAGES.items():
        offset = address - ELF_BIAS
        if offset < 0 or offset + 4 > len(source):
            raise ValueError(f"H.A.N.T. pool instruction outside ELF at {address:#x}")
        actual = struct.unpack_from("<I", source, offset)[0]
        if actual != expected:
            raise ValueError(
                f"H.A.N.T. pool owned instruction changed at {address:#x}: "
                f"expected {expected:#010x}, found {actual:#010x}"
            )
    for address, expected in _PITCH_PREIMAGES.items():
        if struct.unpack_from("<I", source, address - ELF_BIAS)[0] != expected:
            raise ValueError(f"H.A.N.T. row-producer pitch preimage changed at {address:#x}")


def build(source: bytes) -> tuple[bytes, dict]:
    """Return a patched ELF and an auditable report without filesystem effects."""
    _check_preimages(source)
    before_sha = _sha(source)
    out = bytearray(source)
    while len(out) & 3:
        out.append(0)
    helper_va = TRANSLATION_VA + len(out) - TRANSLATION_FO
    helper = _clear_tail_helper()
    if helper_va >= 0x10000000 or len(out) + len(helper) - TRANSLATION_FO > TRANSLATION_RESERVE:
        raise ValueError("H.A.N.T. pool zero-initializer exceeds translation PT_LOAD")
    out.extend(helper)

    def put(address: int, word: int) -> None:
        struct.pack_into("<I", out, address - ELF_BIAS, word & 0xFFFFFFFF)

    for address in (0x28FD9C, 0x28FE94, 0x290EE4):
        old = _PREIMAGES[address]
        put(address, (old & 0xFFFF0000) | POOL_BASE)
    for address in (0x28FDA0, 0x28FE98, 0x290EE8):
        old = _PREIMAGES[address]
        put(address, (old & 0xFFFF0000) | POOL_BASE)
    put(0x28FDC8, (_PREIMAGES[0x28FDC8] & 0xFFFF0000) | POOL_CAPACITY)
    put(0x28FE3C, (_PREIMAGES[0x28FE3C] & 0xFFFF0000) | POOL_CAPACITY)
    put(0x290884, (_PREIMAGES[0x290884] & 0xFFFF0000) | POOL_CAPACITY)
    put(0x290890, _i(9, 0, 16, POOL_CAPACITY))
    put(0x290914, (_PREIMAGES[0x290914] & 0xFFFF0000) | POOL_BASE)
    put(0x290F10, (_PREIMAGES[0x290F10] & 0xFFFF0000) | POOL_CAPACITY)
    put(0x291DE0, _i(9, 0, 5, ALLOCATION_SIZE))

    # On an overfull visible set, advance to the next native row before any
    # pool read. The verified native producers have minimum pitch 16, yielding
    # at most 19 rows in the strict 89<Y<383 viewport.
    put(0x28FE48, _i(4, 0, 0, (0x28FECC - (0x28FE48 + 4)) // 4))
    put(0x28FE4C, 0)

    # Validate total row count before entering the loop that reads row X/Y.
    put(0x28FDD4, _i(35, 19, 2, 0x1A78))
    put(0x28FDD8, _i(11, 2, 2, ROW_CAPACITY + 1))
    put(0x28FDDC, _i(4, 2, 0, (0x28FEE0 - (0x28FDDC + 4)) // 4))

    # The null check has a safe coordinate-load delay slot. A real child then
    # runs the X setter with its handle restored in the call delay slot.
    put(0x28FE9C, _i(4, 4, 0, (0x28FEC8 - (0x28FE9C + 4)) // 4))
    put(0x28FEA0, _PREIMAGES[0x28FE9C])
    put(0x28FEA4, _PREIMAGES[0x28FEA0])

    # A failed owner allocation follows the original zero-return epilogue;
    # successful allocation clears all 19 pool slots before child creation.
    put(0x291E00, _i(4, 16, 0, (0x292054 - (0x291E00 + 4)) // 4))
    put(0x291E08, _jal(helper_va))
    put(0x291E0C, 0)

    new_size = len(out) - TRANSLATION_FO
    if new_size > TRANSLATION_RESERVE:
        raise ValueError("translation PT_LOAD memory reservation exceeded")
    struct.pack_into("<I", out, 0x64, new_size)

    allowed = {offset for spans in ALLOWED_SOURCE_RANGES.values()
               for start, end in spans for offset in range(start, end)}
    allowed.update(range(*_PT_LOAD_FILESZ_RANGE))
    changed = [offset for offset, (old, new) in enumerate(zip(source, out)) if old != new]
    unexpected = [offset for offset in changed if offset not in allowed]
    if unexpected:
        raise ValueError(
            "unexpected existing-ELF change outside named H.A.N.T. ownership: "
            + ", ".join(hex(offset) for offset in unexpected[:12])
        )
    if len(out) < len(source):
        raise ValueError("H.A.N.T. pool transform truncated its source")

    modified_existing_offsets = [
        hex(offset) for offset, (old, new) in enumerate(zip(source, out[:len(source)]))
        if old != new
    ]
    report = {
        "schema_version": 1,
        "status": "STATIC_DIAGNOSTIC_ONLY",
        "source_sha256": before_sha,
        "source_matches_known_15g_elf": before_sha == SOURCE_SHA256,
        "output_sha256": _sha(bytes(out)),
        "pool_base": hex(POOL_BASE),
        "pool_capacity": POOL_CAPACITY,
        "old_pool_base": hex(OLD_POOL_BASE),
        "old_allocation_size": hex(OLD_ALLOCATION_SIZE),
        "allocation_size": hex(ALLOCATION_SIZE),
        "allocation_tail_zeroed_by_helper": True,
        "pool_zero_initializer_va": hex(helper_va),
        "pool_zero_initializer_bytes": len(helper),
        "modified_existing_offsets": modified_existing_offsets,
        "native_row_pitches": list(SUPPORTED_ROW_PITCHES),
        "minimum_native_row_pitch": min(SUPPORTED_ROW_PITCHES),
        "strict_visible_y_bounds": [VISIBLE_MIN_Y, VISIBLE_MAX_Y],
        "maximum_eligible_rows": (VISIBLE_MAX_Y - VISIBLE_MIN_Y + min(SUPPORTED_ROW_PITCHES) - 1)
        // min(SUPPORTED_ROW_PITCHES),
        "row_record_capacity": ROW_CAPACITY,
        "pool_owners": ["constructor", "viewport-reset", "viewport-selection", "fade-loop"],
        "allowed_source_ranges": {
            name: [[hex(start), hex(end)] for start, end in spans]
            for name, spans in ALLOWED_SOURCE_RANGES.items()
        },
        "appended_extent": [len(source), len(out)],
        "translation_segment_filesz": new_size,
        "runtime_verified": False,
        "door_loading_hang_resolved": False,
        "runtime_assumptions": [
            "native row producers retain the pinned 16- and 21-pixel pitches",
            "the selected source row data follows the verified 80-record owner contract",
            "child teardown remains owned by the existing H.A.N.T. task registration",
        ],
    }
    return bytes(out), report
