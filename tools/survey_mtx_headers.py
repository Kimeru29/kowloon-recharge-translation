from __future__ import annotations

from collections import Counter
from pathlib import Path
import struct

roots = [Path('/tmp/khc-ps2-assets/ADV/DG'), Path('/tmp/khc-ps2-assets/ADV/MS')]
rows = []
for root in roots:
    for path in sorted(root.glob('*.MTX')):
        data = path.read_bytes()
        words = []
        pos = 0
        while pos + 2 <= len(data):
            value = struct.unpack_from('<H', data, pos)[0]
            pos += 2
            if value == 0:
                break
            words.append(value)
            if len(words) > 4096:
                break
        if not words:
            continue
        quarter_start = pos // 4 if pos % 4 == 0 else None
        rows.append((path.name, len(data), len(words), pos, quarter_start, words[:8], words[-8:]))

print('files', len(rows))
patterns = Counter()
for name, size, n, pos, q, first, last in rows:
    w0 = first[0]
    w1 = first[1] if len(first) > 1 else None
    patterns[(w0 == (n + 1) // 2, w1 == q, w0 == q)] += 1
print('pattern counts (w0==(n+1)//2, w1==data_start/4, w0==data_start/4):')
for k, v in patterns.most_common():
    print(k, v)

print('\nexceptions / representative:')
shown = set()
for row in rows:
    name, size, n, pos, q, first, last = row
    key = (first[0] == (n + 1) // 2, (first[1] if len(first)>1 else None) == q, first[0] == q)
    if key not in shown or name == 'DG00_00.MTX':
        shown.add(key)
        print(name, 'size', size, 'words', n, 'header_bytes', pos, 'q', q, 'first', first, 'last', last, 'pattern', key)

print('\nDG/MS files where header size not 4-aligned:')
for row in rows:
    if row[3] % 4:
        print(row[0], row[3], row[5])
