"""Clone r67.14r ISO and install the tiny r67.14s Lion Statue fit delta.

Only 3 already-existing bytes change (two private-helper instruction words).
No ELF/ISO size changes, no save/ROFS/graphics/caller metadata changes.
"""
from __future__ import annotations
import argparse,hashlib,json,mmap,shutil,subprocess
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE,index_iso,find_record
from tools.r67_14s_lion_final_fit import apply,sha,SOURCE_R_SHA256
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_14q_approved_lock import verify_approved,MANIFEST

APPROVED_R_ISO_SHA256="80722883fc688a482a68821b34a75d2e97d95c1ef7940535e31f4ffdc265a7ed"
APPROVED_R_INSTALLED_SHA256="81c3c229c828bf5067749c4e6f0836cd2c8861f022fdf6c0b5b3a4003527eaa0"

def build(old_iso:Path,old_elf:bytes,new_elf:bytes,patch_report:dict,
          old_build:dict,output:Path)->tuple[dict,dict]:
    if sha_file(old_iso)!=APPROVED_R_ISO_SHA256:raise ValueError("Wrong r67.14r predecessor ISO")
    expected,metadata=apply(old_elf)
    if new_elf!=expected or metadata!=patch_report:raise ValueError("Patch stage report mismatch")
    if old_build["elf_sha256"]!=APPROVED_R_INSTALLED_SHA256:raise ValueError("Previous build manifest drift")
    diff=[i for i,(a,b) in enumerate(zip(old_elf,new_elf)) if a!=b]
    if len(diff)!=3 or old_elf==new_elf or len(old_elf)!=len(new_elf):
        raise ValueError("Invalid final fit source delta")
    if output.exists() or output.with_suffix(".incomplete").exists():raise FileExistsError("Never overwrite candidate")
    temp=output.with_suffix(".incomplete")
    try:
        clone=subprocess.run(["cp","-c",str(old_iso),str(temp)],capture_output=True,text=True,check=False)
        if clone.returncode:shutil.copyfile(old_iso,temp)
        with temp.open("r+b") as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
            _,recs=index_iso(iso);exe=find_record(recs,"SLPM_665.11")
            start=exe.extent*SECTOR_SIZE
            if (exe.size,exe.extent)!=(len(old_elf),old_build["elf_output_extent"]):
                raise ValueError("ELF size/extent metadata drift")
            installed=bytes(iso[start:start+exe.size])
            if sha(installed)!=APPROVED_R_INSTALLED_SHA256:raise ValueError("Installed r ELF mismatch")
            for pos in diff:
                if iso[start+pos]!=old_elf[pos]:raise ValueError(f"ELF preimage drift {pos:#x}")
                iso[start+pos]=new_elf[pos]
            updated=bytes(iso[start:start+exe.size])
            verify_approved(updated,json.loads(MANIFEST.read_text()))
            installed_sha=sha(updated)
            iso.flush()
        if temp.stat().st_size!=old_iso.stat().st_size:raise ValueError("ISO file size drift")
        digest=sha_file(temp)
        temp.rename(output)
    except BaseException:
        temp.unlink(missing_ok=True);raise
    build=dict(old_build)
    build["elf_sha256"]=installed_sha
    build["output_sha256"]=digest
    build["lion_statue_final_fit"]={
        "previous_iso_sha256":APPROVED_R_ISO_SHA256,
        "previous_installed_elf_sha256":APPROVED_R_INSTALLED_SHA256,
        "private_helper_changed_offsets":list(map(hex,diff)),
        "runtime_verified":False,
        "save_compatible_runtime_verified":False,
    }
    return {
        "status":"DIAGNOSTIC_AWAITING_USER_VISUAL_APPROVAL",
        "previous_iso_sha256":APPROVED_R_ISO_SHA256,
        "candidate_iso_sha256":digest,
        "embedded_elf_sha256":installed_sha,
        "elf_extent":exe.extent,
        "changed_existing_elf_offsets":list(map(hex,diff)),
        "changed_bytes":len(diff),
        "full_iso_size_unchanged":True,
        "runtime_verified":False
    },build

def main():
    p=argparse.ArgumentParser()
    for n in ("baseline-iso","source-elf","candidate-elf","candidate-report","baseline-build-report","output-iso","report","build-report"):
        p.add_argument("--"+n,required=True,type=Path)
    a=p.parse_args()
    if a.report.exists() or a.build_report.exists():raise FileExistsError("Report already exists")
    report,build_report=build(
        a.baseline_iso,a.source_elf.read_bytes(),a.candidate_elf.read_bytes(),
        json.loads(a.candidate_report.read_text()),json.loads(a.baseline_build_report.read_text()),
        a.output_iso
    )
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    a.build_report.write_text(json.dumps(build_report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
