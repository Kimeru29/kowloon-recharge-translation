"""Fit live primary ADV body rows and size their private reveal handles."""

from hashlib import sha256
from struct import pack

from tools.r67_15j_item_layout import _float, _fp, _int_float
from tools.r67_chamber_story_text_only import Assembly, ELF_BIAS, _i, _jal, _r
from tools.r67o_choices import _clone, _patch

TEXT_CALL = 0x24EA20
REVEAL_CALL = 0x24EA58
NATIVE_TEXT = 0x18C1D0
NATIVE_REVEAL = 0x18C670
FONT_SET_SCALE = 0x18B120
MAX_GLYPHS = 56
ROW_WIDTH = 488


def _row_fit():
    m = Assembly()
    sp, ra = 29, 31
    font, node, remaining = 8, 9, 10
    glyphs, spaces, wide_spaces = 11, 12, 13
    code, scratch = 14, 15
    m.emit(_i(9, sp, sp, -0x20))
    m.emit(_i(63, sp, ra, 0x18))
    m.emit(_i(43, sp, 4, 0x10))
    m.emit(_jal(NATIVE_TEXT))
    m.emit(0)
    m.emit(_i(35, sp, 4, 0x10))
    m.emit(_i(35, 4, font, 0x3C))
    m.emit(_i(36, font, code, 0x24))
    m.branch(5, code, 0, "return")
    m.emit(_i(35, font, code, 0x0C))
    m.emit(_i(9, 0, scratch, 2))
    m.branch(5, code, scratch, "return")
    m.emit(_i(35, font, code, 0x28))
    m.branch(5, code, 0, "return")
    m.emit(0)

    # One primary row. Count actual converted glyph and spacing nodes.
    m.emit(_i(35, font, node, 4))
    m.emit(_i(9, 0, remaining, MAX_GLYPHS + 1))
    for register in (glyphs, spaces, wide_spaces):
        m.emit(_i(9, 0, register, 0))
    m.label("measure")
    m.branch(4, node, 0, "return")
    m.emit(_i(9, remaining, remaining, -1))
    m.branch(4, remaining, 0, "return")
    m.emit(_i(35, node, code, 0))
    m.emit(_i(9, 0, scratch, -0xF1))  # FF0F end
    m.branch(4, code, scratch, "fit")
    m.emit(_i(9, 0, scratch, -0xF5))  # FF0B fullwidth space
    m.branch(4, code, scratch, "full_space")
    m.emit(_i(9, 0, scratch, -0xF6))  # FF0A compact space
    m.branch(4, code, scratch, "space")
    m.emit(0)
    m.branch(6, code, 0, "return")  # unknown control or invalid glyph
    m.emit(0)
    m.branch(4, 0, 0, "next")
    m.emit(_i(9, glyphs, glyphs, 1))
    m.label("full_space")
    m.emit(_i(9, wide_spaces, wide_spaces, 1))
    m.label("space")
    m.emit(_i(9, spaces, spaces, 1))
    m.label("next")
    m.branch(4, 0, 0, "measure")
    m.emit(_i(35, node, node, 0x120))

    m.label("fit")
    m.branch(4, glyphs, 0, "return")
    m.emit(0)
    # Required unit-scale width = 12 * (2*glyphs + spaces + fullwidth spaces).
    m.emit(_r(0, glyphs, code, 1, 0))
    m.emit(_r(code, spaces, code, 0, 33))
    m.emit(_r(code, wide_spaces, code, 0, 33))
    m.emit(_i(11, code, scratch, ROW_WIDTH // 12 + 1))
    m.branch(5, scratch, 0, "return")
    m.emit(0)
    # Move fullwidth spaces onto the stock compact-space path only for a
    # row that spills. Keep source text, nodes and reveal indices intact.
    m.emit(_i(35, font, node, 4))
    m.emit(_i(9, 0, code, -0xF5))
    m.emit(_i(9, 0, scratch, -0xF6))
    m.emit(_i(9, 0, wide_spaces, -0xF1))
    m.label("compact")
    m.branch(4, node, 0, "scale")
    m.emit(0)
    m.emit(_i(35, node, 3, 0))
    m.branch(4, 3, wide_spaces, "scale")
    m.emit(0)
    m.branch(5, 3, code, "keep")
    m.emit(0)
    m.emit(_i(43, node, scratch, 0))
    m.label("keep")
    m.branch(4, 0, 0, "compact")
    m.emit(_i(35, node, node, 0x120))

    m.label("scale")
    _int_float(m, 0, glyphs)
    _float(m, 1, 24.)
    _fp(m, 2, 1, 0, 1)
    _int_float(m, 2, spaces)
    _float(m, 3, 12.)
    _float(m, 4, float(ROW_WIDTH))
    m.emit(_i(11, spaces, scratch, 31))
    m.branch(5, scratch, 0, "available")
    m.emit(0)
    # Unusually space-heavy rows also need room for the remaining glyphs.
    # Tracking scales these unscaled spaces from twelve to eight.
    _float(m, 3, 8.)
    _float(m, 5, -4.)
    m.emit(_i(57, font, 5, 0x28))
    _fp(m, 2, 5, 5, 0)
    _fp(m, 1, 4, 4, 5)
    _float(m, 5, 4.)  # last glyph still spans the full scaled texture
    _fp(m, 1, 4, 4, 5)
    m.label("available")
    _fp(m, 2, 2, 2, 3)
    _fp(m, 1, 4, 4, 2)
    _fp(m, 3, 12, 4, 1)
    _float(m, 13, 1.)
    _fp(m, 0x3C, 0, 12, 13)
    m.branch(17, 8, 1, "apply")  # bc1t
    m.emit(0)
    _fp(m, 6, 12, 13)
    m.label("apply")
    m.emit(_jal(FONT_SET_SCALE))
    m.emit(0)
    m.label("return")
    m.emit(_i(55, sp, ra, 0x18))
    m.emit(_i(9, sp, sp, 0x20))
    m.emit(0x03E00008)
    m.emit(0)
    return m.done()


def _large_reveal_constructor(source):
    # The unmodified callback and destructor use the leading fields and the
    # first handle array. Expand both initialized arrays in this private copy.
    start = NATIVE_REVEAL
    code = _clone(source, start, 0x18C7AC)
    second_array = 0x18 + 4 * MAX_GLYPHS
    _patch(code, 0x18C6A8 - start, _i(9, 0, 4, second_array + 4 * MAX_GLYPHS))
    _patch(code, 0x18C768 - start, _i(43, 2, 0, second_array))
    _patch(code, 0x18C770 - start, _i(10, 3, 2, MAX_GLYPHS))
    return code


def patch(source: bytes, base: int) -> tuple[bytes, dict[int, tuple[bytes, bytes]]]:
    guards = (
        (0x24EA18, 0x24EA68, "b5e83facd731c63e62b797d77e722d59147f11f0db449949c9ed7f1dc93b54ad"),
        (NATIVE_REVEAL, 0x18C7AC, "2d1b9eebb4b2b565161fee732418d4b43916c2ffe8dbb58818690b2e501e7b02"),
        (0x5D7834, 0x5D7836, "624b0922e0902695d91aeae6db1a2170dff1ad3d2e58e95f0c144c7a6e8479a3"),
    )
    for start, end, expected in guards:
        if sha256(source[start - ELF_BIAS:end - ELF_BIAS]).hexdigest() != expected:
            raise ValueError(f"Primary ADV body preimage differs at {start:#x}")
    fit = _row_fit()
    return fit + _large_reveal_constructor(source), {
        TEXT_CALL - ELF_BIAS: (pack("<I", _jal(NATIVE_TEXT)), pack("<I", _jal(base))),
        REVEAL_CALL - ELF_BIAS: (pack("<I", _jal(NATIVE_REVEAL)), pack("<I", _jal(base + len(fit)))),
    }
