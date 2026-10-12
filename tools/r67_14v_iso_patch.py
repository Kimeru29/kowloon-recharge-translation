"""Reflink-clone r67.14t ISO with narrowly scoped variant-aware event Y patch.

Preserve original ISO, item + tablet accepted data, PS2 memory cards and all
game serial/serialization. Never overwrite any prior candidate or logs.
"""
from __future__ import annotations
import argparse,hashlib,json,mmap,shutil,subprocess
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record,patch_directory_record,SECTOR_SIZE
from tools.r67_14v_opening_only_bubble_y import apply,EVENT_Y_WRAPPERS
from tools.r67_14v_scoped_approval_lock import validate_scoped
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_lion_statue_ui import sha
SOURCE_ISO_SHA="03526a1779822ad1ec15136c26ff8c3b50d6997bb395a601db228b3fc2fe321f"
SOURCE_INSTALLED_ELF_SHA="f29cb00fa819bdcc82b91d62f889c09f547ad4811f734295c7843a8cb080518a"
def build(previous_iso:Path,old_elf:bytes,new_elf:bytes,old_manifest:dict,patch:dict,
          output:Path)->tuple[dict,dict]:
    if sha_file(previous_iso)!=SOURCE_ISO_SHA:raise ValueError("Unapproved previous ISO baseline")
    if old_manifest["elf_sha256"]!=SOURCE_INSTALLED_ELF_SHA:
        raise ValueError("Original installed ELF hash mismatch")
    validated,info=apply(old_elf)
    if validated!=new_elf or info!=patch:raise ValueError("Candidate source no longer deterministic")
    scoped=validate_scoped(new_elf,old_elf)
    diff=[i for i,(a,b) in enumerate(zip(old_elf,new_elf)) if a!=b]
    if output.exists() or output.with_suffix(".incomplete").exists():
        raise FileExistsError("Refusing to overwrite an ISO")
    tmp=output.with_suffix(".incomplete")
    try:
        clone=subprocess.run(["cp","-c",str(previous_iso),str(tmp)],capture_output=True,text=True)
        if clone.returncode:shutil.copyfile(previous_iso,tmp)
        with tmp.open("r+b") as fd,mmap.mmap(fd.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
            _,records=index_iso(iso)
            entry=find_record(records,"SLPM_665.11")
            if (entry.extent,entry.size)!=(old_manifest["elf_output_extent"],len(old_elf)):
                raise ValueError("Unrecognized ISO9660 ELF extent/size")
            if entry.sectors!=(len(new_elf)+SECTOR_SIZE-1)//SECTOR_SIZE:
                raise ValueError("Unexpected ISO sector reallocation")
            start=entry.extent*SECTOR_SIZE
            prior=bytes(iso[start:start+entry.size])
            if sha(prior)!=SOURCE_INSTALLED_ELF_SHA:
                raise ValueError("Installed r67.14t preimage hash mismatch")
            for pos in diff:
                if iso[start+pos]!=old_elf[pos]:raise ValueError(f"ELF source mismatch at {pos:#x}")
                iso[start+pos]=new_elf[pos]
            if any(iso[start+len(old_elf):start+len(new_elf)]):
                raise ValueError("Appended executable collision in source ISO")
            iso[start+len(old_elf):start+len(new_elf)]=new_elf[len(old_elf):]
            patch_directory_record(iso,entry.record_offset,size=len(new_elf))
            new_installed=bytes(iso[start:start+len(new_elf)])
            embedded_hash=sha(new_installed)
            if any(marker not in new_installed for marker in (b"SLPM-66511",b"BISLPM-66511Save")):
                raise ValueError("Save/game identity missing in candidate")
            scoped_embedded=validate_scoped(new_installed,prior)
            iso.flush()
        if tmp.stat().st_size!=previous_iso.stat().st_size:
            raise ValueError("Finished ISO physical size changed")
        candidate_hash=sha_file(tmp)
        tmp.rename(output)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    manifest=dict(old_manifest)
    manifest["elf_size"]=len(new_elf)
    manifest["elf_sha256"]=embedded_hash
    manifest["output_sha256"]=candidate_hash
    manifest["event_bubble_relative_y"]={
        "baseline_iso_sha256":SOURCE_ISO_SHA,
        "original_q_approval_manifest_preserved":True,
        "q_scoped_exception":[hex(x[0]) for x in EVENT_Y_WRAPPERS],
        "gameplay_approved":False,
        "source_codes_not_modified_beyond_two_words":True,
    }
    result={
        "revision":"r67.14v",
        "status":"DIAGNOSTIC_NOT_YET_VISUALLY_APPROVED",
        "baseline_iso_sha256":SOURCE_ISO_SHA,
        "candidate_iso_sha256":candidate_hash,
        "embedded_elf_sha256":embedded_hash,
        "source_elf_changes":[hex(pos) for pos in diff],
        "appended_private_helper_bytes":len(new_elf)-len(old_elf),
        "native_scoped_approval_lock":scoped,
        "finished_iso_scoped_approval_lock":scoped_embedded,
        "save_runtime_compatibility_verified":False,
    }
    return result,manifest

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("baseline-iso","source-elf","candidate-elf","candidate-report",
                  "baseline-build-report","output-iso","report","build-report"):
        p.add_argument("--"+field,type=Path,required=True)
    a=p.parse_args()
    if a.report.exists() or a.build_report.exists():
        raise FileExistsError("Would overwrite previous report")
    result,build_manifest=build(
        a.baseline_iso,a.source_elf.read_bytes(),a.candidate_elf.read_bytes(),
        json.loads(a.baseline_build_report.read_text()),
        json.loads(a.candidate_report.read_text()),a.output_iso)
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    a.build_report.write_text(json.dumps(build_manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if not k.endswith("lock")},sort_keys=True))
if __name__=="__main__":main()
