"""Compose script deltas on an approved cumulative image and audit exact writes.

The auditor derives byte writes from the source inventory and overlay, without
trusting the builder report, candidate metadata, or broad container allowances.
"""
from __future__ import annotations

import hashlib
import json
import mmap
import struct
from pathlib import Path

from tools.build_translation_iso import build_translation_iso
from tools.elf_rofs import find_rofs_record
from tools.iso9660_patch import find_record, index_iso
from tools.translation_overlay import OverlayManifest

SECTOR = 2048
CVM_HEADER = 0x1800


def _both(value):
    return struct.pack('<I', value) + struct.pack('>I', value)


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _derive_writes(image, overlay):
    _, outer = index_iso(image)
    cvm = find_record(outer, 'DATA.CVM')
    executable = find_record(outer, 'SLPM_665.11')
    base = cvm.extent * SECTOR + CVM_HEADER
    volume, records = index_iso(image, base)
    by_path = {record.path: record for record in records}
    source_elf = bytes(image[executable.extent * SECTOR:
                             executable.extent * SECTOR + executable.size])
    expected_elf = bytearray(source_elf)
    cursor = volume
    resources = []
    used = set()
    for entry in sorted(overlay.entries, key=lambda entry: entry.path):
        if entry.embedded_path in used:
            raise ValueError('Duplicate overlay destination')
        used.add(entry.embedded_path)
        record = by_path[entry.embedded_path]
        data = entry.source_path.read_bytes()
        if len(data) != entry.size or hashlib.sha256(data).hexdigest() != entry.sha256:
            raise ValueError('Overlay changed after manifest generation')
        sectors = (len(data) + SECTOR - 1) // SECTOR
        moved = sectors > record.sectors
        extent = cursor if moved else record.extent
        if moved:
            cursor += sectors
        resources.append((entry, record, extent, data, moved))
        lookup = find_rofs_record(source_elf, record.path, record.size, record.extent)
        struct.pack_into('<I', expected_elf, lookup.size_offset, len(data))
        struct.pack_into('<I', expected_elf, lookup.extent_offset, extent)
    growth = cursor - volume
    old_end = cvm.extent + cvm.sectors
    highest = max(record.extent + record.sectors for record in outer)
    outer_volume, _ = index_iso(image)
    if highest + growth > outer_volume:
        raise ValueError('Insufficient outer slack for cumulative translation')
    writes = []
    if growth:
        writes.append(((old_end + growth) * SECTOR,
                       bytes(image[old_end * SECTOR:highest * SECTOR]), 'outer_tail_shift'))
        for record in outer:
            if record.extent >= old_end:
                if record.is_directory:
                    raise ValueError('Unsupported outer directory relocation')
                writes.append((record.record_offset + 2, _both(record.extent + growth), 'outer_extent'))
        writes.append((cvm.record_offset + 10, _both(cvm.size + growth * SECTOR), 'cvm_directory_size'))
        # Independently update the three proven big-endian CVM size fields.
        for offset in (0x20, 0x808, 0x834):
            pos = cvm.extent * SECTOR + offset
            old_value = struct.unpack_from('>I', image, pos)[0]
            writes.append((pos, struct.pack('>I', old_value + growth * SECTOR), 'cvm_header_size'))
        writes.append((base + 16 * SECTOR + 80, _both(cursor), 'embedded_volume_size'))
    for entry, record, extent, data, moved in resources:
        payload = data + b'\0' * ((-len(data)) % SECTOR) if moved else data
        writes.append((base + extent * SECTOR, payload, entry.embedded_path))
        if moved:
            writes.append((record.record_offset + 2, _both(extent), 'embedded_extent'))
        writes.append((record.record_offset + 10, _both(len(data)), 'embedded_size'))
    elf_extent = executable.extent + (growth if executable.extent >= old_end else 0)
    elf_payload = bytes(expected_elf) + b'\0' * ((-len(expected_elf)) % SECTOR)
    writes.append((elf_extent * SECTOR, elf_payload, 'exact_approved_elf_with_rofs_metadata'))
    if elf_extent != executable.extent:
        writes.append((executable.record_offset + 2, _both(elf_extent), 'executable_extent'))
    writes.append((executable.record_offset + 10, _both(len(expected_elf)), 'executable_size'))
    if any(start < 0 or start + len(data) > len(image) for start, data, _ in writes):
        raise ValueError('Expected write extends beyond image')
    return writes, bytes(expected_elf), {
        'appended_sectors': growth, 'resource_files': len(resources),
        'elf_output_extent': elf_extent, 'installed_elf_sha256': hashlib.sha256(expected_elf).hexdigest(),
        'owned_writes': [{'offset': start, 'size': len(data), 'owner': owner,
                          'sha256': hashlib.sha256(data).hexdigest()} for start, data, owner in writes],
    }


def audit_candidate(source: Path, candidate: Path, overlay: OverlayManifest) -> dict:
    if source.stat().st_size != candidate.stat().st_size:
        raise ValueError('Candidate size differs from cumulative source')
    with source.open('rb') as left, candidate.open('rb') as right, \
            mmap.mmap(left.fileno(), 0, access=mmap.ACCESS_READ) as old, \
            mmap.mmap(right.fileno(), 0, access=mmap.ACCESS_READ) as new:
        writes, _, report = _derive_writes(old, overlay)
        changed = 0
        expected_digest = hashlib.sha256()
        # Small blocks bound working memory even for the full disc audit.
        for start in range(0, len(old), 4 * 1024 * 1024):
            end = min(len(old), start + 4 * 1024 * 1024)
            original = old[start:end]
            expected = bytearray(original)
            for offset, data, _ in writes:
                lower, upper = max(start, offset), min(end, offset + len(data))
                if lower < upper:
                    expected[lower - start:upper - start] = data[lower - offset:upper - offset]
            actual = new[start:end]
            if actual != expected:
                first = next(i for i, (a, b) in enumerate(zip(actual, expected)) if a != b)
                raise ValueError(f'Unexpected candidate byte at {start + first:#x}; exact expected writes differ')
            if actual != original:
                changed += sum(a != b for a, b in zip(actual, original))
            expected_digest.update(expected)
        return {**report, 'complete_disc_bytes_compared': len(old), 'changed_bytes': changed,
                'unexplained_bytes': 0, 'native_elf_preserved_except_rofs': True,
                'expected_and_actual_iso_sha256': expected_digest.hexdigest()}


def build(source: Path, destination: Path, overlay: OverlayManifest) -> dict:
    if destination.exists() or source.resolve() == destination.resolve():
        raise ValueError('Output collision: candidate already exists or aliases source')
    source_sha = sha_file(source)
    build_report = build_translation_iso(source, destination, overlay)
    audit = audit_candidate(source, destination, overlay)
    if sha_file(source) != source_sha:
        raise ValueError('Cumulative source changed during build')
    return {'source_iso_sha256': source_sha, 'build': build_report, 'whole_iso_audit': audit,
            'candidate_iso_sha256': audit['expected_and_actual_iso_sha256'],
            'runtime_verified': False, 'gameplay_approved': False}


def release(output_dir: Path, ps2_adv: Path, ps4_adv: Path,
            baseline_reports: Path, regenerated: Path) -> dict:
    """Install only newly proven files; retain every existing k resource."""
    from collections import Counter
    from dataclasses import asdict
    from tools import r67_15k_approved_lock as approved
    from tools import r67_15l_iso_release as wheel_release
    from tools import r67_15g_iso_release as preservation
    from tools import r67_15l_emotion_wheel as wheel
    from tools.localization import DcLocalization
    from tools.exact_import import import_exact_mtx
    from tools.structural_import import import_structural_mtx
    from tools.translation_overlay import collect_overlay
    from tools.r67_15h_rofs_audit import audit as rofs_audit
    from tools.startup_acceptance import verify_startup_candidate

    if output_dir.exists():
        raise ValueError('Output directory already exists; preserve prior artifacts')
    approved.verify_sources()
    approved.verify_historical_report()
    if sha_file(approved.ISO) != approved.manifest()['iso_sha256']:
        raise ValueError('Approved cumulative ISO identity changed')
    # Exact source/provenance and all four art variants are checked by the
    # existing wheel transform; its native proof runs on the approved k ELF.
    wheel_row, wheel_proof = wheel_release.prepare()
    output_dir.mkdir(parents=True)
    overlay_root = output_dir / 'overlay'
    provenance = []
    report_sources = []
    with approved.ISO.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        cvm = find_record(outer, 'DATA.CVM')
        base = cvm.extent * SECTOR + CVM_HEADER
        _, records = index_iso(image, base)
        for kind, name, report_name, directory in (
                ('exact', 'exact-import-report.json', 'exact-report-v2.json', 'exact-mtx-v2'),
                ('structural', 'structural-import-report.json', 'structural-report-v2.json', 'structural-mtx-v2')):
            historical = baseline_reports / name
            current = regenerated / report_name
            before, after = json.loads(historical.read_text()), json.loads(current.read_text())
            old_paths = {row['path'] for row in before['results'] if row['status'] == 'imported'}
            new_rows = [row for row in after['results'] if row['status'] == 'imported' and row['path'] not in old_paths]
            report_sources.append({'kind': kind, 'baseline_report_sha256': sha_file(historical),
                                   'current_report_sha256': sha_file(current),
                                   'baseline_files': before['imported_files'],
                                   'baseline_entries': before['imported_english_entries'],
                                   'current_files': after['imported_files'],
                                   'current_entries': after['imported_english_entries']})
            for row in new_rows:
                relative = Path(row['path'])
                source2, source4 = (ps2_adv / relative).read_bytes(), (ps4_adv / relative).read_bytes()
                dc_path = ps4_adv / relative.parent / 'EN' / f'{relative.stem}DC.json'
                dc = json.loads(dc_path.read_text())
                record = find_record(records, f'ADV/{row["path"]}')
                offset = base + record.extent * SECTOR
                if bytes(image[offset:offset + record.size]) != source2:
                    raise ValueError(f'New script would replace an existing cumulative translation: {relative}')
                structural = None
                if kind == 'exact':
                    expected = import_exact_mtx(source2, source4, dc)
                else:
                    structural = import_structural_mtx(source2, source4, dc)
                    expected = structural.data
                generated = (regenerated / directory / relative).read_bytes()
                if expected != generated:
                    raise ValueError(f'Regenerated script differs from deterministic import: {relative}')
                target = overlay_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(expected)
                groups = DcLocalization.from_json(source4, dc).groups
                modes = Counter(span.mode for span in structural.spans) if structural else Counter({'exact': len(groups)})
                provenance.append({'path': f'ADV/{row["path"]}', 'kind': kind,
                                   'english_entries': row['english_entries'],
                                   'ps2_sha256': hashlib.sha256(source2).hexdigest(),
                                   'ps4_sha256': hashlib.sha256(source4).hexdigest(),
                                   'official_map_sha256': sha_file(dc_path),
                                   'output_sha256': hashlib.sha256(expected).hexdigest(),
                                   'groups': len(groups), 'mapping_modes': dict(modes),
                                   'name_placeholders': dict(Counter(m for group in groups for line in group.lines
                                                                    for m in __import__('re').findall(r'\(p[a-z]+[0-9]*\)', line))),
                                   'spans': [asdict(span) for span in structural.spans] if structural else [],
                                   'synthetic_groups': [{'anchor': group.anchor, 'synthetic_keys': group.synthetic_keys,
                                                         'end': group.replace_end} for group in groups if group.synthetic_keys]})
    wheel_target = overlay_root / wheel_row.path
    wheel_target.parent.mkdir(parents=True)
    wheel_target.write_bytes(wheel_row.replacement)
    overlay = collect_overlay([('r67m-verified-script-delta-and-15l-wheel', overlay_root)])
    if overlay.collisions:
        raise ValueError('Unexpected overlay collisions')
    candidate = output_dir / '67.15m-cumulative-script-wheel.iso'
    report = build(approved.ISO, candidate, overlay)
    with candidate.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        exe = find_record(outer, 'SLPM_665.11')
        elf = bytes(image[exe.extent * SECTOR:exe.extent * SECTOR + exe.size])
        cvm = find_record(outer, 'DATA.CVM')
        base = cvm.extent * SECTOR + CVM_HEADER
        _, records = index_iso(image, base)
        record = find_record(records, wheel_row.path)
        installed_wheel = bytes(image[base + record.extent * SECTOR:base + record.extent * SECTOR + record.size])
        if installed_wheel != wheel_row.replacement:
            raise ValueError('Installed emotion wheel differs from the verified 15l output')
        group4 = find_record(records, 'BLBRD/B_GP004.BIN')
        group4_bytes = bytes(image[base + group4.extent * SECTOR:base + group4.extent * SECTOR + group4.size])
        approved.verify_installed(elf, group4_bytes, checksums=False)
    source_elf = approved.ELF.read_bytes()
    locks = preservation._verify_static_locks(source_elf, elf)
    graphics = baseline_reports / 'startup-graphics'
    raw_startup = verify_startup_candidate(candidate, graphics)
    static = preservation._static_reports(elf, raw_startup, source_elf)
    if static['startup_scoped']['checks_passed'] != 155:
        raise ValueError('Current startup acceptance failed')
    report.update(release='r67.15m-cumulative-script-wheel', candidate_iso=str(candidate),
                  emotion_wheel={'installed_sha256': hashlib.sha256(installed_wheel).hexdigest(),
                                 'exact_15l_art_included': True, 'runtime_approval_pending': True,
                                 'artwork': wheel_proof['artwork'], 'native_coverage': wheel_proof['native_coverage']},
                  baseline_import_reports=report_sources, newly_installed_script_files=len(provenance),
                  newly_installed_official_entries=sum(row['english_entries'] for row in provenance),
                  assets=provenance, static_locks=locks, static_reports=static,
                  rofs=rofs_audit(approved.ISO, candidate),
                  protected_group4_sha256=hashlib.sha256(group4_bytes).hexdigest(),
                  verification_environment={'python': __import__('sys').version,
                                            'pillow': __import__('PIL').__version__})
    (output_dir / '67.15m-cumulative-script-wheel.elf').write_bytes(elf)
    (output_dir / 'release-report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--ps2-adv', type=Path, required=True)
    parser.add_argument('--ps4-adv', type=Path, required=True)
    parser.add_argument('--baseline-reports', type=Path, required=True)
    parser.add_argument('--regenerated', type=Path, required=True)
    args = parser.parse_args()
    result = release(args.output_dir.resolve(), args.ps2_adv, args.ps4_adv, args.baseline_reports, args.regenerated)
    print(json.dumps({key: result[key] for key in ('candidate_iso', 'candidate_iso_sha256',
                                                  'newly_installed_script_files', 'newly_installed_official_entries')}, indent=2))


if __name__ == '__main__':
    main()
