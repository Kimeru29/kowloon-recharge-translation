"""Preserve raw startup results; explicitly validate bounded y save reflow.

The old gate requires exact legacy wording (including the overflowing line).
Only memory-card entries 8/9/18 may use the deterministically rebuilt y text.
No q/t/history lock is weakened and no raw failure is silently suppressed.
"""
import json
import mmap
import struct
import unicodedata
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_14y_release import ROOT,OUTPUT,PREFIX,payloads,verify_save_identity
from tools.startup_acceptance import verify_startup_candidate
from tools.r67_history_layout_lock import verify_bytes,read_lock


def verify_message(elf, expected, index):
    offset = 0x407440 + index*4
    ptr = struct.unpack_from('<I',elf,offset)[0]
    wanted = struct.unpack_from('<I',expected,offset)[0]
    actual = read_string(elf,ptr)
    if ptr != wanted or actual != read_string(expected,wanted):
        raise ValueError(f'bounded save message {index} differs from y source')
    lines = [unicodedata.normalize('NFKC',s) for s in actual.decode('cp932').split('＠改行')]
    if len(lines) > 6 or any(len(s)>21 or not s.isascii() for s in lines):
        raise ValueError(f'bounded save message {index} exceeds native layout')
    return dict(index=index,lines=lines,max_cells=max(map(len,lines)),
        row_count=len(lines),exact_reproducible_y_payload=True)


def scoped_startup(raw_report, elf, expected):
    allowed = {f'memory_card_{i}':i for i in (8,9,18)}
    result = dict(raw_report)
    result['checks'] = [dict(c) for c in raw_report['checks']]
    exceptions = []
    for check in result['checks']:
        if check['ok']:
            continue
        if check['name'] not in allowed:
            raise ValueError(f'unexpected startup regression: {check["name"]}')
        evidence = verify_message(elf,expected,allowed[check['name']])
        exceptions.append(dict(name=check['name'],legacy_detail=check['detail'],
            reason='intentional bounded English reflow replaces overflowing legacy wording',
            evidence=evidence))
        check.update(ok=True,detail='PASS exact y bounded reflow; explicit legacy wording exception')
    result.update(checks_passed=sum(c['ok'] for c in result['checks']),
        raw_checks_passed=raw_report['checks_passed'],
        explicit_legacy_wording_exceptions=exceptions,
        q_t_lock_exceptions=[],runtime_verified=False)
    return result


def main():
    suffixes = ('-startup-raw.json','-startup.json','-history.json','-save-static.json')
    paths = [Path(str(PREFIX)+s) for s in suffixes]
    for p in paths:
        if p.exists():
            raise FileExistsError(p)
    raw = verify_startup_candidate(OUTPUT,ROOT.parent/'startup-flow-v10/local/startup-graphics')
    with OUTPUT.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as b:
        _,records = index_iso(b)
        e = find_record(records,'SLPM_665.11')
        elf = bytes(b[e.extent*2048:e.extent*2048+e.size])
    expected,_ = payloads()
    scoped = scoped_startup(raw,elf,expected)
    history = dict(verified_regions=verify_bytes(elf,read_lock()),runtime_verified=False)
    save = verify_save_identity(elf)
    save.update(status='STATIC_ONLY_NO_GOLDEN_CHECKPOINT',
        message_bounds=[verify_message(elf,expected,i) for i in (8,9,18)],
        original_cards_and_savestates_not_modified=True,
        cross_release_runtime_test_performed=False)
    for path,data in zip(paths,(raw,scoped,history,save),strict=True):
        with path.open('x') as f:
            json.dump(data,f,indent=2,sort_keys=True)
            f.write('\n')
    print(json.dumps(dict(raw_startup=f'{raw["checks_passed"]}/{raw["checks_total"]}',
        scoped_startup=f'{scoped["checks_passed"]}/{scoped["checks_total"]}',
        explicit_exceptions=[x['name'] for x in scoped['explicit_legacy_wording_exceptions']],
        history_regions=len(history['verified_regions']),save_runtime_verified=False)))


if __name__ == '__main__':
    main()
