"""ISO COW hotfix for 67.07 containment stage only; no ROFS re-layout."""
from __future__ import annotations
import argparse, hashlib, json, mmap, shutil, subprocess
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE,find_record,index_iso
from tools.r67_07_lock import apply,sha

SOURCE_ISO_SHA="192e772163e58450c3f628aa9de9a5fdc83ee175ef8a146c4e3660c316b75f23"
SOURCE_INSTALLED_ELF_SHA="1b1c4065269fb0664f7ce1a61b85a2beea5acffdb54a7c779997b59788439fa0"

def file_sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda:stream.read(16*1024*1024),b""):h.update(block)
    return h.hexdigest()

def build(old_iso:Path,old_elf:bytes,new_elf:bytes,report:dict,dest:Path)->dict:
    if file_sha(old_iso)!=SOURCE_ISO_SHA or sha(old_elf)!=report["previous_sha256"] or sha(new_elf)!=report["sha256"]:
        raise ValueError("Unrecognized stage inputs")
    if dest.exists():raise FileExistsError(dest)
    temp=dest.with_suffix(dest.suffix+".incomplete")
    if temp.exists():raise FileExistsError(temp)
    try:
        clone=subprocess.run(["cp","-c",str(old_iso),str(temp)],capture_output=True,text=True)
        if clone.returncode:shutil.copyfile(old_iso,temp)
        with temp.open("r+b") as fd,mmap.mmap(fd.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
            _,entries=index_iso(iso);exe=find_record(entries,"SLPM_665.11")
            if exe.size!=len(old_elf) or exe.size!=len(new_elf):raise ValueError("Changed ELF size")
            start=exe.extent*SECTOR_SIZE
            if sha(iso[start:start+exe.size])!=SOURCE_INSTALLED_ELF_SHA:
                raise ValueError("Shipped 67.06 ELF checksum mismatch")
            allowed=set(report["modified_offsets"]);applied=0
            for at,(before,after) in enumerate(zip(old_elf,new_elf)):
                if before==after:continue
                if at not in allowed or iso[start+at]!=before:raise ValueError(f"Unowned ISO change at {at:#x}")
                iso[start+at]=after;applied+=1
            if b"SLPM-66511" not in iso[start:start+exe.size] or b"BISLPM-66511Save" not in iso[start:start+exe.size]:
                raise ValueError("Save identifier changed")
            actual_elf_sha=sha(iso[start:start+exe.size])
            iso.flush()
        if temp.stat().st_size!=old_iso.stat().st_size:raise ValueError("ISO size changed")
        result_sha=file_sha(temp)
        temp.rename(dest)
        return dict(iso_sha256=result_sha,source_iso_sha256=SOURCE_ISO_SHA,elf_sha256=actual_elf_sha,
                    changed_bytes=applied,unexplained_bytes=0,save_compatibility_preserved=True,visual_validation=False)
    except BaseException:
        temp.unlink(missing_ok=True);raise

def main():
    p=argparse.ArgumentParser()
    for name in ("baseline-iso","old-elf","new-elf","stage-report","output","report"):p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args();meta=json.loads(a.stage_report.read_text())
    result=build(a.baseline_iso,a.old_elf.read_bytes(),a.new_elf.read_bytes(),meta,a.output)
    a.report.write_text(json.dumps(result,indent=2)+"\n")
    print(result)
if __name__=="__main__":main()
