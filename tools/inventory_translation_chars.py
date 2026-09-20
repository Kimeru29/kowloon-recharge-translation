from pathlib import Path
import json
from collections import Counter

path = Path.home() / 'repos/kowloon-recharge-translation/fixtures/DG00_00/en.mtxdc.json'
obj = json.loads(path.read_text())
c = Counter(''.join(obj['values']))
for ch, count in sorted(c.items(), key=lambda kv: ord(kv[0])):
    print(f'U+{ord(ch):04X} {ch!r} x{count}')
