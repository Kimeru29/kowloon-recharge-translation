"""r67.15b — compact native storage title, preserving the audited 15a ELF.

Clone exact SHA-pinned 15a ISO, replace one bounded native group4 atlas with
a deterministic narrow-title variant, and audit every byte of the 2GB disc.
No executable/native game code, other assets, save data or old ISOs change.
"""
from __future__ import annotations
import json,mmap,subprocess,shutil
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_15b_bounded_storage_title import PREVIOUS_SHA,TEX,sha
from tools.tmx import find_tmx_entry

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'local/r67-candidates/67.15a-item-storage-ui.iso'
BASE_SHA="8eb05f5cfc6cacd4f5dc58e9262b80ac720292e422c7264da3ce16f87cc8a1f0"
DEST=ROOT/'local/r67-candidates/67.15b-item-storage-compact.iso'
ATLAS_BEFORE=ROOT/'local/r67-15a-analysis/B_GP004-translated-v2.BIN'
ATLAS_AFTER=ROOT/'local/r67-15a-analysis/B_GP004-translated-v4.BIN'
REPORT=ROOT/'local/r67-15b-build.json'
AUDIT=ROOT/'local/r67-15b-whole-iso-audit.json'

def locate(image):
    _,outer=index_iso(image)
    cvm=find_record(outer,'DATA.CVM')
    elf=find_record(outer,'SLPM_665.11')
    base=cvm.extent*2048+0x1800
    _,entries=index_iso(image,base)
    group=find_record(entries,'BLBRD/B_GP004.BIN')
    return base+group.extent*2048,group,elf

def audit(previous:Path,latest:Path,old:bytes,new:bytes):
    if sha_file(previous)!=BASE_SHA:raise ValueError("Approved 15a diagnostic changed")
    e=find_tmx_entry(old,TEX)
    permitted=range(e.base_offset,e.base_offset+e.chunk_size)
    with previous.open('rb') as f,latest.open('rb') as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as a,mmap.mmap(
            g.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):raise ValueError("ISO size changed")
            off,record,elf=locate(a)
            new_off,new_record,new_elf=locate(b)
            if (off,record,new_off,new_record)!=(off,record,off,record):
                raise ValueError("Native group4 extent moved")
            if (elf.extent,elf.size,elf.record_offset)!=(new_elf.extent,new_elf.size,new_elf.record_offset):
                raise ValueError("Executable relocated or modified")
            if a[off:off+len(old)]!=old or b[off:off+len(new)]!=new:
                raise ValueError("Unexpected 15a -> 15b texture material")
            expected={off+i:new[i] for i,(x,y) in enumerate(zip(old,new)) if x!=y}
            if not expected:raise ValueError("No bounded artwork changed")
            if any((i-off) not in permitted for i in expected):
                raise ValueError("Another unrelated native texture changed")
            changed=0
            for base in range(0,len(a),8*1024*1024):
                l=a[base:base+8*1024*1024];r=b[base:base+8*1024*1024]
                if l==r:continue
                for i,(x,y) in enumerate(zip(l,r)):
                    if x==y:continue
                    at=base+i
                    if at not in expected or expected[at]!=y:
                        raise ValueError(f"UNEXPLAINED whole-ISO modification at {at:#x}")
                    changed+=1
            if changed!=len(expected):raise ValueError("Expected atlas delta missing")
            return dict(status="PASS_ONLY_BOUNDED_STORAGE_CAPTION_CHANGED",
                baseline_iso_sha256=BASE_SHA,candidate_iso_sha256=sha_file(latest),
                finished_iso_bytes_compared=len(a),modified_bytes=changed,
                unexplained_bytes=0,original_native_elf_intact=True,
                all_non_GRP004_18_assets_intact=True,visual_approval=False)

def build():
    incomplete=DEST.with_suffix('.incomplete')
    for p in (DEST,REPORT,AUDIT,incomplete):
        if p.exists():raise FileExistsError(p)
    if sha_file(BASE)!=BASE_SHA:raise ValueError("Prior 15a candidate changed")
    old=ATLAS_BEFORE.read_bytes();new=ATLAS_AFTER.read_bytes()
    if sha(old)!=PREVIOUS_SHA or sha(new)!="0214ab871549f3b4a8d07e1ce36f7bcb1f9154968943211a08dddf76d5268efb":
        raise ValueError("Localized bounded storage artwork SHA drift")
    if len(old)!=len(new):raise ValueError("Native atlas length changed")
    cp=subprocess.run(['cp','-c',str(BASE),str(incomplete)],capture_output=True)
    if cp.returncode:shutil.copyfile(BASE,incomplete)
    with incomplete.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        off,rec,elf=locate(m)
        if m[off:off+len(old)]!=old:raise ValueError("Original translated group4 not found")
        m[off:off+len(old)]=new
        m.flush()
    result=audit(BASE,incomplete,old,new)
    REPORT.write_text(json.dumps(dict(release='r67.15b',status='DIAGNOSTIC_AWAITING_GAMEPLAY',
        output_iso=str(DEST),candidate_sha256=result['candidate_iso_sha256'],
        item_name_scaling_from='r67.15a',reflow='Choose storage fits first 128px cell',
        save_cross_release_runtime_verified=False),indent=2,sort_keys=True)+'\n')
    AUDIT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    incomplete.rename(DEST)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':build()
