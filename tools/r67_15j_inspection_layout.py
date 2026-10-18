"""Scope text fitting to inspection-owned copies of the native reveal routine.

The original animation is also used by other screens. Its code and dispatch
table stay untouched; only the title, body and action call sites in M_ObjDtl
use copies with a bounded text-update wrapper. Allocation, teardown, timing,
and the six-state native lifecycle remain the original instructions.
"""
import hashlib
import struct
from pathlib import Path
import unicodedata
from tools.r67_chamber_story_text_only import _jal
from tools.r67_15h_item_layout import _validate_translation_load, APPEND_VA, APPEND_FILE_OFFSET, APPEND_RESERVE
from tools.r67_15j_item_layout import helper
from tools.r67_14y_inspection_save import _string
from tools.r67_15j_action_labels import CORPUS_PATH,CORPUS_SHA256
from tools.inspect_english_bytes import parse

BIAS=0xFFF80
CALLBACK=(0x299F30,0x29A440)
CONSTRUCTOR=(0x29A520,0x29A710)
CALLBACK_SHA='68a5aabc3d9e769e23fa6b1c76833aef3342f3818755429f21f8c8fc5f11d7dd'
CONSTRUCTOR_SHA='d56c303a4c5ce0c56ea8bbfb6b35950ba54a93ca686eb0edf38012b798943a33'
OWNERS={
    'body':(0x29BADC,336,None),
    'title':(0x29B4A4,336,256.),
    'action':(0x29B2C8,164,None),
}
READING_HOOK=0x29B5E4
ALLOWED_SOURCE_RANGES={key:((va-BIAS,va-BIAS+4),) for key,(va,_,_) in OWNERS.items()}
ALLOWED_SOURCE_RANGES['reading']=((READING_HOOK-BIAS,READING_HOOK-BIAS+4),)
ALLOWED_SOURCE_RANGES['official_deleted_readings']=((0x58A1C4,0x58A1C8),(0x592A84,0x592A88))
TABLES=((0x690500,400,'1bd6202dd1414c8c1d43321c57127535285be3113b4a7e5dd34e1cc58dc30439'),
        (0x694560,200,'2d568bd6908f8313b509c296a2e406093d05d6a50a7f92a74280769c7605e4e9'))


def catalogue(source):
    # M_ObjDtl reads gp-0x5480, indexed by native category, then object ID.
    # The ELF .reginfo pins gp=0x79B1F0. These are both native arrays, not a
    # heuristic scan for six consecutive words that happen to look like text.
    if struct.unpack_from('<3I',source,0x795D70-BIAS)!=(0x690500,0x694560,0x464F45):
        raise ValueError('inspection category roots changed')
    records={}
    for table,count,digest in TABLES:
        blob=source[table-BIAS:table-BIAS+count*4]
        if hashlib.sha256(blob).hexdigest()!=digest:
            raise ValueError('inspection object table changed')
        for pointer in struct.unpack('<'+'I'*count,blob):
            fields=struct.unpack_from('<6I',source,pointer-BIAS)
            texts=[_string(source,p).decode('cp932') for p in fields]
            for text in texts:
                if '＠' in text or len(text)>255 or (text.count(' ')+text.count('　'))*8>=164:
                    raise ValueError('inspection text outside the supported bounded metric domain')
            records[pointer-BIAS]=texts
    if len(records)!=600: raise ValueError('inspection record coverage changed')
    return records


def deleted_readings(source,records):
    original=(Path(__file__).resolve().parents[1].parent/'startup-flow-v10/fixtures/elf/SLPM_665.11').read_bytes()
    if hashlib.sha256(original).hexdigest()!='6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794':
        raise ValueError('pristine inspection source changed')
    if hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()!=CORPUS_SHA256:
        raise ValueError('official inspection corpus changed')
    dictionary={}
    for jp,en,offset in parse(CORPUS_PATH): dictionary.setdefault(jp,set()).add((en,offset))
    result=[]
    for record,texts in records.items():
        if not texts[0] or texts[0]!=texts[5]: continue
        source_pointers=struct.unpack_from('<6I',original,record)
        jp=_string(original,source_pointers[5]).decode('cp932')
        matches=dictionary.get(jp,set())
        if len(matches)==1 and next(iter(matches))[0]=='@D':
            result.append({'owner':record+20,'japanese':jp,
                           'official_record':next(iter(matches))[1],
                           'removed_duplicate':unicodedata.normalize('NFKC',texts[5])})
    if {row['owner'] for row in result}!={0x58A1C4,0x592A84}:
        raise ValueError('official deleted-reading owners changed')
    return result


def _load_address(blob,offset,register,address):
    # Keep the native LUI/ADDIU instruction pair and signed-low-half semantics.
    struct.pack_into('<II',blob,offset,
        0x3C000000 | register<<16 | ((address+0x8000)>>16),
        0x24000000 | register<<21 | register<<16 | (address&0xFFFF))


def build(source):
    _validate_translation_load(source)
    records=catalogue(source)
    deletions=deleted_readings(source,records)
    callback=source[CALLBACK[0]-BIAS:CALLBACK[1]-BIAS]
    constructor=source[CONSTRUCTOR[0]-BIAS:CONSTRUCTOR[1]-BIAS]
    if hashlib.sha256(callback).hexdigest()!=CALLBACK_SHA:
        raise ValueError('native reveal callback preimage changed')
    if hashlib.sha256(constructor).hexdigest()!=CONSTRUCTOR_SHA:
        raise ValueError('native reveal constructor preimage changed')
    cases=struct.unpack_from('<6I',source,0x7864D0-BIAS)
    if any(not CALLBACK[0]<=va<CALLBACK[1] for va in cases):
        raise ValueError('native reveal switch escaped its callback')
    out=bytearray(source)
    for deletion in deletions: struct.pack_into('<I',out,deletion['owner'],0x795B9C)
    def append(blob):
        out.extend(b'\0'*(-len(out)%4))
        va=APPEND_VA+len(out)-APPEND_FILE_OFFSET
        out.extend(blob)
        return va
    animations={}
    for key,(call,width,center) in OWNERS.items():
        if struct.unpack_from('<II',source,call-BIAS)!=(_jal(CONSTRUCTOR[0]),0):
            raise ValueError(f'{key} inspection animation call preimage changed')
        fitter=append(helper(details=False,width=width,scale_cap=1.,update=True,
                             center=center,animation=True,fit_only_overflow=True))
        out.extend(b'\0'*(-len(out)%4))
        switch_va=APPEND_VA+len(out)-APPEND_FILE_OFFSET
        callback_va=switch_va+24
        append(struct.pack('<6I',*(callback_va+va-CALLBACK[0] for va in cases)))
        copied=bytearray(callback)
        _load_address(copied,0xBC,3,switch_va)
        struct.pack_into('<I',copied,0x190,_jal(fitter))
        if append(copied)!=callback_va: raise ValueError('callback append alignment changed')
        copied_constructor=bytearray(constructor)
        _load_address(copied_constructor,0xB8,7,callback_va)
        constructor_va=append(copied_constructor)
        struct.pack_into('<I',out,call-BIAS,_jal(constructor_va))
        animations[key]={'fitter_va':fitter,'callback_va':callback_va,
                         'switch_va':switch_va,'constructor_va':constructor_va,
                         'width':width,'center':center}
    if struct.unpack_from('<II',source,READING_HOOK-BIAS)!=(_jal(0x18A080),0):
        raise ValueError('inspection reading update preimage changed')
    reading=append(helper(details=False,width=336,scale_cap=1.,update=True,
                          center=256.,fit_only_overflow=True,font_width=12,font_height=12))
    struct.pack_into('<I',out,READING_HOOK-BIAS,_jal(reading))
    if len(out)-APPEND_FILE_OFFSET>APPEND_RESERVE:
        raise ValueError('inspection helpers exceed reserved translation memory')
    struct.pack_into('<I',out,0x64,len(out)-APPEND_FILE_OFFSET)
    allowed=set(range(0x64,0x68))
    for spans in ALLOWED_SOURCE_RANGES.values():
        for lo,hi in spans: allowed.update(range(lo,hi))
    changed={i for i,(a,b) in enumerate(zip(source,out)) if a!=b}
    if changed-allowed: raise ValueError('unexpected inspection mutation')
    return bytes(out),{'source_sha256':hashlib.sha256(source).hexdigest(),
        'result_sha256':hashlib.sha256(out).hexdigest(),'animations':animations,
        'reading_helper_va':reading,'changed_existing_offsets':sorted(changed),
        'catalogue_records':len(records),'maximum_cells':max(len(t) for row in records.values() for t in row),
        'official_deleted_readings':deletions,
        'appended_extent':[len(source),len(out)],'runtime_verified':False}
