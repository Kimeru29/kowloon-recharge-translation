"""Reproducible diagnostic build and exhaustive x-to-y finished-ISO audit.

No earlier output is overwritten. The last outer file (ELF) may grow only
into verified unallocated zero sectors inside the existing volume. Installed
ROFS metadata is preserved from the SHA-pinned x baseline, not staged ELF.
"""
from __future__ import annotations
import hashlib
import json
import mmap
import shutil
import struct
import subprocess
from collections import Counter
from pathlib import Path
from tools.iso9660_patch import index_iso, find_record, patch_directory_record
from tools.r67_14y_event_lifecycle import apply as event_apply
from tools.r67_14y_save_atlas import apply as atlas_apply
from tools.r67_14q_approved_lock import verify_approved, MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui, MANIFEST as T
from tools.r67_lion_statue_iso_patch import sha_file

ROOT = Path(__file__).resolve().parents[1]
X_ISO = ROOT/'local/r67-candidates/67.14x-generic-companion-bubble.iso'
X_SHA = '5ea1fa67d972b00ab499f0ac27bbc4308f51cd11a929b3fdd6741f9f9ee79a13'
X_INSTALLED_SHA = 'd5a3c8756593b447147c6c8da47a94ac4d5addd699e8399b840d43d5d09ccaa5'
X_STAGE_SHA = '20dde0425125af1b4729b6ecd0dacbb77e63d9f70c33bcf3558f2d9a46e7bd44'
OUTPUT = ROOT/'local/r67-candidates/67.14y-event-lifecycle-inspection-save.iso'
PREFIX = ROOT/'local/r67-14y'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_save_identity(elf):
    name = b'BISLPM-66511Save'
    offsets = (0x406771,0x406791,0x4067B1,0x4067D1,0x4067E2,
        0x406801,0x406812,0x406831,0x406842,0x406861,0x406872,
        0x406891,0x4068A2,0x4068C1,0x4068D2)
    digest = sha(b''.join(elf[p-1:p+len(name)+64] for p in offsets))
    if (digest != '27e5830aedec88451070b350897733f043dd11fef38fdab27a1dc9dd5cd5294f'
            or elf.count(name) != 15 or b'SLPM-66511' not in elf):
        raise ValueError('native save namespace/descriptors changed')
    return dict(native_save_descriptors=15,descriptor_windows_sha256=digest,
        serial='SLPM-66511',save_namespace=name.decode(),
        runtime_verified=False,golden_checkpoint_available=False)


def preserve_installed_metadata(old_stage, old_installed, new_stage):
    if len(old_stage) != len(old_installed) or len(new_stage) < len(old_stage):
        raise ValueError('ELF baseline length mismatch')
    out = bytearray(new_stage)
    preserved = []
    for i,(a,b) in enumerate(zip(old_stage,old_installed)):
        if a != b:
            if new_stage[i] != a:
                raise ValueError(f'patch collides with installed metadata at {i:#x}')
            out[i] = b
            preserved.append(i)
    return bytes(out), preserved


def check_growth(image, entry, records, length):
    start = entry.extent*2048
    end = start + ((length+2047)//2048)*2048
    if length < entry.size or end > len(image):
        raise ValueError('executable growth outside existing volume')
    for other in records:
        if other == entry:
            continue
        a, b = other.extent*2048, (other.extent+other.sectors)*2048
        if a < end and b > start:
            raise ValueError('executable growth overlaps another ISO record')
    if any(image[start+entry.size:end]):
        raise ValueError('executable growth would overwrite nonzero sector data')


def payloads():
    from tools.r67_14y_inspection_save import apply as text_apply
    source = (ROOT/'local/r67-14t-lion-and-tablets.elf').read_bytes()
    event, event_report = event_apply(source)
    result, text_report = text_apply(event)
    allowed_native = {i for a in (0x65EE0,0x668A0) for i in range(a,a+4)}
    native_diffs = [i for i in range(0x80,0x330000) if source[i] != result[i]]
    if set(native_diffs) - allowed_native:
        raise ValueError('unapproved native executable instruction mutation')
    # Both manifests are immutable and verified WITHOUT masking exceptions.
    q = verify_approved(result,json.loads(Q.read_text()))
    t = verify_ui(result,json.loads(T.read_text()))
    return result, dict(event=event_report,inspection_save=text_report,q_lock=q,t_lock=t,
        save_identity=verify_save_identity(result),
        native_code_audit=dict(file_range=['0x80','0x330000'],
            changed_offsets=list(map(hex,native_diffs)),
            only_two_ordinary_event_callsites_changed=True,
            native_save_routines_and_serialization_unchanged=True))


def prepare(image, staged):
    _, records = index_iso(image)
    entry = find_record(records,'SLPM_665.11')
    base = entry.extent*2048
    installed = bytes(image[base:base+entry.size])
    old_stage = (ROOT/'local/r67-14x-generic-event-bubble.elf').read_bytes()
    if sha(installed) != X_INSTALLED_SHA or sha(old_stage) != X_STAGE_SHA:
        raise ValueError('x ELF preimage drift')
    new, preserved = preserve_installed_metadata(old_stage,installed,staged)
    check_growth(image,entry,records,len(new))
    cvm = find_record(records,'DATA.CVM')
    cvm_base = cvm.extent*2048+0x1800
    _, inner = index_iso(image,cvm_base)
    atlas = find_record(inner,'BLBRD/B_GP018.BIN')
    atlas_base = cvm_base+atlas.extent*2048
    old_atlas = bytes(image[atlas_base:atlas_base+atlas.size])
    new_atlas, art_report = atlas_apply(old_atlas)
    return entry, installed, new, preserved, atlas_base, old_atlas, new_atlas, art_report


def owner(offset, old_size):
    if 0x64 <= offset < 0x68:
        return 'elf_translation_segment_file_length'
    if any(a <= offset < a+4 for a in (0x65EE0,0x668A0,0x660EC)):
        return 'event_lifecycle_hooks_and_revert_x_reconstruction_hook'
    if offset >= old_size-188:
        return 'replace_obsolete_x_helper_and_append_y_private_payload'
    return 'bounded_inspection_save_text_and_pointer_owners'


def audit(baseline, candidate, staged):
    """Compare every byte, using independently regenerated exact payloads."""
    if sha_file(baseline) != X_SHA:
        raise ValueError('previous ISO hash changed')
    with baseline.open('rb') as af,candidate.open('rb') as bf:
        with mmap.mmap(af.fileno(),0,access=mmap.ACCESS_READ) as a, mmap.mmap(bf.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a) != len(b):
                raise ValueError('ISO physical size changed')
            entry,old,new,preserved,art_base,old_art,new_art,_ = prepare(a,staged)
            base = entry.extent*2048
            _, new_records = index_iso(b)
            new_entry = find_record(new_records,'SLPM_665.11')
            if (new_entry.extent,new_entry.size) != (entry.extent,len(new)):
                raise ValueError('candidate ELF extent/length mismatch')
            if bytes(b[base:base+len(new)]) != new:
                raise ValueError('candidate ELF does not match deterministic build')
            if bytes(b[art_base:art_base+len(new_art)]) != new_art:
                raise ValueError('candidate atlas does not match deterministic build')
            expected = {}
            for i,value in enumerate(new):
                if value != a[base+i]:
                    expected[base+i] = (value,owner(i,len(old)))
            for i,(x,y) in enumerate(zip(old_art,new_art)):
                if x != y:
                    expected[art_base+i] = (y,'native_save_load_back_caption_pixels')
            size_pair = struct.pack('<I',len(new))+struct.pack('>I',len(new))
            for i,value in enumerate(size_pair):
                p = entry.record_offset+10+i
                if a[p] != value:
                    expected[p] = (value,'iso9660_executable_length_both_endians')
            counts = Counter()
            for start in range(0,len(a),8*1024*1024):
                lhs,rhs = a[start:start+8*1024*1024],b[start:start+8*1024*1024]
                if lhs == rhs:
                    continue
                for n,(x,y) in enumerate(zip(lhs,rhs)):
                    if x == y:
                        continue
                    match = expected.get(start+n)
                    if match is None or y != match[0]:
                        raise ValueError(f'unexplained ISO byte at {start+n:#x}')
                    counts[match[1]] += 1
            if sum(counts.values()) != len(expected):
                raise ValueError('expected mutation missing from finished ISO')
            return dict(status='PASS_ALL_FINISHED_ISO_BYTES_CLASSIFIED',
                physical_iso_bytes_compared=len(a),changed_byte_classification=dict(counts),
                changed_bytes=sum(counts.values()),unexplained_modified_bytes=0,
                installed_metadata_bytes_preserved=len(preserved),
                previous_iso_sha256=X_SHA,candidate_iso_sha256=sha_file(candidate),
                save_identity=verify_save_identity(new),
                q_lock=verify_approved(new,json.loads(Q.read_text())),
                t_lock=verify_ui(new,json.loads(T.read_text())),runtime_verified=False)


def main():
    staged_path = Path(str(PREFIX)+'-event-lifecycle-inspection-save.elf')
    report_path = Path(str(PREFIX)+'-build.json')
    audit_path = Path(str(PREFIX)+'-iso-audit.json')
    temp = OUTPUT.with_suffix('.incomplete')
    for path in (OUTPUT,temp,staged_path,report_path,audit_path):
        if path.exists():
            raise FileExistsError(f'refusing to overwrite {path}')
    if sha_file(X_ISO) != X_SHA:
        raise ValueError('previous ISO hash mismatch')
    staged, reports = payloads()
    clone = subprocess.run(['cp','-c',str(X_ISO),str(temp)],capture_output=True)
    if clone.returncode:
        shutil.copyfile(X_ISO,temp)
    # On failure retain the .incomplete file for diagnosis, never label release.
    with temp.open('r+b') as fd,mmap.mmap(fd.fileno(),0,access=mmap.ACCESS_WRITE) as image:
        entry,old,new,preserved,art_base,old_art,new_art,art_report = prepare(image,staged)
        start = entry.extent*2048
        image[start:start+len(new)] = new
        image[art_base:art_base+len(new_art)] = new_art
        patch_directory_record(image,entry.record_offset,size=len(new))
        image.flush()
    audit_report = audit(X_ISO,temp,staged)
    reports.update(release='r67.14y',status='DIAGNOSTIC_GAMEPLAY_APPROVAL_PENDING',
        output_iso=str(OUTPUT),output_sha256=audit_report['candidate_iso_sha256'],
        elf_output_extent=entry.extent,elf_size=len(new),elf_sha256=sha(new),
        staged_elf_sha256=sha(staged),previous_iso_sha256=X_SHA,
        installed_metadata_bytes_preserved=len(preserved),save_atlas=art_report,
        save_runtime_compatibility_verified=False)
    with staged_path.open('xb') as f:
        f.write(staged)
    for path,data in ((report_path,reports),(audit_path,audit_report)):
        with path.open('x') as f:
            json.dump(data,f,indent=2,sort_keys=True)
            f.write('\n')
    temp.rename(OUTPUT)
    print(json.dumps({k:v for k,v in reports.items() if k in (
        'release','status','output_iso','output_sha256','elf_sha256','elf_size')}))


if __name__ == '__main__':
    main()
