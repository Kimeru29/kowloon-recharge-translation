from __future__ import annotations

from pathlib import Path
import sys

ROOTS = [
    Path('/tmp/khc-ps2-data'),
    Path('/Users/juan.pena/repos/kowloon-recharge-translation/fixtures/elf/SLPM_665.11'),
]

queries = sys.argv[1:] or ['Ｈ．Ａ．Ｎ．Ｔ', 'アイテム', 'メール', 'システム', 'セーブ', 'ロード', 'マップ']
for text in queries:
    needle = text.encode('cp932')
    hits: list[tuple[Path, int]] = []
    for root in ROOTS:
        paths = [root] if root.is_file() else root.rglob('*')
        for path in paths:
            if not path.is_file():
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            start = 0
            while True:
                pos = data.find(needle, start)
                if pos < 0:
                    break
                hits.append((path, pos))
                start = pos + 1
    print(f'\n{text!r} {needle.hex()} hits={len(hits)}')
    for path, pos in hits[:200]:
        print(f'{path}:{pos:#x}')
