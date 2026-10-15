"""r67.15b: bounded PS4 storage-caption artwork for native 128px cells.

The official remaster GP004_18 caption 'Choose storage location' is 200+
native PS2 pixels wide and crosses into the adjacent Vest texture cell.
Restore the parchment under the original title with bounded dark-glyph
inpainting, then render 'Choose storage' within the original 128px label
cell, while preserving untouched Vest/Room sprites and other GP004 chunks.
Requires Pillow, numpy and opencv-python-headless during artifact generation.
"""
from __future__ import annotations
from hashlib import sha256
from tools.tmx import find_tmx_entry,_decode_indices,_decode_palette,replace_tmx_indexed

PREVIOUS_SHA="7cc70afb776cf135a796e072a40319c4074dadee410baca1e17c7f68f025f390"
TEX="GRP004/GP004_18.TMX"
LABEL="Choose storage"
FIRST_TILE_WIDTH=128
EDIT_RECT=(0,6,210,26)
INK_NATIVE=(3,2,2,254)

def sha(b):return sha256(b).hexdigest()

def apply(source:bytes):
    import numpy as np
    import cv2
    from PIL import Image,ImageDraw,ImageFont
    if sha(source)!=PREVIOUS_SHA:raise ValueError("Unknown exact PS4 translated group4 source")
    e=find_tmx_entry(source,TEX)
    if (e.width,e.height,e.image_psm,e.palette_entries)!=(256,128,0x13,256):
        raise ValueError("Native storage banner layout changed")
    pal=_decode_palette(source,e)
    if INK_NATIVE not in pal:raise ValueError("Native black caption ink missing")
    original=_decode_indices(source,e)
    palette=np.asarray(pal,dtype=np.int16)
    img=np.asarray([pal[i] for i in original],dtype=np.uint8).reshape(e.height,e.width,4)
    mark=np.zeros((e.height,e.width),dtype=np.uint8)
    for y in range(6,26):
        for x in range(2,210):
            if 125<=x<131:continue
            if int(max(img[y,x,:3]))<95 and img[y,x,3]>200:mark[y,x]=255
    mark=cv2.dilate(mark,np.ones((3,3),np.uint8),iterations=1)
    mark[:6,:]=0;mark[26:,:]=0;mark[:,210:]=0;mark[:,125:131]=0
    if not 1800<int(np.count_nonzero(mark))<2600:
        raise ValueError("Remaster header glyph-mask ownership changed")
    clean=cv2.inpaint(img[:,:,:3],mark,4,cv2.INPAINT_TELEA)
    display=Image.fromarray(np.dstack((clean,img[:,:,3])),"RGBA")
    # Use a locally available, deterministic fallback face. The imported
    # remaster artwork is authoritative; this is a PS2-only bounded repaint.
    font_path="/System/Library/Fonts/Supplemental/Arial.ttf"
    font=ImageFont.truetype(font_path,size=16)
    draw=ImageDraw.Draw(display)
    box=draw.textbbox((0,0),LABEL,font=font)
    width,height=box[2]-box[0],box[3]-box[1]
    if width>FIRST_TILE_WIDTH-12 or height>18:
        raise ValueError("Shortened storage label is still outside native texture tile")
    x=(FIRST_TILE_WIDTH-width)//2
    draw.text((x,8-box[1]),LABEL,font=font,fill=INK_NATIVE)
    out=np.asarray(display).copy()
    result=bytearray(original)
    opaque_indices=np.flatnonzero(palette[:,3]>225)
    allowed={(y*e.width+x) for y in range(EDIT_RECT[1],EDIT_RECT[3])
             for x in range(EDIT_RECT[0],EDIT_RECT[2])}
    for linear in sorted(allowed):
        y,x=divmod(linear,e.width)
        if np.array_equal(out[y,x],img[y,x]):continue
        rgb=out[y,x,:3].astype(np.int16)
        distances=((palette[opaque_indices,:3]-rgb)**2).sum(axis=1)
        result[linear]=int(opaque_indices[int(np.argmin(distances))])
    changes={i for i,(a,b) in enumerate(zip(original,result)) if a!=b}
    if not changes or changes-allowed:
        raise ValueError("Caption replaced unexpected approved pixels")
    changed=replace_tmx_indexed(source,TEX,pal,result)
    if find_tmx_entry(changed,TEX)!=e:raise ValueError("Original native texture layout changed")
    return changed,dict(status="BOUNDED_EN_TITLE_FIRST_NATIVE_CELL",
        previous_group4_sha256=PREVIOUS_SHA,
        new_group4_sha256=sha(changed),official_phrase="Choose storage location",
        native_compact_phrase=LABEL,rendered_width_px=width,
        native_tile_width=FIRST_TILE_WIDTH,changed_pixels=len(changes),
        changed_region=EDIT_RECT,protected_other_tiles=True,gameplay_approved=False)

if __name__=="__main__":
    import argparse,json
    from pathlib import Path
    p=argparse.ArgumentParser()
    for k in ("input","output","report"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Never overwrite prior artwork")
    dst,report=apply(a.input.read_bytes())
    a.output.write_bytes(dst)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
