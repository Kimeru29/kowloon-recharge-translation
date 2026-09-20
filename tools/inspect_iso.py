from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
import sys

SECTOR = 2048


@dataclass
class Record:
    path: str
    extent: int
    size: int
    flags: int
    record_offset: int

    @property
    def sectors(self) -> int:
        return (self.size + SECTOR - 1) // SECTOR


def records_in_directory(raw, extent: int, size: int, parent: str):
    pos = extent * SECTOR
    end = pos + size
    while pos < end:
        length = raw[pos]
        if length == 0:
            pos = ((pos // SECTOR) + 1) * SECTOR
            continue
        rec = raw[pos:pos+length]
        file_extent = struct.unpack_from('<I', rec, 2)[0]
        file_size = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        name_len = rec[32]
        name_raw = bytes(rec[33:33+name_len])
        if name_raw == b'\x00':
            name = '.'
        elif name_raw == b'\x01':
            name = '..'
        else:
            name = name_raw.decode('ascii', 'replace').split(';', 1)[0]
        path = f'{parent}/{name}' if parent else name
        yield Record(path, file_extent, file_size, flags, pos)
        pos += length


def scan_iso(path: Path, target: str | None):
    with path.open('rb') as fh:
        import mmap
        raw = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
        pvd = 16 * SECTOR
        if raw[pvd] != 1 or raw[pvd+1:pvd+6] != b'CD001':
            raise ValueError('ISO9660 primary volume descriptor not found at sector 16')
        volume_sectors = struct.unpack_from('<I', raw, pvd + 80)[0]
        root_len = raw[pvd + 156]
        root = raw[pvd+156:pvd+156+root_len]
        root_extent = struct.unpack_from('<I', root, 2)[0]
        root_size = struct.unpack_from('<I', root, 10)[0]
        print(f'iso={path}')
        print(f'bytes={len(raw)} sectors_on_disk={len(raw)//SECTOR} pvd_volume_sectors={volume_sectors}')
        print(f'root_extent={root_extent} root_size={root_size}')

        stack = [('', root_extent, root_size)]
        seen_dirs = set()
        all_records: list[Record] = []
        while stack:
            parent, extent, size = stack.pop()
            key = (extent, size)
            if key in seen_dirs:
                continue
            seen_dirs.add(key)
            for rec in records_in_directory(raw, extent, size, parent):
                if rec.path.endswith('/.') or rec.path.endswith('/..') or rec.path in ('.', '..'):
                    continue
                all_records.append(rec)
                if rec.flags & 0x02:
                    stack.append((rec.path, rec.extent, rec.size))

        highest_end = 0
        for rec in all_records:
            highest_end = max(highest_end, rec.extent + rec.sectors)
        print(f'records={len(all_records)} dirs={len(seen_dirs)} highest_referenced_sector={highest_end}')
        print(f'trailing_free_sectors={volume_sectors-highest_end} trailing_free_bytes={(volume_sectors-highest_end)*SECTOR}')
        if target:
            normalized = target.strip('/').upper()
            matches = [rec for rec in all_records if rec.path.upper() == normalized]
            for rec in matches:
                print(f'TARGET path={rec.path} extent={rec.extent} size={rec.size} sectors={rec.sectors} record_offset={rec.record_offset}')
            if not matches:
                print(f'TARGET NOT FOUND: {target}')
        raw.close()


if __name__ == '__main__':
    scan_iso(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None)
