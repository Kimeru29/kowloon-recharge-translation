"""Apply Details metrics to real native node lists, including their end marker."""
import hashlib
import struct

from tools import r67_15h_item_layout as previous
from tools.r67_chamber_story_text_only import Assembly, _i, _r, _jal
from tools.r67_15g_item_details import collect_catalogue, _va_to_offset, _read_string

SOURCE_SHA256='de5b2e49ffc0a458a053becd50ac6fcf511a194319038a79236e19187ade4816'
ALLOWED_SOURCE_RANGES={'details_constructor':((0x1520C,0x15210),)}


def catalogue_rows(source):
    # Restore only the constructor call in a disposable view for the existing
    # catalogue reader. Its name/description tables and getter remain pinned.
    view=bytearray(source)
    struct.pack_into('<I',view,0x1520C,0x0C062790)
    records=collect_catalogue(bytes(view))
    table=_va_to_offset(source,0x974EA8)
    result={}
    for record in records:
        pointer=struct.unpack_from('<I',source,table+record.item_id*4)[0] or record.description_pointer
        text=_read_string(source,pointer)
        if text is None:
            raise ValueError(f'unreadable Details record {record.item_id}')
        rows=text.split('＠改行')
        if any('＠' in row for row in rows):
            raise ValueError(f'unmodelled Details control in record {record.item_id}')
        if max(map(len,rows),default=0)*8>220 or len(rows)*9>60:
            raise ValueError(f'Details geometry outside panel for item {record.item_id}')
        if sum(map(len,rows))+len(rows)>256:
            raise ValueError(f'Details node limit exceeded for item {record.item_id}')
        result[record.item_id]=rows
    if len(result)!=431:
        raise ValueError('Details catalogue coverage changed')
    return result


def _corrected_helper(va):
    raw=previous._layout_helper(details=True,helper_va=va)
    words=list(struct.unpack('<'+'I'*(len(raw)//4),raw))
    signature=_r(0,15,24,8,2)
    matches=[i for i,w in enumerate(words) if w==signature]
    if len(matches)!=1:
        raise ValueError('previous Details classifier changed')
    idx=matches[0]
    def branch_target(index):
        immediate=words[index]&0xFFFF
        if immediate&0x8000: immediate-=0x10000
        return index+1+immediate
    invalid=branch_target(idx+2)
    ordinary=branch_target(idx+4)
    restore=branch_target(invalid)
    next_node=branch_target(ordinary+1)
    extension_va=va+len(raw)
    words[idx]=0x08000000 | (extension_va>>2)
    words[idx+1]=0
    m=Assembly()
    m.emit(_i(35,10,15,0))  # native nodes hold a full glyph pointer or signed control
    m.const(24,0xFFFFFF00)
    m.emit(_r(15,24,25,0,36))
    m.branch(5,25,24,'ordinary')
    m.emit(0)
    m.const(24,0xFFFFFF0F)
    m.branch(4,15,24,'end_marker')
    m.emit(0)
    m.emit(0x08000000 | ((va+restore*4)>>2))
    m.emit(0)
    m.label('ordinary')
    m.emit(0x08000000 | ((va+ordinary*4)>>2))
    m.emit(0)
    m.label('end_marker')
    m.emit(0x08000000 | ((va+next_node*4)>>2))
    m.emit(0)
    m.emit(0x03E00008)  # unreachable, all classifier exits tail-jump
    m.emit(0)
    return struct.pack('<'+'I'*len(words),*words)+m.done()


def build(source):
    if hashlib.sha256(source).hexdigest()!=SOURCE_SHA256:
        raise ValueError('15i Details requires the pinned 15h ELF')
    previous._validate_translation_load(source)
    rows=catalogue_rows(source)
    out=bytearray(source)
    out.extend(b'\0'*(-len(out)%4))
    va=previous.APPEND_VA+len(out)-previous.APPEND_FILE_OFFSET
    helper=_corrected_helper(va)
    out.extend(helper)
    if len(out)-previous.APPEND_FILE_OFFSET>previous.APPEND_RESERVE:
        raise ValueError('Details helper exceeds translation reserve')
    struct.pack_into('<I',out,0x1520C,_jal(va))
    struct.pack_into('<I',out,0x64,len(out)-previous.APPEND_FILE_OFFSET)
    changed=[i for i,(a,b) in enumerate(zip(source,out)) if a!=b]
    allowed=set(range(0x64,0x68))|set(range(0x1520C,0x15210))
    if set(changed)-allowed:
        raise ValueError('unexpected Details source mutation')
    return bytes(out),{'status':'CATALOGUE_LAYOUT_VALIDATED_RUNTIME_UNVERIFIED',
        'source_sha256':SOURCE_SHA256,'result_sha256':hashlib.sha256(out).hexdigest(),
        'helper_va':va,'helper_bytes':len(helper),'catalogue_records':len(rows),
        'maximum_rows':max(map(len,rows.values())),
        'maximum_advance':max(len(line)*8 for lines in rows.values() for line in lines),
        'maximum_height':max(map(len,rows.values()))*9,
        'official_and_fallback_text_unchanged':True,
        'appended_extent':[len(source),len(out)],
        'modified_existing_offsets':[hex(i) for i in changed], 'runtime_verified':False}
