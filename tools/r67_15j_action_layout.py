"""Fit new item action captions without moving accepted bubble backings."""
import hashlib
import struct
from tools.r67_15h_item_layout import _validate_translation_load, APPEND_VA, APPEND_FILE_OFFSET, APPEND_RESERVE
from tools.r67_15j_item_layout import helper
from tools.r67_chamber_story_text_only import _jal

HOOK = 0x14C18  # VA 0x114B98, action caption constructor
ALLOWED_SOURCE_RANGES = {'item_action_caption': ((HOOK,HOOK+4),)}
# Native type 0x5e: width 96, pivot X -29; caption origin +51.
# Right edge +125 minus caption origin 51 minus 8px inset = 66px.
WIDTH = 66


def build(source):
    _validate_translation_load(source)
    if struct.unpack_from('<II',source,HOOK)!=(_jal(0x189E40),0):
        raise ValueError('action caption constructor preimage changed')
    out=bytearray(source)
    out.extend(b'\0'*(-len(out)%4))
    va=APPEND_VA+len(out)-APPEND_FILE_OFFSET
    out.extend(helper(details=False,width=WIDTH,scale_cap=.75,preserve_actions=True))
    if len(out)-APPEND_FILE_OFFSET>APPEND_RESERVE:
        raise ValueError('action layout exceeds translation reserve')
    struct.pack_into('<I',out,HOOK,_jal(va))
    struct.pack_into('<I',out,0x64,len(out)-APPEND_FILE_OFFSET)
    return bytes(out),{'source_sha256':hashlib.sha256(source).hexdigest(),
        'result_sha256':hashlib.sha256(out).hexdigest(),'helper_va':va,
        'width':WIDTH,'preserved_action_ids':[1,3],'runtime_verified':False,
        'appended_extent':[len(source),len(out)]}
