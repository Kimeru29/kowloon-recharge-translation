from collections import Counter
from pathlib import Path
import struct

root = Path('/tmp/khc-ps2-assets/ADV')
counts = Counter()
examples = {}
for path in root.rglob('*.MTX'):
    raw = path.read_bytes()
    if len(raw) < 2:
        continue
    data_start = struct.unpack_from('<H', raw, 0)[0] * 4
    if not (0 < data_start <= len(raw)):
        continue
    i = data_start
    while i < len(raw):
        byte = raw[i]
        if (0x81 <= byte <= 0x9F) or (0xE0 <= byte <= 0xFC):
            i += 2
            continue
        if 0xA1 <= byte <= 0xDF:
            counts[byte] += 1
            examples.setdefault(byte, (str(path), i))
        i += 1
print('single-byte halfwidth count', sum(counts.values()), 'codes', len(counts))
for byte, count in sorted(counts.items()):
    char = bytes([byte]).decode('cp932')
    path_text, offset = examples[byte]
    raw = Path(path_text).read_bytes()
    start = max(0, offset - 24)
    end = min(len(raw), offset + 48)
    context = raw[start:end].decode('cp932', 'backslashreplace')
    print(f'{byte:02X} {char!r} count={count} example={path_text}:{offset} context={context!r}')
