"""Apply a horizontal fit scale to the native speaker-header font object."""

from struct import pack, unpack_from

from tools.r67_chamber_story_text_only import (
    ELF_BIAS,
    ELF_SEGMENT_FO,
    ELF_SEGMENT_RESERVE,
    ELF_SEGMENT_VA,
    Assembly,
    _float_word,
    _i,
    _jal,
    _r,
)


OWNER_CALL = 0x250010
NATIVE_VISIBILITY = 0x18B100
NATIVE_FONT_SCALE = 0x18B120
VERTICAL_SCALE = 1.0
MAX_NODES = 51
AVAILABLE_WIDTH = 491
FULLWIDTH_SPACE = 0xFFFFFF0B
HALFWIDTH_SPACE = 0xFFFFFF0A
NEWLINE = 0xFFFFFF0E
TERMINATOR = 0xFFFFFF0F


def _cop1_mtc1(rt: int, fs: int) -> int:
    return (17 << 26) | (4 << 21) | (rt << 16) | (fs << 11)


def _cop1_cvt_s_w(fd: int, fs: int) -> int:
    return (17 << 26) | (20 << 21) | (fs << 11) | (fd << 6) | 0x20


def _cop1_div_s(fd: int, fs: int, ft: int) -> int:
    return (17 << 26) | (16 << 21) | (ft << 16) | (fs << 11) | (fd << 6) | 0x03


def _scale_after_visibility(base: int) -> bytes:
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x20))  # addiu sp,sp,-32
    m.emit(_i(63, 29, 31, 0))  # sd ra,0(sp)
    m.emit(_i(43, 29, 4, 8))  # sw a0,8(sp), original text handle
    m.emit(_i(43, 29, 5, 12))  # sw a1,12(sp), visibility duration
    m.emit(_jal(NATIVE_VISIBILITY))
    m.emit(0)
    m.emit(_i(35, 29, 8, 8))  # t0 = handle
    m.branch(4, 8, 0, "done")
    m.emit(0)
    m.emit(_i(35, 8, 9, 0x3C))  # t1 = handle private font data
    m.branch(4, 9, 0, "done")
    m.emit(0)
    m.emit(_i(35, 9, 10, 4))  # t2 = native glyph-list head
    for register in (11, 12, 13, 14):
        m.emit(_i(9, 0, register, 0))

    m.label("scan")
    m.branch(4, 10, 0, "measure")
    m.emit(0)
    m.emit(_i(12, 10, 24, 3))  # Reject an unaligned node.
    m.branch(5, 24, 0, "done")
    m.emit(0)
    m.emit(_i(9, 14, 14, 1))
    m.emit(_i(11, 14, 24, MAX_NODES + 1))
    m.branch(4, 24, 0, "done")  # More than 51 nodes fails closed.
    m.emit(0)
    m.emit(_i(35, 10, 15, 0))  # t7 = native glyph/control word
    m.const(24, 0xFFFFFF00)
    m.emit(_r(15, 24, 25, 0, 36))
    m.branch(5, 25, 24, "glyph")
    m.emit(0)
    for control, label in ((FULLWIDTH_SPACE, "full_space"), (HALFWIDTH_SPACE, "half_space"),
                           (TERMINATOR, "next")):
        m.const(24, control)
        m.branch(4, 15, 24, label)
        m.emit(0)
    m.const(24, NEWLINE)
    m.branch(4, 15, 24, "done")  # Existing multi-line labels are left untouched.
    m.emit(0)
    m.branch(4, 0, 0, "done")  # Unknown native controls are left untouched.
    m.emit(0)

    m.label("glyph")
    m.emit(_i(9, 11, 11, 1))
    m.branch(4, 0, 0, "next")
    m.emit(0)
    m.label("full_space")
    m.emit(_i(9, 12, 12, 1))
    m.branch(4, 0, 0, "next")
    m.emit(0)
    m.label("half_space")
    m.emit(_i(9, 13, 13, 1))
    m.label("next")
    m.emit(_i(35, 10, 10, 0x120))
    m.branch(4, 0, 0, "scan")
    m.emit(0)

    m.label("measure")
    m.branch(4, 11, 0, "done")  # No ordinary glyphs means no safe ratio.
    m.emit(0)
    m.emit(_i(9, 0, 24, AVAILABLE_WIDTH))
    m.emit(_r(0, 12, 25, 4, 0))  # t9 = 16 * fullwidth spaces
    m.emit(_r(24, 25, 24, 0, 35))  # available -= 16 * full spaces
    m.emit(_r(0, 13, 25, 3, 0))  # t9 = 8 * halfwidth spaces
    m.emit(_r(24, 25, 24, 0, 35))  # available -= 8 * half spaces
    m.emit(_i(10, 24, 25, 1))
    m.branch(5, 25, 0, "done")  # At least one ordinary glyph pixel must fit.
    m.emit(0)
    m.emit(_r(0, 11, 25, 4, 0))  # t9 = 16 * ordinary glyphs
    m.emit(_r(24, 25, 15, 0, 43))  # t7 = available < ordinary glyph width
    m.branch(4, 15, 0, "done")  # Already fits; preserve original geometry exactly.
    m.emit(0)
    m.emit(_cop1_mtc1(24, 12))  # f12 = available non-space pixel width
    m.emit(0)
    m.emit(_cop1_cvt_s_w(12, 12))
    m.emit(0)
    m.emit(_cop1_mtc1(25, 14))  # f14 = ordinary glyph width at native scale
    m.emit(0)
    m.emit(_cop1_cvt_s_w(14, 14))
    m.emit(0)
    m.emit(_cop1_div_s(12, 12, 14))  # f12 = max fit ratio, strictly below 1
    m.emit(0)
    m.const(24, _float_word(VERTICAL_SCALE))
    m.emit(_cop1_mtc1(24, 13))
    m.emit(0)
    m.emit(_i(35, 29, 4, 8))
    m.emit(_jal(NATIVE_FONT_SCALE))
    m.emit(0)
    m.label("done")
    m.emit(_i(55, 29, 31, 0))  # ld ra,0(sp)
    m.emit(_i(9, 29, 29, 0x20))
    m.emit(0x03E00008)
    m.emit(0)
    helper = m.done()
    if not base or base & 3 or base >= 0x10000000:
        raise ValueError("Speaker helper address is not a reachable aligned EE VA")
    return helper


def patch(source: bytes, base: int) -> tuple[bytes, dict[int, tuple[bytes, bytes]]]:
    """Return the appended helper and the exact owner-call replacement."""
    if len(source) < ELF_SEGMENT_FO:
        raise ValueError("Speaker source ELF is truncated before its load segment")
    p_offset, p_vaddr, p_paddr = unpack_from("<III", source, 0x58)
    p_filesz, p_memsz, flags = unpack_from("<III", source, 0x64)
    if (p_offset, p_vaddr, p_filesz, p_memsz, flags) != (
        ELF_SEGMENT_FO,
        ELF_SEGMENT_VA,
        len(source) - ELF_SEGMENT_FO,
        ELF_SEGMENT_RESERVE,
        7,
    ) or p_paddr != ELF_SEGMENT_VA:
        raise ValueError("Speaker source load segment or append reserve differs")
    if len(source) - ELF_SEGMENT_FO >= ELF_SEGMENT_RESERVE:
        raise ValueError("Speaker source load segment has no append reserve")

    call_offset = OWNER_CALL - ELF_BIAS
    expected = pack("<I", _jal(NATIVE_VISIBILITY))
    if source[call_offset:call_offset + 8] != expected + b"\0" * 4:
        raise ValueError(f"Speaker owner preimage differs at {OWNER_CALL:#x}")

    helper_offset = (len(source) + 15) & ~15
    minimum_helper_va = ELF_SEGMENT_VA + helper_offset - ELF_SEGMENT_FO
    if base < minimum_helper_va or (base - ELF_SEGMENT_VA) & 3:
        raise ValueError(f"Speaker helper base is before the append point or unaligned: {base:#x}")
    helper = _scale_after_visibility(base)
    if base - ELF_SEGMENT_VA + len(helper) > ELF_SEGMENT_RESERVE:
        raise ValueError("Speaker helper exceeds the reserved ELF segment")

    changes = {call_offset: (expected, pack("<I", _jal(base)))}
    return helper, changes
