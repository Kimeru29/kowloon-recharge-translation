"""Independent exact-write auditing for cumulative script and native deltas."""
from __future__ import annotations

import hashlib
import mmap
from pathlib import Path
import struct

from tools.elf_rofs import find_rofs_record
from tools.iso9660_patch import find_record, index_iso

SECTOR = 2048
CVM_HEADER = 0x1800
N_ELF_SHA256 = '0d5ace47c618c8c9af92f76aecad72dd0da2c4f7588410d2f9d866458a8f38bb'
HOOKS = (0x22c388, 0x22c394, 0x2506bc, 0x2506e4, 0x251594,
         0x251668, 0x2516a8, 0x2516f8, 0x251a24, 0x251be0)


def _sha(data) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_native_delta(source: bytes, candidate: bytes) -> dict:
    """Reject changes outside the explicitly traced call owners and append area.

    Component execution tests establish the appended program's semantics. This
    separate check protects all existing code/data and the translation reserve.
    """
    if _sha(source) != N_ELF_SHA256:
        raise ValueError('Native source is not the pinned n executable')
    if len(candidate) < len(source):
        raise ValueError('Native executable shrank')
    segment_offset, segment_va = struct.unpack_from('<II', source, 0x58)
    reserve = struct.unpack_from('<I', source, 0x68)[0]
    if struct.unpack_from('<I', candidate, 0x64)[0] != len(candidate) - segment_offset:
        raise ValueError('Native load size does not match exact appended bytes')
    if (struct.unpack_from('<I', candidate, 0x68)[0] != reserve
            or len(candidate) - segment_offset > reserve):
        raise ValueError('Native program exceeds or changes the existing heap reserve')
    allowed = set(range(0x64, 0x68))
    changed_hooks = []
    append_va = segment_va + len(source) - segment_offset
    end_va = segment_va + len(candidate) - segment_offset
    for address in HOOKS:
        offset = address - 0xfff80
        allowed.update(range(offset, offset + 4))
        before = struct.unpack_from('<I', source, offset)[0]
        after = struct.unpack_from('<I', candidate, offset)[0]
        if before == after:
            continue
        if before >> 26 != 3 or after >> 26 != 3:
            raise ValueError(f'Owned call is not a JAL at {address:#x}')
        target = ((address + 4) & 0xf0000000) | ((after & 0x03ffffff) << 2)
        if not append_va <= target < end_va:
            raise ValueError(f'Owned call does not target the native append at {address:#x}')
        changed_hooks.append(address)
    for offset, (before, after) in enumerate(zip(source, candidate)):
        if before != after and offset not in allowed:
            raise ValueError(f'Unowned existing native byte changed at {offset:#x}')
    return {'source_elf_sha256': _sha(source), 'native_elf_sha256': _sha(candidate),
            'changed_hook_addresses': changed_hooks, 'appended_bytes': len(candidate) - len(source),
            'append_va': append_va, 'append_end_va': end_va,
            'original_translation_reserve': reserve,
            'all_other_existing_native_bytes_preserved': True}


def _both(value: int) -> bytes:
    return struct.pack('<I', value) + struct.pack('>I', value)


def expected_writes(image, overlay, native_elf: bytes | None = None):
    """Derive payloads, directory fields and executable ROFS writes from source."""
    volume, outer = index_iso(image)
    cvm = find_record(outer, 'DATA.CVM')
    exe = find_record(outer, 'SLPM_665.11')
    nested = cvm.extent * SECTOR + CVM_HEADER
    inner_volume, records = index_iso(image, nested)
    by_path = {r.path: r for r in records}
    source_elf = bytes(image[exe.extent * SECTOR:exe.extent * SECTOR + exe.size])
    output_elf = bytearray(source_elf if native_elf is None else native_elf)
    if len(output_elf) < len(source_elf):
        raise ValueError('Replacement ELF is smaller than installed source')
    cursor = inner_volume
    payloads = []
    seen = set()
    for entry in sorted(overlay.entries, key=lambda e: e.path):
        if entry.embedded_path in seen:
            raise ValueError('Duplicate overlay destination')
        seen.add(entry.embedded_path)
        record = by_path[entry.embedded_path]
        raw = entry.source_path.read_bytes()
        if _sha(raw) != entry.sha256 or len(raw) != entry.size:
            raise ValueError('Overlay source changed after fingerprinting')
        relocated = (len(raw) + SECTOR - 1) // SECTOR > record.sectors
        extent = cursor if relocated else record.extent
        if relocated:
            cursor += (len(raw) + SECTOR - 1) // SECTOR
        payloads.append((entry, record, extent, raw, relocated))
        rofs = find_rofs_record(source_elf, record.path, record.size, record.extent)
        # Code/data producers must retain original runtime resource identities.
        for offset, old_value in ((rofs.size_offset, record.size), (rofs.extent_offset, record.extent)):
            if struct.unpack_from('<I', output_elf, offset)[0] != old_value:
                raise ValueError('Native producer changed original resource metadata')
        struct.pack_into('<I', output_elf, rofs.size_offset, len(raw))
        struct.pack_into('<I', output_elf, rofs.extent_offset, extent)
    growth = cursor - inner_volume
    old_end = cvm.extent + cvm.sectors
    highest = max(r.extent + r.sectors for r in outer)
    if highest + growth > volume:
        raise ValueError('Insufficient outer slack for DATA.CVM growth')
    writes = []
    if growth:
        writes.append(((old_end + growth) * SECTOR,
                       bytes(image[old_end * SECTOR:highest * SECTOR]), 'exact_outer_tail_shift'))
        for record in outer:
            if record.extent >= old_end:
                if record.is_directory:
                    raise ValueError('Unsupported outer directory relocation')
                writes.append((record.record_offset + 2, _both(record.extent + growth), 'outer_extent'))
        writes.append((cvm.record_offset + 10, _both(cvm.size + growth * SECTOR), 'cvm_size'))
        for field in (0x20, 0x808, 0x834):
            offset = cvm.extent * SECTOR + field
            old = struct.unpack_from('>I', image, offset)[0]
            writes.append((offset, struct.pack('>I', old + growth * SECTOR), 'cvm_header_size'))
        writes.append((nested + 16 * SECTOR + 80, _both(cursor), 'inner_volume_size'))
    for entry, record, extent, raw, relocated in payloads:
        payload = raw + b'\0' * ((-len(raw)) % SECTOR) if relocated else raw
        writes.append((nested + extent * SECTOR, payload, entry.embedded_path))
        if relocated:
            writes.append((record.record_offset + 2, _both(extent), 'inner_extent'))
        writes.append((record.record_offset + 10, _both(len(raw)), 'inner_file_size'))
    exe_sectors = (len(output_elf) + SECTOR - 1) // SECTOR
    shifted = exe.extent + (growth if exe.extent >= old_end else 0)
    last_file = (exe.extent + exe.sectors == highest
                 and all(r is exe or r.extent + r.sectors <= exe.extent for r in outer))
    extended = exe_sectors > exe.sectors and last_file and shifted + exe_sectors <= volume
    relocated_elf = exe_sectors > exe.sectors and not extended
    exe_extent = highest + growth if relocated_elf else shifted
    if exe_extent + exe_sectors > volume:
        raise ValueError('Insufficient outer slack for executable')
    payload = bytes(output_elf) + b'\0' * ((-len(output_elf)) % SECTOR)
    writes.append((exe_extent * SECTOR, payload, 'exact_native_elf_with_derived_rofs'))
    if exe_extent != exe.extent:
        writes.append((exe.record_offset + 2, _both(exe_extent), 'executable_extent'))
    writes.append((exe.record_offset + 10, _both(len(output_elf)), 'executable_size'))
    if any(start < 0 or start + len(data) > len(image) for start, data, _ in writes):
        raise ValueError('Expected write crosses disc boundary')
    return writes, {'appended_cvm_sectors': growth, 'resource_files': len(payloads),
                    'elf_output_extent': exe_extent, 'elf_relocated': relocated_elf,
                    'elf_extended_in_place': extended, 'installed_elf_sha256': _sha(output_elf),
                    'owned_writes': [{'offset': p, 'size': len(b), 'owner': owner, 'sha256': _sha(b)}
                                     for p, b, owner in writes]}


def audit_candidate(source: Path, candidate: Path, overlay, native_elf: bytes | None = None) -> dict:
    if source.stat().st_size != candidate.stat().st_size:
        raise ValueError('Candidate disc size changed')
    with source.open('rb') as a, candidate.open('rb') as b, \
            mmap.mmap(a.fileno(), 0, access=mmap.ACCESS_READ) as old, \
            mmap.mmap(b.fileno(), 0, access=mmap.ACCESS_READ) as new:
        writes, report = expected_writes(old, overlay, native_elf)
        digest = hashlib.sha256()
        changed = 0
        for start in range(0, len(old), 4 * 1024 * 1024):
            end = min(len(old), start + 4 * 1024 * 1024)
            original = old[start:end]
            expected = bytearray(original)
            for offset, payload, _ in writes:
                lower, upper = max(start, offset), min(end, offset + len(payload))
                if lower < upper:
                    expected[lower - start:upper - start] = payload[lower - offset:upper - offset]
            actual = new[start:end]
            if actual != expected:
                first = next(i for i, (x, y) in enumerate(zip(actual, expected)) if x != y)
                raise ValueError(f'Unexpected candidate byte at {start + first:#x}')
            if actual != original:
                changed += sum(x != y for x, y in zip(actual, original))
            digest.update(expected)
    return {**report, 'complete_disc_bytes_compared': source.stat().st_size,
            'changed_bytes': changed, 'unexplained_bytes': 0,
            'expected_and_actual_iso_sha256': digest.hexdigest()}
