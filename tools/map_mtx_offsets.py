from __future__ import annotations

from pathlib import Path
import struct
import sys


def read_offsets(data: bytes) -> tuple[list[int], int]:
    values: list[int] = []
    pos = 0
    while pos + 2 <= len(data):
        value = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        if value == 0:
            return values, pos
        values.append(value)
    raise ValueError("MTX header has no zero terminator")


for name in sys.argv[1:]:
    path = Path(name)
    data = path.read_bytes()
    values, data_start = read_offsets(data)
    print(f"== {path} ==")
    print(f"size={len(data)} table_entries={len(values)} data_start={data_start}")
    for index, value in enumerate(values):
        absolute = value * 4
        before = data[max(0, absolute - 12):absolute]
        after = data[absolute:min(len(data), absolute + 40)]
        context = (before + b"|" + after).decode("cp932", "backslashreplace")
        print(f"[{index:03}] word={value:5} abs={absolute:6} context={context!r}")
