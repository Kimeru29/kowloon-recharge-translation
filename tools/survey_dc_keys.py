from __future__ import annotations

from pathlib import Path
import json

root = Path.home() / 'repos/kowloon-recharge-translation/fixtures/DG00_00'
data = (root / 'original.MTX').read_bytes()
obj = json.loads((root / 'en.mtxdc.json').read_text())
pairs = sorted(zip(obj['keys'], obj['values']))

# Mark whether an offset is a CP932 character boundary when decoding from the
# beginning of the containing MTX data stream. ASCII bytes are boundaries too.
boundaries = {0}
i = 0
while i < len(data):
    boundaries.add(i)
    b = data[i]
    if (0x81 <= b <= 0x9F) or (0xE0 <= b <= 0xFC):
        i += 2
    else:
        i += 1
boundaries.add(len(data))

print('adjacent DC key runs:')
run = []
for item in pairs:
    if run and item[0] != run[-1][0] + 1:
        if len(run) > 1:
            print('RUN', [(k, k in boundaries, v) for k, v in run])
        run = []
    run.append(item)
if len(run) > 1:
    print('RUN', [(k, k in boundaries, v) for k, v in run])

print('\nkeys that are not CP932 boundaries:')
for key, value in pairs:
    if key not in boundaries:
        print(key, repr(value), 'lead/trail', data[key-1:key+2].hex(' '))
