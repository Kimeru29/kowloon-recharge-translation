"""r67.15c full ISO builder and exact entire-disc audit.

Supersedes diagnostic r67.15b; preserves b, z, y, t and q binaries, their
original saves and every unrelated native UI/sprite byte. Adds exact PS4
formatted synthesis messages and replaces INFO with official Details.
"""
from __future__ import annotations
import json,mmap,shutil,struct,subprocess
from collections import Counter
from pathlib import Path

from tools.iso9660_patch import index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_15c_synthesis_prompts import apply as patch_synthesis,sha as digest_elf
from tools.r67_15c_details_footer import apply as patch_footer,sha as digest_art,TEX
from tools.tmx import find_tmx_entry
from tools.r67_14y_release import verify_save_identity
from tools.r67_14y_inspection_save import validate_result

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'local/r67-candidates/67.15b-item-storage-compact.iso'
BASE_SHA="8c63c86d64de7cb770bab350a8728fe76db5e6825693b3614d9c559e408f7704"
PREV_ELF=ROOT/'local/r67-15b-installed.elf'
PREV_ELF_SHA="e250cf4822ad70fa9597d14d837513c97cce065c30d6f0a8f945a782293a8bd6"
OUT_ELF=ROOT/'local/r67-15c-synthesis.elf'
DEST=ROOT/'local/r67-candidates/67.15c-synthesis-items-ui.iso'
REPORT=ROOT/'local/r67-15c-build.json'
AUDIT=ROOT/'local/r67-15c-whole-iso-audit.json'
GP004_BASE_SHA="0214ab871549f3b4a8d07e1ce36f7bcb1f9154968943211a08dddf76d5268efb"
NAME_CHECKS={(0xd660,0xd664),(0xd718,0xd71c)}

def locate(b):
    _,outer=index_iso(b)
    ex=find_record(outer,'SLPM_665.11')
    cvm=find_record(outer,'DATA.CVM')
    cvm_base=cvm.extent*2048+0x1800
    _,nested=index_iso(b,cvm_base)
    art=find_record(nested,'BLBRD/B_GP004.BIN')
    return ex,ex.extent*2048,art,cvm_base+art.extent*2048

def preflight():
    if sha_file(BASE)!=BASE_SHA:raise ValueError("Prior diagnostic ISO SHA drift")
    a=PREV_ELF.read_bytes()
    if digest_elf(a)!=PREV_ELF_SHA:raise ValueError("Prior installed ELF changed")
    b,meta=patch_synthesis(a,PREV_ELF_SHA)
    if OUT_ELF.read_bytes()!=b:raise ValueError("Native PS4 synthesis prompt patch not deterministic")
    verify_save_identity(b)
    validate_result(b)
    expected_art=None
    with BASE.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
        exe,exoff,rec,artoff=locate(mm)
        if mm[exoff:exoff+exe.size]!=a:raise ValueError("Unexpected executable inside 15b ISO")
        expected_art=bytes(mm[artoff:artoff+rec.size])
    if digest_art(expected_art)!=GP004_BASE_SHA:
        raise ValueError("Original 15b group4 art hash changed")
    rewritten,artreport=patch_footer(expected_art)
    return a,b,meta,expected_art,rewritten,artreport

def audit(previous:Path,current:Path,prepared=None):
    if sha_file(previous)!=BASE_SHA:raise ValueError("15b ISO SHA drift")
    if prepared is None:prepared=preflight()
    a,b,metadata,oldart,newart,artmeta=prepared
    with previous.open('rb') as f,current.open('rb') as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as left,mmap.mmap(
            g.fileno(),0,access=mmap.ACCESS_READ) as right:
            if len(left)!=len(right):raise ValueError("Full ISO size changed")
            oldrec,off,oldtex,texoff=locate(left)
            nextrec,nextoff,nexttex,nexttexoff=locate(right)
            if (oldrec.extent,off,texoff,oldtex.size)!=(
                nextrec.extent,nextoff,nexttexoff,nexttex.size):
                raise ValueError("Installed ELF or native texture relocated")
            if nextrec.size!=len(b):
                raise ValueError("Installed ISO9660 executable size wrong")
            if left[off:off+len(a)]!=a or right[off:off+len(b)]!=b:
                raise ValueError("Installed ELF does not match approved synthesis transform")
            if left[texoff:texoff+len(oldart)]!=oldart:
                raise ValueError("Prior group4 art changed")
            if right[texoff:texoff+len(newart)]!=newart:
                raise ValueError("New details art differs from deterministic build")
            expected={}
            owners={}
            for i in range(len(b)):
                oldval=a[i] if i<len(a) else left[off+i]
                if oldval!=b[i]:
                    at=off+i
                    expected[at]=b[i]
                    owners[at]="append_english_synthesis_data" if i>=len(a) else (
                        "PT_LOAD_size_field" if 0x64<=i<0x68 else
                        "native_synthesis_pointer_and_LUI_ADDIU"
                    )
            e=find_tmx_entry(oldart,TEX)
            for i,(x,y) in enumerate(zip(oldart,newart)):
                if x!=y:
                    if not e.base_offset<=i<e.base_offset+e.chunk_size:
                        raise ValueError("Details caption changed another sprite")
                    expected[texoff+i]=y
                    owners[texoff+i]="english_details_caption"
            sizepair=struct.pack('<I',len(b))+struct.pack('>I',len(b))
            for i,v in enumerate(sizepair):
                at=oldrec.record_offset+10+i
                if left[at]!=v:
                    expected[at]=v
                    owners[at]="iso9660_executable_size_both_endians"
            counts=Counter()
            for pos in range(0,len(left),8*1024*1024):
                x=left[pos:pos+8*1024*1024]
                y=right[pos:pos+8*1024*1024]
                if x==y:continue
                for k,(u,v) in enumerate(zip(x,y)):
                    if u==v:continue
                    at=pos+k
                    if at not in expected or expected[at]!=v:
                        raise ValueError(f"Unexplained whole-ISO byte {at:#x} ({u:#x}->{v:#x})")
                    counts[owners[at]]+=1
            if sum(counts.values())!=len(expected):
                raise ValueError("Finished disc does not contain all expected owner changes")
            return dict(status="PASS_FULL_DISC_EXACT_OWNED_CHANGES",
                baseline_sha256=BASE_SHA,candidate_sha256=sha_file(current),
                full_iso_bytes_compared=len(left),modified_bytes=sum(counts.values()),
                diff_by_owner=dict(sorted(counts.items())),unexplained_bytes=0,
                english_synthesis_owner_count=len(metadata["owners"]),
                original_approved_lion_dialogue_room_save_preserved=True,
                user_runtime_approved=False)

def build():
    temp=DEST.with_suffix('.incomplete')
    for p in (DEST,temp,REPORT,AUDIT):
        if p.exists():raise FileExistsError("Refuse overwrite prior candidate/report "+str(p))
    packaged=preflight()
    old,b,meta,oldart,newart,artmeta=packaged
    cp=subprocess.run(['cp','-c',str(BASE),str(temp)],capture_output=True)
    if cp.returncode:shutil.copyfile(BASE,temp)
    with temp.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as mm:
        rec,off,grp,artoff=locate(mm)
        if rec.sectors!=(len(b)+2047)//2048:
            raise ValueError("Synthesis translation no longer fits original ELF ISO sector allocation")
        if any(mm[off+len(old):off+len(b)]):
            raise ValueError("No free executable sector bytes to extend without relocation")
        if mm[off:off+len(old)]!=old or mm[artoff:artoff+len(oldart)]!=oldart:
            raise ValueError("Base content changed during ISO build")
        mm[off:off+len(b)]=b
        mm[artoff:artoff+len(newart)]=newart
        patch_directory_record(mm,rec.record_offset,size=len(b))
        mm.flush()
    proof=audit(BASE,temp,packaged)
    REPORT.write_text(json.dumps(dict(release='r67.15c',
        status='DIAGNOSTIC_PENDING_USER_RUNTIME_SCREENSHOTS',
        source_iso_sha256=BASE_SHA,
        new_iso_sha256=proof['candidate_sha256'],
        installed_elf_sha256=digest_elf(b),
        installed_elf_size=len(b),
        official_compound_prompts=meta['owners'],
        official_details=artmeta,
        output_iso=str(DEST),native_save_runtime_compatibility_verified=False,
        gameplay_approved=False),sort_keys=True,indent=2)+'\n')
    AUDIT.write_text(json.dumps(proof,sort_keys=True,indent=2)+'\n')
    temp.rename(DEST)
    print(json.dumps(proof,sort_keys=True))

if __name__=='__main__':
    build()
