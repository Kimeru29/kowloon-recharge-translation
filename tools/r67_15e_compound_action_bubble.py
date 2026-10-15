"""r67.15e: Compounding action bubble width and official same-item label.

User-approved r67.15d is immutable. Native H_Item action selector 0x114A20
constructs the white background sprite type 0x5E/0x5F, puts its pointer
in 0(s0), and renders the action indexed at 0x18(s0). Sprite constructor
0x107FBC initializes horizontal scale at +0x60 to 1.0f. Only action index
3 (Compound) needs the horizontal scale increased to 2.0f; other action
IDs retain exact original geometry.

The same-item action id 1 points to native 禁止. Official PS4 English corpus
record 0x461E4 reads Can't. Redirect only its pointer table owner 0x386324
to appended fullwidth native English glyphs. Earlier game/saves untouched.
"""
from __future__ import annotations
import json,hashlib,struct
from pathlib import Path
from tools.r67_chamber_story_text_only import _i
from tools.localization import encode_ps2_english
from tools.inspect_english_bytes import parse
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T
from tools.r67_14y_release import verify_save_identity
from tools.r67_14y_inspection_save import validate_result

ROOT=Path(__file__).resolve().parents[1]
BASE_SHA="bff8439a1696272342130808339dd20580c3391538dc5a2c9f1b773f129b23e4"
CORPUS_SHA="b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
CORPUS=Path('/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
FO=0x803150
VA=0x902F00
RESERVE=0x100000
BIAS=0xfff80
JUMP_SITE=0x114AD8
JUMP_ORIGINAL=0x10000009    # original branch to 0x114B00, with nop delay
RESUME=0x114B00
ACTION_PTR_OFF=0x386324
ACTION_OLD_PTR=0x793668
ACTION_NAME_JP="禁止"
ACTION_NAME_EN="Can't"
PS4_ROW_OFFSET=0x461E4
COMPOUND_ACTION_ID=3
SPRITE_X_SCALE_OFFSET=0x60
TARGET_X_SCALE=2.0
UNMODIFIED_PREVIOUS_POINTERS={0x386320:0x793660,0x386328:0x793670}
ENGLISH_COMPOUND_OWNER=0x38632c

def sha(data):return hashlib.sha256(data).hexdigest()

def _j(va:int)->int:
    if not 0<=va<0x10000000:raise ValueError('MIPS jump cannot reach selected address')
    return (2<<26)|((va>>2)&0x03ffffff)

def build_helper()->bytes:
    # Exactly eleven instructions. Conditional branches skip the scale
    # write and jump directly to original 0x114B00. No return-address
    # dependence: this is a tail jump from a replaced native branch.
    words=(
        _i(35,16,8,0x18),                   # 0 lw t0,action_id(s0)
        _i(9,0,9,COMPOUND_ACTION_ID),        # 1 li t1,3
        _i(5,8,9,6),                        # 2 bne -> index9
        0,                                   # 3 delay
        _i(35,16,8,0),                      # 4 lw t0,0(s0)
        _i(4,8,0,3),                        # 5 beq null -> index9
        0,                                   # 6 delay
        _i(15,0,9,0x4000),                  # 7 lui t1,2.0f
        _i(43,8,9,SPRITE_X_SCALE_OFFSET),   # 8 sw t1,+0x60(sprite)
        _j(RESUME),                          # 9 resume original code
        0,                                   # 10 jump delay
    )
    return struct.pack('<11I',*words)

def apply(old:bytes)->tuple[bytes,dict]:
    if sha(old)!=BASE_SHA:
        raise ValueError('Previously approved r67.15d ELF SHA changed')
    if sha(CORPUS.read_bytes())!=CORPUS_SHA:
        raise ValueError('Official PS4 text corpus changed')
    rows={off:(jp,en) for jp,en,off in parse(CORPUS)}
    if rows.get(PS4_ROW_OFFSET)!=(ACTION_NAME_JP,ACTION_NAME_EN):
        raise ValueError('Same-item label not confirmed in official PS4 release')
    if struct.unpack_from('<I',old,JUMP_SITE-BIAS)[0]!=JUMP_ORIGINAL:
        raise ValueError('Native background branch preimage drift')
    if struct.unpack_from('<I',old,JUMP_SITE-BIAS+4)[0]!=0:
        raise ValueError('Native background jump-delay slot drift')
    if struct.unpack_from('<I',old,ACTION_PTR_OFF)[0]!=ACTION_OLD_PTR:
        raise ValueError('Same-item native pointer drift')
    if read_string(old,ACTION_OLD_PTR).decode('cp932')!=ACTION_NAME_JP:
        raise ValueError('Same-item source Japanese drift')
    for off,expected in UNMODIFIED_PREVIOUS_POINTERS.items():
        if struct.unpack_from('<I',old,off)[0]!=expected:
            raise ValueError(f'Protected neighbor H_Item label changed {off:#x}')
    p=struct.unpack_from('<I',old,ENGLISH_COMPOUND_OWNER)[0]
    if read_string(old,p).decode('cp932')!='Ｃｏｍｐｏｕｎｄ':
        raise ValueError('Approved Compound label is not present')
    if struct.unpack_from('<I',old,0x107FBC-BIAS)[0]!=_i(43,18,2,0x60):
        raise ValueError('Native sprite constructor scaleX field not proven')
    data=bytearray(old)
    while len(data)&3:data.append(0)
    helper_va=VA+len(data)-FO
    body=build_helper()
    if len(body)!=44:raise ValueError('Unexpected private MIPS hook length')
    data.extend(body)
    while len(data)&1:data.append(0)
    ptr=VA+len(data)-FO
    en=encode_ps2_english(ACTION_NAME_EN,collapse_spaces=False)
    if len(en)!=2*len(ACTION_NAME_EN):
        raise ValueError('Expected native fullwidth ASCII glyphs')
    data.extend(en+b'\0')
    while len(data)&3:data.append(0)
    if len(data)-FO>RESERVE:raise ValueError('Translation ELF reservation exceeded')
    struct.pack_into('<I',data,JUMP_SITE-BIAS,_j(helper_va))
    struct.pack_into('<I',data,ACTION_PTR_OFF,ptr)
    struct.pack_into('<I',data,0x64,len(data)-FO)
    allowed=set(range(0x64,0x68))|set(range(JUMP_SITE-BIAS,JUMP_SITE-BIAS+4))|set(range(ACTION_PTR_OFF,ACTION_PTR_OFF+4))
    edits={i for i,(a,b) in enumerate(zip(old,data)) if a!=b}
    if not edits or edits-allowed:raise ValueError(f'Prior approved ELF changed {edits-allowed}')
    result=bytes(data)
    verify_approved(result,json.loads(Q.read_text()))
    z=(ROOT/'local/r67-14z-storeroom-tablet.elf').read_bytes()
    if sha(z)!='c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2':
        raise ValueError('Approved 14z Lion helper source drift')
    original_lion=bytearray(result)
    for site in (0x2A2A6C,0x2A6060):
        pos=site-BIAS
        original_lion[pos:pos+4]=z[pos:pos+4]
    verify_ui(bytes(original_lion),json.loads(T.read_text()))
    validate_result(result)
    verify_save_identity(result)
    return result,dict(status='DIAGNOSTIC_NEEDS_COMPOUND_PLAYTEST',
        source_sha256=BASE_SHA,result_sha256=sha(result),
        old_branch_va=hex(JUMP_SITE),old_branch=hex(JUMP_ORIGINAL),
        helper_va=hex(helper_va),helper_bytes=len(body),
        only_compound_action_id=COMPOUND_ACTION_ID,
        action_sprite_x_scale=TARGET_X_SCALE,sprite_y_and_other_actions_unchanged=True,
        translated_label_owner=hex(ACTION_PTR_OFF),translated_label_pointer=hex(ptr),
        official_ps4_row=hex(PS4_ROW_OFFSET),official_ps4_english=ACTION_NAME_EN,
        approved_15d_elf_existing_byte_changes=list(map(hex,sorted(edits))),
        original_save_paths_unchanged=True,gameplay_approved=False)

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    for k in ('input','output','report'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError('No overwrites')
    out,report=apply(a.input.read_bytes())
    a.output.write_bytes(out)
    a.report.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('result_sha256','helper_va','official_ps4_english')},sort_keys=True))
