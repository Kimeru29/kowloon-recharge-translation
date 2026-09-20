from __future__ import annotations

from pathlib import Path
import struct
import sys

MAGIC = 0x0131A366


def parse_font(path: Path):
    raw = path.read_bytes()
    magic, count, glyph_size, palette_offset, data_offset = struct.unpack_from('<5I', raw, 0)
    if magic != MAGIC:
        raise ValueError(f'bad magic {magic:#x}')
    if data_offset + count * glyph_size != len(raw):
        raise ValueError('font size does not match header')
    if glyph_size == 312:
        width, height = 24, 26
    elif glyph_size == 144:
        width, height = 16, 18
    else:
        raise ValueError(f'unknown glyph size {glyph_size}')
    palette = [tuple(raw[palette_offset+i:palette_offset+i+4]) for i in range(0, data_offset-palette_offset, 4)]
    return raw, count, glyph_size, data_offset, width, height, palette


def glyph_pixels(record: bytes, width: int, height: int) -> list[int]:
    out: list[int] = []
    for byte in record:
        out.append(byte & 0x0F)
        out.append(byte >> 4)
    if len(out) != width * height:
        raise ValueError('bad glyph geometry')
    return out


def write_pgm(path: Path, width: int, height: int, pixels: list[int]) -> None:
    # Invert the palette index so ink is dark on a light inspection background.
    maxv = 15
    payload = bytes((maxv - p) * 17 for p in pixels)
    path.write_bytes(f'P5\n{width} {height}\n255\n'.encode('ascii') + payload)


def main() -> None:
    font = Path(sys.argv[1])
    out = Path(sys.argv[2])
    start = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0
    end = int(sys.argv[4], 0) if len(sys.argv) > 4 else 256
    raw, count, glyph_size, data_offset, gw, gh, palette = parse_font(font)
    end = min(end, count)
    cols = 16
    rows = (end - start + cols - 1) // cols
    cell_w, cell_h = gw + 2, gh + 2
    canvas_w, canvas_h = cols * cell_w, rows * cell_h
    canvas = [0] * (canvas_w * canvas_h)
    for index in range(start, end):
        rec = raw[data_offset + index * glyph_size:data_offset + (index + 1) * glyph_size]
        pix = glyph_pixels(rec, gw, gh)
        slot = index - start
        ox, oy = (slot % cols) * cell_w + 1, (slot // cols) * cell_h + 1
        for y in range(gh):
            base = (oy + y) * canvas_w + ox
            canvas[base:base+gw] = pix[y*gw:(y+1)*gw]
    write_pgm(out, canvas_w, canvas_h, canvas)
    print(f'magic={MAGIC:#x} glyphs={count} glyph_size={glyph_size} geometry={gw}x{gh} palette_entries={len(palette)}')
    print(f'wrote {out} indices {start}..{end-1}')


if __name__ == '__main__':
    main()
