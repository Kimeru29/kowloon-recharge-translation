from __future__ import annotations

from dataclasses import dataclass
import struct
from pathlib import Path


@dataclass(frozen=True)
class RofsFileUpdate:
    path: str
    expected_size: int
    expected_extent: int
    size: int
    extent: int


@dataclass(frozen=True)
class RofsRecord:
    filename_offset: int
    size_offset: int
    extent_offset: int
    filename: str
    size: int
    extent: int


def find_rofs_record(raw: bytes, path: str, expected_size: int, expected_extent: int) -> RofsRecord:
    """Find the unique SLPM ROFS record for an embedded CVM file.

    Kowloon's executable stores fixed records whose filename begins 14 bytes
    after the little-endian size field and 6 bytes after the little-endian
    sector extent field.  Matching both pristine size and extent makes the
    lookup fail closed even when a basename occurs elsewhere in the ELF.
    """

    filename = Path(path).name
    needle = filename.encode("ascii") + b"\x00"
    matches: list[RofsRecord] = []
    cursor = 0
    while True:
        found = raw.find(needle, cursor)
        if found < 0:
            break
        cursor = found + 1
        if found < 14:
            continue
        size = struct.unpack_from("<I", raw, found - 14)[0]
        extent = struct.unpack_from("<I", raw, found - 6)[0]
        if size == expected_size and extent == expected_extent:
            matches.append(
                RofsRecord(
                    filename_offset=found,
                    size_offset=found - 14,
                    extent_offset=found - 6,
                    filename=filename,
                    size=size,
                    extent=extent,
                )
            )

    if len(matches) != 1:
        raise ValueError(
            f"Expected exactly one ROFS record for {path} "
            f"(size={expected_size}, extent={expected_extent}), found {len(matches)}"
        )
    return matches[0]


def patch_rofs_records(raw: bytes, updates: tuple[RofsFileUpdate, ...]) -> tuple[bytes, tuple[RofsRecord, ...]]:
    result = bytearray(raw)
    patched: list[RofsRecord] = []
    used_offsets: set[int] = set()

    # Match against the pristine/base bytes before mutating so updates cannot
    # influence later record discovery.
    for update in updates:
        record = find_rofs_record(raw, update.path, update.expected_size, update.expected_extent)
        if record.filename_offset in used_offsets:
            raise ValueError(f"ROFS record reused by multiple updates: {update.path}")
        used_offsets.add(record.filename_offset)
        if update.size < 0 or update.extent < 0:
            raise ValueError(f"Invalid ROFS output metadata for {update.path}")
        struct.pack_into("<I", result, record.size_offset, update.size)
        struct.pack_into("<I", result, record.extent_offset, update.extent)
        patched.append(record)

    return bytes(result), tuple(patched)
