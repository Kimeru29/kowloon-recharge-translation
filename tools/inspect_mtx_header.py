from __future__ import annotations

from pathlib import Path
import struct
import sys

for name in sys.argv[1:]:
    path = Path(name)
    data = path.read_bytes()
    values: list[int] = []
    offset = 0
    while offset + 2 <= len(data):
        value = struct.unpack_from("<H", data, offset)[0]
        offset += 2
        if value == 0:
            break
        values.append(value)
    print(path)
    print(f"  entries={len(values)} data_start={offset} max={max(values) if values else None} min={min(values) if values else None}")
    print(f"  first={values[:12]}")
    print(f"  last={values[-12:]}")
