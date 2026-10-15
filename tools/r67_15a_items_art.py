"""r67.15a item-acquisition textures: PS4 EN sprites plus native footer repaint.

The chest choices/header/storage images have DIRECT official PS4 English art
(GP004_03 and GP004_15..18), whose native-JP source masks can be matched to
the current PS2 entries. Each corresponding TMX is imported by the existing
strict, same-size atlas porter. The PS4 GP004_19 EN texture contains NO
labels; PS2 UI relies on baked JP labels. Keep the original transparent native
font atlas and repaint only its five label cells, using verified PS4 command
terms for Compound/Swap and compact semantic equivalents for the others.

All changes are confined to exact seven named group-4 TMX chunks. Chest
ornaments, item illustrations, playfield, other groups, save/HANT and every
existing ELF byte remain untouched by this texture module.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from tools.first_save_graphics_port import get_english_pixels,translated_asset
from tools.tmx import (
    find_tmx_entry,_decode_palette,_decode_indices,replace_tmx_indexed,
)
from tools.hant_graphics import _FONT_5X7

INPUT_SHA="732a68c2c4e7e22a2d0e553ddd066d2c1c3b96a6ed15bc73edc89d988a3816b4"
PS4_ROOT=Path('/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/BLBRD')
OFFICIAL_INDICES=(3,5,15,16,17,18)
FOOTER_TMX="GRP004/GP004_19.TMX"
FOOTER_RECTANGLES=(
    (0,0,48,32,"INFO"),
    (48,0,124,32,"COMPOUND"),
    (0,34,48,64,"SWAP"),
    (48,34,124,64,"DISCARD"),
    (0,68,124,100,"RECYCLE"),
)
FOOTER_NATIVE_TRANSPARENT=171
FOOTER_NATIVE_GOLD=6
FONT=dict(_FONT_5X7,W=("10001","10001","10001","10101","10101","11011","10001"))


def sha(data:bytes)->str:
    return sha256(data).hexdigest()


def paint_footer(source:bytes)->tuple[bytes,dict]:
    e=find_tmx_entry(source,FOOTER_TMX)
    if (e.width,e.height,e.image_psm,e.palette_entries)!=(128,128,0x13,256):
        raise ValueError("Native item-bar glyph texture changed dimensions/layout")
    pal=_decode_palette(source,e)
    if (pal[FOOTER_NATIVE_TRANSPARENT][3]!=0 or
        pal[FOOTER_NATIVE_GOLD]!=(255,156,0,255)):
        raise ValueError("Original item footer transparent/gold palette drift")
    original=_decode_indices(source,e)
    updated=bytearray(original)
    affected=set()
    for x0,y0,x1,y1,label in FOOTER_RECTANGLES:
        if not (0<=x0<x1<=128 and 0<=y0<y1<=128):
            raise ValueError("Footer rectangle outside the atlas")
        if any(ch not in FONT for ch in label):
            raise ValueError(f"Unsupported footer letter in {label}")
        tw=len(label)*6-1
        th=14
        if tw>x1-x0-6 or th>y1-y0-6:
            raise ValueError(f"Footer label {label} would collide with adjacent button")
        for y in range(y0,y1):
            for x in range(x0,x1):
                off=y*e.width+x
                if off in affected:raise ValueError("Footer caption rectangles overlap")
                affected.add(off)
                updated[off]=FOOTER_NATIVE_TRANSPARENT
        xbase=x0+(x1-x0-tw)//2
        ybase=y0+(y1-y0-th)//2
        for i,ch in enumerate(label):
            for row in range(7):
                for col,bit in enumerate(FONT[ch][row]):
                    if bit=="1":
                        for fy in (0,1):
                            pos=(ybase+row*2+fy)*e.width+xbase+i*6+col
                            updated[pos]=FOOTER_NATIVE_GOLD
    changed={i for i,(a,b) in enumerate(zip(original,updated)) if a!=b}
    if not changed or not changed<=affected:
        raise ValueError("Item footer repaint unexpectedly changed other pixels")
    result=replace_tmx_indexed(source,FOOTER_TMX,pal,updated)
    if find_tmx_entry(result,FOOTER_TMX)!=e:
        raise ValueError("Item footer texture layout changed")
    return result,dict(texture=FOOTER_TMX,captions=[r[-1] for r in FOOTER_RECTANGLES],
        rectangles=[r[:4] for r in FOOTER_RECTANGLES],changed_pixel_count=len(changed),
        terminology="PS4 Compound/Swap official; Info/Discard/Recycle compact semantic UI labels",
        ps4_localized_art_is_blank=True)


def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=INPUT_SHA:
        raise ValueError("Approved native B_GP004 source fingerprint mismatch")
    current=source
    art=[]
    for idx in OFFICIAL_INDICES:
        jp,en,dim,jp_sha,en_sha=get_english_pixels(PS4_ROOT,4,idx)
        current,report=translated_asset(current,jp,en,dim,4,idx)
        if report["jp_geometry_dice"]<0.93:
            raise ValueError(f"Official item atlas native Japanese preimage not proven {idx}")
        art.append(dict(official_en_index=idx,official_ps4_jp_sha256=jp_sha,
                        official_ps4_en_sha256=en_sha,**report))
    current,footer=paint_footer(current)
    if len(current)!=len(source):
        raise ValueError("Native item acquisition container size changed")
    covered=[]
    for idx in (*OFFICIAL_INDICES,19):
        e=find_tmx_entry(source,f"GRP004/GP004_{idx:02}.TMX")
        covered.append((e.base_offset,e.base_offset+e.chunk_size))
    unexpected=[i for i,(a,b) in enumerate(zip(source,current))
                if a!=b and not any(l<=i<r for l,r in covered)]
    if unexpected:raise ValueError(f"Non-item sprite changed at {unexpected[0]:#x}")
    return current,dict(status="DIAGNOSTIC_NEEDS_NATIVE_SCREENSHOTS",
        source_sha256=INPUT_SHA,output_sha256=sha(current),
        official_ps4_art=art,footer=footer,
        prior_user_approved_nonitem_sprites_byte_identical=True,
        original_isos_untouched=True,
        gameplay_approved=False)


if __name__=="__main__":
    import argparse,json
    ap=argparse.ArgumentParser()
    for k in ("input","output","report"):ap.add_argument("--"+k,type=Path,required=True)
    p=ap.parse_args()
    if p.output.exists() or p.report.exists():raise FileExistsError("Do not overwrite")
    dest,report=apply(p.input.read_bytes())
    p.output.write_bytes(dest)
    p.report.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"sha256":report["output_sha256"],
                      "official_art":[p["official_en_index"] for p in report["official_ps4_art"]]},sort_keys=True))
