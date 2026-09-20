from __future__ import annotations

from pathlib import Path
import mmap
import struct
import sys

from tools.inspect_iso import SECTOR, records_in_directory

path = Path(sys.argv[1])
with path.open('rb') as fh:
    raw = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    pvd = 16 * SECTOR
    root_len = raw[pvd + 156]
    root = raw[pvd+156:pvd+156+root_len]
    root_extent = struct.unpack_from('<I', root, 2)[0]
    root_size = struct.unpack_from('<I', root, 10)[0]
    stack = [('', root_extent, root_size)]
    seen = set()
    items = []
    while stack:
        parent, extent, size = stack.pop()
        if (extent,size) in seen:
            continue
        seen.add((extent,size))
        for rec in records_in_directory(raw, extent, size, parent):
            if rec.path.endswith('/.') or rec.path.endswith('/..') or rec.path in ('.','..'):
                continue
            items.append(rec)
            if rec.flags & 0x02:
                stack.append((rec.path,rec.extent,rec.size))
    for rec in sorted(items, key=lambda r:(r.extent,r.path)):
        print(f'{rec.extent:8}..{rec.extent+rec.sectors-1:8} sectors={rec.sectors:7} size={rec.size:10} flags={rec.flags:02x} record={rec.record_offset:8} {rec.path}')
    raw.close()
