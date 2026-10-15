"""r67.14z append-only ISO builder with full y→z finished-disc byte audit.

Only five pointer words, executable size and appended translated text may
differ from the SHA-pinned user-approved r67.14y. Preserve the installed
ROFS metadata bytes, all graphics, prior native code, save paths and assets.
"""
from __future__ import annotations
import hashlib,json,mmap,shutil,struct,subprocess
from collections import Counter
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_14z_storeroom_tablet import (
    ROOT,Y_STAGE_SHA,Y_INSTALLED_SHA,Y_ISO_SHA,ROOM_OWNERS,TABLET_OWNERS,
    expected_writes,sha,
)
from tools.r67_14q_approved_lock import MANIFEST as Q,verify_approved
from tools.r67_14t_approved_ui_lock import MANIFEST as T,verify_ui
from tools.r67_14y_release import verify_save_identity
from tools.r67_14y_inspection_save import validate_result as validate_y_inspections

Y_ISO=ROOT/'local/r67-candidates/67.14y-event-lifecycle-inspection-save.iso'
Y_STAGE=ROOT/'local/r67-14y-event-lifecycle-inspection-save.elf'
Z_STAGE=ROOT/'local/r67-14z-storeroom-tablet.elf'
Z_ISO=ROOT/'local/r67-candidates/67.14z-storeroom-inscription.iso'
PREFIX=ROOT/'local/r67-14z'
OWNERS=ROOM_OWNERS+TABLET_OWNERS

def classify(before:bytes,after:bytes)->tuple[list[int],dict[int,str]]:
    if sha(before)!=Y_STAGE_SHA:
        raise ValueError("Not the approved staged y baseline")
    new,metadata=expected_writes(before)
    if new!=after:
        raise ValueError("Candidate source not reproducible from exact five-owner patch")
    allowed={p:"elf_size" for p in range(0x64,0x68)}
    for owner in OWNERS:
        for p in range(owner,owner+4):
            allowed[p]="room_label_pointer" if owner in ROOM_OWNERS else "stone_inscription_pointer"
    diffs=[i for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    if not diffs or any(i not in allowed for i in diffs):
        raise ValueError("Unapproved source ELF mutation")
    return diffs,allowed

def derive_installed(old_stage:bytes,old_installed:bytes,new_stage:bytes)->tuple[bytes,dict]:
    diffs,allowed=classify(old_stage,new_stage)
    if len(old_installed)!=len(old_stage) or sha(old_installed)!=Y_INSTALLED_SHA:
        raise ValueError("Approved installed y ELF SHA/size mismatch")
    if len(new_stage)<len(old_stage):raise ValueError("Executable shrank")
    out=bytearray(old_installed)
    for i in diffs:
        if old_installed[i]!=old_stage[i]:
            raise ValueError(f"New patch collides with installed ROFS metadata: {i:#x}")
        out[i]=new_stage[i]
    out.extend(new_stage[len(old_stage):])
    result=bytes(out)
    verify_approved(result,json.loads(Q.read_text()))
    verify_ui(result,json.loads(T.read_text()))
    validate_y_inspections(result)
    verify_save_identity(result)
    return result,dict(modified_old_offsets=[hex(i) for i in diffs],
                       metadata_bytes_preserved=sum(a!=b for a,b in zip(old_stage,old_installed)),
                       appended_bytes=len(result)-len(old_installed))

def load_and_check(iso):
    _,files=index_iso(iso)
    entry=find_record(files,'SLPM_665.11')
    base=entry.extent*2048
    original=bytes(iso[base:base+entry.size])
    if sha(original)!=Y_INSTALLED_SHA:
        raise ValueError("Installed approved y ELF fingerprint mismatch")
    return files,entry,base,original

def verify_growth(iso,files,entry,new_size):
    begin=entry.extent*2048
    end=begin+((new_size+2047)//2048)*2048
    if end>len(iso):raise ValueError("Appended ELF exceeds ISO volume")
    for other in files:
        if other==entry:continue
        if other.extent*2048<end and (other.extent+other.sectors)*2048>begin:
            raise ValueError("New ELF overlaps another ISO file")
    if any(iso[begin+entry.size:end]):
        raise ValueError("New ELF would overwrite nonzero ISO bytes")

def audit(previous:Path,new:Path,staged_before:bytes,staged_after:bytes):
    if sha_file(previous)!=Y_ISO_SHA:
        raise ValueError("Approved y ISO changed")
    with previous.open('rb') as pa,new.open('rb') as pb:
        with mmap.mmap(pa.fileno(),0,access=mmap.ACCESS_READ) as a,mmap.mmap(
            pb.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):raise ValueError("Whole disc size changed")
            files,old_entry,base,old_installed=load_and_check(a)
            _,new_files=index_iso(b)
            new_entry=find_record(new_files,'SLPM_665.11')
            wanted,meta=derive_installed(staged_before,old_installed,staged_after)
            if (old_entry.extent,old_entry.record_offset)!=(new_entry.extent,new_entry.record_offset):
                raise ValueError("Executable moved on disc")
            if new_entry.size!=len(wanted) or bytes(b[base:base+new_entry.size])!=wanted:
                raise ValueError("Installed candidate bytes/extent do not match original y plus owned delta")
            expected={}
            diffs,kinds=classify(staged_before,staged_after)
            for i in diffs:
                if a[base+i]!=wanted[i]:expected[base+i]=(wanted[i],kinds[i])
            for i in range(len(old_installed),len(wanted)):
                if a[base+i]!=wanted[i]:expected[base+i]=(wanted[i],"append_only_storeroom_english")
            size_words=struct.pack('<I',len(wanted))+struct.pack('>I',len(wanted))
            for n,val in enumerate(size_words):
                p=old_entry.record_offset+10+n
                if a[p]!=val:expected[p]=(val,"iso9660_executable_size_both_endians")
            tally=Counter()
            for begin in range(0,len(a),8*1024*1024):
                lhs=a[begin:begin+8*1024*1024];rhs=b[begin:begin+8*1024*1024]
                if lhs==rhs:continue
                for local,(before,after) in enumerate(zip(lhs,rhs)):
                    if before==after:continue
                    absolute=begin+local
                    if absolute not in expected or expected[absolute][0]!=after:
                        raise ValueError(f"Unclassified ISO byte {absolute:#x}: {before:#x}->{after:#x}")
                    tally[expected[absolute][1]]+=1
            if sum(tally.values())!=len(expected):
                raise ValueError("Expected permitted ISO modifications are missing")
            return dict(status="PASS_ZERO_UNEXPLAINED_FINISHED_ISO_BYTES",
                        previous_approved_y_iso_sha256=Y_ISO_SHA,
                        candidate_iso_sha256=sha_file(new),
                        physical_iso_bytes=len(a),changed_bytes=sum(tally.values()),
                        changed_bytes_by_owner=dict(tally),unexplained_bytes=0,
                        original_metadata_bytes_preserved=meta["metadata_bytes_preserved"],
                        saved_state_runtime_verified=False,
                        protected_q=verify_approved(wanted,json.loads(Q.read_text()))["status"],
                        protected_t=verify_ui(wanted,json.loads(T.read_text()))["status"])

def build():
    stage_report=Path(str(PREFIX)+'-storeroom-report.json')
    report=Path(str(PREFIX)+'-build.json')
    audit_path=Path(str(PREFIX)+'-iso-audit.json')
    tmp=Z_ISO.with_suffix('.incomplete')
    for p in (Z_ISO,tmp,report,audit_path):
        if p.exists():raise FileExistsError(f"Never overwrite existing release artifact {p}")
    original=Y_STAGE.read_bytes();staged=Z_STAGE.read_bytes()
    classify(original,staged)
    if sha_file(Y_ISO)!=Y_ISO_SHA:raise ValueError("Approved y ISO fingerprint drift")
    if not stage_report.exists():raise FileNotFoundError(stage_report)
    cloned=subprocess.run(["cp","-c",str(Y_ISO),str(tmp)],capture_output=True)
    if cloned.returncode:shutil.copyfile(Y_ISO,tmp)
    try:
        with tmp.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as image:
            files,e,base,embedded=load_and_check(image)
            wanted,meta=derive_installed(original,embedded,staged)
            verify_growth(image,files,e,len(wanted))
            image[base:base+len(wanted)]=wanted
            patch_directory_record(image,e.record_offset,size=len(wanted))
            image.flush()
        data=audit(Y_ISO,tmp,original,staged)
        manifest=dict(release="r67.14z",status="DIAGNOSTIC_PENDING_USER_SCREENSHOTS",
                      original_approved_y_iso_sha256=Y_ISO_SHA,
                      output_iso=str(Z_ISO),
                      output_sha256=data["candidate_iso_sha256"],
                      staged_elf_sha256=sha(staged),
                      elf_sha256=sha(wanted),elf_output_extent=e.extent,elf_size=len(wanted),
                      installed_metadata_bytes_preserved=meta["metadata_bytes_preserved"],
                      user_visual_approval=False,
                      save_runtime_compatibility_verified=False)
        with report.open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
        with audit_path.open('x') as f:json.dump(data,f,indent=2,sort_keys=True);f.write('\n')
        tmp.rename(Z_ISO)
        print(json.dumps({"iso":str(Z_ISO),"sha256":data["candidate_iso_sha256"],
                          "diff_bytes":data["changed_bytes"],"unexplained":0}))
    except BaseException:
        # Retain an incomplete image on error for forensic review; never
        # publish it under the diagnostic filename.
        raise

def main():
    build()

if __name__=="__main__":
    main()
