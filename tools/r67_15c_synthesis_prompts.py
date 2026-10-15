"""r67.15c: official PS4 item synthesis messages, preserving native placeholders.

Three independent executable UI owners:
- Native item-compound notification text, one pointer alias.
- Small Compounded-name action prompt, native LUI/ADDIU pair.
- Complementary 'Stored in' text, distinct LUI/ADDIU pair.
Official English.bytes uses {0}/{1}; original PS2 requires native ASCII %s
format directives while all display glyphs remain CP932 2-byte text.
No global item catalog, renderer, approved screen, save code or art modified.
"""
from __future__ import annotations
import hashlib,struct
from pathlib import Path
from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q
import json

OFFICIAL=Path('/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
PAIRS=(
    (0x386010,'%s　を調合！！＠改行%s＠改行に格納しました。',
     '{0}　を調合！！＠改行{1}＠改行に格納しました。',
     'Compounded {0}! Item has been stored in＠改行{1}＠改行.',0x458c9),
    (0x386238,'%s　を調合！','{0}　を調合！','Compounded {0}!',0xd13c5),
    (0x386248,'に格納しました','に格納しました','Stored in ',0xd13ee),
)
OWNERS={
    0x386010:('pointer',0x3861d0),
    0x386238:('code',0xd660,0xd664),
    0x386248:('code',0xd718,0xd71c),
}
FO=0x803150
VA=0x902F00
RESERVE=0x100000

def sha(raw):return hashlib.sha256(raw).hexdigest()

def encoded_formatted(text:str)->bytes:
    import re
    tokens=re.split(r'(\{[01]\})',text)
    out=b''.join(b'%s' if p in ('{0}','{1}') else encode_ps2_english(p,collapse_spaces=False)
                 for p in tokens if p)
    if out.count(b'%s')!=text.count('{'):raise ValueError("Synthesis placeholder dropped")
    return out+b'\0'

def _materialize_hi_lo(value:int,rs:int)->tuple[int,int]:
    hi=(value+0x8000)>>16
    lo=value&0xffff
    if not 0<=hi<=0xffff:raise ValueError("Synthesis text pointer outside MIPS 32-bit range")
    return ((15<<26)|(rs<<16)|hi,
            (9<<26)|(rs<<21)|(rs<<16)|lo)

def apply(source:bytes,expected_sha:str)->tuple[bytes,dict]:
    if sha(source)!=expected_sha:raise ValueError("Approved 15b installed ELF preimage mismatch")
    corpus={(jp,off):en for jp,en,off in parse(OFFICIAL)}
    data=bytearray(source)
    modifications=set(range(0x64,0x68))
    records=[]
    for offset,source_jp,ps4_jp,ps4_en,ps4_record in PAIRS:
        if corpus.get((ps4_jp,ps4_record))!=ps4_en:
            raise ValueError(f"Official PS4 synthesized prompt mapping drift: {offset:#x}")
        native=source_jp.encode('cp932')+b'\0'
        if source[offset:offset+len(native)]!=native:
            raise ValueError(f"Original formatted prompt drift: {offset:#x}")
        if len(data)&1:data.append(0)
        pointer=VA+len(data)-FO
        payload=encoded_formatted(ps4_en)
        if payload.count(b'%s')!=source_jp.count('%s'):
            raise ValueError("Old/new synthesis format argument count differs")
        data.extend(payload)
        info=OWNERS[offset]
        if info[0]=='pointer':
            where=info[1]
            if struct.unpack_from('<I',source,where)[0]!=offset+0xfff80:
                raise ValueError("Synthesis prompt pointer alias fingerprint drift")
            struct.pack_into('<I',data,where,pointer)
            modifications.update(range(where,where+4))
            patched=[hex(where)]
        else:
            _,hi_off,lo_off=info
            reg=(struct.unpack_from('<I',source,hi_off)[0]>>16)&31
            old=_materialize_hi_lo(offset+0xfff80,reg)
            if (struct.unpack_from('<I',source,hi_off)[0],
                struct.unpack_from('<I',source,lo_off)[0])!=old:
                raise ValueError(f"Synthesis code materialization drift {offset:#x}")
            new=_materialize_hi_lo(pointer,reg)
            struct.pack_into('<I',data,hi_off,new[0])
            struct.pack_into('<I',data,lo_off,new[1])
            modifications.update(range(hi_off,hi_off+4))
            modifications.update(range(lo_off,lo_off+4))
            patched=[hex(hi_off),hex(lo_off)]
        records.append(dict(source=hex(offset),official_ps4_record=hex(ps4_record),
                            official_english=ps4_en,
                            ps2_format_directives=payload.count(b'%s'),
                            relocated_va=hex(pointer),owners=patched))
    while len(data)&3:data.append(0)
    if len(data)-FO>RESERVE:raise ValueError("Translation ELF reservation exceeded")
    struct.pack_into('<I',data,0x64,len(data)-FO)
    edits={i for i,(x,y) in enumerate(zip(source,data)) if x!=y}
    if not edits or edits-modifications:
        raise ValueError(f"Unapproved synthesis old ELF mutation: {edits-modifications}")
    result=bytes(data)
    # Audit *exact* user-approved q/t bytes WITHOUT modifying the manifests.
    verify_approved(result,json.loads(Q.read_text()))
    # The preceding 15a name-width change already replaces exactly two
    # approved 14t Lion JALs. Restore their z bytes IN MEMORY for the original
    # unchanged lock. Nothing else is masked or rebaselined.
    original_z=Path(__file__).resolve().parents[1]/'local/r67-14z-storeroom-tablet.elf'
    z=original_z.read_bytes()
    if sha(z)!='c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2':
        raise ValueError('Approved z reconstruction source SHA drift')
    reconstructed=bytearray(result)
    for va in (0x2A2A6C,0x2A6060):
        pos=va-0xfff80
        reconstructed[pos:pos+4]=z[pos:pos+4]
    verify_ui(bytes(reconstructed),json.loads(T.read_text()))
    return result,dict(status="DIAGNOSTIC_AWAITING_SYNTHESIS_PLAYTEST",
        input_elf_sha256=expected_sha,output_elf_sha256=sha(result),
        expanded_bytes=len(result)-len(source),owners=records,
        changed_old_offsets=list(map(hex,sorted(edits))),
        native_500_item_names_unchanged=True,
        official_ps4_strings=True,
        runtime_verified=False)

if __name__=='__main__':
    import argparse,json
    ap=argparse.ArgumentParser()
    for name in ('input','output','report'):ap.add_argument('--'+name,required=True,type=Path)
    ap.add_argument('--input-sha',required=True)
    opts=ap.parse_args()
    if opts.output.exists() or opts.report.exists():raise FileExistsError("Never overwrite diagnostic files")
    result,report=apply(opts.input.read_bytes(),opts.input_sha)
    opts.output.write_bytes(result)
    opts.report.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps(report,sort_keys=True))
