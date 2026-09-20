from __future__ import annotations

from dataclasses import dataclass
import struct

SECTOR_SIZE = 2048


@dataclass(frozen=True)
class IsoRecord:
    path: str
    extent: int
    size: int
    flags: int
    record_offset: int

    @property
    def sectors(self) -> int:
        return (self.size + SECTOR_SIZE - 1) // SECTOR_SIZE

    @property
    def is_directory(self) -> bool:
        return bool(self.flags & 0x02)


def read_both_u32(buffer: bytes | bytearray | memoryview, offset: int) -> int:
    little = struct.unpack_from("<I", buffer, offset)[0]
    big = struct.unpack_from(">I", buffer, offset + 4)[0]
    if little != big:
        raise ValueError(
            f"ISO9660 endian copies disagree at {offset:#x}: LE={little:#x}, BE={big:#x}"
        )
    return little


def write_both_u32(buffer, offset: int, value: int) -> None:
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("ISO9660 u32 value is out of range")
    struct.pack_into("<I", buffer, offset, value)
    struct.pack_into(">I", buffer, offset + 4, value)


def patch_directory_record(
    buffer,
    record_offset: int,
    *,
    extent: int | None = None,
    size: int | None = None,
) -> None:
    if record_offset < 0 or record_offset + 18 > len(buffer):
        raise ValueError("ISO9660 directory record header lies outside the supplied buffer")
    record_length = buffer[record_offset]
    if record_length < 18:
        raise ValueError(f"Invalid ISO9660 directory record length {record_length}")
    if extent is not None:
        write_both_u32(buffer, record_offset + 2, extent)
    if size is not None:
        write_both_u32(buffer, record_offset + 10, size)


def _directory_records(buffer, base: int, extent: int, size: int, parent: str):
    pos = base + extent * SECTOR_SIZE
    end = pos + size
    while pos < end:
        length = buffer[pos]
        if length == 0:
            relative = pos - base
            pos = base + ((relative // SECTOR_SIZE) + 1) * SECTOR_SIZE
            continue
        rec = buffer[pos:pos + length]
        file_extent = read_both_u32(rec, 2)
        file_size = read_both_u32(rec, 10)
        flags = rec[25]
        name_len = rec[32]
        name_raw = bytes(rec[33:33 + name_len])
        if name_raw == b"\x00":
            name = "."
        elif name_raw == b"\x01":
            name = ".."
        else:
            name = name_raw.decode("ascii", "replace").split(";", 1)[0]
        path = f"{parent}/{name}" if parent else name
        yield IsoRecord(path, file_extent, file_size, flags, pos)
        pos += length


def index_iso(buffer, base: int = 0) -> tuple[int, tuple[IsoRecord, ...]]:
    pvd = base + 16 * SECTOR_SIZE
    if bytes(buffer[pvd + 1:pvd + 6]) != b"CD001" or buffer[pvd] != 1:
        raise ValueError(f"ISO9660 PVD not found at base {base:#x}")
    volume_sectors = read_both_u32(buffer, pvd + 80)
    root_offset = pvd + 156
    root_length = buffer[root_offset]
    root = buffer[root_offset:root_offset + root_length]
    root_extent = read_both_u32(root, 2)
    root_size = read_both_u32(root, 10)

    stack = [("", root_extent, root_size)]
    seen_dirs: set[tuple[int, int]] = set()
    records: list[IsoRecord] = []
    while stack:
        parent, extent, size = stack.pop()
        key = (extent, size)
        if key in seen_dirs:
            continue
        seen_dirs.add(key)
        for record in _directory_records(buffer, base, extent, size, parent):
            if record.path in (".", "..") or record.path.endswith("/.") or record.path.endswith("/.."):
                continue
            records.append(record)
            if record.is_directory:
                stack.append((record.path, record.extent, record.size))
    return volume_sectors, tuple(records)


def find_record(records: tuple[IsoRecord, ...], path: str) -> IsoRecord:
    normalized = path.strip("/").upper()
    matches = [record for record in records if record.path.upper() == normalized]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one ISO9660 record for {path!r}, found {len(matches)}")
    return matches[0]
