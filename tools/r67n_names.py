"""Recover native ADV name controls from the installed legacy English MTX scripts."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
import json
import mmap
from pathlib import Path
import re

from tools.iso9660_patch import find_record, index_iso
from tools.localization import DcLocalization, encode_ps2_english
from tools.mtx import MtxFile, MtxReplacement

# PS4 localized name replacement uses both complete name fields for the 1 variants.
# The PS2 spellings with a trailing 1 produce only the first CP932 glyph.
NATIVE_CONTROLS = {'(px)': b'px', '(pm1)': b'pm', '(pn1)': b'pn'}
MACRO = re.compile(r'\(p[a-z]+[0-9]*\)')


@dataclass(frozen=True)
class NameRepair:
    status: str
    output: bytes
    groups: list[dict]
    occurrences: list[dict]


def _encoded_lines(keys, lines):
    legacy = bytearray()
    native = bytearray()
    occurrences = []
    positions = []
    for line_index, (key, line) in enumerate(zip(keys, lines, strict=True)):
        if line_index:
            legacy.extend(b'r')
            native.extend(b'r')
        positions.append((key, len(native)))
        pos = 0
        for match in MACRO.finditer(line):
            macro = match.group()
            if macro not in NATIVE_CONTROLS:
                raise ValueError(f'Unsupported official placeholder {macro}')
            prefix = encode_ps2_english(line[pos:match.start()])
            legacy.extend(prefix)
            native.extend(prefix)
            occurrences.append((key, macro, len(legacy), len(native)))
            legacy.extend(encode_ps2_english(macro))
            native.extend(NATIVE_CONTROLS[macro])
            pos = match.end()
        tail = encode_ps2_english(line[pos:])
        legacy.extend(tail)
        native.extend(tail)
    return bytes(legacy), bytes(native), occurrences, positions


def _region_offsets(mtx):
    return sorted(set(mtx.pointer_offsets) - {0})


def repair_exact(ps2: bytes, ps4: bytes, dc: dict, installed: bytes) -> NameRepair:
    if ps2 != ps4:
        raise ValueError('Name repair requires identical PS2 and PS4 sources')
    return _repair(ps2, ps4, dc, installed, None)


def repair_structural(ps2: bytes, ps4: bytes, dc: dict, installed: bytes, spans: list[dict]) -> NameRepair:
    """Replay already installed historical offsets; no alignment or new matching."""
    return _repair(ps2, ps4, dc, installed, spans)


def _repair(ps2, ps4, dc, installed, spans):
    keys, values = dc['keys'], dc['values']
    if len(keys) != len(values) or not all(isinstance(value, str) for value in values):
        raise ValueError('Invalid DC keys or values')
    by_key = dict(zip(keys, values, strict=True))
    for value in values:
        for match in MACRO.finditer(value):
            if match.group() not in NATIVE_CONTROLS:
                raise ValueError(f'Unsupported official placeholder {match.group()}')

    # The legacy parser's *structural* checks operate on the original key arrays
    # and MTX bytes. Its separate source-wide name gate cannot tell whether the
    # English moved a name to another line. Supply the real text after grouping.
    groups = DcLocalization.from_json(ps4, {'keys': keys, 'values': [''] * len(keys)}).groups
    if spans is None:
        spans = [{'first_group': i, 'last_group': i, 'ps4_start': g.anchor, 'ps4_end': g.replace_end,
                  'ps2_start': g.anchor, 'ps2_end': g.replace_end} for i, g in enumerate(groups)]
    chunks = []
    legacy_spans, native_spans = [], []
    expected_group = 0
    for span in sorted(spans, key=lambda s: s['first_group']):
        first, last = span['first_group'], span['last_group']
        if not (first == expected_group <= last < len(groups)):
            raise ValueError('Missing or repeated historical group')
        if (span['ps4_start'], span['ps4_end']) != (groups[first].anchor, groups[last].replace_end):
            raise ValueError('Historical group source range differs')
        expected_group = last + 1
        start, end = span['ps2_start'], span['ps2_end']
        cluster_old, cluster_new = [], []
        for group in groups[first:last+1]:
            line_keys = (group.anchor, *group.synthetic_keys)
            old, new, occurrences, positions = _encoded_lines(line_keys, [by_key[key] for key in line_keys])
            chunks.append((start, end, group, old, new, occurrences, positions, group is groups[last]))
            cluster_old.append(old)
            cluster_new.append(new)
        legacy_spans.append(MtxReplacement(start, end, b'r'.join(cluster_old)))
        native_spans.append(MtxReplacement(start, end, b'r'.join(cluster_new)))
    if expected_group != len(groups):
        raise ValueError('Historical mapping does not cover every group')
    source = MtxFile.parse(ps2)
    legacy = source.apply_replacements(tuple(legacy_spans))
    native = source.apply_replacements(tuple(native_spans))
    legacy_raw, output = legacy.compile(), native.compile()
    if installed == output:
        status = 'already_native'
    elif installed == legacy_raw:
        status = 'repaired'
    else:
        raise ValueError('The installed MTX differs from both complete source replays')

    source_starts = _region_offsets(source)
    legacy_starts, native_starts = _region_offsets(legacy), _region_offsets(native)
    delta_old, delta_new = Counter(), Counter()
    offsets, names, changes = [], [], []
    for start, end, group, old, new, occurrences, positions, cluster_end in chunks:
        region = bisect_right(source_starts, start) - 1
        local_start = start - source_starts[region]
        old_start = legacy_starts[region] + local_start + delta_old[region]
        new_start = native_starts[region] + local_start + delta_new[region]
        if legacy_raw[old_start:old_start+len(old)] != old or output[new_start:new_start+len(new)] != new:
            raise ValueError('Source replay did not preserve group coordinates')
        offsets.append({'source_start': group.anchor, 'source_end': group.replace_end,
                        'legacy_start': old_start, 'output_start': new_start, 'output_end': new_start+len(new),
                        'lines': [{'dc_key': key, 'output_offset': new_start+offset} for key, offset in positions]})
        for key, macro, old_offset, new_offset in occurrences:
            old_at, new_at = old_start + old_offset, new_start + new_offset
            literal = encode_ps2_english(macro)
            if legacy_raw[old_at:old_at+len(literal)] != literal:
                raise ValueError('Legacy placeholder lost its source ownership')
            changes.append(MtxReplacement(old_at, old_at + len(literal), NATIVE_CONTROLS[macro]))
            names.append({'dc_key': key, 'source_anchor': group.anchor, 'macro': macro,
                          'control': NATIVE_CONTROLS[macro].decode(), 'legacy_offset': old_at,
                          'installed_offset': old_at if status == 'repaired' else new_at,
                          'output_offset': new_at})
        # An inherited cluster inserts 'r' between groups and consumes its PS2 span once.
        adjustment = start - end if cluster_end else 1
        delta_old[region] += len(old) + adjustment
        delta_new[region] += len(new) + adjustment

    # Independently edit only the owned literal ranges on the historical binary.
    # A historical rebuild can carry additional alignment zeroes. Use canonical
    # source-replay padding after proving each pointer-selected payload identical.
    edited = legacy.apply_replacements(tuple(changes))
    edited_raw = edited.compile()
    for i, (a,b) in enumerate(zip(edited.pointer_offsets, native.pointer_offsets, strict=True)):
        if bool(a) != bool(b):
            raise ValueError(f'Pointer slot {i} changed its sentinel role')
    e_starts = _region_offsets(edited)
    if len(e_starts) != len(native_starts):
        raise ValueError('Pointer region ownership changed')
    if [e_starts.index(v) if v else -1 for v in edited.pointer_offsets] != [
            native_starts.index(v) if v else -1 for v in native.pointer_offsets]:
        raise ValueError('Pointer slot aliases changed')
    for a,ae,b,be in zip(e_starts,e_starts[1:]+[len(edited_raw)],native_starts,
                          native_starts[1:]+[len(output)],strict=True):
        left, right = edited_raw[a:ae], output[b:be]
        if left != right and not (left.rstrip(b'\0') == right.rstrip(b'\0') and right.rstrip(b'\0').endswith(b'_')):
            raise ValueError('Name repair changed bytes outside a literal or terminal padding')
    return NameRepair(status,output,offsets,names)


def _historical_spans(historical_report: Path, current_manifest: Path):
    manifests = ((historical_report, '9250a3f653a3b007ee59dd88303d06c50bce016ac21793a56c297b061bd829d8', 'results'),
                 (current_manifest, '665c01e1b17ffac5c7e89bd6dc97d8543f81f7b2895b962772250eb6afe2422a', 'assets'))
    result = {}
    for path, expected, section in manifests:
        raw = path.read_bytes()
        if sha256(raw).hexdigest() != expected:
            raise ValueError(f'Historical span evidence differs: {path}')
        for row in json.loads(raw)[section]:
            if row.get('spans'):
                result[row['path'].removeprefix('ADV/')] = row
    return result


def run(ps2_adv: Path, ps4_adv: Path, baseline_iso: Path, output_dir: Path, historical_report: Path,
        current_manifest: Path = Path('translations/r67m_script_transfer.json')) -> dict:
    if output_dir.exists():
        raise ValueError(f'Choose a fresh output directory: {output_dir}')
    historical = _historical_spans(historical_report, current_manifest)
    rows, overlays = [], {}
    with baseline_iso.open('rb') as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        base = find_record(outer,'DATA.CVM').extent*2048+0x1800
        _, records = index_iso(image, base)
        records = {r.path:r for r in records}
        for path in sorted(ps4_adv.glob('*/EN/*DC.json')):
            if path.name.endswith('.KSFDC.json'):
                continue
            dc = json.loads(path.read_bytes())
            macros = Counter(m.group() for value in dc['values'] for m in MACRO.finditer(value))
            if not macros:
                continue
            relative = path.parent.parent.relative_to(ps4_adv)/(path.name[:-7]+'.MTX')
            target = ps2_adv/relative
            if not target.is_file():
                continue
            key = 'ADV/'+relative.as_posix()
            rec = records[key]
            pos = base+rec.extent*2048
            installed = bytes(image[pos:pos+rec.size])
            ps2, ps4 = target.read_bytes(), (ps4_adv/relative).read_bytes()
            row = {'path':key, 'macros':dict(macros), 'dc_sha256':sha256(path.read_bytes()).hexdigest(),
                   'ps2_sha256':sha256(ps2).hexdigest(),'ps4_sha256':sha256(ps4).hexdigest(),
                   'installed_sha256':sha256(installed).hexdigest()}
            rows.append(row)
            if ps2 == ps4:
                row['relation'] = 'exact'
                repaired = repair_exact(ps2,ps4,dc,installed)
            else:
                row['relation'] = 'structural'
                prior = historical.get(relative.as_posix())
                if prior is None and ps2 == installed:
                    row['status'] = 'original_not_imported'
                    continue
                if prior is None or prior['output_sha256'] != row['installed_sha256']:
                    raise ValueError(f'Cannot verify installed historical structural output: {key}')
                repaired = repair_structural(ps2,ps4,dc,installed,prior['spans'])
            row.update(status=repaired.status,output_sha256=sha256(repaired.output).hexdigest(),
                       groups=repaired.groups,occurrences=repaired.occurrences)
            if repaired.status == 'repaired':
                overlays[key] = repaired.output
    output_dir.mkdir(parents=True)
    for key,data in overlays.items():
        path = output_dir/'overlay'/key
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
    report = {'schema_version':1,'statuses':dict(Counter(row['status'] for row in rows)),
              'repaired_occurrences':sum(len(row['occurrences']) for row in rows if row['status']=='repaired'),
              'assets':rows}
    (output_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('ps2-adv','ps4-adv','baseline-iso','output-dir','historical-report'):
        parser.add_argument('--'+option,type=Path,required=True)
    args = parser.parse_args()
    result = run(args.ps2_adv,args.ps4_adv,args.baseline_iso,args.output_dir,args.historical_report)
    print(json.dumps({'statuses':result['statuses'],'repaired_occurrences':result['repaired_occurrences']}))
