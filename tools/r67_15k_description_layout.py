"""Install final-draw wrapping only for Item Details and inspection bodies."""
import hashlib
import struct

from tools.r67_chamber_story_text_only import Assembly, _i, _r, _jal
from tools.r67_15h_item_layout import (
    APPEND_FILE_OFFSET, APPEND_VA, APPEND_RESERVE, _validate_translation_load,
    _emit_gpr_frame, _emit_fpr_frame, _float_word,
)
from tools.r67_15j_inspection_layout import _load_address
from tools.r67_15k_kernel import build_kernel

BIAS = 0xfff80
SOURCE_SHA256 = '6ebb80d3346f4f5ab68bc49197419658603b14686e4a8b549b451c1c8d7e76d8'
DRAW = 0x188420
FRAME = 0x380
CONTEXT = 0x300
ALLOWED_SOURCE_RANGES = ((0x64, 0x68), (0x1520c, 0x15210),
                         (0x29acbc - BIAS, 0x29acc0 - BIAS),
                         (0x29badc - BIAS, 0x29bae0 - BIAS))


def draw_callback(kernel, *, inspection):
    m = Assembly()
    m.emit(_i(9, 29, 29, -FRAME))
    _emit_gpr_frame(m, save=True)
    m.emit(_i(0x1f, 29, 30, 0x1e0))  # LLVM may use fp as a general register.
    _emit_fpr_frame(m, save=True)
    m.emit((17 << 26) | (2 << 21) | (8 << 16) | (31 << 11))  # cfc1 t0,fcr31
    m.emit(0)
    m.emit(_i(43, 29, 8, 0x280))
    m.emit(_i(35, 4, 8, 0x3c))
    m.branch(4, 8, 0, 'restore')
    m.emit(0)
    if inspection:
        m.emit(_i(35, 8, 9, 0x254))
        m.branch(4, 9, 0, 'restore')
        m.emit(0)
        # Resolve all four live handles on every callback. There is no cached
        # task pointer or dependency on the relative ordering of draw tasks.
        for index in range(4):
            m.emit(_i(35, 9, 10, 0x38 + index * 4))
            m.branch(4, 10, 0, 'restore')
            m.emit(0)
            m.emit(_i(35, 10, 10, 0x3c))
            m.branch(4, 10, 0, 'restore')
            m.emit(0)
            m.emit(_i(43, 29, 10, CONTEXT + index * 4))
        m.emit(_i(35, 29, 8, CONTEXT))
    else:
        m.emit(_i(43, 29, 8, CONTEXT))
        for offset in (4, 8, 12):
            m.emit(_i(43, 29, 0, CONTEXT + offset))
    for offset, value in ((16, 4 if inspection else 1), (20, 0 if inspection else 1)):
        m.emit(_i(9, 0, 10, value))
        m.emit(_i(43, 29, 10, CONTEXT + offset))
    for native, field in ((0x14, 24), (0x18, 28)):
        m.emit(_i(35, 8, 10, native))
        m.emit(_i(43, 29, 10, CONTEXT + field))
    for offset, value in ((32, 336. if inspection else 198.),
                          (36, 90. if inspection else 60.), (40, .5 if inspection else 1.)):
        m.const(10, _float_word(value))
        m.emit(_i(43, 29, 10, CONTEXT + offset))
    m.emit(_i(43, 29, 0, CONTEXT + 44))
    m.emit(_i(43, 29, 0, CONTEXT + 48))
    m.emit(_r(0, 0, 4, 0, 33))
    m.emit(_i(9, 29, 5, CONTEXT))
    m.emit(_jal(kernel))
    m.emit(0)
    m.label('restore')
    m.emit(_i(35, 29, 8, 0x280))
    m.emit((17 << 26) | (6 << 21) | (8 << 16) | (31 << 11))  # ctc1 t0,fcr31
    m.emit(0)
    _emit_fpr_frame(m, save=False)
    m.emit(_i(0x1e, 29, 30, 0x1e0))
    _emit_gpr_frame(m, save=False)
    m.emit(_i(9, 29, 29, FRAME))
    m.emit(0x03e00008)
    m.emit(0)
    result = bytearray(m.done())
    # The repository emitter validates a return epilogue; this wrapper instead
    # tail-calls the original callback with its complete entry state restored.
    struct.pack_into('<I', result, len(result) - 8, (2 << 26) | (DRAW >> 2))
    return bytes(result)


def details_constructor(callback):
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x20))
    m.emit(_i(63, 29, 31, 0x18))
    m.emit(_jal(0x975a78))  # accepted official sparse selector and base font size
    m.emit(0)
    m.branch(4, 2, 0, 'return')
    m.emit(0)
    m.const(3, callback)
    m.emit(_i(43, 2, 3, 0x34))
    m.label('return')
    m.emit(_i(55, 29, 31, 0x18))
    m.emit(_i(9, 29, 29, 0x20))
    m.emit(0x03e00008)
    m.emit(0)
    return m.done()


def inspection_constructor(allocator):
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x30))
    m.emit(_i(63, 29, 31, 0x20))
    # Native constructor has three stack float arguments, in 8-byte slots.
    for offset in (0, 8, 16):
        m.emit(_i(35, 29, 3, 0x30 + offset))
        m.emit(_i(43, 29, 3, offset))
    m.emit(_jal(allocator))
    m.emit(0)
    m.branch(4, 2, 0, 'return')
    m.emit(0)
    m.emit(_i(35, 2, 3, 0x3c))
    m.emit(_i(43, 3, 17, 0x254))  # s1 is the live M_ObjDtl private owner.
    m.label('return')
    m.emit(_i(55, 29, 31, 0x20))
    m.emit(_i(9, 29, 29, 0x30))
    m.emit(0x03e00008)
    m.emit(0)
    return m.done()


def build(source):
    _validate_translation_load(source)
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('expected the unchanged r67.15j release ELF')
    out = bytearray(source)

    def current():
        out.extend(bytes(-len(out) % 16))
        return APPEND_VA + len(out) - APPEND_FILE_OFFSET

    def append(blob):
        va = current()
        out.extend(blob)
        return va

    code, kernel = build_kernel(current())
    append(code)
    details_draw = append(draw_callback(kernel['entry_va'], inspection=False))
    inspection_draw = append(draw_callback(kernel['entry_va'], inspection=True))
    copied = bytearray(source[0x188ad0 - BIAS:0x188d88 - BIAS])
    struct.pack_into('<I', copied, 0x6c, _i(9, 0, 4, 0x258))
    _load_address(copied, 0x234, 7, inspection_draw)
    allocator = append(copied)
    details = append(details_constructor(details_draw))
    inspection = append(inspection_constructor(allocator))
    for call, target in ((0x11518c, details), (0x29acbc, inspection), (0x29badc, 0x29a520)):
        struct.pack_into('<I', out, call - BIAS, _jal(target))
    if len(out) - APPEND_FILE_OFFSET > APPEND_RESERVE:
        raise ValueError('layout exceeds reserved translation memory')
    struct.pack_into('<I', out, 0x64, len(out) - APPEND_FILE_OFFSET)
    allowed = {i for lo, hi in ALLOWED_SOURCE_RANGES for i in range(lo, hi)}
    changed = [i for i, (a, b) in enumerate(zip(source, out)) if a != b]
    if set(changed) - allowed:
        raise ValueError('unregistered mutation outside description owners')
    return bytes(out), {
        'source_sha256': SOURCE_SHA256, 'result_sha256': hashlib.sha256(out).hexdigest(),
        'kernel': kernel, 'details_draw_va': details_draw,
        'inspection_draw_va': inspection_draw, 'allocator_va': allocator,
        'details_constructor_va': details, 'inspection_constructor_va': inspection,
        'changed_existing_offsets': changed, 'appended_extent': [len(source), len(out)],
        'runtime_verified': False,
    }
