"""r67.15d exact unlocalized Gold Chains and in-menu Compound owners.

Native inventory object record: 0x58A9F0 (six pointer fields)
0: title Gold Chains; 1..3: three bounded description lines; 4: reserved
empty; 5: original phonetic Japanese subtitle removed, mirroring approved
Anubis/Snake Staff handling. Original source bytes remain intact.

The little floating synthesis action label uses H_Item pointer table entry
0x38632C, separate from the previously translated compound-success text.

Only these six native owner words and append-only English are modified.
"""
from __future__ import annotations
import hashlib,json,struct
from pathlib import Path
from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_14y_inspection_save import validate_result,EMPTY
from tools.r67_14y_release import verify_save_identity
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T

ROOT=Path(__file__).resolve().parents[1]
CORPUS=Path('/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
SOURCE_SHA="c9328e04282e652035119ab331adaa9adeac232507b86632ea67ecab39356ffa"
CORPUS_SHA="b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
FO=0x803150
VA=0x902F00
BIAS=0xfff80
RESERVE=0x100000
OWNERS={
  0x58A9F0:(0x68A8F8,'黄金の鎖','Gold Chains',0xC58DD),
  0x58A9F4:(0x68A910,'　純金製の強度の高い鎖。','Very strong chains',0xC58FC),
  0x58A9F8:(0x68A930,'　扉に固定されている。','made of pure gold.',0xC594B),
  0x58A9FC:(EMPTY,'','Affixed to the door.',0xC594B),
  0x58AA04:(0x68A950,'おうごんのくさり','',None),
  0x38632C:(0x793678,'調合','Compound',0x46208)
}
OFFICIAL={
    0xC58DD:('黄金の鎖','Gold Chains'),
    0xC58FC:('　純金製の強度の高い鎖。','　Very strong chains of pure gold.'),
    0xC594B:('　扉に固定されている。','　Affixed to the door.'),
    0x46208:('調合','Compound'),
}

def sha(x):return hashlib.sha256(x).hexdigest()

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=SOURCE_SHA:raise ValueError('Only exact, independently audited 15c ELF preimage accepted')
    if sha(CORPUS.read_bytes())!=CORPUS_SHA:raise ValueError('PS4 English source corpus changed')
    lookup={offset:(jp,en) for jp,en,offset in parse(CORPUS)}
    for offset,pair in OFFICIAL.items():
        if lookup.get(offset)!=pair:raise ValueError(f'PS4 reference mismatch at {offset:#x}')
    six=struct.unpack_from('<6I',source,0x58A9F0)
    if six!=(0x68A8F8,0x68A910,0x68A930,EMPTY,EMPTY,0x68A950):
        raise ValueError('Native Gold Chains record topology drift')
    out=bytearray(source)
    changed_words={}
    records=[]
    for owner,(ptr,jp,en,official_ref) in OWNERS.items():
        value=struct.unpack_from('<I',source,owner)[0]
        if value!=ptr:raise ValueError(f'Native exact owner pointer drift {owner:#x}')
        if read_string(source,value).decode('cp932')!=jp:
            raise ValueError(f'Native original Japanese source drift {owner:#x}')
        cells=len(en)
        bound=14 if owner in (0x58A9F0,0x58AA04) else 21
        if cells>bound:raise ValueError(f'Native row too wide at {owner:#x}: {cells}>{bound}')
        if owner==0x58AA04:
            next_va=EMPTY
        else:
            while len(out)%2:out.append(0)
            next_va=VA+len(out)-FO
            payload=encode_ps2_english(en,collapse_spaces=False)
            if len(payload)!=2*cells:raise ValueError('Unexpected CP932 encoded glyph cells')
            out.extend(payload+b'\0')
        struct.pack_into('<I',out,owner,next_va)
        changed_words[owner]=next_va
        records.append(dict(native_owner=hex(owner),old_pointer=hex(ptr),
            new_pointer=hex(next_va),old_native=jp,new_english=en,
            official_corpus_record=hex(official_ref) if official_ref else None,
            title_or_action_fit_cells=cells,limit=bound))
    while len(out)%4:out.append(0)
    if len(out)-FO>RESERVE:raise ValueError('Translation ELF segment has insufficient reserved bytes')
    struct.pack_into('<I',out,0x64,len(out)-FO)
    allowed=set(range(0x64,0x68))
    for owner in changed_words:allowed.update(range(owner,owner+4))
    edits={i for i,(a,b) in enumerate(zip(source,out)) if a!=b}
    if not edits or edits-allowed:raise ValueError(f'Changed protected existing bytes: {edits-allowed}')
    result=bytes(out)
    if struct.unpack_from('<I',result,0x58AA00)[0]!=EMPTY:
        raise ValueError('Native empty-inspection sentinel changed')
    if struct.unpack_from('<I',result,0x58A9FC)[0]==EMPTY:
        raise ValueError('Gold Chains third visible English row missing')
    for rec in records:
        owner=int(rec['native_owner'],16)
        value=struct.unpack_from('<I',result,owner)[0]
        assert read_string(result,value).decode('cp932')==(
            '' if owner==0x58AA04 else ''.join(chr(ord(ch)+0xFEE0) if 33<=ord(ch)<=126 else
            '\u3000' if ch==' ' else ch for ch in OWNERS[owner][2]))
    verify_approved(result,json.loads(Q.read_text()))
    # 15a explicitly replaced the two accepted Lion JAL sites with its
    # documented generic width helper. In-memory reconstruction only.
    original_z=ROOT/'local/r67-14z-storeroom-tablet.elf'
    z=original_z.read_bytes()
    if sha(z)!='c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2':
        raise ValueError('Approved z source lock changed')
    reconstructed=bytearray(result)
    for site in (0x2A2A6C,0x2A6060):
        p=site-BIAS
        reconstructed[p:p+4]=z[p:p+4]
    verify_ui(bytes(reconstructed),json.loads(T.read_text()))
    validate_result(result)
    verify_save_identity(result)
    return result,dict(release='r67.15d',prior_sha256=SOURCE_SHA,
        result_sha256=sha(result),official_ps4_records=OFFICIAL,
        owned_native_pointer_records=records,
        changed_original_bytes=len(edits),
        appended_bytes=len(result)-len(source),
        strict_q_t_approval_verified_with_prior_lion_jals_reconstructed=True,
        all_other_inspections_save_and_event_data_intact=True,
        gameplay_approval=False)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    for key in ('input','output','report'):ap.add_argument('--'+key,required=True,type=Path)
    args=ap.parse_args()
    if args.output.exists() or args.report.exists():raise FileExistsError('Never overwrite diagnostic files')
    patched,meta=apply(args.input.read_bytes())
    args.output.write_bytes(patched)
    args.report.write_text(json.dumps(meta,indent=2,sort_keys=True,default=str)+'\n')
    print(json.dumps(dict(status='PASS',sha256=meta['result_sha256'],changed_prior_bytes=meta['changed_original_bytes'])))
