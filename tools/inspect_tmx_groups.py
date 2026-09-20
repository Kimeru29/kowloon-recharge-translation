from pathlib import Path
import struct

root = Path('/Users/juan.pena/repos/kowloon-recharge-translation/fixtures/early-ui')
for path in sorted(root.glob('B_GP*.BIN'))[:15]:
    data = path.read_bytes()
    rows = []
    cursor = 0
    while True:
        marker = data.find(b'.TMX\x00', cursor)
        if marker < 0:
            break
        name_start = marker
        while name_start > 0 and data[name_start - 1] != 0:
            name_start -= 1
        name = data[name_start:marker + 4].decode('ascii', 'replace')
        tmx = data.find(b'TMX0', marker, marker + 0x400)
        if tmx >= 8:
            chunk_start = tmx - 8
            ident, chunk_size = struct.unpack_from('<II', data, chunk_start)
            palette_count = data[tmx + 8]
            palette_psm = data[tmx + 9]
            width, height = struct.unpack_from('<HH', data, tmx + 10)
            image_psm = data[tmx + 14]
            mip_levels = data[tmx + 15]
            rows.append((name, name_start, chunk_start, ident, chunk_size, palette_count, palette_psm, width, height, image_psm, mip_levels))
        cursor = marker + 1

    print(f'{path.name} entries={len(rows)}')
    for row in rows:
        name, entry_start, chunk_start, ident, chunk_size, palette_count, palette_psm, width, height, image_psm, mip_levels = row
        print(f'  {name} entry={entry_start:#x} chunk={chunk_start:#x} id={ident} size={chunk_size} pal={palette_count} ppsm={palette_psm:#x} {width}x{height} ipsm={image_psm:#x} mip={mip_levels}')
