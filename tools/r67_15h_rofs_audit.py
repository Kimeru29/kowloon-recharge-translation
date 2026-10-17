"""Read-only comparison of embedded ROFS lookups with installed DATA.CVM files."""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
from typing import Sequence

from tools.elf_rofs import find_rofs_record
from tools.iso9660_patch import IsoRecord, SECTOR_SIZE, find_record, index_iso

DATA_CVM_HEADER_SIZE = 0x1800
EXECUTABLE_NAME = 'SLPM_665.11'


def _files(records: Sequence[IsoRecord]) -> dict[str, IsoRecord]:
    files = [record for record in records if not record.is_directory]
    result = {record.path: record for record in files}
    if len(result) != len(files):
        raise ValueError('duplicate DATA.CVM file path')
    if not result:
        raise ValueError('empty DATA.CVM file inventory')
    return result


def audit_records(original_elf: bytes, candidate_elf: bytes,
                  original_records: Sequence[IsoRecord],
                  installed_records: Sequence[IsoRecord]) -> dict:
    original = _files(original_records)
    installed = _files(installed_records)
    if original.keys() != installed.keys():
        raise ValueError('DATA.CVM file inventory changed')
    used = set()
    relocated = 0
    for path, source in original.items():
        lookup = find_rofs_record(original_elf, path, source.size, source.extent)
        if lookup.filename_offset in used:
            raise ValueError(f'ROFS lookup reused by multiple files: {path}')
        used.add(lookup.filename_offset)
        name = lookup.filename.encode('ascii') + b'\0'
        if lookup.filename_offset + len(name) > len(candidate_elf):
            raise ValueError(f'ROFS lookup outside candidate ELF: {path}')
        if candidate_elf[lookup.filename_offset:lookup.filename_offset + len(name)] != name:
            raise ValueError(f'ROFS filename changed: {path}')
        size = struct.unpack_from('<I', candidate_elf, lookup.size_offset)[0]
        extent = struct.unpack_from('<I', candidate_elf, lookup.extent_offset)[0]
        target = installed[path]
        if (size, extent) != (target.size, target.extent):
            raise ValueError(f'ROFS metadata mismatch: {path}')
        relocated += (source.size, source.extent) != (target.size, target.extent)
    return {
        'audit_kind': 'finished_iso_embedded_rofs_against_installed_data_cvm',
        'read_only': True,
        'embedded_rofs_file_records': len(used),
        'relocated_or_resized_records': relocated,
        'mismatches': 0,
        'unmatched_records': 0,
        'original_elf_sha256': hashlib.sha256(original_elf).hexdigest(),
        'installed_elf_sha256': hashlib.sha256(candidate_elf).hexdigest(),
    }


def _inventory(image: mmap.mmap) -> tuple[bytes, tuple[IsoRecord, ...]]:
    _, outer = index_iso(image)
    executable = find_record(outer, EXECUTABLE_NAME)
    start = executable.extent * SECTOR_SIZE
    if start + executable.size > len(image):
        raise ValueError('executable extends outside ISO')
    cvm = find_record(outer, 'DATA.CVM')
    cvm_start = cvm.extent * SECTOR_SIZE
    cvm_end = cvm_start + cvm.size
    base = cvm_start + DATA_CVM_HEADER_SIZE
    if cvm_end > len(image) or base >= cvm_end:
        raise ValueError('DATA.CVM extends outside ISO')
    _, nested = index_iso(image, base)
    for record in nested:
        if base + record.extent * SECTOR_SIZE + record.size > cvm_end:
            raise ValueError(f'DATA.CVM record outside container: {record.path}')
    return bytes(image[start:start + executable.size]), nested


def audit(original_iso: Path, candidate_iso: Path) -> dict:
    with original_iso.open('rb') as source, candidate_iso.open('rb') as candidate:
        with mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as left, \
                mmap.mmap(candidate.fileno(), 0, access=mmap.ACCESS_READ) as right:
            original_elf, original_records = _inventory(left)
            installed_elf, installed_records = _inventory(right)
            return audit_records(original_elf, installed_elf, original_records, installed_records)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('original_iso', type=Path)
    parser.add_argument('candidate_iso', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.original_iso, args.candidate_iso), indent=2, sort_keys=True))
