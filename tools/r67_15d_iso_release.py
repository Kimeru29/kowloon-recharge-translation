"""r67.15d append-only Golden Lock + menu texts and two atlas cells.

Builds the new diagnostic on the exact local r67.15c ISO, preserving every
other byte. Strict whole-image verification enumerates all 2.095GB bytes;
no old ISO, active PCSX2 session, card, save or prior approval is mutated.
"""
from __future__ import annotations
from collections import Counter
import hashlib,json,mmap,struct,shutil,subprocess
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.tmx import find_tmx_entry
from tools.r67_15d_gold_chains_compound import apply as patch_owners
from tools.r67_15d_visible_art import apply as patch_art

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'local/r67-candidates/67.15c-synthesis-items-ui.iso'
NEW=ROOT/'local/r67-candidates/67.15d-gold-chains-item-ui.iso'
OLD_SHA='d140cca2ce4c9603d5f89a4b0413c4dc5ddce0e1385301e9a11f376fa17368aa'
ELF_BEFORE=ROOT/'local/r67-15c-synthesis.elf'
ELF_AFTER=ROOT/'local/r67-15d-gold-chains-compound.elf'
ART_BEFORE=ROOT/'local/r67-15c-group4.BIN'
ART_AFTER=ROOT/'local/r67-15d-group4-clean.BIN'
PS4_EN=ROOT/'local/r67-15a-analysis/B_GP004-translated-v2.BIN'
REPORT=ROOT/'local/r67-15d-build.json'
AUDIT=ROOT/'local/r67-15d-whole-iso-audit.json'

def sha(b):return hashlib.sha256(b).hexdigest()

def locate(m):
    _,outer=index_iso(m)
    exe=find_record(outer,'SLPM_665.11')
    cvm=find_record(outer,'DATA.CVM')
    cvm_base=cvm.extent*2048+0x1800
    _,nested=index_iso(m,cvm_base)
    group=find_record(nested,'BLBRD/B_GP004.BIN')
    return exe,exe.extent*2048,group,cvm_base+group.extent*2048

def preflight():
    if sha_file(OLD)!=OLD_SHA:raise ValueError('Previous diagnostic changed')
    base=ELF_BEFORE.read_bytes()
    new,meta=patch_owners(base)
    if new!=ELF_AFTER.read_bytes():raise ValueError('Candidate ELF not source reproducible')
    a=ART_BEFORE.read_bytes()
    b,artreport=patch_art(a,PS4_EN.read_bytes())
    if b!=ART_AFTER.read_bytes():raise ValueError('Atlas candidate not deterministic')
    if len(a)!=len(b):raise ValueError('Group4 atlas length changed')
    allowed=set(range(0x64,0x68))
    for owner in (0x58A9F0,0x58A9F4,0x58A9F8,0x58A9FC,0x58AA04,0x38632C):
        allowed.update(range(owner,owner+4))
    changed_existing={i for i,(a0,b0) in enumerate(zip(base,new)) if a0!=b0}
    if changed_existing-allowed:raise ValueError('Unexpected prior ELF change outside exact registered owners')
    changed_chunks=[]
    for key in ('GRP004/GP004_18.TMX','GRP004/GP004_19.TMX'):
        entry=find_tmx_entry(a,key)
        if find_tmx_entry(b,key)!=entry:raise ValueError('Changed native TMX geometry')
        changed_chunks.append((entry.base_offset,entry.base_offset+entry.chunk_size,key))
    for i,(x,y) in enumerate(zip(a,b)):
        if x!=y and not any(lo<=i<hi for lo,hi,_ in changed_chunks):
            raise ValueError(f'Unregistered artwork byte {i:#x}')
    return base,new,a,b,meta,artreport,changed_existing,changed_chunks

def audit(old_path:Path,new_path:Path,prepared=None):
    if sha_file(old_path)!=OLD_SHA:raise ValueError('15c frozen predecessor SHA mismatch')
    base,new,art0,art1,meta,artmeta,elf_edits,chunks=preflight() if prepared is None else prepared
    with old_path.open('rb') as f,new_path.open('rb') as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as original,mmap.mmap(g.fileno(),0,access=mmap.ACCESS_READ) as candidate:
            if len(original)!=len(candidate):raise ValueError('Physical ISO size changed')
            e,elfpos,ge,artpos=locate(original)
            ne,elfpos2,nge,artpos2=locate(candidate)
            if (e.extent,e.record_offset,elfpos,ge.extent,ge.size,artpos)!=(
                ne.extent,ne.record_offset,elfpos2,nge.extent,nge.size,artpos2):
                raise ValueError('ISO file locations/record layout changed')
            if len(base)!=e.size or ne.size!=len(new):
                raise ValueError('Executable extent size mismatch')
            if original[elfpos:elfpos+len(base)]!=base:
                raise ValueError('15c installed ELF not identical to pinned source')
            if candidate[elfpos:elfpos+len(new)]!=new:
                raise ValueError('15d installed ELF differs from authorized patch')
            if original[artpos:artpos+len(art0)]!=art0 or candidate[artpos:artpos+len(art1)]!=art1:
                raise ValueError('Original/translated art not at expected location')
            expected={}
            classes={}
            for i in elf_edits:
                if original[elfpos+i]!=new[i]:
                    at=elfpos+i
                    expected[at]=new[i]
                    classes[at]='native_gold_chains_and_compound_pointers' if i>=0x68 else 'elf_pt_load_size'
            for i in range(len(base),len(new)):
                if original[elfpos+i]!=new[i]:
                    expected[elfpos+i]=new[i]
                    classes[elfpos+i]='append_only_gold_chains_compound_english'
            for i,(a0,b0) in enumerate(zip(art0,art1)):
                if a0!=b0:
                    at=artpos+i
                    expected[at]=b0
                    name=next(name for lo,hi,name in chunks if lo<=i<hi)
                    classes[at]='bounded_storage_label' if '_18' in name else 'condensed_full_compound'
            for index,v in enumerate(struct.pack('<I',len(new))+struct.pack('>I',len(new))):
                at=e.record_offset+10+index
                if original[at]!=v:
                    expected[at]=v
                    classes[at]='iso9660_size_both_endians'
            count=Counter()
            for start in range(0,len(original),8*1024*1024):
                a=original[start:start+8*1024*1024]
                b=candidate[start:start+8*1024*1024]
                if a==b:continue
                for i,(u,v) in enumerate(zip(a,b)):
                    if u==v:continue
                    off=start+i
                    if off not in expected or expected[off]!=v:
                        raise ValueError(f'Unexplained finished ISO byte {off:#x} {u:#x}->{v:#x}')
                    count[classes[off]]+=1
            if sum(count.values())!=len(expected):
                raise ValueError('Some expected approved modifications absent')
            return dict(status='PASS_ZERO_UNEXPLAINED_15D_FINISHED_ISO_BYTES',
                previous_sha256=OLD_SHA,new_sha256=sha_file(new_path),
                physical_iso_bytes_compared=len(original),
                changed_bytes=sum(count.values()),changed_by_owner=dict(sorted(count.items())),
                unexplained_bytes=0,other_native_routines_unchanged=True,
                original_memory_card_and_savestates_untouched=True,
                actual_gameplay_approval=False)

def build():
    temporary=NEW.with_suffix('.incomplete')
    for p in (NEW,temporary,REPORT,AUDIT):
        if p.exists():raise FileExistsError(f'Diagnostic overwrite forbidden {p}')
    baseline=preflight()
    before,after,art0,art1,meta,artmeta,elf_edits,chunks=baseline
    process=subprocess.run(['cp','-c',str(OLD),str(temporary)],capture_output=True)
    if process.returncode:shutil.copyfile(OLD,temporary)
    with temporary.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        e,at,g,artat=locate(m)
        if e.sectors != (len(after)+2047)//2048:
            raise ValueError('ELF translation overran the original ISO allocation')
        if any(m[at+len(before):at+len(after)]):
            raise ValueError('Appended text overlaps nonzero original ISO bytes')
        if m[at:at+len(before)]!=before or m[artat:artat+len(art0)]!=art0:
            raise ValueError('Approved 15c local baseline altered during build')
        m[at:at+len(after)]=after
        m[artat:artat+len(art1)]=art1
        patch_directory_record(m,e.record_offset,size=len(after))
        m.flush()
    report=audit(OLD,temporary,baseline)
    manifest=dict(release='r67.15d',status='DIAGNOSTIC_AWAITING_GAMEPLAY_SCREENSHOTS',
        old_sha256=OLD_SHA,new_sha256=report['new_sha256'],
        output_iso=str(NEW),gold_chains_and_compound=meta,
        corrected_art=artmeta,gameplay_approved=False,
        cross_release_save_runtime_verified=False)
    REPORT.write_text(json.dumps(manifest,indent=2,sort_keys=True,default=str)+'\n')
    AUDIT.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    temporary.rename(NEW)
    print(json.dumps(report,sort_keys=True))

if __name__=='__main__':build()
