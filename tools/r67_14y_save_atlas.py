"""Bounded English repaint of native group-18 load/save/back captions.

Only three indexed rectangles change. Bar, palette, Circle/Cross icons,
sprite rectangles, resource layout and H.A.N.T. remain byte-identical.
PS4 text supplies terminology; this is not remaster-derived artwork.
"""
from hashlib import sha256
from tools.hant_graphics import _FONT_5X7
from tools.tmx import find_tmx_entry, _decode_indices, _decode_palette, replace_tmx_indexed

SOURCE_SHA = '707cc4280282524bd87971cede51d1e7c1604144074df8bba424b7e5177db9f2'
TMX = 'GRP018/GP018_03.TMX'
RECTS = ((0, 40, 48, 64), (48, 40, 96, 64), (96, 40, 128, 64))
FONT = dict(_FONT_5X7, **{
    'B': ('11110','10001','10001','11110','10001','10001','11110'),
    'K': ('10001','10010','10100','11000','10100','10010','10001'),
    'V': ('10001','10001','10001','10001','10001','01010','00100'),
})


def draw(indices, width, height, rect, text, ink, background):
    """Deterministic 5x7 glyphs expanded to 7x14, within the native tile."""
    left, top, right, bottom = rect
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise ValueError('caption rectangle outside atlas')
    tw, th = len(text) * 8 - 1, 14
    if not text or tw > right-left or th > bottom-top:
        raise ValueError('caption does not fit native sprite tile')
    if set(text) - FONT.keys():
        raise ValueError('unsupported caption glyph')
    for y in range(top, bottom):
        for x in range(left, right):
            indices[y*width+x] = background
    ox, oy = left+(right-left-tw)//2, top+(bottom-top-th)//2
    for n, char in enumerate(text):
        for y in range(th):
            for x in range(7):
                if FONT[char][y//2][x*5//7] == '1':
                    indices[(oy+y)*width+ox+n*8+x] = ink


def apply(source: bytes) -> tuple[bytes, dict]:
    if sha256(source).hexdigest() != SOURCE_SHA:
        raise ValueError('save atlas preimage drift')
    e = find_tmx_entry(source, TMX)
    if (e.width, e.height) != (512, 64):
        raise ValueError('native atlas dimensions changed')
    palette = _decode_palette(source, e)
    # Existing opaque pale-gold foreground and transparent white background.
    if palette[168] != (250,233,155,255) or palette[188][3] != 0:
        raise ValueError('native caption palette drift')
    original = _decode_indices(source, e)
    indices = bytearray(original)
    captions = ('LOAD', 'SAVE', 'BACK')
    for rect, text in zip(RECTS, captions, strict=True):
        draw(indices, e.width, e.height, rect, text, 168, 188)
    out = replace_tmx_indexed(source, TMX, palette, indices)
    if len(out) != len(source) or find_tmx_entry(out, TMX) != e:
        raise ValueError('native resource layout changed')
    changed = [i for i,(a,b) in enumerate(zip(source,out)) if a != b]
    if any(not e.pixel_offset <= i < e.pixel_offset+32768 for i in changed):
        raise ValueError('non-caption resource bytes changed')
    return out, dict(source_sha256=SOURCE_SHA, candidate_sha256=sha256(out).hexdigest(),
        captions=list(captions), rectangles=RECTS, changed_offsets=changed,
        source='PS4 English Save/Load; semantic Back for Return',
        native_owner='0x178008; group 18 resources 6,7,8; texture 3',
        glyph_style='deterministic local bitmap, not PS4 artwork',
        gameplay_verified=False)
