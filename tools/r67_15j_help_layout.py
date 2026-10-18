"""Build Help text and sprite positions from the same source-backed units."""
import hashlib
import math
import struct
from pathlib import Path

from tools.first_save_help import _raw_rows, _metadata, _normalized_english, SEMANTIC_CONTROLS
from tools.first_save_help_inventory import inventory
from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english
from tools.r67_15g_help_layout import _va_to_offset, _wrap
from tools.r67_15h_item_layout import _validate_translation_load, APPEND_VA, APPEND_FILE_OFFSET, APPEND_RESERVE
from tools.r67_15j_action_labels import CORPUS_PATH, CORPUS_SHA256

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent/'startup-flow-v10/fixtures/elf/SLPM_665.11'
ORIGINAL_SHA256 = '6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794'
BLANK, EOF = 0x795FB8, 0x795FBC

# Half-open original row ranges, native metadata indices, blank separator.
# These encode source ownership, not translations or resulting row positions.
UNITS = {
    'item_screen': [
        (0,1,(),0),(2,4,(0,),1),(5,7,(),1),(9,11,(),1),
        (11,12,(1,),0),(12,13,(2,3),0),(13,14,(4,),0),
        (14,15,(5,),0),(15,16,(6,),0),(16,17,(7,),0),
        (17,18,(8,),0),(18,19,(9,10),0),(21,23,(),1),
        (23,24,(11,),0),(24,25,(12,),0),
        *[(row,row+1,(row-13,),0) for row in range(26,33)],
        (35,37,(20,),1),(38,39,(21,),0),(39,40,(22,),0)],
    'item_synthesis': [(0,1,(),0),(2,4,(),1),(6,8,(),1),
                       (8,10,(0,),1),(11,13,(1,),1),(14,15,(2,),1),(16,18,(3,4),1)],
    'save_load': [(0,1,(),0),(2,5,(),1),(6,9,(),1),(11,16,(0,),1)],
    'wire_gun': [(0,1,(),0),(2,5,(0,),1),(7,9,(),1),
                 (9,12,(1,4),1),(16,19,(3,),1),(20,24,(2,5),1),(25,26,(6,),1)],
    'jumping': [(0,1,(),0),(2,4,(0,),1),(6,8,(),1),
                (8,11,(1,4),1),(16,19,(2,5),1),(23,25,(3,6),1),
                (29,33,(7,),1),(34,37,(8,),1)],
}
OWNERS = {
    'item_screen': (0x5CBAC8,0x5CBA78,0x960FF4,0x957D0C),
    'item_synthesis': (0x5CBADC,0x5CBA8C,0x964E30,0x964EBC),
    'save_load': (0x5CBAE8,0x5CBA98,0x96510C,0x965158),
    'wire_gun': (0x5C8A90,0x5C8A40,0x965494,0x965574),
    'jumping': (0x5C8A8C,0x5C8A3C,0x965958,0x965A74),
}
ALLOWED_SOURCE_RANGES = {
    key: ((td,td+4),(md,md+4)) for key,(td,md,_,_) in OWNERS.items()
}


def frames(raw, group, sprite):
    table = struct.unpack_from('<I',raw,_va_to_offset(raw,0x485240+group*4))[0]
    address,count = struct.unpack_from('<II',raw,_va_to_offset(raw,table+sprite*8))
    if not 0<count<=32: raise ValueError('invalid native animation frame count')
    result=[]
    for index in range(count):
        values=struct.unpack_from('<4f',raw,_va_to_offset(raw,address+index*0x30)+4)
        if any(not math.isfinite(v) or v!=int(v) for v in values):
            raise ValueError('unsupported fractional native sprite geometry')
        width,height,px,py=map(int,values)
        if not 0<width<=512 or not 0<height<=512:
            raise ValueError('invalid native sprite extent')
        result.append((width,height,px,py))
    return tuple(result)


def envelope(values):
    # Bounds are half-open; native final vertex is one pixel before right/bottom.
    return (min(-px for w,h,px,py in values), min(-py for w,h,px,py in values),
            max(w-px for w,h,px,py in values), max(h-py for w,h,px,py in values))


def plan(raw, page, original, official):
    source_rows = _raw_rows(original,page)
    source_icons = _metadata(original,page)
    rows,blocks=[],[]
    icons=[None]*len(source_icons)
    metadata=[None]*len(source_icons)
    used_rows=set()
    for lo,hi,indices,gap in UNITS[page['key']]:
        if used_rows.intersection(range(lo,hi)): raise ValueError('overlapping source units')
        used_rows.update(range(lo,hi))
        pieces,provenance=[],[]
        for item in source_rows[lo:hi]:
            if item is None: continue
            offset,encoded=item
            jp=encoded[:-1].decode('cp932')
            matches=official.get(jp,set())
            if len(matches)==1:
                english,record=next(iter(matches))
                provenance.append({'ps2_offset':offset,'ps4_record':record,'kind':'exact'})
            elif offset in SEMANTIC_CONTROLS:
                english=SEMANTIC_CONTROLS[offset]
                provenance.append({'ps2_offset':offset,'kind':'existing_ps2_control'})
            else: raise ValueError(f'no unique official row at {offset:#x}')
            normalized=_normalized_english(english)
            if normalized: pieces.append(normalized)
        text=' '.join(pieces)
        if not text: raise ValueError('empty semantic unit')
        if rows: rows.extend(['']*gap)
        row=len(rows)
        left=85
        maximum_height=0
        placements=[]
        for index in indices:
            if icons[index] is not None: raise ValueError('duplicate icon association')
            group,sprite,_,_=source_icons[index]
            geometry=frames(raw,group,sprite)
            x0,y0,x1,y1=envelope(geometry)
            width,height=x1-x0,y1-y0
            placements.append((index,left,width,height,x0,y0,geometry))
            left+=width+6
            maximum_height=max(maximum_height,height)
        indent=math.ceil((left-85)/12) if indices else 0
        wrapped=_wrap(text,28-indent)
        rows.extend(' '*indent+line for line in wrapped)
        occupied=max(len(wrapped),math.ceil(maximum_height/16))
        rows.extend(['']*(occupied-len(wrapped)))
        blocks.append({'row':row,'end_row':len(rows),'text':text,
                       'source_rows':[lo,hi],'provenance':provenance})
        for index,left,width,height,x0,y0,geometry in placements:
            group,sprite,_,_=source_icons[index]
            # Metadata stores the anchor, not its top-left corner.
            metadata[index]=(group,sprite,left-x0-73,131+16*row-y0-119)
            icons[index]={'index':index,'identity':[group,sprite],
                'row':row,'instruction_row':row,'official_text':text,
                'rect':[left,131+16*row,width,height], 'frames':geometry}
    for index,entry in enumerate(source_rows):
        if entry and index not in used_rows:
            jp=entry[1][:-1].decode('cp932')
            values=official.get(jp,set())
            if len(values)!=1 or _normalized_english(next(iter(values))[0]):
                raise ValueError(f'unaccounted source row {page["key"]}/{index}')
    if any(icon is None for icon in icons): raise ValueError('unassigned native icon')
    if len(rows)>80: raise ValueError('page exceeds audited native row capacity')
    glyphs=[]
    for index,line in enumerate(rows):
        for column,character in enumerate(line):
            if character!=' ': glyphs.append((85+12*column,131+16*index,12,12))
    intersections=[]
    for icon in icons:
        x,y,w,h=icon['rect']
        for gx,gy,gw,gh in glyphs:
            if x<gx+gw and gx<x+w and y<gy+gh and gy<y+h:
                intersections.append([icon['index'],gx,gy])
    if intersections: raise ValueError(f'icon/text intersection: {intersections[:3]}')
    return {'rows':rows,'icons':icons,'blocks':blocks,'intersections':intersections,
            'source_icons':len(source_icons)}, metadata


def build(source):
    _validate_translation_load(source)
    original=ORIGINAL.read_bytes()
    if hashlib.sha256(original).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('pristine Help source identity changed')
    if hashlib.sha256(CORPUS_PATH.read_bytes()).hexdigest()!=CORPUS_SHA256:
        raise ValueError('official Help corpus identity changed')
    corpus=parse(CORPUS_PATH)
    official={}
    for jp,en,record in corpus: official.setdefault(jp,set()).add((en,record))
    source_pages={p['key']:p for p in inventory(original,corpus)['pages']}
    out=bytearray(source)
    reports={}
    def append(data,alignment=4):
        out.extend(b'\0'*(-len(out)%alignment))
        va=APPEND_VA+len(out)-APPEND_FILE_OFFSET
        out.extend(data)
        return va
    for key,(td,md,old_text,old_meta) in OWNERS.items():
        if (struct.unpack_from('<I',source,td)[0],struct.unpack_from('<I',source,md)[0])!=(old_text,old_meta):
            raise ValueError(f'{key} descriptor preimage changed')
        page=source_pages[key]
        report,metadata=plan(source,page,original,official)
        pointers=[append(encode_ps2_english(row,collapse_spaces=False)+b'\0',2) if row else BLANK
                  for row in report['rows']]
        text_va=append(struct.pack('<'+'I'*(len(pointers)+1),*pointers,EOF))
        meta_va=append(b''.join(struct.pack('<4h',*row) for row in [*metadata,(-1,-1,-1,-1)]))
        struct.pack_into('<I',out,td,text_va)
        struct.pack_into('<I',out,md,meta_va)
        report.update(text_va=text_va,metadata_va=meta_va)
        reports[key]=report
    if len(out)-APPEND_FILE_OFFSET>APPEND_RESERVE: raise ValueError('Help append exceeds memory reserve')
    struct.pack_into('<I',out,0x64,len(out)-APPEND_FILE_OFFSET)
    allowed=set(range(0x64,0x68))
    for spans in ALLOWED_SOURCE_RANGES.values():
        for lo,hi in spans: allowed.update(range(lo,hi))
    changed={i for i,(a,b) in enumerate(zip(source,out)) if a!=b}
    if changed-allowed: raise ValueError('unexpected Help source mutation')
    return bytes(out),{'source_sha256':hashlib.sha256(source).hexdigest(),
        'result_sha256':hashlib.sha256(out).hexdigest(),'corpus_sha256':CORPUS_SHA256,
        'pages':reports,'runtime_verified':False,'changed_existing_offsets':sorted(changed),
        'appended_extent':[len(source),len(out)]}
