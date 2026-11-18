"""Transfer bounded KSF choices from identical full records at the same ordinal."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from tools.corpus import scan_corpus
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.r67_15g_route_audit import DATA_CVM_HEADER_SIZE
from tools.r67n_ksf import PAYLOAD, digest, native_slots, verify_native_reader

SOURCE_INVENTORY = '9d3f6c5d9faa620f26b9da32438901c9ec223e268156b2866d717477d23f3425'


def record_choices(raw):
    slots = native_slots(raw)
    active = Counter(index for index, _, _ in slots.values())
    return {key: (index, choice, start, start + 0x910 + PAYLOAD * active[index])
            for key, (index, start, choice) in slots.items()}


def transfer(ps2, ps4, dc, installed):
    if installed != ps2:
        raise ValueError('installed structural KSF must equal the original PS2 file')
    if ps2 == ps4:
        raise ValueError('structural transfer requires distinct PS2 and PS4 files')
    ps4_slots = record_choices(ps4)
    ps2_slots = record_choices(ps2)
    choices = {(idx, choice): (key,start,end) for key,(idx,choice,start,end) in ps2_slots.items()}
    keys, values = dc['keys'], dc['values']
    if len(keys) != len(values) or len(set(keys)) != len(keys):
        raise ValueError('invalid or duplicate KSF DC keys')
    out = bytearray(ps2)
    rows = []
    for index, (key, value) in enumerate(zip(keys, values, strict=True)):
        if type(key) is not int or key not in ps4_slots or not isinstance(value, str):
            raise ValueError('DC key must select an active native PS4 label')
        ordinal, choice, start, end = ps4_slots[key]
        record4 = ps4[start:end]
        pair = choices.get((ordinal,choice))
        row = {'official_array_index':index, 'key':key, 'record_ordinal':ordinal, 'choice_index':choice,
               'ps4_record_range':[start,end], 'ps4_record_sha256':digest(record4),
               'official_utf8_sha256':digest(value.encode()), 'status':'record mismatch'}
        if pair is not None:
            dest, a, b = pair
            row.update(ps2_key=dest,ps2_record_range=[a,b],ps2_record_sha256=digest(ps2[a:b]),
                       before_payload_sha256=digest(ps2[dest:dest+PAYLOAD]))
            if ps2[a:b] == record4:
                if key-start != dest-a or b'\0' not in ps2[dest:dest+PAYLOAD]:
                    raise ValueError('unterminated source choice or inconsistent relative key')
                normalized = re.sub(r' +',' ',value)
                if (not normalized or not normalized.isascii() or not normalized.isprintable()):
                    row['status'] = 'unsupported encoding'
                elif len(normalized) >= PAYLOAD:
                    row['status'] = 'overflow'
                else:
                    out[dest:dest+PAYLOAD] = normalized.encode('ascii').ljust(PAYLOAD,b'\0')
                    row['status'] = 'installed'
                row['normalized_bytes'] = len(normalized.encode('cp932'))
            row['after_payload_sha256'] = digest(out[dest:dest+PAYLOAD])
        rows.append(row)
    mask = out.copy()
    for row in rows:
        if row['status'] == 'installed':
            key = row['ps2_key']
            mask[key:key+PAYLOAD] = ps2[key:key+PAYLOAD]
    if bytes(mask) != ps2 or native_slots(bytes(out)) != native_slots(ps2):
        raise ValueError('KSF transfer altered a structural byte or native control')
    return bytes(out),rows


def generate(ps2_adv:Path, ps4_adv:Path, iso:Path, target:Path):
    if target.exists():
        raise ValueError('choose a fresh output directory')
    sources,files,overlay = [],[],{}
    with iso.open('rb') as stream, mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as image:
        outer = index_iso(image)[1]
        elf = find_record(outer,'SLPM_665.11')
        start = elf.extent * SECTOR_SIZE
        verify_native_reader(image[start:start+elf.size])
        nested = find_record(outer,'DATA.CVM').extent*SECTOR_SIZE+DATA_CVM_HEADER_SIZE
        records = {r.path:r for r in index_iso(image,nested)[1]}
        for asset in scan_corpus(ps2_adv,ps4_adv)['assets']:
            if asset['kind'] != 'KSF' or not asset['english_map'] or asset['relation'] == 'exact':
                continue
            path = asset['path']
            a,b = (ps2_adv/path).read_bytes(),(ps4_adv/path).read_bytes()
            dc = (ps4_adv/asset['english_map']).read_bytes()
            sources.append(f'{path} {digest(a)} {digest(b)} {digest(dc)}\n')
            record = records['ADV/'+path]
            start = nested + record.extent*SECTOR_SIZE
            installed = image[start:start+record.size]
            out,rows = transfer(a,b,json.loads(dc),installed)
            files.append({'path':path,'ps2_sha256':digest(a),'ps4_sha256':digest(b),'map_sha256':digest(dc),
                          'before_sha256':digest(installed),'after_sha256':digest(out),'rows':rows})
            if out != installed:
                overlay[path] = out
    if digest(''.join(sources).encode()) != SOURCE_INVENTORY:
        raise ValueError('structural KSF source/map inventory differs from verified inputs')
    counts = Counter(r['status'] for f in files for r in f['rows'])
    report = {'files_audited':len(files),'files_changed':len(overlay),'status_counts':dict(counts),
              'source_inventory_sha256':SOURCE_INVENTORY,'files':files}
    target.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as tmp:
        stage = Path(tmp)/'bundle'
        (stage/'overlay').mkdir(parents=True)
        for path,data in overlay.items():
            dest=stage/'overlay'/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(data)
        (stage/'report.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
        stage.rename(target)
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('ps2-adv','ps4-adv','installed-iso','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=generate(args.ps2_adv,args.ps4_adv,args.installed_iso,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='files'},sort_keys=True))
