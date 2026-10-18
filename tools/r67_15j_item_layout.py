"""Fit owned item text using native per-row glyph and unscaled-space metrics.

The native renderer does not scale space advances or newline pitch. Each row
therefore has its own affine width constraint, not a character-count ratio.
No shared renderer instructions, source strings or numeric columns are changed.
"""
import hashlib
import struct

from tools.r67_chamber_story_text_only import Assembly, _i, _r, _jal
from tools import r67_15h_item_layout as native

SOURCE_SHA256 = 'ffd1fb3f912268d589c19b607eeed68899ac0c31151c731aac59afeb913c8096'
# Text starts at 26 in the native 256px frame. The 224 content edge is a
# conservative inset chosen from its decorative texture, not a native scissor.
DETAILS_WIDTH = 198
DETAILS_HEIGHT = 60
RECIPE_WIDTH = 114
ALLOWED_SOURCE_RANGES = native.ALLOWED_SOURCE_RANGES


def _fp(m, opcode, destination, left, right=0):
    m.emit((17 << 26) | (16 << 21) | (right << 16) |
           (left << 11) | (destination << 6) | opcode)


def _float(m, destination, value):
    m.const(24, native._float_word(value))
    m.emit((17 << 26) | (4 << 21) | (24 << 16) | (destination << 11))


def _int_float(m, destination, source):
    m.emit((17 << 26) | (4 << 21) | (source << 16) | (destination << 11))
    m.emit(0)
    m.emit((17 << 26) | (20 << 21) | (destination << 11) |
           (destination << 6) | 0x20)


def _row_constraint(m, width, suffix, font_width=16):
    # t3/t4 count glyphs/spaces. Every space advances 8, regardless of scale.
    m.emit(_i(9, 0, 24, width))
    m.emit(_r(0, 12, 25, 3 if font_width==16 else 2, 0))
    if font_width==12:
        m.emit(_r(0, 12, 15, 1, 0))
        m.emit(_r(25, 15, 25, 0, 33))
    m.emit(_r(24, 25, 24, 0, 35))
    m.emit(_i(10, 24, 25, 1))
    m.branch(5, 25, 0, 'restore')
    m.emit(0)
    m.branch(4, 11, 0, 'row_done_' + suffix)
    m.emit(0)
    _int_float(m, 22, 24)
    m.emit(_r(0, 11, 25, 4 if font_width==16 else 3, 0))
    if font_width==12:
        m.emit(_r(0, 11, 15, 2, 0))
        m.emit(_r(25, 15, 25, 0, 33))
    _int_float(m, 23, 25)
    _fp(m, 3, 22, 22, 23)
    _fp(m, 0x3C, 0, 22, 20)  # c.lt.s candidate,min_scale
    m.branch(17, 8, 0, 'row_done_' + suffix)  # bc1f
    m.emit(0)
    _fp(m, 6, 20, 22)
    m.label('row_done_' + suffix)


def helper(*, details, width=None, scale_cap=.5, preserve_actions=False,
           update=False, center=None, animation=False, fit_only_overflow=False,
           font_width=16, font_height=18):
    if font_width not in (12,16): raise ValueError('unsupported native font width')
    width = width if width is not None else DETAILS_WIDTH if details else RECIPE_WIDTH
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x300))
    native._emit_gpr_frame(m, save=True)
    if update: m.emit(_i(43, 29, 4, 0x2C0))
    target = 0x18A080 if update else native.DETAILS_HELPER_VA if details else native.CONSTRUCTOR_VA
    m.emit(_jal(target))
    m.emit(0)
    native._emit_fpr_frame(m, save=True)
    if update:
        m.emit(_i(43, 29, 2, 0x2C4))
        m.emit(_i(35, 29, 2, 0x2C0))
    else:
        m.emit(_i(43, 29, 2, 0x2C0))
    if preserve_actions:
        m.emit(_i(35, 16, 24, 0x18))  # original H_Item action object, callee-saved s0
        for action_id in (1, 3):
            m.emit(_i(9, 0, 25, action_id))
            m.branch(4, 24, 25, 'restore')
            m.emit(0)
    m.branch(4, 2, 0, 'restore')
    m.emit(0)
    m.emit(_i(35, 2, 8, 0x3C))
    m.branch(4, 8, 0, 'restore')
    m.emit(0)
    # Pin the font metrics consumed by this owner's native constructors.
    m.emit(_i(35, 8, 9, 0x10))
    m.branch(4, 9, 0, 'restore')
    m.emit(0)
    m.emit(_i(36, 9, 24, 4))
    m.emit(_i(9, 0, 25, font_width))
    m.branch(5, 24, 25, 'restore')
    m.emit(0)
    m.emit(_i(36, 9, 24, 5))
    m.emit(_i(9, 0, 25, font_height))
    m.branch(5, 24, 25, 'restore')
    m.emit(0)
    m.emit(_i(35, 8, 10, 4))
    for register in (11, 12, 13, 14): m.emit(_i(9, 0, register, 0))
    _float(m, 20, scale_cap)
    m.label('walk')
    m.branch(4, 10, 0, 'last_row')
    m.emit(0)
    m.emit(_i(11, 10, 15, 0x1000))
    m.branch(5, 15, 0, 'restore')
    m.emit(0)
    m.const(24, 0x1FFFEDD)
    m.emit(_r(10, 24, 15, 0, 43))
    m.branch(4, 15, 0, 'restore')
    m.emit(0)
    m.emit(_i(12, 10, 15, 3))
    m.branch(5, 15, 0, 'restore')
    m.emit(0)
    m.emit(_i(9, 14, 14, 1))
    m.emit(_i(10, 14, 15, 257))
    m.branch(4, 15, 0, 'restore')
    m.emit(0)
    m.emit(_i(35, 10, 15, 0))
    m.const(24, 0xFFFFFF00)
    m.emit(_r(15, 24, 25, 0, 36))
    m.branch(5, 25, 24, 'glyph')
    m.emit(0)
    for value, label in ((0xFFFFFF0A, 'space'), (0xFFFFFF0B, 'space'),
                         (0xFFFFFF0E, 'newline'), (0xFFFFFF0F, 'next')):
        m.const(24, value)
        m.branch(4, 15, 24, label)
        m.emit(0)
    m.branch(4, 0, 0, 'restore')
    m.emit(0)
    m.label('glyph')
    m.emit(_i(9, 11, 11, 1))
    m.branch(4, 0, 0, 'next')
    m.emit(0)
    m.label('space')
    m.emit(_i(9, 12, 12, 1))
    m.branch(4, 0, 0, 'next')
    m.emit(0)
    m.label('newline')
    if details:
        _row_constraint(m, width, 'newline', font_width)
        m.emit(_i(9, 0, 11, 0))
        m.emit(_i(9, 0, 12, 0))
        m.emit(_i(9, 13, 13, 1))
    else:
        m.branch(4, 0, 0, 'restore')
        m.emit(0)
    m.label('next')
    m.emit(_i(35, 10, 10, 0x120))
    m.branch(4, 0, 0, 'walk')
    m.emit(0)
    m.label('last_row')
    _row_constraint(m, width, 'last', font_width)
    if fit_only_overflow:
        m.emit(_r(11,12,24,0,33))
        m.emit(_i(10,24,25,width//font_width+1))
        m.branch(5,25,0,'reset_scale')
        m.emit(0)
    if center is not None or animation:
        _int_float(m,22,11)
        _float(m,23,font_width)
        _fp(m,2,22,22,23)
        _fp(m,2,22,22,20)
        _int_float(m,23,12)
        _float(m,21,font_width/2)
        _fp(m,2,23,23,21)
        _fp(m,0,22,22,23)  # full fitted advance including spaces
        if center is not None:
            _float(m,23,2.)
            _fp(m,3,23,22,23)
            _float(m,21,center)
            _fp(m,1,23,21,23)
            m.emit(_i(57,8,23,0x14))
        if animation:
            # This helper is called only from a private copy of M_StrDraw.
            # s2 is that animation's private state, never a global text handle.
            m.emit(_r(11,12,24,0,33))
            m.branch(4,24,0,'animation_ready')
            m.emit(0)
            _int_float(m,23,24)
            _fp(m,3,23,22,23)
            _float(m,21,16.)
            _fp(m,1,23,23,21)
            m.emit(_i(57,18,23,0x34))
            m.emit(_i(49,8,23,0x14))
            m.emit(_i(57,18,23,0x10))
            m.emit(_i(35,18,24,0))
            m.branch(4,24,0,'animation_ready')
            m.emit(0)
            m.emit(_i(57,24,23,0x3C))
            m.label('animation_ready')
    # Vertical advance is independent of scale too. Reserve the whole last
    # cell, not only its ink, within the description/recipe separator.
    _float(m, 13, scale_cap)
    if details:
        _float(m, 21, 9.)
        m.emit(_i(9, 13, 13, 1))
        _int_float(m, 22, 13)
        _float(m, 23, DETAILS_HEIGHT)
        _fp(m, 3, 22, 23, 22)
        _fp(m, 0x3C, 0, 22, 21)
        m.branch(17, 8, 0, 'pitch_ready')
        m.emit(0)
        _fp(m, 6, 21, 22)
        m.label('pitch_ready')
        _float(m, 23, 18.)
        _fp(m, 3, 13, 21, 23)
        _fp(m, 1, 21, 21, 23)
        m.emit(_i(57, 8, 21, 0x2C))
    m.emit(_i(43, 8, 0, 0x28))  # owner-local tracking, never shared font state
    m.emit(_i(35, 8, 10, 4))
    m.label('normalize')
    m.branch(4, 10, 0, 'set_scale')
    m.emit(0)
    m.emit(_i(35, 10, 15, 0))
    m.const(24, 0xFFFFFF0B)
    m.branch(5, 15, 24, 'normalize_next')
    m.emit(0)
    m.const(24, 0xFFFFFF0A)
    m.emit(_i(43, 10, 24, 0))
    m.label('normalize_next')
    m.emit(_i(35, 10, 10, 0x120))
    m.branch(4, 0, 0, 'normalize')
    m.emit(0)
    m.label('set_scale')
    _fp(m, 6, 12, 20)
    m.emit(_i(35, 29, 4, 0x2C0))
    m.emit(_jal(native.SETTER_VA))
    m.emit(0)
    m.branch(4,0,0,'restore')
    m.emit(0)
    if fit_only_overflow:
        m.label('reset_scale')
        _float(m,20,1.)
        _float(m,13,1.)
        m.branch(4,0,0,'set_scale')
        m.emit(0)
    m.label('restore')
    native._emit_fpr_frame(m, save=False)
    native._emit_gpr_frame(m, save=False)
    m.emit(_i(35, 29, 2, 0x2C4 if update else 0x2C0))
    m.emit(_i(9, 29, 29, 0x300))
    m.emit(0x03E00008)
    m.emit(0)
    return m.done()


def build(source):
    native._validate_translation_load(source)
    expected = {0x1520C: 0x976200, **{offset: 0x975E40 for offset in native.RECIPE_HOOKS}}
    for offset, target in expected.items():
        if struct.unpack_from('<II', source, offset) != (_jal(target), 0):
            raise ValueError(f'item layout preimage changed at {offset:#x}')
    out = bytearray(source)
    targets = {}
    for details in (True, False):
        out.extend(b'\0' * (-len(out) % 4))
        va = native.APPEND_VA + len(out) - native.APPEND_FILE_OFFSET
        targets['details' if details else 'recipes'] = va
        out.extend(helper(details=details))
        for offset in ((0x1520C,) if details else native.RECIPE_HOOKS):
            struct.pack_into('<I', out, offset, _jal(va))
    if len(out) - native.APPEND_FILE_OFFSET > native.APPEND_RESERVE:
        raise ValueError('item layout exceeds reserved translation memory')
    struct.pack_into('<I', out, 0x64, len(out) - native.APPEND_FILE_OFFSET)
    allowed = set(range(0x64, 0x68))
    for spans in ALLOWED_SOURCE_RANGES.values():
        for lo, hi in spans: allowed.update(range(lo, hi))
    changed = {i for i, (a,b) in enumerate(zip(source,out)) if a != b}
    if changed - allowed: raise ValueError('unexpected item layout mutation')
    return bytes(out), {'source_sha256': hashlib.sha256(source).hexdigest(),
        'result_sha256': hashlib.sha256(out).hexdigest(), 'helpers': targets,
        'details_width': DETAILS_WIDTH, 'details_height': DETAILS_HEIGHT,
        'recipe_width': RECIPE_WIDTH, 'runtime_verified': False,
        'changed_existing_offsets': sorted(changed), 'appended_extent': [len(source),len(out)]}
