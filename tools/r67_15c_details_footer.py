"""r67.15c official 'Details' command in original native item menu footer.

PS4 group4 English GP004_05 explicitly labels the corresponding item
command 'Details'. The old 15a fallback 'INFO' is not official. Replace only
the bounded first footer sprite cell (0,0,48,32) from the approved native
group4 atlas, preserving all other labels and character background/palette.
"""
from __future__ import annotations
from hashlib import sha256
from tools.tmx import find_tmx_entry,_decode_indices,_decode_palette,replace_tmx_indexed
from tools.r67_15a_items_art import FONT,FOOTER_NATIVE_TRANSPARENT,FOOTER_NATIVE_GOLD

BASE_SHA="0214ab871549f3b4a8d07e1ce36f7bcb1f9154968943211a08dddf76d5268efb"
TEX="GRP004/GP004_19.TMX"
RECT=(0,0,48,32)
OFFICIAL_EN="DETAILS"

def sha(data):return sha256(data).hexdigest()

def apply(source:bytes)->tuple[bytes,dict]:
    if sha(source)!=BASE_SHA:raise ValueError("Non-approved group4 native item footer")
    entry=find_tmx_entry(source,TEX)
    pal=_decode_palette(source,entry)
    if (pal[FOOTER_NATIVE_TRANSPARENT][3]!=0 or
        pal[FOOTER_NATIVE_GOLD]!=(255,156,0,255)):
        raise ValueError("Native menu footer palette changed")
    a=_decode_indices(source,entry)
    b=bytearray(a)
    x0,y0,x1,y1=RECT
    tw=len(OFFICIAL_EN)*6-1
    if tw>(x1-x0)-6 or set(OFFICIAL_EN)-set(FONT):
        raise ValueError("The official Details caption exceeds native button bounds")
    for y in range(y0,y1):
        for x in range(x0,x1):
            b[y*entry.width+x]=FOOTER_NATIVE_TRANSPARENT
    xbase=(x0+x1-tw)//2
    ybase=(y0+y1-14)//2
    for i,ch in enumerate(OFFICIAL_EN):
        for row,bits in enumerate(FONT[ch]):
            for col,bit in enumerate(bits):
                if bit=="1":
                    for dy in (0,1):
                        x=xbase+i*6+col;y=ybase+row*2+dy
                        if not (x0<x<x1 and y0<y<y1):
                            raise ValueError("Details glyph overflows first button")
                        b[y*entry.width+x]=FOOTER_NATIVE_GOLD
    diff={i for i,(x,y) in enumerate(zip(a,b)) if x!=y}
    if not diff or any(not (x0<=i%entry.width<x1 and y0<=i//entry.width<y1)
                       for i in diff):
        raise ValueError("Details patch modifies neighboring command caption")
    out=replace_tmx_indexed(source,TEX,pal,b)
    if find_tmx_entry(out,TEX)!=entry:
        raise ValueError("Footer changes moved native texture")
    return out,dict(prior_sha256=BASE_SHA,result_sha256=sha(out),
                    official_caption="Details",source="PS4 GP004_05 EN text",
                    replaced_fallback="INFO",native_tile=RECT,
                    altered_pixels=len(diff),other_button_slots_intact=True)
