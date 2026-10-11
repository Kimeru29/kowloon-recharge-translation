"""Reproducible isolated 67.13 ISO probe from the visually approved 67.12 disc.

Patch only the ELF loader size, the native font constructor hook, the new
segment tail helper, and the ISO directory record length. Preserve the
installed ELF's independent ROFS relocation patches byte-for-byte.

Diagnostic only; requires scene test and user approval. Do not overwrite source.
"""
from __future__ import annotations
import argparse, hashlib, json, mmap, shutil, struct, subprocess
from pathlib import Path
from tools.iso9660_patch import index_iso, find_record, patch_directory_record, SECTOR_SIZE
from tools.r67_chamber_comment_geometry_probe import BASELINE_SHA, sha, apply

SOURCE_ISO_SHA="87cfa6f445eba36687e1d5badc621d9efd3157560a3be8da0c5eda4309a54e63"
SOURCE_INSTALLED_ELF_SHA="669b997d767d39c1ca5e29dc6458eaedc71bfe78e2fe74ca7f1dd9312858988c"

def file_sha(path:Path)->str:
    digest=hashlib.sha256()
    with path.open("rb") as inp:
        for buf in iter(lambda:inp.read(16*1024*1024),b""):digest.update(buf)
    return digest.hexdigest()

def build(source:Path, stage:Path, destination:Path)->dict:
    if destination.exists():raise FileExistsError(destination)
    if file_sha(source)!=SOURCE_ISO_SHA:raise ValueError("Source ISO sha mismatch")
    original=stage.read_bytes()
    if sha(original)!=BASELINE_SHA:raise ValueError("Wrong baseline staged ELF")
    proposed,meta=apply(original)
    source_installed_size=len(original)
    altered_offsets={i for i in range(len(original)) if original[i]!=proposed[i]}
    expected=set(range(0x64,0x68))|set(range(0x88d6c,0x88d70))
    if not altered_offsets<=expected:raise ValueError("Unowned existing executable modifications")
    final_size=len(proposed)
    temp=destination.with_suffix(destination.suffix+".incomplete")
    if temp.exists():raise FileExistsError(temp)
    try:
        clone=subprocess.run(["cp","-c",str(source),str(temp)],capture_output=True,text=True)
        if clone.returncode:shutil.copyfile(source,temp)
        before_iso_len=source.stat().st_size
        with temp.open("r+b") as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_WRITE) as iso:
            _,records=index_iso(iso)
            exe=find_record(records,"SLPM_665.11")
            if exe.size!=source_installed_size:raise ValueError("ISO ELF record size drift")
            if (final_size+SECTOR_SIZE-1)//SECTOR_SIZE > exe.sectors:
                raise ValueError("Executable exceeds existing allocated sectors")
            start=exe.extent*SECTOR_SIZE
            if sha(iso[start:start+exe.size])!=SOURCE_INSTALLED_ELF_SHA:
                raise ValueError("Unexpected installed ELF checksum")
            # Copy only stage deltas, not old stage bytes, because installed ELF
            # contains independent file-pointer rewrites needed by the game.
            for at in sorted(altered_offsets):
                if iso[start+at]!=original[at]:
                    raise ValueError(f"Installed ELF diverges at hook/header {at:#x}")
                iso[start+at]=proposed[at]
            new_tail=proposed[len(original):]
            # Existing trailing sector padding must be zero; never clobber files.
            if any(iso[start+len(original):start+final_size]):
                raise ValueError("Executable padding not empty")
            iso[start+len(original):start+final_size]=new_tail
            patch_directory_record(iso,exe.record_offset,size=final_size)
            _,again=index_iso(iso)
            changed=find_record(again,"SLPM_665.11")
            if (changed.extent,changed.size)!=(exe.extent,final_size):
                raise ValueError("ISO record not updated correctly")
            if iso[start+len(original):start+final_size]!=new_tail:
                raise ValueError("Helper payload missing from ISO")
            if b"SLPM-66511" not in iso[start:start+final_size] or b"BISLPM-66511Save" not in iso[start:start+final_size]:
                raise ValueError("Save identifier unexpectedly changed")
            installed_sha=sha(iso[start:start+final_size])
            iso.flush()
        if temp.stat().st_size!=before_iso_len:raise ValueError("ISO size drift")
        final_iso_sha=file_sha(temp)
        temp.rename(destination)
        return dict(
          stage_sha=meta["output_sha256"],
          installed_elf_sha256=installed_sha,
          iso_sha256=final_iso_sha,
          iso_source_sha256=SOURCE_ISO_SHA,
          existing_elf_modified_offsets=list(map(hex,sorted(altered_offsets))),
          elf_tail_appended_bytes=len(new_tail),
          record=hex(exe.record_offset),
          iso_size=before_iso_len,
          release_approved=False,
          visual_verification_required=True,
        )
    finally:
        if temp.exists():temp.unlink()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("source-iso","staged-elf","dest-iso","report"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args()
    if a.report.exists():raise FileExistsError(a.report)
    data=build(a.source_iso,a.staged_elf,a.dest_iso)
    a.report.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,sort_keys=True))

if __name__=="__main__":
    main()
