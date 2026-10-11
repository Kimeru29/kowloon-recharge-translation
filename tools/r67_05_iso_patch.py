"""Strictly apply 67.04 -> 67.05 ELF-local changes to 67.04 playable ISO.

Preserve the already relocated CVM and 1162 ROFS records in the shipped ELF.
ISO generation from a prerelease is safe here only because every accepted ELF
byte difference is classified and the new ELF fits the existing allocated sectors.
No copyrighted bytes are stored in this repository or published.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
import shutil
import subprocess

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso, patch_directory_record
from tools.r67_05_layout import ROTATE_SLOT as NATIVE_ROTATE_SLOT, ROTATE_LENGTH as ROTATE_SLOT_SIZE

EXPECTED_BASE_ISO = "0d60cc45a10487185a15a64f1acecf459e91b3c7b59a97c18edcd29e4658dcca"
EXPECTED_BASE_SHIPPED_ELF = "fb182391f782643e996927c94a5029ea517b3a8565a02f7240d044523222c23b"
EXE = "SLPM_665.11"

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8*1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def owners(baseline: bytes, candidate: bytes, report: dict) -> dict[int, str]:
    if (len(baseline) != report["previous_size"] or len(candidate) != report["new_size"]
            or sha(baseline) != report["prior_sha256"] or sha(candidate) != report["sha256"]):
        raise ValueError("67.05 stage and report fingerprints disagree")
    allowed = {i:"PT_LOAD_filesz" for i in range(0x64,0x68)}
    def reserve(begin:int,end:int,label:str)->None:
        for i in range(begin,end):
            if i in allowed: raise ValueError("67.05 allowed-byte overlap")
            allowed[i]=label
    reserve(NATIVE_ROTATE_SLOT,NATIVE_ROTATE_SLOT+ROTATE_SLOT_SIZE,"rotate_prompt")
    for row in report["basic_attack_rows"]:
        offset=int(row["owner"],16)
        reserve(offset,offset+4,f"basic_row_{row['row']}")
    counts=Counter()
    for i,(before,after) in enumerate(zip(baseline,candidate)):
        if before!=after:
            role=allowed.get(i)
            if role is None:raise ValueError(f"Unexplained 67.05 staged ELF byte {i:#x}")
            counts[role]+=1
    if len(candidate)<=len(baseline):raise ValueError("Missing expected translated text")
    return allowed

def build(previous_iso: Path, old_elf: Path, new_elf: Path,
          owner_report: Path, output: Path) -> dict:
    if output.exists():raise FileExistsError("Output already exists")
    if file_sha(previous_iso)!=EXPECTED_BASE_ISO:
        raise ValueError("Unrecognized 67.04 ISO checksum")
    old,new=old_elf.read_bytes(),new_elf.read_bytes()
    report=json.loads(owner_report.read_text())
    permitted=owners(old,new,report)
    baseline_size=previous_iso.stat().st_size
    dest_temp=output.with_suffix(output.suffix+".incomplete")
    if dest_temp.exists():raise FileExistsError(dest_temp)
    try:
        clone=subprocess.run(["cp","-c",str(previous_iso),str(dest_temp)],
                             capture_output=True,text=True)
        if clone.returncode:
            shutil.copyfile(previous_iso,dest_temp)
        with dest_temp.open("r+b") as file:
            with mmap.mmap(file.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
                _, entries=index_iso(iso)
                elf=find_record(entries,EXE)
                start=elf.extent*SECTOR_SIZE
                if elf.size!=len(old):
                    raise ValueError("67.04 outer ELF record size unexpected")
                present=iso[start:start+len(old)]
                if sha(present)!=EXPECTED_BASE_SHIPPED_ELF:
                    raise ValueError("ROFS-relocated 67.04 executable checksum changed")
                new_sectors=(len(new)+SECTOR_SIZE-1)//SECTOR_SIZE
                old_sectors=(len(old)+SECTOR_SIZE-1)//SECTOR_SIZE
                end_sector=elf.extent+new_sectors
                for other in entries:
                    if other.path==EXE or other.is_directory:continue
                    a=other.extent
                    b=other.extent+other.sectors
                    if max(a,elf.extent)<min(b,end_sector):
                        raise ValueError("Extended ELF conflicts with another ISO record")
                if end_sector*SECTOR_SIZE>len(iso):
                    raise ValueError("No slack in ISO for ELF growth")
                sector_start=start+old_sectors*SECTOR_SIZE
                sector_end=start+new_sectors*SECTOR_SIZE
                if iso[sector_start:sector_end]!=b"\0"*(sector_end-sector_start):
                    raise ValueError("New ELF sector is not empty; refuse to overwrite")
                applied=Counter()
                for pos,(before,after) in enumerate(zip(old,new)):
                    if before==after:continue
                    if pos not in permitted or iso[start+pos]!=before:
                        raise ValueError(f"Unrecognized installed ELF change: {pos:#x}")
                    iso[start+pos]=after
                    applied[permitted[pos]]+=1
                iso[start+len(old):start+len(new)]=new[len(old):]
                iso[start+len(new):start+new_sectors*SECTOR_SIZE]=b"\0"*(new_sectors*SECTOR_SIZE-len(new))
                patch_directory_record(iso,elf.record_offset,size=len(new))
                final=iso[start:start+len(new)]
                for pos,(before,after) in enumerate(zip(old,new)):
                    if before!=after and final[pos]!=after:
                        raise ValueError(f"Lost patch byte: {pos:#x}")
                if final[len(old):]!=new[len(old):]:
                    raise ValueError("Appended English text mismatch")
                if b"SLPM-66511" not in final or b"BISLPM-66511Save" not in final:
                    raise ValueError("Save identity changed")
                final_elf_sha=sha(final)
                iso.flush()
        if dest_temp.stat().st_size!=baseline_size:
            raise ValueError("Translated ISO grew in total size")
        output_hash=file_sha(dest_temp)
        dest_temp.rename(output)
        return dict(source_iso_sha256=EXPECTED_BASE_ISO,
                    output_iso_sha256=output_hash, final_elf_sha256=final_elf_sha,
                    source_elf_size=len(old),new_elf_size=len(new),
                    growth_sectors=new_sectors-old_sectors,
                    changed_existing_bytes=dict(applied),appended_bytes=len(new)-len(old),
                    save_identity_preserved=True,stage_report=report["sha256"])
    except Exception:
        dest_temp.unlink(missing_ok=True)
        raise

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("baseline-iso","old-elf","new-elf","owner-report","output","report"):
        p.add_argument("--"+name, type=Path, required=True)
    a=p.parse_args()
    if a.report.exists():raise FileExistsError(a.report)
    result=build(a.baseline_iso,a.old_elf,a.new_elf,a.owner_report,a.output)
    a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":
    main()
