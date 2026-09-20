from pathlib import Path
import re

root = Path('/tmp/khc-ps2-assets/ADV')
results = []
pattern = re.compile(rb'(?<![\x20-\x7e])[A-Za-z][A-Za-z0-9 .,!?:;\'"+\-/]{2,}\x00')
for path in root.rglob('*.KSF'):
    raw = path.read_bytes()
    for match in pattern.finditer(raw):
        text = match.group()[:-1].decode('ascii', 'replace')
        results.append((str(path.relative_to(root)), match.start(), text))
print('ascii_nul_strings', len(results))
for item in results[:500]:
    print(f'{item[0]}:{item[1]} {item[2]!r}')
