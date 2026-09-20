from __future__ import annotations

from pathlib import Path
import mmap
import struct
import sys

from tools.inspect_iso import SECTOR, records_in_directory

path = Path(sys.argv[1])
minimum = int(sys.argv[2]) if len(sys.argv) > 2 else 1
with path.open('rb') as fh:
    raw = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
    pvd = 16 * SECTOR
    volume_sectors = struct.unpack_from('<I', raw, pvd + 80)[0]
    root_len = raw[pvd + 156]
    root = raw[pvd+156:pvd+156+root_len]
    root_extent = struct.unpack_from('<I', root, 2)[0]
    root_size = struct.unpack_from('<I', root, 10)[0]

    intervals: list[tuple[int, int, str]] = [(0, 32, '<system-reserved>')]
    stack = [('', root_extent, root_size)]
    seen_dirs = set()
    while stack:
        parent, extent, size = stack.pop()
        key = (extent, size)
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        sectors = (size + SECTOR - 1) // SECTOR
        intervals.append((extent, extent + sectors, parent or '<root>'))
        for rec in records_in_directory(raw, extent, size, parent):
            if rec.path.endswith('/.') or rec.path.endswith('/..') or rec.path in ('.', '..'):
                continue
            sectors = rec.sectors
            intervals.append((rec.extent, rec.extent + sectors, rec.path))
            if rec.flags & 0x02:
                stack.append((rec.path, rec.extent, rec.size))

    intervals.sort()
    merged: list[tuple[int, int]] = []
    for start, end, _ in intervals:
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
        else:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))

    gaps = []
    cursor = 0
    for start, end in merged:
        if start > cursor:
            gaps.append((cursor, start, start - cursor))
        cursor = max(cursor, end)
    if cursor < volume_sectors:
        gaps.append((cursor, volume_sectors, volume_sectors - cursor))

    large = [gap for gap in gaps if gap[2] >= minimum]
    print(f'volume_sectors={volume_sectors} occupied_merged_ranges={len(merged)} gaps={len(gaps)} gaps_ge_{minimum}={len(large)}')
    for start, end, count in sorted(large, key=lambda x: (-x[2], x[0]))[:50]:
        print(f'gap {start}..{end-1} sectors={count} bytes={count*SECTOR}')
    raw.close()
