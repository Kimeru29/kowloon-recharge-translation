"""Restore HANT viewport initialization and setter ABI without losing pool bounds."""
import hashlib
import struct

from tools.r67_chamber_story_text_only import Assembly, _i, _r
from tools.r67_15h_hant_pool import _segments, TRANSLATION_FO, TRANSLATION_VA, TRANSLATION_RESERVE

BIAS = 0xFFF80
PREIMAGES = {
    0x28FDD4: 0x8E621A78, 0x28FDD8: 0x2C420051,
    0x28FE94: 0x24521A94, 0x28FE9C: 0x1080000A,
    0x28FEA0: 0xC62C0120, 0x28FEA4: 0x0C062AAC,
}
ALLOWED_SOURCE_RANGES = {
    f'hant_instruction_{va:x}': ((va-BIAS, va-BIAS+4),) for va in PREIMAGES
}


def jump(va):
    if va & 3 or not 0 <= va < 0x10000000:
        raise ValueError('unreachable HANT helper')
    return 0x08000000 | va >> 2


def build(source):
    _segments(source)
    for va, expected in PREIMAGES.items():
        if struct.unpack_from('<I', source, va-BIAS)[0] != expected:
            raise ValueError(f'HANT 15h preimage changed at {va:#x}')
    # Pin all coordination points of the accepted 19-slot safety correction.
    for va, expected in {0x28FDC8:0x2A230013, 0x28FE98:0x8C441A94,
                         0x28FEA8:0x8E440000, 0x290914:0xAC621A94,
                         0x291DE0:0x24051AE0}.items():
        if struct.unpack_from('<I', source, va-BIAS)[0] != expected:
            raise ValueError(f'HANT pool safety preimage changed at {va:#x}')
    out = bytearray(source)
    def append(raw):
        out.extend(b'\0' * (-len(out) % 4))
        va = TRANSLATION_VA + len(out) - TRANSLATION_FO
        out.extend(raw)
        return va
    m = Assembly()
    m.emit(_r(0, 0, 20, 0, 45))  # s4 row index; s5 reset in hook delay slot
    m.emit(_i(35, 19, 2, 0x1A78))
    m.emit(_i(11, 2, 2, 81))
    m.branch(5, 2, 0, 'valid')
    m.emit(0)
    m.emit(jump(0x28FEE0))
    m.emit(0)
    m.label('valid')
    m.emit(jump(0x28FED0))  # native precondition also handles zero rows
    m.emit(0)
    m.emit(0x03E00008)  # unreachable assembler epilogue; both paths tail-jump
    m.emit(0)
    entry = append(m.done())
    m = Assembly()
    m.emit(_i(9, 2, 18, 0x1A94))  # displaced pool-slot pointer calculation
    m.branch(5, 4, 0, 'present')
    m.emit(0)
    m.emit(jump(0x28FEC8))  # null slot consumes slot but calls no setter
    m.emit(0)
    m.label('present')
    m.emit(jump(0x28FE9C))
    m.emit(0)
    m.emit(0x03E00008)
    m.emit(0)
    select = append(m.done())
    words = {0x28FDD4:jump(entry), 0x28FDD8:_r(0,0,21,0,45),
             0x28FE94:jump(select), 0x28FE9C:0xC62C0120,
             0x28FEA0:0x0C062AAC, 0x28FEA4:0}
    for va, word in words.items():
        struct.pack_into('<I', out, va-BIAS, word)
    if len(out)-TRANSLATION_FO > TRANSLATION_RESERVE:
        raise ValueError('HANT helper exceeds translation reserve')
    struct.pack_into('<I', out, 0x64, len(out)-TRANSLATION_FO)
    changed = [i for i, (a,b) in enumerate(zip(source,out)) if a!=b]
    allowed = set(range(0x64,0x68)) | {i for va in words for i in range(va-BIAS,va-BIAS+4)}
    if set(changed)-allowed:
        raise ValueError('unexpected HANT source mutation')
    return bytes(out), {'status':'NATIVE_REGRESSION_PATCH',
        'source_sha256':hashlib.sha256(source).hexdigest(),
        'result_sha256':hashlib.sha256(out).hexdigest(),
        'entry_helper_va':entry, 'selection_helper_va':select,
        'appended_extent':[len(source),len(out)],
        'modified_existing_offsets':[hex(i) for i in changed],
        'pool_capacity':19, 'pool_base':'0x1a94', 'runtime_verified':False}
