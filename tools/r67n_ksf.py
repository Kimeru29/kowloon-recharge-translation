"""Repair unterminated historical KSF choices from verified pristine payloads."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
from tempfile import TemporaryDirectory

from tools.accepted_overrides import apply_ksf_override_manifest
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.ksf_import import import_exact_ksf
from tools.r67_15g_route_audit import CHOICE_MANIFEST, CHOICE_MANIFEST_SHA256, DATA_CVM_HEADER_SIZE

PAYLOAD = 30
FALLBACK = 'deliberate technical-safety fallback'
NOOP = 'official U+3000 no-op'
# Sorted lines: relative path, pristine SHA, official map SHA, and installed m SHA.
INPUT_INVENTORY = '98d47250eae57a9ae34dc1da11f5cb9da1d196a530a3a90047e31c96bd9a089e'
# Independently measured eight-file reconstruction, sorted path and output SHA.
REPAIR_INVENTORY = 'ccb9eb4a16313f75341a609bb09f69ac2e340006f558dcf5d58679f7bc7e2d71'
NATIVE_RANGES = (
    (0x22D0B0, 0x22D174, '6cbeb5631329f1df5db142f08bb211040861cdb6445b95eea7878a5f32571a7b'),
    (0x22C2E8, 0x22C434, '6a273219416dd0f375560f7d781080486f6a7a2c29537910fe780af163c8f6b6'),
    (0x39F7F8, 0x39F81C, '67763b5cf7ddfd05241d67844cc0e353cb121aa5ac2b079c657c57c8753642f5'),
    (0x251604, 0x251700, '56d436fcdc2126b26e40a2b51cd42e330c79689891aab459d9effa64a5a5b489'),
    (0x18C730, 0x18C77C, '95719bb360e0a7312c98be3b0ec4d6a17223bf7a72c624c7241aa29af7cba62c'),
    (0x18C8C8, 0x18C8E8, 'db17c19cd220e8b0baa53988cb2b8544f50b343a10a9e6b30a593485fc918e33'),
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def verify_native_reader(elf: bytes) -> None:
    for start, end, expected in NATIVE_RANGES:
        offset = start - 0x100000 + 0x80
        if digest(elf[offset:offset + end - start]) != expected:
            raise ValueError(f'native KSF instructions differ at {start:#x}')


def native_slots(raw: bytes) -> dict[int, tuple[int, int, int]]:
    """Map payload offsets to record ordinal, record offset, choice ordinal."""
    if len(raw) < 2:
        raise ValueError('missing KSF record count')
    count = int.from_bytes(raw[:2], 'little')
    offset = 2
    slots = {}
    for index in range(count):
        start = offset
        offset += 0x26 + 5 * 30 + 19 * 112
        active = 0
        for choice in range(4):
            if offset >= len(raw):
                raise ValueError('incomplete KSF record')
            flag = raw[offset]
            offset += 1
            if flag == 1:
                if choice != active or offset + PAYLOAD > len(raw):
                    raise ValueError('unsupported sparse or incomplete KSF choice record')
                slots[offset] = (index, start, choice)
                offset += PAYLOAD
                active += 1
        # The native ordinal walker reads flags at FIXED +31*i addresses.
        # Compare its skip to the packed size wherever a next record is required.
        if index + 1 < count:
            probes = [start + 0x90c + i * 31 for i in range(4)]
            if probes[-1] >= len(raw) or sum(raw[i] == 1 for i in probes) != active:
                raise ValueError('native record stride disagrees with packed KSF')
    if offset != len(raw):
        raise ValueError('KSF record walk did not end at EOF')
    return slots


def audit_file(path: str, source: bytes, official: bytes, dc: dict, installed: bytes) -> tuple[bytes, list[dict]]:
    expected, fields = import_exact_ksf(source, official, dc)
    if path == 'DG/DG00_00.KSF':
        manifest = CHOICE_MANIFEST.read_bytes()
        if digest(manifest) != CHOICE_MANIFEST_SHA256:
            raise ValueError('approved DG00 choice manifest changed')
        expected = apply_ksf_override_manifest(expected, json.loads(manifest))
    slots = native_slots(source)
    if any(field.key not in slots for field in fields):
        raise ValueError('official map key is not a native label')
    if expected != installed:
        raise ValueError(f'installed KSF differs from historical replay: {path}')
    output = bytearray(installed)
    rows = []
    for field, verbatim in zip(fields, dc['values']):
        key = field.key
        end = key + PAYLOAD
        original_payload = source[key:end]
        if b'\0' not in original_payload:
            raise ValueError(f'unterminated pristine KSF choice at {path}:{key}')
        normalized = field.text.encode('cp932')
        official_bytes = verbatim.encode('cp932')
        before = installed[key:end]
        structural = []
        if field.status == 'fit' and b'\0' not in before:
            if len(normalized) < PAYLOAD or before != normalized[:PAYLOAD]:
                raise ValueError('unexpected malformed historical label')
            classification = FALLBACK
            output[key:end] = original_payload
            # Legacy fit overwrote the entire measured NUL run. Only restore
            # changed bytes after the actual 30-byte field inside that run.
            for offset in range(end, key + field.capacity):
                if source[offset] != installed[offset]:
                    structural.append(offset)
                    output[offset] = source[offset]
        elif field.status == 'fit' and before.split(b'\0')[0] == normalized:
            classification = 'inherited official choice (accepted spacing)'
        elif path == 'DG/DG00_00.KSF' and key in (9339, 11689):
            classification = 'inherited approved constrained choice'
        elif field.status == 'overflow' and before == original_payload:
            classification = 'original retained: English exceeds native field'
        elif (field.status == 'ambiguous' and verbatim and set(verbatim) == {'\u3000'}
              and original_payload.split(b'\0')[0] == official_bytes and before == original_payload):
            classification = NOOP
        else:
            raise ValueError(f'unrecognized KSF state at {path}:{key}')
        index, start, choice = slots[key]
        rows.append({'key': key, 'record_index': index, 'record_start': start, 'choice_index': choice,
                     'classification': classification, 'historical_status': field.status,
                     'raw_official_bytes': len(official_bytes), 'normalized_bytes': len(normalized),
                     'official_utf8_sha256': digest(verbatim.encode()), 'source_payload_sha256': digest(original_payload),
                     'before_payload_sha256': digest(before), 'after_payload_sha256': digest(output[key:end]),
                     'payload_range_half_open': [key, end], 'restored_structural_offsets': structural,
                     'installed_first_nul_distance': installed.index(b'\0', key) - key})
    # Independent global invariant: every byte outside a mapped payload equals
    # pristine, including hidden/disabled labels, flags and following headers.
    structure = output.copy()
    for row in rows:
        start, end = row['payload_range_half_open']
        if b'\0' not in output[start:end]:
            raise ValueError('unterminated output label')
        structure[start:end] = source[start:end]
    if structure != source or native_slots(output) != slots:
        raise ValueError(f'output changes native control data in {path}')
    return bytes(output), rows


def generate(ps2_adv: Path, ps4_adv: Path, installed_iso: Path, target: Path) -> dict:
    files, inventory, repairs = [], [], {}
    with installed_iso.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        outer = index_iso(image)[1]
        executable = find_record(outer, 'SLPM_665.11')
        start = executable.extent * SECTOR_SIZE
        verify_native_reader(image[start:start + executable.size])
        base = find_record(outer, 'DATA.CVM').extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        records = {r.path: r for r in index_iso(image, base)[1]}
        for source in sorted(ps2_adv.rglob('*.KSF')):
            rel = source.relative_to(ps2_adv)
            official = ps4_adv / rel
            dc_path = official.parent / 'EN' / (official.name + 'DC.json')
            if not dc_path.is_file() or not official.is_file():
                continue
            raw, comparison = source.read_bytes(), official.read_bytes()
            if raw != comparison:
                continue
            dc = dc_path.read_bytes()
            path = rel.as_posix()
            record = records['ADV/' + path]
            start = base + record.extent * SECTOR_SIZE
            installed = image[start:start + record.size]
            output, rows = audit_file(path, raw, comparison, json.loads(dc), installed)
            inventory.append(f'{path} {digest(raw)} {digest(dc)} {digest(installed)}\n')
            files.append({'path': path, 'ps2_sha256': digest(raw), 'ps4_sha256': digest(comparison),
                          'map_sha256': digest(dc), 'before_sha256': digest(installed), 'after_sha256': digest(output),
                          'size': len(output), 'changed_bytes': sum(a != b for a,b in zip(output,installed)), 'rows': rows})
            if installed != output:
                repairs[path] = output
    if digest(''.join(inventory).encode()) != INPUT_INVENTORY:
        raise ValueError('KSF source, map, or installed inventory differs from pinned inputs')
    outputs = ''.join(f'{path} {digest(data)}\n' for path, data in sorted(repairs.items()))
    if digest(outputs.encode()) != REPAIR_INVENTORY:
        raise ValueError('KSF safety repair differs from independently reconstructed output')
    all_rows = [r for f in files for r in f['rows']]
    report = {'input_inventory_sha256': INPUT_INVENTORY, 'repair_inventory_sha256': REPAIR_INVENTORY,
              'files_audited': len(files), 'files_changed': len(repairs), 'rows_audited': len(all_rows),
              'classifications': dict(Counter(r['classification'] for r in all_rows)),
              'exceeds_native_with_accepted_spacing': sum(r['normalized_bytes'] >= PAYLOAD for r in all_rows),
              'exceeds_native_with_raw_spacing': sum(r['raw_official_bytes'] >= PAYLOAD for r in all_rows),
              'files': files}
    bundle = {f'overlay/{path}': data for path, data in repairs.items()}
    bundle['report.json'] = (json.dumps(report, indent=2, sort_keys=True) + '\n').encode()
    if target.exists():
        actual = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()}
        if actual != bundle:
            raise ValueError('output destination already exists with different contents')
        return report
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as temp:
        stage = Path(temp) / 'bundle'
        for name, data in bundle.items():
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        stage.rename(target)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('ps2-adv', 'ps4-adv', 'installed-iso', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = generate(args.ps2_adv, args.ps4_adv, args.installed_iso, args.output)
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}, sort_keys=True))
