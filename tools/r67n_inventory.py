"""Inventory native ADV scripts, official keys, and Japanese text candidates on a disc."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import replace
import hashlib
import json
import mmap
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from tools.corpus import scan_corpus
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.localization import DcLocalization, encode_ps2_english
from tools.mtx import MtxFile, MtxReplacement
from tools.r67_15g_route_audit import DATA_CVM_HEADER_SIZE, UNCHANGED_MTX
from tools.r67n_ksf import FALLBACK, digest, native_slots
from tools.r67n_ksf_structural import transfer

SOURCE_INVENTORY = '1ab214641ae7906e7f4afc3eb6ccca53ad14116390baeaaf214e98e9687633db'
JAPANESE = re.compile('[ぁ-ゖァ-ヺ一-鿿㐀-䶿ｦ-ﾝ]')
MISSING = 'missing counterpart; correspondence unresolved'
UNRESOLVED = 'correspondence unresolved'
NOT_INSTALLED = 'official English available; not installed'
PRESENT = 'official English installed'
SEMANTIC = 'historical English installed; semantic-cluster correspondence requires review'
LEGACY_NAME = 'official English installed with historical literal name placeholder'
CONTROL_HASHES = {r['sha256'] for r in UNCHANGED_MTX.values() if r['classification'] == 'control_only'}


def relation_name(row):
    return MISSING if row['ps4'] is None else row['relation']


def japanese_runs(raw, start):
    """Search CP932-aligned runs only. ASCII commands and invalid pairs delimit candidates."""
    for match in re.finditer(rb'(?:[\x81-\x9f\xe0-\xfc][\x40-\x7e\x80-\xfc]|[\xa1-\xdf])+|[\x81-\x9f\xe0-\xfc].?', raw[start:], re.DOTALL):
        data = match.group()
        try:
            text = data.decode('cp932')
        except UnicodeDecodeError:
            # Undefined two-byte characters delimit a span. Do not resynchronize on
            # a trail byte that merely resembles an ASCII command or another lead.
            cursor = 0
            while cursor < len(data):
                try:
                    part = data[cursor:].decode('cp932')
                    end = len(data)
                    next_at = end
                except UnicodeDecodeError as error:
                    end = cursor + error.start
                    part = data[cursor:end].decode('cp932')
                    next_at = min(len(data), end + 2)
                if JAPANESE.search(part):
                    yield start + match.start() + cursor, start + match.start() + end, part
                cursor = next_at
            continue
        if JAPANESE.search(text):
            yield start + match.start(), start + match.end(), text


def physical_labels(raw):
    for key, (index, start, choice) in native_slots(raw).items():
        payload = raw[key:key + 30]
        yield key, index, start, choice, payload.split(b'\0')[0], b'\0' in payload


def groups_for(raw, dc):
    # Geometry uses original key order and synthetic-key checks. Text is encoded
    # separately so a rejected dynamic placeholder cannot hide the other keys.
    groups = DcLocalization.from_json(raw, {'keys': dc['keys'], 'values': [''] * len(dc['keys'])}).groups
    values = dict(zip(dc['keys'], dc['values'], strict=True))
    return [replace(g, lines=tuple(values[k] for k in (g.anchor, *g.synthetic_keys))) for g in groups]


def replay(ps2, ps4, dc, installed, spans=None):
    groups = groups_for(ps4, dc)
    if spans is None:
        spans = [dict(first_group=i, last_group=i, ps2_start=g.anchor, ps2_end=g.replace_end, mode='exact')
                 for i, g in enumerate(groups)]
    source = MtxFile.parse(ps2)
    source_starts = sorted(set(source.pointer_offsets) - {0})
    for legacy in (False, True):
        changes, contents = [], []
        for span in sorted(spans, key=lambda s: s['ps2_start']):
            selected = groups[span['first_group']:span['last_group'] + 1]
            lines = []
            for g in selected:
                for key, line in zip((g.anchor, *g.synthetic_keys), g.lines, strict=True):
                    encoded = encode_ps2_english(line) if legacy else replace(g, lines=(line,)).encoded_replacement()
                    lines.append((key, encoded, g.anchor, g.replace_end, line))
            data = b'r'.join(line[1] for line in lines)
            changes.append(MtxReplacement(span['ps2_start'], span['ps2_end'], data))
            contents.append((span, lines))
        result = source.apply_replacements(tuple(changes))
        if result.compile() != installed:
            continue
        starts = sorted(set(result.pointer_offsets) - {0})
        moved = Counter()
        entries = {}
        for change, (span, lines) in zip(changes, contents, strict=True):
            region = bisect_right(source_starts, change.start) - 1
            pos = starts[region] + change.start - source_starts[region] + moved[region]
            for key, data, ps4_start, ps4_end, text in lines:
                if installed[pos:pos + len(data)] != data:
                    raise ValueError('installed offsets differ from complete MTX replay')
                status = PRESENT
                if span['mode'] == 'semantic-cluster':
                    status = SEMANTIC
                elif legacy and re.search(r'\(p[a-z0-9_]+\)', text):
                    status = LEGACY_NAME
                entries[key] = {'status': status, 'proof': f"whole payload replay/{span['mode']}",
                                'ps4_group_range':[ps4_start, ps4_end], 'ps2_group_or_cluster_range':[change.start, change.end],
                                'installed_offset':pos, 'installed_length':len(data), 'installed_bytes_sha256':digest(data)}
                pos += len(data) + 1
            moved[region] += len(change.data) - (change.end - change.start)
        if set(entries) != set(dc['keys']):
            raise ValueError('complete replay did not cover all original DC keys')
        return entries
    raise ValueError('installed bytes differ from both complete MTX replays')


def exact_evidence(source, counterpart, dc, installed):
    if source != counterpart:
        raise ValueError('nonidentical exact MTX source')
    return replay(source, counterpart, dc, installed)


def checked_row(report, source, counterpart, dc_digest, installed, allowed):
    if (report['ps2_sha256'] != digest(source) or report['ps4_sha256'] != digest(counterpart)
            or dc_digest not in allowed or digest(installed) not in {report.get(k) for k in
                        ('output_sha256','installed_sha256','before_sha256','after_sha256','ps2_sha256')}):
        raise ValueError(f'source, map or installed payload drift: {report.get("path")}')


def ksf_evidence(source, counterpart, dc_digest, installed, report):
    checked_row(report, source, counterpart, dc_digest, installed, {report['map_sha256']})
    final = report['after_sha256'] == digest(installed)
    if not final and report['before_sha256'] != digest(installed):
        raise ValueError('unexpected installed KSF hash')
    slots = native_slots(source)
    out = {}
    for item in report['rows']:
        key = item['key']
        payload = installed[key:key+30]
        expected = item['after_payload_sha256'] if final else item['before_payload_sha256']
        if key not in slots or digest(payload) != expected:
            raise ValueError('installed KSF row differs from verified native span')
        cls = item['classification']
        if cls == FALLBACK and not final:
            cls = 'inherited malformed choice; safety repair absent'
        elif cls.startswith('original retained'):
            cls = NOT_INSTALLED
        elif cls.startswith('inherited official'):
            cls = PRESENT
        out[key] = {'status': cls, 'proof':'native slot and verified whole-file hash',
                    'ps2_group_or_cluster_range':[key,key+30], 'installed_offset':key,
                    'installed_length':30, 'installed_bytes_sha256':digest(payload)}
    return out


def report_by_path(path, key):
    if path is None:
        return {}
    doc = json.loads(path.read_bytes())
    return {row['path']:row for row in doc[key]}


def expected_sources(ps2_adv, ps4_adv):
    corpus = scan_corpus(ps2_adv, ps4_adv)
    manifest = hashlib.sha256()
    for row in corpus['assets']:
        dc = (ps4_adv / row['english_map']).read_bytes() if row['english_map'] else None
        row['dc_sha256'] = digest(dc) if dc is not None else None
        values = (row['path'], row['ps2']['sha256'], (row['ps4'] or {}).get('sha256','-'), row['dc_sha256'] or '-')
        manifest.update((' '.join(values) + '\n').encode())
    if manifest.hexdigest() != SOURCE_INVENTORY:
        raise ValueError('PS2, PS4 or official map inventory differs from measured source hashes')
    return corpus


def partial_evidence(row, source, counterpart, dc, installed, raw_dc_hash):
    if (row['ps2_sha256'] != digest(source) or row['ps4_sha256'] != digest(counterpart)
            or raw_dc_hash != row.get('official_map_sha256', row.get('map_sha256',row.get('raw_dc_sha256')))):
        raise ValueError(f'partial source/map drift: {row.get("path")}')
    if digest(installed) != row['output_sha256']:
        if installed == source:
            return {}
        raise ValueError('partial installed payload differs from verified output')
    entries = {}
    for span in row['spans']:
        start, end = span['ps2_start'], span['ps2_end']
        p4, e4 = span['ps4_start'], span['ps4_end']
        if (source[start:end] != counterpart[p4:e4] or digest(source[start:end]) != span['original_sha256']
                or digest(installed[span['output_start']:span['output_end']]) != span['replacement_sha256']):
            raise ValueError('partial correspondence or replacement bytes differ')
        for line in span['entries']:
            pos, end = line['output_start'], line['output_end']
            if not (span['output_start'] <= pos <= end <= span['output_end']) or digest(installed[pos:end]) != line['sha256']:
                raise ValueError('partial entry output does not match installed line')
            entries[line['entry_id']] = {'status':PRESENT,'proof':'source-checked partial correspondence and installed span',
                    'ps4_group_range':[p4,e4], 'ps2_group_or_cluster_range':[start,span['ps2_end']],
                    'installed_offset':pos,'installed_length':end-pos,'installed_bytes_sha256':line['sha256']}
    for rejected in row['unresolved']:
        for key in rejected['entry_ids']:
            entries[key] = {'status':UNRESOLVED, 'proof':rejected['reason'],
                'ps4_group_range':[rejected['ps4_start'],rejected['ps4_end']],
                'candidate_ps2_ranges':rejected.get('ps2_candidates',[])}
    if set(entries) != set(dc['keys']):
        raise ValueError('partial proof does not account for all DC keys')
    return entries


def scan_assets(iso, ps2_adv, ps4_adv, ksf, structural, names, partial, structural_ksf):
    corpus = expected_sources(ps2_adv, ps4_adv)
    files, entries, findings, labels = [], [], [], []
    ps4_peers = defaultdict(list)
    for item in corpus['assets']:
        if item['ps4']:
            ps4_peers[(item['kind'],item['ps4']['sha256'])].append(item['path'])
    with iso.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        volume = index_iso(image)[1]
        nested = find_record(volume,'DATA.CVM').extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        records = {r.path:r for r in index_iso(image,nested)[1]}
        iso_hash = hashlib.sha256(image).hexdigest()
        for row in corpus['assets']:
            rel = row['path']
            path = 'ADV/' + rel
            source = (ps2_adv / rel).read_bytes()
            counterpart = (ps4_adv / rel).read_bytes() if row['ps4'] else None
            dc = json.loads((ps4_adv / row['english_map']).read_bytes()) if row['english_map'] else {'keys':[], 'values':[]}
            record = records[path]
            offset = nested + record.extent * SECTOR_SIZE
            binary = image[offset:offset + record.size]
            before, installed = digest(source), digest(binary)
            evidence = {}
            mode = 'pristine bytes'
            if row['kind'] == 'KSF' and rel in ksf:
                evidence = ksf_evidence(source,counterpart,row['dc_sha256'],binary,ksf[rel])
                mode = 'KSF baseline or safety overlay verified'
            elif rel in structural_ksf:
                proof = structural_ksf[rel]
                checked_row(proof,source,counterpart,row['dc_sha256'],binary,{proof['map_sha256']})
                computed, structural_rows = transfer(source,counterpart,dc,source)
                if digest(computed) != proof['after_sha256'] or structural_rows != proof['rows']:
                    raise ValueError(f'structural KSF evidence differs from source replay: {rel}')
                if binary != computed and binary != source:
                    raise ValueError(f'unknown installed structural KSF state: {rel}')
                for item in structural_rows:
                    key = item['key']
                    status = item['status']
                    if status == 'record mismatch':
                        evidence[key] = {'status':UNRESOLVED, 'proof':'same-ordinal complete record does not match',
                                         'ps4_group_range':[key,key+30]}
                        continue
                    dest = item['ps2_key']
                    evidence[key] = {'status':PRESENT if status == 'installed' and binary == computed else NOT_INSTALLED,
                                     'proof':f'same ordinal, choice and complete native record/{status}',
                                     'ps4_group_range':[key,key+30], 'ps2_group_or_cluster_range':[dest,dest+30],
                                     'installed_offset':dest,'installed_length':30,'installed_bytes_sha256':digest(binary[dest:dest+30])}
                mode = 'same ordinal, choice and complete KSF record replay'
            elif rel in partial and partial[rel]['output_sha256'] == installed:
                evidence = partial_evidence(partial[rel],source,counterpart,dc,binary,row['dc_sha256'])
                mode = 'source-checked partial producer evidence'
            elif row['kind'] == 'MTX' and row['relation'] == 'exact' and dc['keys'] and binary != source:
                evidence = exact_evidence(source,counterpart,dc,binary)
                mode = 'exact complete native/legacy replay'
                if path in names:
                    report = names[path]
                    checked_row(report,source,counterpart,row['dc_sha256'],binary,{report['dc_sha256']})
            elif row['kind'] == 'MTX' and binary != source and rel in structural:
                accepted = {installed}
                name_row = names.get(path)
                if name_row and name_row.get('output_sha256') == installed:
                    checked_row(name_row,source,counterpart,row['dc_sha256'],binary,{name_row['dc_sha256']})
                    accepted.add(name_row['installed_sha256'])
                history = next((r for r in structural[rel] if r.get('output_sha256') in accepted), None)
                if history is None:
                    raise ValueError(f'unrecognized installed structural hash: {rel}')
                evidence = replay(source,counterpart,dc,binary,history['spans'])
                mode = 'pinned historical structural output and whole-file replay'
            elif binary != source:
                raise ValueError(f'changed installed payload lacks a recognized producer: {rel}')
            name_row = names.get(path)
            if name_row and name_row.get('output_sha256') == installed and name_row.get('groups'):
                for group in name_row['groups']:
                    for line in group['lines']:
                        key = line['dc_key']
                        if key not in evidence or evidence[key].get('installed_offset') != line['output_offset']:
                            raise ValueError(f'name and independent replay disagree on installed offset: {rel}:{key}')
            ordinary_exact_map = (row['relation'] == 'exact' and len(set(dc['keys'])) == len(dc['keys'])
                                  and all(0 <= key < len(source) for key in dc['keys']))
            file_entries = []
            for index,(key,text) in enumerate(zip(dc['keys'],dc['values'],strict=True)):
                default = NOT_INSTALLED if ordinary_exact_map else UNRESOLVED
                item = evidence.get(key, {'status':default,'proof': 'unchanged source bytes; exact DC key' if default == NOT_INSTALLED else 'PS4 map key has no verified PS2 association'})
                entry = {'file':rel, 'official_array_index':index, 'dc_key':key,
                         'official_text_utf8_sha256':digest(text.encode()), **item}
                if 'installed_offset' in entry:
                    entry['installed_iso_offset'] = offset + entry['installed_offset']
                entries.append(entry)
                file_entries.append(entry)
            if row['kind'] == 'KSF':
                if native_slots(source) != native_slots(binary):
                    raise ValueError(f'installed KSF choice topology changed: {rel}')
                physical_evidence = {e['installed_offset']:e for e in evidence.values() if 'installed_offset' in e}
                for key,index,start,choice,content,terminated in physical_labels(binary):
                    txt = content.decode('cp932',errors='replace')
                    evidence_row = physical_evidence.get(key, {})
                    label = {'file':rel,'record':index,'record_offset':start,'choice':choice,'file_offset':key,
                             'iso_offset':offset+key,'pristine_payload_sha256':digest(source[key:key+30]),
                             'installed_payload_sha256':digest(binary[key:key+30]),'has_inline_nul':terminated,
                             'status':evidence_row.get('status',UNRESOLVED)}
                    labels.append(label)
                    if JAPANESE.search(txt):
                        findings.append({'file':rel,'file_offset':key,'iso_offset':offset+key,'byte_length':len(content),
                                         'text':txt,'installed_bytes_sha256':digest(content),'proof':'active native choice; runtime reachability untested',
                                         'status':evidence_row.get('status',UNRESOLVED)})
                control_only = False
                run_count = sum(1 for _ in native_slots(binary))
                measure = 'active native choices'
            else:
                mtx = MtxFile.parse(binary)
                runs = list(japanese_runs(binary,mtx.header_size))
                for start,end,txt in runs:
                    status = UNRESOLVED
                    proof = 'CP932-aligned body text candidate; render path unverified'
                    if binary == source and ordinary_exact_map and start in dc['keys']:
                        status = NOT_INSTALLED
                        proof = 'exact official DC anchor starts at this unchanged CP932 body candidate'
                    findings.append({'file':rel,'file_offset':start,'iso_offset':offset+start,'byte_length':end-start,
                                     'text':txt,'installed_bytes_sha256':digest(binary[start:end]),'proof':proof,'status':status})
                control_only = installed in CONTROL_HASHES
                run_count = len(runs)
                measure = 'Japanese lexical candidate spans'
            files.append({'path':rel,'kind':row['kind'],'relation':relation_name(row),
                          'ps2_sha256':before,'ps2_size':len(source),'ps4':row['ps4'],'map_path':row['english_map'],
                          'other_byte_identical_ps4_paths':sum(p != rel for p in ps4_peers.get((row['kind'],before),())),
                          'map_sha256':row['dc_sha256'],'official_entries':len(dc['keys']), 'iso_record':path,
                          'iso_offset':offset,'size':len(binary),'installed_sha256':installed,
                          'installed_proof':mode,'entry_status_counts':dict(Counter(e['status'] for e in file_entries)),
                          'known_control_only_payload':control_only,'unique_official_keys':len(set(dc['keys'])),measure:run_count})
    mapped_mtx = {r['ps4']['sha256'] for r in corpus['assets'] if r['kind']=='MTX' and r['english_map']}
    no_mtx_map = [r for r in corpus['assets'] if r['kind']=='MTX' and not r['english_map']]
    alias_audit = {'ps2_mtx_without_same_path_map':len(no_mtx_map),
                   'ps4_mtx_with_map':corpus['summary']['MTX']['mapped'],
                   'ps2_mtx_with_byte_identical_alternate_mapped_ps4_file':sum(r['ps2']['sha256'] in mapped_mtx for r in no_mtx_map)}
    summary = {'whole_file_alias_audit':alias_audit,'iso_sha256':iso_hash,'source_inventory_sha256':SOURCE_INVENTORY,
               'source_counts':corpus['summary'],'files':len(files),'official_dc_entries':len(entries),
               'installed_native_ksf_labels':len(labels),'japanese_text_candidates':len(findings),
               'entry_status_counts':dict(Counter(e['status'] for e in entries)),
               'finding_status_counts':dict(Counter(e['status'] for e in findings)),
               'file_relation_counts':dict(Counter(f['relation'] for f in files)),
               'limits':['Each DC key is an official map entry. Synthetic continuation keys belong to shared source spans.',
                         'Lexical MTX candidates may be names, punctuation, labels, commands with text operands, or dialogue. Runtime display and route reachability remain untested.',
                         'KSF candidates come only from active native choice slots. Packed binary data and MTX pointer headers are excluded.',
                         'Known all-control MTX payloads use positively identified complete hashes. Missing same-path counterparts leave correspondence unresolved.',
                         'The PS4 payload index lists same-kind byte-identical files by SHA-256. Shared data alone does not establish shared display context.',
                         'ADV-only inventory. ELF tables, graphics, fonts, audio, and save data are outside the scanned trees.']}
    return {'summary.json':summary,'files.json':files,'entries.json':entries,'japanese.json':findings,'ksf-labels.json':labels,
            'ps4-payload-index.json':{kind+':'+sha:paths for (kind,sha),paths in ps4_peers.items()}}


def generate(iso,ps2_adv,ps4_adv,output,ksf_report,structural_reports,names_report=None,partial_report=None,structural_ksf_report=None):
    if output.exists():
        raise ValueError(f'choose a fresh inventory output path: {output}')
    structural = defaultdict(list)
    for path in structural_reports:
        for rel,item in report_by_path(path,'results').items():
            if item.get('status') == 'imported':
                structural[rel].append(item)
    partial = {} if partial_report is None else report_by_path(partial_report,'results')
    partial = {k.removeprefix('ADV/'):v for k,v in partial.items()}
    bundle = scan_assets(iso,ps2_adv,ps4_adv,report_by_path(ksf_report,'files'),structural,
                         report_by_path(names_report,'assets'),partial,report_by_path(structural_ksf_report,'files'))
    bundle['summary.json']['producer_report_sha256'] = {str(path):digest(path.read_bytes()) for path in
                                   (*structural_reports,ksf_report,names_report,partial_report,structural_ksf_report) if path is not None}
    output.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp)/'inventory'
        stage.mkdir()
        for name, doc in bundle.items():
            (stage/name).write_text(json.dumps(doc,ensure_ascii=False,separators=(',',':'))+'\n')
        stage.rename(output)
    return bundle['summary.json']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso','ps2-adv','ps4-adv','output','ksf-report','names-report','partial-report','structural-ksf-report'):
        parser.add_argument('--'+name,type=Path,required=name not in ('partial-report','names-report','structural-ksf-report'))
    parser.add_argument('--structural-report',type=Path,action='append',required=True)
    args = parser.parse_args()
    print(json.dumps(generate(args.iso,args.ps2_adv,args.ps4_adv,args.output,args.ksf_report,
                              args.structural_report,args.names_report,args.partial_report,args.structural_ksf_report),sort_keys=True))
