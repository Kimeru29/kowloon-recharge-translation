from pathlib import Path
import json
import sys

root = Path.home() / 'repos/kowloon-recharge-translation/fixtures/DG00_00'
data = (root / 'original.MTX').read_bytes()
obj = json.loads((root / 'en.mtxdc.json').read_text())
start = int(sys.argv[1], 0)
end = int(sys.argv[2], 0)
for key, value in sorted(zip(obj['keys'], obj['values'])):
    if start <= key <= end:
        raw = data[key:key + 64]
        print(f'{key} {key:#x} {value!r}')
        print(f'  bytes {raw.hex(" ")}')
        print(f'  cp932 {raw.decode("cp932", "backslashreplace")!r}')
