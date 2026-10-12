"""Clone r67.14s diagnostic ISO with only verified gamewide stone-tablet deltas."""
from __future__ import annotations
import argparse,json,mmap,shutil,subprocess
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE,index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_lion_statue_ui import sha
from tools.r67_14t_stone_tablet_fit import apply,COMPACT_INSCRIPTION_TEXT

SOURCE_S_ISO_SHA256="0090539ef27833624c58fc52fc9b10f1900be289eb6f810eb77aa96f7f6f6cb4"
SOURCE_S_EMBEDDED_SHA256="ab539b157c436c7d57607559508505f663ef028eed176c5da3808c37fbc6b929"

def build(old_iso:Path,old_elf:bytes,new_elf:bytes,patch_report:dict,old_report:dict,
          out:Path)->tuple[dict,dict]:
    if sha_file(old_iso)!=SOURCE_S_ISO_SHA256:raise ValueError("Unknown predecessor ISO")
    if old_report["elf_sha256"]!=SOURCE_S_EMBEDDED_SHA256:
        raise ValueError("Unknown predecessor installed ELF")
    expected,expected_metadata=apply(old_elf)
    if new_elf!=expected or patch_report!=expected_metadata:
        raise ValueError("Not a verified universal tablet-fit patch")
    if out.exists() or out.with_suffix(".incomplete").exists():raise FileExistsError("Do not overwrite")
    changed=[p for p,(a,b) in enumerate(zip(old_elf,new_elf)) if a!=b]
    allowed=set(range(0x64,0x68))
    for off in COMPACT_INSCRIPTION_TEXT:
        allowed.update(range(off,off+4))
    if not changed or set(changed)-allowed:raise ValueError("Unexpected old ELF changes")
    tmp=out.with_suffix(".incomplete")
    try:
        cmd=subprocess.run(["cp","-c",str(old_iso),str(tmp)],capture_output=True,text=True)
        if cmd.returncode:shutil.copyfile(old_iso,tmp)
        with tmp.open("r+b") as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
            _,recs=index_iso(iso);elf=find_record(recs,"SLPM_665.11")
            if (elf.size,elf.extent)!=(len(old_elf),old_report["elf_output_extent"]):
                raise ValueError("ELF ISO9660 record drift")
            if elf.sectors!=(len(new_elf)+SECTOR_SIZE-1)//SECTOR_SIZE:
                raise ValueError("ELF sector relocation required")
            start=elf.extent*SECTOR_SIZE
            installed=bytes(iso[start:start+elf.size])
            if sha(installed)!=SOURCE_S_EMBEDDED_SHA256:
                raise ValueError("Embedded old ELF SHA mismatch")
            for pos in changed:
                if iso[start+pos]!=old_elf[pos]:raise ValueError(f"Original ELF preimage drift {pos:#x}")
                iso[start+pos]=new_elf[pos]
            end=start+len(new_elf)
            if any(iso[start+len(old_elf):end]):
                raise ValueError("Appended tablet strings collide with nonzero ISO bytes")
            iso[start+len(old_elf):end]=new_elf[len(old_elf):]
            patch_directory_record(iso,elf.record_offset,size=len(new_elf))
            installed_new=bytes(iso[start:end])
            if b"SLPM-66511" not in installed_new or b"BISLPM-66511Save" not in installed_new:
                raise ValueError("Game save identity changed")
            embedded_new_sha=sha(installed_new)
            iso.flush()
        if out.parent.exists() and tmp.stat().st_size!=old_iso.stat().st_size:
            raise ValueError("Whole ISO size changed")
        digest=sha_file(tmp);tmp.rename(out)
    except BaseException:
        tmp.unlink(missing_ok=True);raise
    build=dict(old_report)
    build["elf_size"]=len(new_elf)
    build["elf_sha256"]=embedded_new_sha
    build["output_sha256"]=digest
    build["stone_tablet_generic_fit"]={
        "registered_tablets":58,"populated_inscription_rows":160,"glyph_limit":21,
        "patched_rows":len(COMPACT_INSCRIPTION_TEXT),
        "predecessor_sha256":SOURCE_S_ISO_SHA256,
        "candidate_sha256":digest,
        "runtime_approved":False
    }
    report={
        "revision":"r67.14t","status":"DIAGNOSTIC_AWAITING_VISUAL_APPROVAL",
        "source_iso_sha256":SOURCE_S_ISO_SHA256,"candidate_iso_sha256":digest,
        "embedded_elf_sha256":embedded_new_sha,
        "appended_bytes":len(new_elf)-len(old_elf),
        "elf_extent":elf.extent,"elf_size":len(new_elf),
        "changed_old_elf_offsets":list(map(hex,changed)),
        "modified_tablet_pointer_owners":list(map(hex,sorted(COMPACT_INSCRIPTION_TEXT))),
        "entire_iso_size_unchanged":True,
        "runtime_approved":False,"save_runtime_compatibility_verified":False,
    }
    return report,build

def main():
    p=argparse.ArgumentParser()
    for n in ("baseline-iso","source-elf","candidate-elf","candidate-report","baseline-build-report","output-iso","report","build-report"):
        p.add_argument("--"+n,type=Path,required=True)
    a=p.parse_args()
    if a.report.exists() or a.build_report.exists():raise FileExistsError("Report exists")
    report,meta=build(a.baseline_iso,a.source_elf.read_bytes(),a.candidate_elf.read_bytes(),
        json.loads(a.candidate_report.read_text()),json.loads(a.baseline_build_report.read_text()),a.output_iso)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    a.build_report.write_text(json.dumps(meta,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))

if __name__=="__main__":main()
