"""Verify the r67.15o ADV inventory against original sources and the installed disc."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
import json
import mmap
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

from tools.elf_rofs import find_rofs_record
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.mtx import MtxFile
from tools import r67o_bundles, r67o_choices, r67o_kwlnscr, r67o_reviewed, r67o_speakers
from tools.r67n_inventory import (
    CONTROL_HASHES, JAPANESE, PRESENT, SEMANTIC, UNRESOLVED, digest, expected_sources,
    japanese_runs, physical_labels, relation_name,
)
from tools.r67n_ksf import native_slots
from tools.r67o_iso import CVM_HEADER

BASELINE = 'c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0'
PS4_SOURCE = '74b62548a5e1ddcc9a9c476b06fb93fa7f624c32050cb73cd5e4c6ff5e5798fe'
BASELINE_INVENTORY = {
    'summary.json': '097c1507d9876dccdff24ed362e7252f3b051af659cdafc88bdbad1e84c57f9a',
    'entries.json': '651635984c955f00c3f2231b6bcc5a6d712ddd45f8e10c7bf671213c8e1126e6',
    'japanese.json': '5520a433fba597de205f0cc8a2fe27c70a700483e4396ec7347228e11ee0156d',
    'ps4-payload-index.json': '5b53dd15a8a7576020a2048e84d6f47267cfdb542d0c7914591da7f82ad498c3',
    'files.json': '1946a1f9e07483e932475281f2868f75adbc50aabd942fb6187f3af4f7ad5499',
    'ksf-labels.json': '2ca2d64914046123ad2832d86b4d51ee0dd0a4ec079546236f2a46f078029f63',
}
PRODUCER_REPORTS = {
    'bundle': '879ab842981954c52f1b0df60c466f0dcba5161b7379818b694609ac22395938',
    'kwlnscr': '4f7c0671e09ea26f916d6d3bb675021f2a202f7fd5a52b33e342fe76e1afa4ab',
    'speaker': '548b58519e885b34f8c536e11dbe4dcd3f5bcfb5c53e50e3fc80c6aa71543bf9',
    'reviewed': 'fc4d4b39137f1854039a7ff64d7b669f123c826140ddfee6ed68ceb381a72e75',
    'choices': '3dc1400704f2a68ce32578febcbbf47b578dc6780596a81ecaa70fb1ae811ba3',
}
GUARDED = 'official English installed via guarded native ELF choice table'
FALLBACK = 'original Japanese safety fallback, verified guarded English owner active'
STOCK_CHOICE = 'physical KSF fallthrough, verified guarded English owner active'


def checked_digest(raw, expected, label):
    if digest(raw) != expected:
        raise ValueError(f'{label} hash drift')
    return raw


def read_pinned(path, expected):
    return checked_digest(path.read_bytes(), expected, str(path))


def verify_installed_range(row, raw, iso_offset):
    start, length = row['installed_offset'], row['installed_length']
    if (not 0 <= start <= start + length <= len(raw)
            or row['installed_iso_offset'] != iso_offset + start
            or digest(raw[start:start + length]) != row['installed_bytes_sha256']):
        raise ValueError(f'installed range drift: {row}')


def verify_dc_rows(path, entries, dc):
    if len(entries) != len(dc['keys']) or len(dc['keys']) != len(dc['values']):
        raise ValueError(f'official DC entry count drift: {path}')
    for index, (entry, key, text) in enumerate(zip(entries, dc['keys'], dc['values'], strict=True)):
        if ((entry['file'], entry['official_array_index'], entry['dc_key']) != (path, index, key)
                or entry['official_text_utf8_sha256'] != digest(text.encode())):
            raise ValueError(f'official DC identity drift: {path}:{index}')


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    output_start: int
    output_end: int
    before_sha256: str
    after_sha256: str
    slots: tuple[int, ...]


def pointer_regions(raw):
    slots = defaultdict(list)
    for slot, start in enumerate(MtxFile.parse(raw).pointer_offsets):
        if start:
            slots[start].append(slot)
    starts = sorted(slots)
    return [(start, end, tuple(slots[start]))
            for start, end in zip(starts, starts[1:] + [len(raw)], strict=True)]


class PositionMap:
    """Verify an MTX splice and project intact coordinates through the relocation."""

    def __init__(self, before: bytes, after: bytes, edits: list[Edit]):
        input_regions, output_regions = pointer_regions(before), pointer_regions(after)
        if (input_regions[0][0] != output_regions[0][0]
                or [slots for _, _, slots in input_regions] != [slots for _, _, slots in output_regions]):
            raise ValueError('MTX pointer order, aliases or null slots changed')
        self.starts = [start for start, _, _ in input_regions]
        self.regions = []
        self.evidence = []
        self.changes = []
        by_slots = defaultdict(list)
        for edit in sorted(edits, key=lambda e: e.start):
            by_slots[edit.slots].append(edit)
        for (start, end, slots), (out_start, out_end, _) in zip(input_regions, output_regions, strict=True):
            region_edits = by_slots.pop(slots, [])
            in_cursor, out_cursor = start, out_start
            for edit in region_edits:
                if not (in_cursor <= edit.start < edit.end <= end
                        and out_cursor <= edit.output_start <= edit.output_end <= out_end):
                    raise ValueError('MTX edit overlaps another edit or crosses its pointer region')
                if before[in_cursor:edit.start] != after[out_cursor:edit.output_start]:
                    raise ValueError('MTX unchanged run differs before edit')
                checked_digest(before[edit.start:edit.end], edit.before_sha256, 'MTX input edit')
                checked_digest(after[edit.output_start:edit.output_end], edit.after_sha256, 'MTX output edit')
                in_cursor, out_cursor = edit.end, edit.output_end
            tail = before[in_cursor:end]
            padding = after[out_cursor + len(tail):out_end]
            if after[out_cursor:out_cursor + len(tail)] != tail:
                raise ValueError('MTX unchanged terminal run differs')
            required = (-(out_cursor + len(tail) - out_start)) % 4
            if out_end == len(after) and not before[start:end].rstrip(b'\0').endswith(b'_'):
                required = 0
            if not edits:
                required = 0
            if (len(padding) != required or padding != bytes(required)
                    or (required and not before[start:end].rstrip(b'\0').endswith(b'_'))):
                raise ValueError('MTX terminal alignment padding differs')
            self.regions.append((end, out_start - start, region_edits))
            evidence = {'slots': list(slots), 'input_span': [start, end], 'output_span': [out_start, out_end],
                        'alignment_nul_added': required, 'input_sha256': digest(before[start:end]),
                        'output_sha256': digest(after[out_start:out_end])}
            self.evidence.append(evidence)
            if region_edits or required or start != out_start:
                self.changes.append(evidence)
        if by_slots:
            raise ValueError('MTX edit has no owning pointer region')

    def at(self, start: int, length: int) -> int:
        region = bisect_right(self.starts, start) - 1
        if region < 0:
            raise ValueError('installed range starts inside the MTX pointer header')
        end, displacement, edits = self.regions[region]
        if not 0 <= length <= end - start:
            raise ValueError('installed range crosses an MTX pointer region')
        for edit in edits:
            if edit.end <= start:
                displacement += (edit.output_end - edit.output_start) - (edit.end - edit.start)
            elif edit.start < start + length or edit.start < start:
                raise ValueError('inherited installed range overlaps a new MTX replacement')
            else:
                break
        return start + displacement


def install_mtx_entry(rows, identity, key, target, span, checksum, proof, iso_offset, **fields):
    row = rows.get(identity)
    if row is None or row['dc_key'] != key:
        raise ValueError(f'official DC identity drift: {identity}')
    if 'installed_offset' in row or row['status'] != UNRESOLVED:
        raise ValueError(f'official DC entry already installed: {identity}')
    start, end = span
    row.update(status=PRESENT, proof=proof, installed_asset=target, installed_offset=start,
               installed_length=end - start, installed_bytes_sha256=checksum,
               installed_iso_offset=iso_offset + start, **fields)


def read_choice_rows(table, base, corpus, expected_hash):
    """Read all table identities, guarded preimages and exact English byte strings."""
    checked_digest(table, expected_hash, 'choice table')
    def read(fmt, start):
        if start + struct.calcsize(fmt) > len(table):
            raise ValueError('truncated choice table record')
        return struct.unpack_from(fmt, table, start)

    indices = {}
    cursor = 0
    for index, file in enumerate(corpus.files):
        if read('<20sI', cursor) != (file.loaded_name.ljust(20, b'\0'), file.installed_size):
            raise ValueError(f'choice table file identity drift: {file.path}')
        indices[file.loaded_name] = index
        cursor += 24

    row_cursor = cursor + 68 * len(corpus.records)
    installed = {}
    for record in corpus.records:
        offset, file_index, ordinal, flags, header, fill, *pointers = read('<IHH4s38s2s4I', cursor)
        if (offset, file_index, ordinal, flags, header, fill) != (
                record.offset, indices[record.loaded_name], record.ordinal, record.flags, record.header, b'\0\0'):
            raise ValueError(f'choice native record identity drift: {record.loaded_name}:{record.ordinal}')
        if any(pointers[len(record.rows):]):
            raise ValueError('nonempty unused choice table row pointer')
        for row, pointer in zip(record.rows, pointers[:len(record.rows)], strict=True):
            if pointer != base + row_cursor:
                raise ValueError(f'choice row pointer drift: {row.path}:{row.key}')
            if table[row_cursor:row_cursor + 60] != row.preimage + row.pristine:
                raise ValueError(f'choice table preimage drift: {row.path}:{row.key}')
            start = row_cursor + 60
            size = len(row.encoded)
            if table[start:start + size + 1] != row.encoded + b'\0':
                raise ValueError(f'choice English glyph bytes drift: {row.path}:{row.key}')
            identity = row.path, row.array_index
            if identity in installed:
                raise ValueError(f'duplicate official choice identity: {identity}')
            installed[identity] = (start, size)
            row_cursor = start + size + 1
        cursor += 68
    if row_cursor != len(table):
        raise ValueError('unowned trailing choice table bytes')
    return installed


def speaker_counts(definitions, occurrences):
    used = {row['official_proof_id'] for row in occurrences}
    if not used <= definitions.keys():
        raise ValueError('speaker occurrence without an official label definition')
    return {'verified_fixed_label_pairs': len(definitions), 'used_fixed_label_pairs': len(used),
            'localized_occurrences': len(occurrences), 'affected_files': len({row['file'] for row in occurrences})}


@contextmanager
def open_disc(path):
    with path.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        yield Disc(image)


class Disc:
    def __init__(self, image):
        self.image = image
        outer = index_iso(image)[1]
        self.cvm_start = find_record(outer, 'DATA.CVM').extent * SECTOR_SIZE + CVM_HEADER
        self.records = {record.path.removeprefix('ADV/'): record for record in index_iso(image, self.cvm_start)[1]
                        if record.path.startswith('ADV/') and record.path.endswith(('.MTX', '.KSF'))}
        executable = find_record(outer, 'SLPM_665.11')
        self.elf_offset = executable.extent * SECTOR_SIZE
        self.elf = image[self.elf_offset:self.elf_offset + executable.size]

    def asset(self, path):
        record = self.records[path]
        offset = self.cvm_start + record.extent * SECTOR_SIZE
        return offset, self.image[offset:offset + record.size]


def grouped(rows, field='file'):
    out = defaultdict(list)
    for row in rows:
        out[row[field]].append(row)
    return out


def unique_index(rows, key):
    index = {key(row): row for row in rows}
    if len(index) != len(rows):
        raise ValueError('duplicate inventory identity')
    return index


def verify_sources(ps2, ps4):
    # The baseline combined manifest covers every PS2 file and its same-path PS4/DC
    # owners. Pin the full PS4 archive as well, including alternate assets.
    corpus = expected_sources(ps2, ps4)
    full = sha256()
    for path in sorted(ps4.rglob('*')):
        if path.is_file() and (path.suffix in {'.MTX', '.KSF'} or path.name.endswith('DC.json')):
            full.update(f'{path.relative_to(ps4).as_posix()} {digest(path.read_bytes())}\n'.encode())
    if full.hexdigest() != PS4_SOURCE:
        raise ValueError('full PS4 ADV source and DC archive hash drift')
    return corpus


def baseline_asset(asset, file, entries, findings, labels, source, dc, disc):
    path = asset['path']
    offset, raw = disc.asset(path)
    actual = (asset['kind'], relation_name(asset), asset['ps2']['size'], asset['ps2']['sha256'],
              asset['ps4'], asset['english_map'], asset['dc_sha256'], len(dc['keys']),
              'ADV/' + path, offset, len(raw), digest(raw))
    expected = tuple(file[k] for k in (
        'kind', 'relation', 'ps2_size', 'ps2_sha256', 'ps4', 'map_path', 'map_sha256', 'official_entries',
        'iso_record', 'iso_offset', 'size', 'installed_sha256'))
    if actual != expected:
        raise ValueError(f'baseline source or installed file drift: {path}')
    verify_dc_rows(path, entries, dc)
    for entry in entries:
        if 'installed_offset' in entry:
            verify_installed_range(entry, raw, offset)

    if file['kind'] == 'KSF':
        if native_slots(source) != native_slots(raw):
            raise ValueError(f'baseline KSF structure drift: {path}')
        physical = list(physical_labels(raw))
        for (pos, record, start, slot, _, has_nul), label in zip(physical, labels, strict=True):
            physical_identity = (pos, record, start, slot, offset + pos, has_nul,
                                 digest(raw[pos:pos + 30]), digest(source[pos:pos + 30]))
            if physical_identity != tuple(label[k] for k in (
                    'file_offset', 'record', 'record_offset', 'choice', 'iso_offset', 'has_inline_nul',
                    'installed_payload_sha256', 'pristine_payload_sha256')):
                raise ValueError(f'baseline native choice drift: {path}:{pos}')
        candidates = [(pos, pos + len(text), text.decode('cp932', errors='replace'))
                      for pos, _, _, _, text, _ in physical if JAPANESE.search(text.decode('cp932', errors='replace'))]
    else:
        candidates = list(japanese_runs(raw, MtxFile.parse(raw).header_size))

    for (start, end, text), finding in zip(candidates, findings, strict=True):
        if (start, end - start, offset + start, text, digest(raw[start:end])) != tuple(
                finding[k] for k in ('file_offset', 'byte_length', 'iso_offset', 'text', 'installed_bytes_sha256')):
            raise ValueError(f'baseline Japanese candidate drift: {path}:{start}')


def verified_stage_one(ps2, ps4, baseline_iso, partial, paths, reports):
    # Replay the two published producers against their original trusted inputs.
    with TemporaryDirectory() as work:
        bundle_dir, kw_dir = (Path(work) / kind for kind in ('bundle', 'kwlnscr'))
        bundle = r67o_bundles.run(ps2, ps4, baseline_iso, partial, bundle_dir)
        kw = r67o_kwlnscr.run(ps2, ps4, baseline_iso, kw_dir)
        for kind, directory in (('bundle', bundle_dir), ('kwlnscr', kw_dir)):
            if json.loads((directory / 'report.json').read_bytes()) != reports[kind]:
                raise ValueError(f'{kind} report differs from fresh source replay')
        outputs = {}
        for row in bundle['results']:
            if not row['spans']:
                continue
            path = row['path'].removeprefix('ADV/')
            output = (bundle_dir / 'overlay' / path).read_bytes()
            if output != (paths['bundle'].parent / 'overlay' / path).read_bytes():
                raise ValueError(f'bundle artifact drift: {path}')
            outputs[path] = output
        path = r67o_kwlnscr.TARGET_MTX
        output = (kw_dir / kw['output_path']).read_bytes()
        if output != (paths['kwlnscr'].parent / kw['output_path']).read_bytes():
            raise ValueError(f'alternate owner artifact drift: {path}')
        outputs[path] = output
    return outputs


def bundle_edits(report):
    return [Edit(row['installed_start'], row['installed_end'], row['output_start'], row['output_end'],
                 row['original_sha256'], row['replacement_sha256'], tuple(row['pointer_slots']))
            for row in report['spans']]


def kwlnscr_edits(report):
    return [Edit(*row['installed_ps2']['span'], *row['output_ps2']['span'],
                 row['installed_ps2']['sha256'], row['output_ps2']['sha256'],
                 tuple(row['installed_ps2']['pointer_slots']))
            for row in report['spans']]


def speaker_edits(report):
    return [Edit(*row['input_span'], *row['output_span'], row['input_span_sha256'],
                 row['output_span_sha256'], tuple(row['pointer_slots']))
            for row in report['occurrences']]


def apply_stage_one(path, before, output, bundle, kw):
    if path == r67o_kwlnscr.TARGET_MTX:
        projection = PositionMap(before, output, kwlnscr_edits(kw))
        padding = [{'pointer_slots': row['slots'], 'added_null_bytes': row['alignment_nul_added']}
                   for row in projection.evidence]
        if padding != kw['region_alignment_bytes']:
            raise ValueError('KWLNSCR alignment records differ from actual MTX')
        return projection

    row = bundle[path]
    projection = PositionMap(before, output, bundle_edits(row))
    regions = [dict(pointer_slots=r['slots'], installed_start=r['input_span'][0],
                    installed_end=r['input_span'][1], output_start=r['output_span'][0],
                    output_end=r['output_span'][1], installed_sha256=r['input_sha256'],
                    output_sha256=r['output_sha256'], alignment_bytes_added=r['alignment_nul_added'])
               for r in projection.evidence]
    if regions != row['regions']:
        raise ValueError(f'bundle pointer region records drift: {path}')
    return projection


def verify_speaker_corpus(ps4, report):
    corpus = r67o_speakers.load_corpus(ps4)
    labels = {
        digest(row.original): {'japanese': row.japanese, 'english': row.english,
                               'japanese_sha256': digest(row.original), 'english_sha256': digest(row.localized),
                               'ps4_dc': row.proofs}
        for row in corpus.speakers
    }
    if (json.loads(json.dumps(labels)) != report['official_labels']
            or corpus.source_inventory != report['official_source_inventory']
            or json.loads(json.dumps(corpus.excluded)) != report['excluded_labels']):
        raise ValueError('speaker official source proof drift')
    return corpus


def apply_speaker_stage(path, stage_one, corpus, report, report_path, actual, offset, occurrences):
    changed = report['script_files'].get(path)
    expected, replay = r67o_speakers.patch_script(stage_one, corpus)
    if replay['unresolved'] != [] or path in report['unresolved']:
        if json.loads(json.dumps(replay['unresolved'])) != report['unresolved'].get(path, []):
            raise ValueError(f'speaker unresolved roles drift: {path}')
    if changed is None:
        if (report['unchanged_input_sha256'].get(path) != digest(stage_one)
                or replay['occurrences'] or expected != stage_one or actual != stage_one):
            raise ValueError(f'unexpected change in unstaged MTX: {path}')
        return None

    if expected != actual or (report_path.parent / 'overlay' / path).read_bytes() != expected:
        raise ValueError(f'installed MTX differs from composed expected bytes: {path}')
    projection = PositionMap(stage_one, expected, speaker_edits(changed))
    if (digest(stage_one) != changed['input_sha256'] or digest(expected) != changed['output_sha256']
            or projection.changes != changed['regions']):
        raise ValueError(f'speaker pointer region records drift: {path}')
    for claimed, proved in zip(changed['occurrences'], replay['occurrences'], strict=True):
        native = report['native']['proof']['identities'][claimed['official_proof_id']]
        proved.update({key: native[key] for key in ('stock_actor', 'stock_alias_column', 'native_japanese_sha256')})
        if claimed != json.loads(json.dumps(proved)):
            raise ValueError(f'speaker dispatch or byte-range evidence drift: {path}')
        occurrences.append({**claimed, 'file': path, 'installed_iso_offset': offset + claimed['output_span'][0]})
    return projection


def verify_final_elf(baseline, final, changed, reports, paths):
    choices = reports['choices']
    speakers = reports['speaker']['native']
    choice_elf = read_pinned(paths['choices'].parent / '67.15o-ksf-choice-diagnostic.elf', choices['result_sha256'])
    composed = read_pinned(paths['speaker'].parent / 'patched.elf', speakers['result_sha256'])
    if (choices['source_sha256'] != digest(baseline.elf) or speakers['source_sha256'] != digest(choice_elf)):
        raise ValueError('native executable predecessor drift')

    for report, source, installed, append_key in (
            (choices, baseline.elf, choice_elf, 'append_sha256'),
            (speakers, choice_elf, composed, 'appended_sha256')):
        start, end = report['appended_extent']
        if (start, end) != (len(source), len(installed)):
            raise ValueError('native append extent drift')
        checked_digest(installed[start:end], report[append_key], 'native executable append')
        for call in report['call_sites']:
            at = call['file_offset']
            if (source[at:at + 4].hex() != call['expected']
                    or final.elf[at:at + 4].hex() != call['replacement']):
                raise ValueError(f"installed native code owner mismatch: {call['address']:#x}")

    expected = bytearray(composed)
    for path in changed:
        before, after = baseline.records[path], final.records[path]
        rofs = find_rofs_record(baseline.elf, before.path, before.size, before.extent)
        struct.pack_into('<I', expected, rofs.size_offset, after.size)
        struct.pack_into('<I', expected, rofs.extent_offset, after.extent)
    if expected != final.elf:
        raise ValueError('installed ELF differs from verified composed executable and ADVs ROFS records')
    return digest(final.elf)


def installed_choices(baseline_iso, baseline_dir, pristine_elf, ps2, ps4, research, supplement,
                      baseline_disc, final, report, entries):
    corpus = r67o_choices.load_corpus(
        baseline_disc.elf, pristine_elf.read_bytes(), baseline_iso, ps2, ps4,
        research, baseline_dir / 'files.json', supplement)
    table = report['table']
    address = table['address']
    segment_offset, virtual = struct.unpack_from('<II', final.elf, 0x58)
    load_size = struct.unpack_from('<I', final.elf, 0x64)[0]
    table_offset = address - virtual + segment_offset
    if not segment_offset <= table_offset <= table_offset + table['size'] <= segment_offset + load_size <= len(final.elf):
        raise ValueError('choice table address leaves the supported ELF load segment')
    raw = final.elf[table_offset:table_offset + table['size']]
    table_rows = read_choice_rows(raw, address, corpus, table['sha256'])
    if ((len(corpus.files), len(corpus.records), len(table_rows), len(corpus.blank_rows), corpus.supplement_sha256)
            != tuple(table[k] for k in ('files', 'records', 'choices', 'stock_noops', 'supplement_sha256'))
            or report['entries']['choice_files'] != address
            or report['entries']['choice_records'] != address + 24 * len(corpus.files)):
        raise ValueError('choice table census or runtime table address drift')

    sources = unique_index(report['ksf_installed_files'], lambda row: row['path'])
    file_bytes = {}
    for file in corpus.files:
        _, installed = final.asset(file.path)
        if (sources.pop(file.path) != {'path': file.path, 'size': len(installed), 'sha256': digest(installed)}
                or len(installed) != file.installed_size or digest(installed) != file.installed_sha256):
            raise ValueError(f'final KSF differs from the guarded file preimage: {file.path}')
        file_bytes[file.path] = installed
    if sources:
        raise ValueError('unaccounted guarded KSF file preimages')

    active, noops = {}, {}
    for record in corpus.records:
        for row in record.rows:
            identity = (row.path, row.array_index)
            installed = file_bytes[row.path]
            if (installed[record.offset:record.offset + 38] != record.header
                    or installed[row.offset:row.offset + 30] != row.preimage
                    or installed[row.offset - 1] != record.flags[row.slot]):
                raise ValueError(f'final KSF branch or active choice guard drift: {identity}')
            entry = entries[identity]
            native = (row.path, row.offset)
            if (native in active or entry['dc_key'] != row.key
                    or entry['official_text_utf8_sha256'] != digest(row.text.encode())):
                raise ValueError(f'official KSF identity drift: {identity}')
            pos, length = table_rows[identity]
            if 'installed_offset' in entry:
                entry['baseline_ksf_evidence'] = {key: entry[key] for key in (
                    'installed_offset', 'installed_length', 'installed_bytes_sha256', 'installed_iso_offset')}
            entry.update(status=GUARDED, proof='verified native file, ordinal, slot, flags, 30-byte guard and official glyph stream',
                         installed_asset='SLPM_665.11', installed_offset=table_offset + pos,
                         installed_iso_offset=final.elf_offset + table_offset + pos, installed_length=length,
                         installed_bytes_sha256=digest(raw[pos:pos + length]),
                         choice_table_virtual_address=address + pos, native_ksf_asset=row.path,
                         native_ksf_offset=row.offset, native_record_offset=record.offset,
                         native_record_ordinal=record.ordinal, native_choice_slot=row.slot,
                         runtime_name_macros=sorted(marker for marker, token in r67o_choices.NAME_MARKERS.items()
                                                    if token in row.encoded),
                         native_ksf_preimage_sha256=digest(row.preimage), baseline_status=entry['status'])
            verify_installed_range(entry, final.elf, final.elf_offset)
            active[native] = entry
    for row in corpus.blank_rows:
        identity = row.path, row.array_index
        entry = entries[identity]
        native = row.path, row.offset
        if (entry['status'] != r67o_choices.BLANK_STATUS or entry['dc_key'] != row.key
                or entry['official_text_utf8_sha256'] != digest(row.text.encode())
                or native in active or native in noops
                or file_bytes[row.path][row.offset:row.offset + 30] != row.pristine):
            raise ValueError(f'official U+3000 stock no-op drift: {identity}')
        noops[native] = entry
    held = json.loads(supplement.read_bytes())['held']
    for row in held:
        entry = entries[row['source_path'], row['index']]
        if entry['dc_key'] != row['key'] or entry['status'] != UNRESOLVED:
            raise ValueError('unproven choice does not retain unresolved disposition')
        entry['proof'] = row['reason']
    return active, noops, held


def read_baseline_inventory(directory):
    return {name: json.loads(read_pinned(directory / name, checksum))
            for name, checksum in BASELINE_INVENTORY.items()}


def verify_baseline(disc, ps2, ps4, inventory):
    checked_digest(disc.image, BASELINE, 'r67.15n ISO')
    sources = verify_sources(ps2, ps4)
    files = unique_index(inventory['files.json'], lambda row: row['path'])
    by_file, findings, labels = (grouped(inventory[name]) for name in
                               ('entries.json', 'japanese.json', 'ksf-labels.json'))
    if (disc.records.keys() != files.keys() or files.keys() != {a['path'] for a in sources['assets']}
            or any(not group.keys() <= files.keys() for group in (by_file, findings, labels))):
        raise ValueError('baseline ADV file census drift')
    for source in sources['assets']:
        path = source['path']
        row = files[path]
        ps2_raw = read_pinned(ps2 / path, source['ps2']['sha256'])
        dc_path = source['english_map']
        dc = json.loads(read_pinned(ps4 / dc_path, source['dc_sha256'])) if dc_path else {'keys': [], 'values': []}
        baseline_asset(source, row, by_file[path], findings[path], labels[path], ps2_raw, dc, disc)
    return files, by_file, findings, labels


def install_stage_one(path, stage_one, final, final_offset, bundle, kw, projection, by_file, entries):
    if path == r67o_kwlnscr.TARGET_MTX:
        logical_path = r67o_kwlnscr.SOURCE_MTX
        claims = kw['entries']
        for row in claims:
            identity = (logical_path, row['dc_index'])
            original = entries[identity]
            if original['dc_key'] != row['key'] or original['official_text_utf8_sha256'] != row['official_utf8_sha256']:
                raise ValueError(f'KWLNSCR logical source identity drift: {identity}')
            if row['reason'] != r67o_kwlnscr.APPROVED:
                if original['status'] != UNRESOLVED:
                    raise ValueError(f'KWLNSCR held corresponding entry is already installed: {identity}')
                original['proof'] = row['reason']
                continue
            line = row['output_entry']
            start, end = line['span']
            length = end - start
            checked_digest(stage_one[start:end], line['sha256'], 'KWLNSCR stage-one official line')
            start = projection.at(start, length) if projection else start
            install_mtx_entry(entries, identity, row['key'], path, (start, start + length), line['sha256'],
                              row['reason'], final_offset, ps4_group_range=row['source_ps4']['span'],
                              ps2_group_or_cluster_range=row['original_ps2']['span'],
                              source_scene_block_sha256=row['scene_block_sha256'], native_owner=row['native_owner'])
            verify_installed_range(original, final, final_offset)
        return

    source_by_key = unique_index(by_file[path], lambda row: row['dc_key'])
    for span in bundle[path]['spans']:
        for line in span['entries']:
            key = line['entry_id']
            original = source_by_key[key]
            identity = (path, original['official_array_index'])
            start, end = line['output_start'], line['output_end']
            length = end - start
            checked_digest(stage_one[start:end], line['output_sha256'], 'bundle stage-one official line')
            start = projection.at(start, length) if projection else start
            install_mtx_entry(entries, identity, key, path, (start, start + length), line['output_sha256'],
                              'exact unique adjacent bundle, anchor order and native control evidence', final_offset,
                              ps4_group_range=[span['ps4_start'], span['ps4_end']],
                              ps2_group_or_cluster_range=[span['ps2_start'], span['ps2_end']])
            verify_installed_range(original, final, final_offset)


def project_inherited(file, prior, final, offset, *projections):
    for row in prior:
        if 'installed_offset' not in row or row.get('installed_asset', file) != file:
            continue
        length = row['installed_length']
        pos = row['installed_offset']
        for projection in projections:
            if projection is not None:
                pos = projection.at(pos, length)
        row.update(installed_asset=file, installed_offset=pos, installed_iso_offset=offset + pos)
        verify_installed_range(row, final, offset)


def mark_reviewed_entries(reviewed, rows):
    expected = {identity for identity, row in rows.items() if row['status'] == SEMANTIC}
    verified = unique_index(reviewed['entries'], lambda row: (row['file'], row['official_array_index']))
    if verified.keys() != expected:
        raise ValueError('reviewed source-specific proof does not cover the inherited entry census')
    for identity, proof in verified.items():
        prior = rows[identity]
        if any(prior[key] != value for key, value in proof.items()
               if key not in ('correspondence_id', 'status', 'proof')):
            raise ValueError(f'inherited installed entry differs from its reviewed proof: {identity}')
        prior.update(status=proof['status'], proof=proof['proof'], correspondence_id=proof['correspondence_id'])


def ksf_inventory(path, raw, offset, labels, japanese, active, noops, output_labels, output_findings):
    for old in labels:
        pos = old['file_offset']
        owner = active.pop((path, pos), None)
        noop = noops.pop((path, pos), None)
        label = {**old, 'iso_offset': offset + pos, 'stock_status': old['status']}
        if owner:
            label.update(status=GUARDED, official_array_index=owner['official_array_index'],
                         dc_key=owner['dc_key'], operative_label_iso_offset=owner['installed_iso_offset'],
                         operative_label_length=owner['installed_length'],
                         operative_label_sha256=owner['installed_bytes_sha256'],
                         operative_owner=owner['installed_asset'], record_ordinal=owner['native_record_ordinal'])
        elif noop:
            label.update(status=r67o_choices.BLANK_STATUS, official_array_index=noop['official_array_index'],
                         dc_key=noop['dc_key'], operative_owner=path)
        else:
            label['operative_owner'] = path
        output_labels.append(label)
        if pos not in japanese:
            continue
        finding = {**japanese[pos], 'iso_offset': offset + pos}
        checked_digest(raw[pos:pos + finding['byte_length']], finding['installed_bytes_sha256'], 'Japanese stock choice bytes')
        if owner:
            finding.update(status=FALLBACK if old['status'] == 'deliberate technical-safety fallback' else STOCK_CHOICE,
                           proof='physical original KSF label retained for stock fallthrough; guarded ELF choice is the verified English owner',
                           official_array_index=owner['official_array_index'], dc_key=owner['dc_key'],
                           operative_label_iso_offset=owner['installed_iso_offset'], operative_owner=owner['installed_asset'])
        output_findings.append(finding)


def mtx_findings(path, raw, offset):
    for start, end, text in japanese_runs(raw, MtxFile.parse(raw).header_size):
        yield {'file': path, 'file_offset': start, 'iso_offset': offset + start,
               'byte_length': end - start, 'text': text,
               'installed_bytes_sha256': digest(raw[start:end]), 'status': UNRESOLVED,
               'proof': 'CP932-aligned body text candidate; render path unverified'}


def generate(baseline_iso, candidate_iso, baseline_inventory, ps2_adv, ps4_adv, output_dir,
             report_paths, bundle_partial, choice_research, choice_supplement, pristine_elf):
    if output_dir.exists() or output_dir.is_symlink():
        raise ValueError(f'choose a fresh inventory output directory: {output_dir}')
    reports = {kind: json.loads(read_pinned(path, PRODUCER_REPORTS[kind])) for kind, path in report_paths.items()}
    prior = read_baseline_inventory(baseline_inventory)
    stages = verified_stage_one(ps2_adv, ps4_adv, baseline_iso, bundle_partial, report_paths, reports)
    bundle = {row['path'].removeprefix('ADV/'): row for row in reports['bundle']['results']}
    kw = reports['kwlnscr']
    speaker_report = reports['speaker']
    speaker_corpus = verify_speaker_corpus(ps4_adv, speaker_report)
    if not (reports['reviewed'] == r67o_reviewed.verify_correspondence(
            baseline_iso, ps2_adv, ps4_adv, baseline_inventory)):
        raise ValueError('reviewed nine-entry proof drift on baseline ISO')

    entries = unique_index(prior['entries.json'], lambda row: (row['file'], row['official_array_index']))
    files, findings, labels, speaker_occurrences = [], [], [], []
    with open_disc(baseline_iso) as old, open_disc(candidate_iso) as new:
        prior_files, prior_entries, prior_findings, prior_labels = verify_baseline(old, ps2_adv, ps4_adv, prior)
        if (new.records.keys() != old.records.keys() or len(new.image) != len(old.image)):
            raise ValueError('candidate does not preserve the complete baseline ADV file census')
        mt_files = {path for path, row in prior_files.items() if row['kind'] == 'MTX'}
        changed_speakers = speaker_report['script_files'].keys()
        unchanged_speakers = speaker_report['unchanged_input_sha256'].keys()
        if (changed_speakers & unchanged_speakers or changed_speakers | unchanged_speakers != mt_files
                or not (stages.keys() | speaker_report['unresolved'].keys()) <= mt_files):
            raise ValueError('speaker provenance does not cover the exact stage-one MTX inventory')

        mark_reviewed_entries(reports['reviewed'], entries)
        changed = stages.keys() | changed_speakers
        elf_hash = verify_final_elf(old, new, changed, reports, report_paths)
        active, noops, held = installed_choices(baseline_iso, baseline_inventory, pristine_elf, ps2_adv, ps4_adv,
                                               choice_research, choice_supplement, old, new, reports['choices'], entries)
        localized = Counter()
        for path, file in prior_files.items():
            _, before = old.asset(path)
            offset, final = new.asset(path)
            installed_proof = 'r67.15n whole-file bytes reverified'
            if file['kind'] == 'MTX':
                stage_one = stages.get(path, before)
                stage_one_positions = apply_stage_one(path, before, stage_one, bundle, kw) if path in stages else None
                stage_two_positions = apply_speaker_stage(path, stage_one, speaker_corpus, speaker_report,
                                                          report_paths['speaker'], final, offset, speaker_occurrences)
                project_inherited(path, prior_entries[path], final, offset, stage_one_positions, stage_two_positions)
                if stage_one_positions:
                    install_stage_one(path, stage_one, final, offset, bundle, kw, stage_two_positions,
                                      prior_entries, entries)
                start = len(findings)
                findings.extend(mtx_findings(path, final, offset))
                measure = 'Japanese lexical candidate spans'
                count = len(findings) - start
                if path in changed:
                    installed_proof = 'byte-for-byte composition of applicable verified MTX stages'
            else:
                if final != before:
                    raise ValueError(f'KSF payload changed despite the executable-only overlay: {path}')
                project_inherited(path, (row for row in prior_entries[path] if row['status'] != GUARDED), final, offset)
                japan = unique_index(prior_findings[path], lambda row: row['file_offset'])
                ksf_inventory(path, final, offset, prior_labels[path], japan, active, noops, labels, findings)
                measure = 'active native choices'
                count = len(prior_labels[path])
                localized[path] = sum(r['status'] == GUARDED for r in prior_entries[path])
                if localized[path]:
                    installed_proof = 'unchanged native KSF; guarded English is installed in SLPM_665.11'
            files.append({**file, 'baseline_sha256': file['installed_sha256'],
                          'iso_offset': offset, 'size': len(final), 'installed_sha256': digest(final),
                          'installed_proof': installed_proof, measure: count,
                          'known_control_only_payload': digest(final) in CONTROL_HASHES if file['kind'] == 'MTX' else False})
        if active or noops:
            raise ValueError('verified choice has no installed native KSF slot')
        iso_hash = digest(new.image)

    cross_file = Counter(row['installed_asset'] for row in entries.values()
                         if row['file'].endswith('.MTX') and row.get('installed_asset', row['file']) != row['file'])
    speaker_by_file = Counter(row['file'] for row in speaker_occurrences)
    for file in files:
        path = file['path']
        file['entry_status_counts'] = dict(Counter(row['status'] for row in prior_entries[path]))
        if file['kind'] == 'MTX':
            file.update(alternate_source_english_entries_owned=cross_file[path],
                        localized_fixed_speaker_occurrences=speaker_by_file[path])
        else:
            file['operative_english_choice_labels'] = localized[path]

    expected_sizes = (3032, 101487, 1136)
    if (len(files), len(entries), len(labels)) != expected_sizes:
        raise ValueError('incomplete installed inventory census')
    speaker_stats = speaker_counts(speaker_report['official_labels'], speaker_occurrences)
    if (speaker_stats['localized_occurrences'] != speaker_report['summary']['occurrences']
            or speaker_stats['affected_files'] != speaker_report['summary']['changed_files']):
        raise ValueError('incomplete fixed speaker occurrence census')
    status_counts = Counter(row['status'] for row in entries.values())
    if (status_counts[PRESENT], status_counts[GUARDED], status_counts[UNRESOLVED],
            status_counts[r67o_choices.BLANK_STATUS], len(held), sum(cross_file.values())) != (98201, 1079, 2203, 4, 6, 148):
        raise ValueError(f'incomplete official disposition census: {status_counts}')

    source_counts = {
        kind: {('missing_same_path_counterpart' if key == 'ps2-only' else key): value
               for key, value in counts.items()}
        for kind, counts in prior['summary.json']['source_counts'].items()
    }
    summary = {**prior['summary.json'], 'schema_version': 1, 'baseline_iso_sha256': BASELINE,
               'source_counts': source_counts,
               'iso_sha256': iso_hash, 'installed_elf_sha256': elf_hash,
               'producer_report_sha256': PRODUCER_REPORTS, 'baseline_inventory_sha256': BASELINE_INVENTORY,
               'complete_ps4_source_inventory_sha256': PS4_SOURCE,
               'files': len(files), 'official_dc_entries': len(entries),
               'installed_native_ksf_labels': len(labels),
               'japanese_text_candidates': len(findings),
               'entry_status_counts': dict(status_counts),
               'finding_status_counts': dict(Counter(row['status'] for row in findings)),
               'official_english_mtx_entries': status_counts[PRESENT],
               'official_mtx_entries_held': sum(row['status'] == UNRESOLVED and row['file'].endswith('.MTX')
                                                for row in entries.values()),
               'new_bundle_entries': reports['bundle']['new_english_entries'],
               'new_alternate_owner_entries': dict(cross_file),
               'reviewed_inherited_entries': len(reports['reviewed']['entries']),
               'guarded_ksf_english': reports['choices']['table'],
               'ksf_held_numbered_source_entries': len(held),
               'fixed_speaker_labels': speaker_stats,
               'pcsx2_runtime_verified': False,
               'limits': [
                   'Every official DC array identity is retained. Synthetic continuation keys may share one source span.',
                   'The alternate MS01_03 owner is KWLNSCR.MTX. The numbered PS2 script retains its source control program.',
                   'Fixed speaker label occurrences use source-proven label identities separate from target scene-entry mappings.',
                   'MTX candidates exclude pointer headers and are CP932-aligned lexical runs. KSF findings come from native active choice slots.',
                   'A Japanese KSF finding may be the stock bytes behind a verified guarded English label. Unknown choices and blank no-ops retain stock behavior.',
                   'An absent corresponding source leaves the correspondence unresolved. File identity alone does not establish shared context.',
                   'This ADV and choice-table inventory establishes static installed ownership. PCSX2 rendering, runtime fallthrough and route reachability remain unobserved.',
               ]}
    output = {'summary.json': summary, 'files.json': files, 'entries.json': list(entries.values()),
              'japanese.json': findings, 'ksf-labels.json': labels,
              'ps4-payload-index.json': prior['ps4-payload-index.json'],
              'speakers.json': {'labels': speaker_report['official_labels'], 'occurrences': speaker_occurrences,
                                'unresolved_roles_by_file': speaker_report['unresolved']}}
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir.parent) as work:
        stage = Path(work) / 'inventory'
        stage.mkdir()
        for name, doc in output.items():
            with (stage / name).open('w', encoding='utf8') as stream:
                stream.write(json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + '\n')
        stage.rename(output_dir)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('baseline-iso', 'candidate-iso', 'baseline-inventory', 'ps2-adv', 'ps4-adv', 'output-dir',
                   *[kind + '-report' for kind in PRODUCER_REPORTS]):
        parser.add_argument('--' + option, required=True, type=Path)
    for option in ('bundle-partial-report', 'choice-research', 'choice-supplement', 'pristine-elf'):
        parser.add_argument('--' + option, type=Path)
    args = parser.parse_args()
    root = args.baseline_inventory.parent
    paths = {kind: getattr(args, kind + '_report') for kind in PRODUCER_REPORTS}
    summary = generate(
        args.baseline_iso, args.candidate_iso, args.baseline_inventory, args.ps2_adv, args.ps4_adv, args.output_dir,
        paths, args.bundle_partial_report or root / 'r67n-partial/report.json',
        args.choice_research or root / 'r67o-research/ksf-design-evidence.json',
        args.choice_supplement or root / 'r67o-choice-correspondence/report.json',
        args.pristine_elf or args.ps2_adv.parents[1] / 'SLPM_665.11')
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
