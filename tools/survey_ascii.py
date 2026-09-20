from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

root = Path('/tmp/khc-ps2-assets/ADV')
mtx_files = list(root.rglob('*.MTX'))

runs: list[tuple[str, int, str]] = []
chars = Counter()
for path in mtx_files:
    data = path.read_bytes()
    for b in data:
        if 0x20 <= b <= 0x7e:
            chars[chr(b)] += 1
    for match in re.finditer(rb'[A-Za-z][A-Za-z0-9 .,!?:;\'"+\-/]{3,}', data):
        text = match.group().decode('ascii', 'replace')
        runs.append((str(path.relative_to(root)), match.start(), text))

print('files', len(mtx_files))
print('ASCII char frequency:', ''.join(f'{k}:{v} ' for k, v in chars.most_common()))
print('long ASCII-ish runs', len(runs))
for item in runs[:500]:
    print(f'{item[0]}:{item[1]} {item[2]!r}')
