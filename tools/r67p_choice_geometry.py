"""Restore stock Japanese choice orientation and fit style-2 fallbacks in place."""
from __future__ import annotations

from struct import pack, unpack_from

from tools.r67_15j_item_layout import _float, _fp, _int_float
from tools.r67_chamber_story_text_only import Assembly, ELF_BIAS, _i, _jal, _r

STOCK_ORIENTATION_CALL = 0x251594
CHOICE_SETTER = 0x2516A8
NATIVE_SCALE = 0x18B120
VIEW_BOTTOM = 444
VERTICAL_ADVANCE = 26
MAX_NODES = 51


def _jump(address: int) -> int:
    return 0x08000000 | (address >> 2)


def _stock_orientation_wrapper(previous_hook: int) -> bytes:
    m = Assembly()
    # The pinned instruction at 0x251588 stays untouched. This owner is
    # stock-only; the existing bridge resets a2 for guarded English records.
    m.emit(_i(9, 0, 6, 1))
    m.emit(_jump(previous_hook))
    m.emit(0)
    m.emit(0x03E00008)
    m.emit(0)
    return m.done()


def _fallback_wrapper(previous_hook: int) -> bytes:
    m = Assembly()
    font, node, remaining = 8, 9, 10
    glyphs, full_spaces, half_spaces = 11, 12, 13
    code, scratch, amount = 14, 15, 3
    m.emit(_i(35, 4, scratch, 0x3C))
    m.emit(_i(35, scratch, scratch, 0x0C))
    m.emit(_i(9, 0, code, 2))
    m.branch(5, scratch, code, 'tail')
    m.emit(0)

    # The guarded v15o setter still owns input validation and the complete
    # label. Measure the linked style-2 font after native conversion.
    m.emit(_i(9, 29, 29, -0x30))
    m.emit(_i(63, 29, 31, 0x28))
    m.emit(_i(43, 29, 4, 0x18))
    m.emit(_jal(previous_hook))
    m.emit(0)
    m.emit(_i(63, 29, 2, 0x20))
    m.emit(_i(35, 29, 4, 0x18))
    m.emit(_i(35, 4, font, 0x3C))
    m.emit(_i(36, font, code, 0x24))
    m.emit(_i(9, 0, scratch, 1))
    m.branch(5, code, scratch, 'return')
    m.emit(_i(35, font, code, 0x28))
    m.branch(5, code, 0, 'return')
    m.emit(0)
    m.emit(_i(35, font, node, 4))
    m.emit(_i(9, 0, remaining, MAX_NODES + 1))
    for counter in (glyphs, full_spaces, half_spaces):
        m.emit(_i(9, 0, counter, 0))
    m.label('scan')
    m.branch(4, node, 0, 'return')
    m.emit(_i(9, remaining, remaining, -1))
    m.branch(4, remaining, 0, 'return')
    m.emit(_i(35, node, code, 0))
    for tag, label in ((-0xF1, 'measure'), (-0xF5, 'full'), (-0xF6, 'half')):
        m.emit(_i(9, 0, scratch, tag))
        m.branch(4, code, scratch, label)
        m.emit(0)
    m.branch(6, code, 0, 'return')
    m.emit(0)
    m.branch(4, 0, 0, 'next')
    m.emit(_i(9, glyphs, glyphs, 1))
    m.label('full')
    m.branch(4, 0, 0, 'next')
    m.emit(_i(9, full_spaces, full_spaces, 1))
    m.label('half')
    m.emit(_i(9, half_spaces, half_spaces, 1))
    m.label('next')
    m.branch(4, 0, 0, 'scan')
    m.emit(_i(35, node, node, 0x120))

    m.label('measure')
    m.branch(4, glyphs, 0, 'return')
    m.emit(0)
    _int_float(m, 0, glyphs)
    _int_float(m, 1, full_spaces)
    _int_float(m, 2, half_spaces)
    _float(m, 3, float(VERTICAL_ADVANCE))
    _float(m, 4, VERTICAL_ADVANCE / 2)
    _float(m, 5, float(VIEW_BOTTOM))
    _fp(m, 2, 0, 0, 3)
    _fp(m, 2, 1, 1, 3)
    _fp(m, 2, 2, 2, 4)
    _fp(m, 0, 1, 1, 2)  # Unscaled native spacing contribution.
    _fp(m, 0, 2, 0, 1)
    m.emit(_i(49, font, 4, 0x18))
    _float(m, 3, 0.)
    _fp(m, 0x3C, 0, 4, 3)
    m.branch(17, 8, 1, 'reposition')
    m.emit(0)
    _fp(m, 0, 2, 2, 4)
    _fp(m, 0x3C, 0, 5, 2)
    m.branch(17, 8, 0, 'return')
    m.emit(0)
    m.label('reposition')
    m.emit(_i(43, font, 0, 0x18))
    _fp(m, 1, 2, 5, 1)  # height available for glyphs at the top of the column
    _fp(m, 0x3C, 0, 2, 0)
    m.branch(17, 8, 0, 'unit')
    m.emit(0)

    # On overflowing columns use the native half-space control. A bounded
    # negative tracking step also handles names dominated by wide spaces.
    m.emit(_r(full_spaces, half_spaces, amount, 0, 33))
    m.emit(_i(35, font, node, 4))
    m.emit(_i(9, 0, code, -0xF5))
    m.emit(_i(9, 0, remaining, -0xF1))
    m.emit(_i(9, 0, scratch, -0xF6))
    m.label('compact')
    m.emit(_i(35, node, full_spaces, 0))
    m.branch(4, full_spaces, remaining, 'ratio')
    m.emit(0)
    m.branch(5, full_spaces, code, 'keep')
    m.emit(0)
    m.emit(_i(43, node, scratch, 0))
    m.label('keep')
    m.branch(4, 0, 0, 'compact')
    m.emit(_i(35, node, node, 0x120))
    m.label('ratio')
    _int_float(m, 2, amount)
    _float(m, 1, VERTICAL_ADVANCE / 2)
    m.emit(_i(11, amount, scratch, 31))
    m.branch(5, scratch, 0, 'compute')
    m.emit(0)
    _float(m, 1, 7.)
    _float(m, 3, -6.)
    m.emit(_i(57, font, 3, 0x28))
    m.emit(_i(9, glyphs, scratch, -1))
    _int_float(m, 4, scratch)
    _fp(m, 2, 3, 3, 4)
    _fp(m, 1, 5, 5, 3)
    m.label('compute')
    _fp(m, 2, 2, 2, 1)
    _fp(m, 1, 2, 5, 2)
    _fp(m, 3, 13, 2, 0)
    _float(m, 12, 1.)
    _fp(m, 0x3C, 0, 13, 12)
    m.branch(17, 8, 1, 'rebuild')
    m.emit(0)
    m.label('unit')
    _float(m, 12, 1.)
    _fp(m, 6, 13, 12)
    m.label('rebuild')
    m.emit(_jal(NATIVE_SCALE))
    m.emit(0)
    m.label('return')
    m.emit(_i(55, 29, 2, 0x20))
    m.emit(_i(55, 29, 31, 0x28))
    m.emit(_i(9, 29, 29, 0x30))
    m.emit(0x03E00008)
    m.emit(0)
    m.label('tail')
    m.emit(_jump(previous_hook))
    m.emit(0)
    m.emit(0x03E00008)
    m.emit(0)
    return m.done()


def _target(site: int, word: bytes) -> int:
    jal = unpack_from('<I', word)[0]
    return ((site + 4) & 0xF0000000) | ((jal & 0x03FFFFFF) << 2)


def patch(source: bytes, base: int) -> tuple[bytes, dict[int, tuple[bytes, bytes]]]:
    orientation_offset = STOCK_ORIENTATION_CALL - ELF_BIAS
    setter_offset = CHOICE_SETTER - ELF_BIAS
    orientation = source[orientation_offset:orientation_offset + 4]
    setter = source[setter_offset:setter_offset + 4]
    if orientation != bytes.fromhex('3c98260c'):
        raise ValueError(f'choice orientation call preimage differs at {STOCK_ORIENTATION_CALL:#x}')
    if setter != bytes.fromhex('d099260c'):
        raise ValueError(f'choice setter preimage differs at {CHOICE_SETTER:#x}')
    orientation_bridge = _target(STOCK_ORIENTATION_CALL, orientation)
    setter_bridge = _target(CHOICE_SETTER, setter)
    code = _stock_orientation_wrapper(orientation_bridge)
    setter_entry = base + len(code)
    code += _fallback_wrapper(setter_bridge)
    return code, {
        orientation_offset: (orientation, pack('<I', _jal(base))),
        setter_offset: (setter, pack('<I', _jal(setter_entry))),
    }
