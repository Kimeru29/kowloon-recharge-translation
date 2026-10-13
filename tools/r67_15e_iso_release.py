"""r67.15e diagnostic ISO and byte-accurate whole-disc change classification.

Base is the user's gameplay-approved r67.15d ISO. Exactly two existing
ELF offsets may change: floating 'Can't' text table pointer and the native
white-bubble constructor branch, plus required ELF/ISO9660 sizes and
append-only private helper/text. No original ISOs, assets, save files,
active PCSX2 sessions or memory cards are changed.
"""
from __future__ import annotations
from collections import Counter
import json,mmap,shutil,struct,subprocess
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_15e_compound_action_bubble import apply as patch,sha,JUMP_SITE,ACTION_PTR_OFF,BIAS

ROOT=Path(__file__).resolve().parents[1]
PREVIOUS_ISO=ROOT/'local/r67-candidates/67.15d-gold-chains-item-ui.iso'
CANDIDATE_ISO=ROOT/'local/r67-candidates/67.15e-compound-bubble.iso'
SOURCE_ELF=ROOT/'local/r67-15d-gold-chains-compound.elf'
CANDIDATE_ELF=ROOT/'local/r67-15e-compound-bubble.elf'
MANIFEST=ROOT/'local/r67-15e-release.json'
AUDIT=ROOT/'local/r67-15e-whole-iso-audit.json'
PREVIOUS_SHA='5d5850b660e92d9fd0dcb11456519d99b060cbaae131ebf48f6d0f80262a446d'

def where(iso):
    _,records=index_iso(iso)
    e=find_record(records,'SLPM_665.11')
    return e,e.extent*2048

def preflight():
    if sha_file(PREVIOUS_ISO)!=PREVIOUS_SHA:raise ValueError('Previously user-approved ISO drift')
    old=SOURCE_ELF.read_bytes()
    new,info=patch(old)
    if new!=CANDIDATE_ELF.read_bytes():raise ValueError('Nonreproducible 15e ELF')
    whitelist=set(range(0x64,0x68))
    for off in (ACTION_PTR_OFF,JUMP_SITE-BIAS):whitelist.update(range(off,off+4))
    existing={i for i,(a,b) in enumerate(zip(old,new)) if a!=b}
    if not existing or existing-whitelist:
        raise ValueError('Approved 15d ELF existing owner modified outside the two exact sites')
    return old,new,info,existing

def audit(previous:Path,latest:Path,prep=None):
    if sha_file(previous)!=PREVIOUS_SHA:raise ValueError('Previous ISO changed during audit')
    before,after,proof,edits=preflight() if prep is None else prep
    with previous.open('rb') as f,latest.open('rb') as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as left,mmap.mmap(g.fileno(),0,access=mmap.ACCESS_READ) as right:
            if len(left)!=len(right):raise ValueError('ISO physical length differs')
            re,at=where(left);rn,bt=where(right)
            if (re.extent,re.record_offset,at)!=(rn.extent,rn.record_offset,bt):
                raise ValueError('Native executable moved')
            if re.size!=len(before) or rn.size!=len(after):
                raise ValueError('ELF embedded size metadata incorrect')
            if left[at:at+len(before)]!=before or right[at:at+len(after)]!=after:
                raise ValueError('Wrong executable bytes installed')
            expected={}
            classes={}
            for i in edits:
                if left[at+i]!=after[i]:
                    pos=at+i
                    expected[pos]=after[i]
                    classes[pos]='elf_segment_size' if i<0x68 else (
                        'conditional_compound_bubble_hook' if i==JUMP_SITE-BIAS else 'same_item_action_pointer')
            for i in range(len(before),len(after)):
                if left[at+i]!=after[i]:
                    pos=at+i
                    expected[pos]=after[i]
                    classes[pos]='appended_private_helper_and_ps4_english_label'
            canonical=struct.pack('<I',len(after))+struct.pack('>I',len(after))
            for i,val in enumerate(canonical):
                pos=re.record_offset+10+i
                if left[pos]!=val:
                    expected[pos]=val
                    classes[pos]='iso9660_executable_size_both_endians'
            result=Counter()
            for block in range(0,len(left),8*1024*1024):
                a=left[block:block+8*1024*1024]
                b=right[block:block+8*1024*1024]
                if a==b:continue
                for offset,(x,y) in enumerate(zip(a,b)):
                    if x==y:continue
                    loc=block+offset
                    if loc not in expected or expected[loc]!=y:
                        raise ValueError(f'Unexplained finished-disc byte {loc:#x}: {x:#x}->{y:#x}')
                    result[classes[loc]]+=1
            if sum(result.values())!=len(expected):
                raise ValueError('An expected approved change did not appear in candidate')
            return dict(status='PASS_EXACT_15D_BASELINE_ZERO_UNEXPLAINED',
                baseline_15d_iso_sha256=PREVIOUS_SHA,
                candidate_iso_sha256=sha_file(latest),
                complete_disc_bytes_compared=len(left),
                modified_bytes=sum(result.values()),
                byte_owner_summary=dict(sorted(result.items())),
                unexplained_bytes=0,
                all_previous_15d_group4_graphics_identical=True,
                all_save_and_gameplay_native_routines_identical=True,
                user_gameplay_approved=False)

def build():
    tmp=CANDIDATE_ISO.with_suffix('.incomplete')
    for p in (CANDIDATE_ISO,tmp,MANIFEST,AUDIT):
        if p.exists():raise FileExistsError('Refuse to replace prior release '+str(p))
    prep=preflight()
    before,after,info,edits=prep
    subprocess.run(['cp','-c',str(PREVIOUS_ISO),str(tmp)],check=True)
    with tmp.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as m:
        rec,pos=where(m)
        if rec.sectors!=(len(after)+2047)//2048:
            raise ValueError('Executable exceeds original sector allocation')
        if any(m[pos+len(before):pos+len(after)]):
            raise ValueError('New helper overlaps existing nonzero ISO data')
        if m[pos:pos+len(before)]!=before:
            raise ValueError('Game image baseline ELF drift during install')
        m[pos:pos+len(after)]=after
        patch_directory_record(m,rec.record_offset,size=len(after))
        m.flush()
    proof=audit(PREVIOUS_ISO,tmp,prep)
    MANIFEST.write_text(json.dumps(dict(release='r67.15e',status='DIAGNOSTIC_NOT_GAMEPLAY_APPROVED',
        output_iso=str(CANDIDATE_ISO),candidate_sha256=proof['candidate_iso_sha256'],
        translated_action=info,source_sha256=PREVIOUS_SHA,
        live_savestate_memorycard_or_emulator_modified=False,
        runtime_save_compatibility_verified=False),indent=2,sort_keys=True)+'\n')
    AUDIT.write_text(json.dumps(proof,indent=2,sort_keys=True)+'\n')
    tmp.rename(CANDIDATE_ISO)
    print(json.dumps(proof,sort_keys=True))

if __name__=='__main__':
    build()
