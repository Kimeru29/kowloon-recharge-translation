"""Restore ordinary-event geometry at initial construction AND each active frame.

r67.14x intercepted only slot-change reconstruction (0x16606c). Initial
creation at 0x165e60 and same-slot messages skip that hook. L1 can also
mutate shared metadata later in H_TalkBuddyTask. The frame wrapper runs
after the final native callback and only while an ordinary event owns a
live speech sprite. Existing text-node Y=280/300, timing and AFK stay intact.
"""
from __future__ import annotations
import hashlib
import struct
from tools.r67_chamber_story_text_only import (
    Assembly, ELF_BIAS, ELF_SEGMENT_FO, ELF_SEGMENT_VA,
    ELF_SEGMENT_RESERVE, _i, _r, _jal, _float_word,
)
from tools.r67_14w_restore_opening_bubble_shape import preimage

SITES = ((0x165E60, 0x107D60), (0x166820, 0x167980))


def _restore(a: Assembly, *, active_frame: bool) -> None:
    a.emit(_i(33,16,12,4))
    a.emit(_i(11,12,13,601))
    a.branch(4,13,0,'done')
    a.emit(0)
    a.emit(_i(33,16,12,0x2F8))
    a.emit(_i(11,12,13,2))
    a.branch(4,13,0,'done')
    a.emit(0)
    if active_frame:
        a.emit(_i(33,16,13,2))
        a.emit(_i(9,13,13,-9))
        a.emit(_i(11,13,13,5))  # only native event states 9..13
        a.branch(4,13,0,'done')
        a.emit(0)
        a.emit(_i(35,16,13,0x58))
        a.branch(4,13,0,'done')
        a.emit(0)
        a.emit(_i(36,13,14,0x93))
        a.branch(4,14,0,'done')
        a.emit(0)
        a.emit(_i(37,13,14,0x82))
        a.emit(_i(9,14,14,-2))
        a.branch(5,14,0,'done')
        a.emit(0)
        a.emit(_i(37,13,14,0x84))
        a.emit(_i(9,12,15,0x68))
        a.branch(5,14,15,'done')
        a.emit(0)
    a.emit(_r(0,12,13,4,0))
    a.emit(_r(0,12,14,5,0))
    a.emit(_r(13,14,13,0,33))
    a.const(14,0x450AC4)
    a.emit(_r(14,13,14,0,33))
    for offset, value in ((0,288.),(4,80.),(12,77.)):
        a.const(15,_float_word(value))
        a.emit(_i(43,14,15,offset))
    a.const(15,_float_word(67.))
    a.branch(4,12,0,'pivot')
    a.emit(0)
    a.const(15,_float_word(125.))
    a.label('pivot')
    a.emit(_i(43,14,15,8))
    a.const(14,0x450B24)
    for frame in range(3):
        for offset, value in ((0,288.),(4,56.),(8,67.),(12,74.+frame)):
            a.const(15,_float_word(value))
            a.emit(_i(43,14,15,frame*48+offset))


def make_helper(*, active_frame: bool) -> bytes:
    a = Assembly()
    a.emit(_i(9,29,29,-16))
    a.emit(_i(63,29,31,0))  # keep 64-bit EE RA; packed a2 XY never touched
    if active_frame:
        a.emit(_jal(0x167980))
        a.emit(0)
    _restore(a,active_frame=active_frame)
    a.label('done')
    if not active_frame:
        a.emit(_jal(0x107D60))
        a.emit(0)
    a.emit(_i(55,29,31,0))
    a.emit(_i(9,29,29,16))
    a.emit(_r(31,0,0,0,8))
    a.emit(0)
    return a.done()


def apply(source: bytes) -> tuple[bytes,dict]:
    preimage(source)  # exact accepted t, including original strict q lock
    b = bytearray(source)
    allowed = set(range(0x64,0x68))
    hooks = []
    for (site,callee), active in zip(SITES,(False,True),strict=True):
        at = site-ELF_BIAS
        if struct.unpack_from('<2I',source,at) != (_jal(callee),0):
            raise ValueError(f'Native lifecycle callsite drift at {site:#x}')
        while len(b)%4:
            b.append(0)
        helper = make_helper(active_frame=active)
        va = ELF_SEGMENT_VA+len(b)-ELF_SEGMENT_FO
        b.extend(helper)
        struct.pack_into('<I',b,at,_jal(va))
        allowed.update(range(at,at+4))
        hooks.append(dict(site=hex(site),original_callee=hex(callee),
                          helper_va=hex(va),helper_bytes=len(helper),
                          active_frame=active))
    if len(b)-ELF_SEGMENT_FO > ELF_SEGMENT_RESERVE:
        raise ValueError('Event helper exceeds reserved translation segment')
    struct.pack_into('<I',b,0x64,len(b)-ELF_SEGMENT_FO)
    changed = [i for i,(x,y) in enumerate(zip(source,b)) if x!=y]
    if set(changed)-allowed:
        raise ValueError('Unexpected original ELF mutation')
    return bytes(b), dict(release='r67.14y',hooks=hooks,
        source_sha256=hashlib.sha256(source).hexdigest(),
        candidate_sha256=hashlib.sha256(b).hexdigest(),
        changed_existing_offsets=list(map(hex,changed)),
        ordinary_records=601,afk_records_excluded=600,
        original_text_y=[280,300],original_event_timer_unchanged=True,
        original_q_lock_exceptions=[],gameplay_verified=False)
