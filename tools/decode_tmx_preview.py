from __future__ import annotations

from pathlib import Path
import re
import struct
import sys
import zlib

ROOT = Path('/Users/juan.pena/repos/kowloon-recharge-translation/fixtures/early-ui')
OUT = ROOT / 'decoded'
OUT.mkdir(exist_ok=True)

NAME_RE = re.compile(rb'GRP(\d{3})/GP\1_(\d{2})\.TMX\x00')


def png(path: Path, width: int, height: int, rgba: bytes) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', zlib.crc32(kind + payload) & 0xFFFFFFFF)

    rows = bytearray()
    stride = width * 4
    for y in range(height):
        rows.append(0)
        rows.extend(rgba[y * stride:(y + 1) * stride])
    data = b'\x89PNG\r\n\x1a\n'
    data += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    data += chunk(b'IDAT', zlib.compress(bytes(rows), 9))
    data += chunk(b'IEND', b'')
    path.write_bytes(data)


def alpha_ps2(a: int) -> int:
    # GS alpha is nominally 0..0x80. Values above 0x80 are commonly treated as fully opaque.
    return min(255, a * 2)


def unswizzle_clut_8(palette: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    # PSMT8 CLUT storage swaps the middle 8-color blocks in each 32-color group.
    out = palette[:]
    for base in range(0, 256, 32):
        out[base + 8:base + 16], out[base + 16:base + 24] = palette[base + 16:base + 24], palette[base + 8:base + 16]
    return out


def decode_entry(blob: bytes, match: re.Match[bytes]) -> tuple[str, int, int, bytes]:
    name = match.group(0)[:-1].decode('ascii')
    search_start = match.end()
    tmx = blob.find(b'TMX0', search_start, search_start + 0x1000)
    if tmx < 8:
        raise ValueError(f'{name}: TMX0 not found')
    base = tmx - 8
    ident, chunk_size = struct.unpack_from('<II', blob, base)
    if ident != 2:
        raise ValueError(f'{name}: unexpected chunk id {ident}')

    palette_count = blob[tmx + 8]
    palette_psm = blob[tmx + 9]
    width, height = struct.unpack_from('<HH', blob, tmx + 10)
    image_psm = blob[tmx + 14]
    if palette_count != 1 or palette_psm != 0:
        raise ValueError(f'{name}: unsupported palette count/PSM {palette_count}/{palette_psm:#x}')

    payload = base + 0x40
    if image_psm == 0x13:  # PSMT8
        palette_bytes = 256 * 4
        raw_palette = [tuple(blob[payload + i:payload + i + 4]) for i in range(0, palette_bytes, 4)]
        palette = unswizzle_clut_8([(r, g, b, alpha_ps2(a)) for r, g, b, a in raw_palette])
        indices = blob[payload + palette_bytes:payload + palette_bytes + width * height]
    elif image_psm == 0x14:  # PSMT4
        palette_bytes = 16 * 4
        raw_palette = [tuple(blob[payload + i:payload + i + 4]) for i in range(0, palette_bytes, 4)]
        palette = [(r, g, b, alpha_ps2(a)) for r, g, b, a in raw_palette]
        packed = blob[payload + palette_bytes:payload + palette_bytes + (width * height // 2)]
        indices = bytearray(width * height)
        for i, value in enumerate(packed):
            indices[2 * i] = value & 0x0F
            indices[2 * i + 1] = value >> 4
    else:
        raise ValueError(f'{name}: unsupported image PSM {image_psm:#x}')

    rgba = bytearray(width * height * 4)
    for i, index in enumerate(indices):
        rgba[i * 4:i * 4 + 4] = bytes(palette[index])

    expected = 0x40 + palette_bytes + len(indices) if image_psm == 0x13 else 0x40 + palette_bytes + width * height // 2
    if expected != chunk_size:
        raise ValueError(f'{name}: chunk size {chunk_size} != expected {expected}')
    return name, width, height, bytes(rgba)


containers = [ROOT / sys.argv[1]] if len(sys.argv) > 1 else sorted(ROOT.glob('B_GP*.BIN'))
for container in containers:
    data = container.read_bytes()
    for match in NAME_RE.finditer(data):
        try:
            name, width, height, rgba = decode_entry(data, match)
        except ValueError as exc:
            print(f'SKIP {container.name}: {exc}')
            continue
        target = OUT / (name.replace('/', '_').replace('.TMX', '') + '.png')
        png(target, width, height, rgba)
        print(f'{container.name}: {name} -> {target.name} ({width}x{height})')
