"""r67.15d exact two-texture fixes after r67.15c gameplay screenshots.

GP004_18: Keep the original *official PS4 English* 'Choose storage'
lettering within the first native 128px cell. Restore only the removed
overflowing 'location' glyphs in the adjacent tile; the approved native Vest
and Room pixels stay untouched. Do not redraw the first title or synthesize
unrelated background.

GP004_19: The PS2 live renderer samples only a 48px action cell (x48..96)
for 'Compound'; the prior eight-character 6px font spills beyond it.
Redraw official COMPOUND using a condensed 4-column glyph with 1px spacing,
within the observed native source cell. Keep all four other action labels.
"""
from __future__ import annotations
import hashlib
import numpy as np
import cv2
from tools.tmx import find_tmx_entry,_decode_indices,_decode_palette,replace_tmx_indexed
from tools.hant_graphics import _FONT_5X7
from tools.r67_15a_items_art import FONT,FOOTER_NATIVE_GOLD,FOOTER_NATIVE_TRANSPARENT

BASE_C_SHA="e1f0fdbd7cf763304e03c69c5b7e53b0abf34fbd4b3b16d218fb24e251349ee1"
OFFICIAL_V2_SHA="7cc70afb776cf135a796e072a40319c4074dadee410baca1e17c7f68f025f390"
STORAGE="GRP004/GP004_18.TMX"
FOOTER="GRP004/GP004_19.TMX"
HEADER_REGION=(130,7,220,25)
FOOTER_REGION=(48,0,124,32)
LIVE_SECOND_SLOT=(48,0,96,32)

def sha(data):return hashlib.sha256(data).hexdigest()

def restore_header(native_c:bytes,ps4_art:bytes)->tuple[bytes,dict]:
    current=find_tmx_entry(native_c,STORAGE)
    official=find_tmx_entry(ps4_art,STORAGE)
    if current!=official or (current.width,current.height)!=(256,128):
        raise ValueError("Native storage sprite geometry drift")
    a=_decode_indices(native_c,current)
    b=_decode_indices(ps4_art,official)
    pal=_decode_palette(native_c,current)
    if _decode_palette(ps4_art,official)!=pal:
        raise ValueError("Official English storage sprite palette drift")
    # The PS4 atlas already contains 'Choose storage' entirely within its
    # original first 128px texture tile. Keep those native pixels EXACTLY.
    # Only the continuation 'location' inside the adjacent tile conflicts
    # with the Vest label. Reconstruct its parchment from eight nearby
    # verified text-free columns (205-212), mirrored in 16px periods.
    # This avoids the previous synthetic typography and CV2 inpainting
    # that created intrusive dark vertical artifacts.
    out=bytearray(b)
    dirty=set()
    for y in range(7,25):
        for x in range(130,205):
            phase=(x-130)%16
            sample_x=205+min(phase,15-phase)
            at=y*256+x
            out[at]=b[y*256+sample_x]
            if out[at]!=a[at]:dirty.add(at)
    result=replace_tmx_indexed(native_c,STORAGE,pal,out)
    final=_decode_indices(result,find_tmx_entry(result,STORAGE))
    # The first title, the full Vest/Room and all untouched regions
    # must exactly match the imported official PS4 English image.
    for i in range(len(b)):
        x,y=i%256,i//256
        if not (130<=x<205 and 7<=y<25) and final[i]!=b[i]:
            raise ValueError("Modified original PS4 storage title, Vest or Room")
    if not dirty:raise ValueError("Native overflowing location glyphs not removed")
    return result,dict(status="ORIGINAL_PS4_FIRST_TILE_VERBATIM",
        restored_caption="Choose storage",removed_overflowing_phrase="location",
        clean_parchment_sample_columns=[205,206,207,208,209,210,211,212],
        exact_official_ps4_title_and_vest=True,
        modified_native_location_rectangle=[130,7,205,25],
        modified_pixels=len(dirty))

def compact_footer(source:bytes)->tuple[bytes,dict]:
    e=find_tmx_entry(source,FOOTER)
    if (e.width,e.height)!=(128,128):raise ValueError("Footer atlas geometry drift")
    original=_decode_indices(source,e)
    p=_decode_palette(source,e)
    if p[FOOTER_NATIVE_TRANSPARENT][3]!=0 or p[FOOTER_NATIVE_GOLD]!=(255,156,0,255):
        raise ValueError("Footer palette drift")
    out=bytearray(original)
    for y in range(FOOTER_REGION[1],FOOTER_REGION[3]):
        for x in range(FOOTER_REGION[0],FOOTER_REGION[2]):
            out[y*128+x]=FOOTER_NATIVE_TRANSPARENT
    title="COMPOUND"
    cell=5
    width=len(title)*cell-1
    left=LIVE_SECOND_SLOT[0]+(LIVE_SECOND_SLOT[2]-LIVE_SECOND_SLOT[0]-width)//2
    top=8
    for ci,ch in enumerate(title):
        # Condense each native 5-column bitmap to 4, retaining outer
        # letter contours; 1px inter-glyph spacing => 39px title in 48px.
        columns=(0,1,3,4)
        for row,bits in enumerate(FONT[ch]):
            for dx,c in enumerate(columns):
                if bits[c]!="1":continue
                for dy in (0,1):
                    x=left+ci*cell+dx;y=top+row*2+dy
                    if not(LIVE_SECOND_SLOT[0]<=x<LIVE_SECOND_SLOT[2] and
                           LIVE_SECOND_SLOT[1]<=y<LIVE_SECOND_SLOT[3]):
                        raise ValueError("Official COMPOUND spills into neighbor native action")
                    out[y*128+x]=FOOTER_NATIVE_GOLD
    changes={i for i,(a,b) in enumerate(zip(original,out)) if a!=b}
    if not changes or any(not(48<=i%128<124 and 0<=i//128<32) for i in changes):
        raise ValueError("Other item footer action modified")
    revised=replace_tmx_indexed(source,FOOTER,p,out)
    return revised,dict(status="COMPOUND_FITS_48PX_NATIVE_TILE",
        official_label="COMPOUND",onscreen_cell_width_px=48,label_width_px=width,
        source_changed_pixels=len(changes),unchanged_four_other_actions=True)

def apply(source:bytes,ps4_english_group4:bytes)->tuple[bytes,dict]:
    if sha(source)!=BASE_C_SHA:raise ValueError("Unsupported 15c source art SHA")
    if sha(ps4_english_group4)!=OFFICIAL_V2_SHA:raise ValueError("Official imported PS4 English baseline changed")
    step,header=restore_header(source,ps4_english_group4)
    result,footer=compact_footer(step)
    if len(result)!=len(source):raise ValueError("Group4 art file size changed")
    allowed=[]
    for name in (STORAGE,FOOTER):
        e=find_tmx_entry(source,name)
        allowed.append(range(e.base_offset,e.base_offset+e.chunk_size))
        if find_tmx_entry(result,name)!=e:raise ValueError("Rearranged TMX records")
    unexpected=[i for i,(a,b) in enumerate(zip(source,result))
                if a!=b and not any(i in r for r in allowed)]
    if unexpected:raise ValueError(f"Unrelated sprite change {unexpected[0]:#x}")
    return result,dict(old_group4_sha256=BASE_C_SHA,new_group4_sha256=sha(result),
        header=header,footer=footer,changed_original_bytes=sum(a!=b for a,b in zip(source,result)),
        other_approved_sprite_bytes_unchanged=True,visual_approval_pending=True)

if __name__=="__main__":
    import argparse,json
    from pathlib import Path
    ap=argparse.ArgumentParser()
    for name in ("input","official","output","report"):ap.add_argument("--"+name,type=Path,required=True)
    a=ap.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Refuse to overwrite any prior release")
    dest,report=apply(a.input.read_bytes(),a.official.read_bytes())
    a.output.write_bytes(dest)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
