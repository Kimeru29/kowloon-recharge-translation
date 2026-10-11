"""67.07 feedback baseline: roll back rejected target UI geometry, freeze Basic Attack.

The user's 67.06 screenshot disproves the hypothesis that four apparent X origins
move the L1/R1 icons with the caption. Restore the 67.05 native geometry and
previous short caption without changing the 67.06-approved H.A.N.T. page.
This is an INTERIM containment candidate, not a fix for the full caption.
"""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from tools.r67_06_layout import TARGET_X, ROTATE_SLOT, ROTATE_LENGTH, render_text
BASE_SHA="0b6786e9e69b490117306df543247871ff688ba791a1a7c698580476a78a36ed"
EXPECTED_6705_SHA="a1e5665be7ee71d1ad6b5b9f442d8155abc313a8303537962dc4b4ebe61a8f92"
def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def apply(previous:bytes, approved6705:bytes, manifest:dict)->tuple[bytes,dict]:
    if sha(previous)!=BASE_SHA or sha(approved6705)!=EXPECTED_6705_SHA:
        raise ValueError("67.06/67.05 fingerprint mismatch")
    old=render_text("Change target").ljust(ROTATE_LENGTH,b"\0")
    restored=render_text("Target").ljust(ROTATE_LENGTH,b"\0")
    if previous[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]!=old:
        raise ValueError("Current target label is not the screenshot-rejected experiment")
    if approved6705[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]!=restored:
        raise ValueError("67.05 label preimage changed")
    candidate=bytearray(previous)
    candidate[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]=restored
    whitelist=set(range(ROTATE_SLOT,ROTATE_SLOT+ROTATE_LENGTH))
    for pos,(original,shifted) in TARGET_X.items():
        if struct.unpack_from("<I",previous,pos)[0]!=shifted or struct.unpack_from("<I",approved6705,pos)[0]!=original:
            raise ValueError(f"Unexpected control geometry at {pos:#x}")
        struct.pack_into("<I",candidate,pos,original)
        whitelist.update(range(pos,pos+4))
    # The user explicitly approved the Basic Attack page rendered by 67.06:
    # freeze its pointer table, glyph metadata and 67.06 English text content.
    page=next(p for p in manifest["pages"] if p["key"]=="basic_attack")
    fo,va=struct.unpack_from("<II",previous,0x58)
    off=fo+struct.unpack_from("<I",previous,page["descriptor_offset"])[0]-va
    table_length=4*(page["rows"]+1)
    if candidate[off:off+table_length]!=previous[off:off+table_length]:
        raise ValueError("Approved Basic Attack pointer table changed")
    if candidate[page["metadata_descriptor_offset"]:page["metadata_descriptor_offset"]+4]!=previous[page["metadata_descriptor_offset"]:page["metadata_descriptor_offset"]+4]:
        raise ValueError("Approved Basic Attack icon atlas changed")
    pointers=struct.unpack_from(f"<{page['rows']}I",previous,off)
    for pointer in pointers:
        if pointer in (0x795fb8,0x795fbc):continue
        ix=fo+pointer-va
        text=previous[ix:previous.find(b"\0",ix)]
        if candidate[ix:ix+len(text)+1]!=text+b"\0":
            raise ValueError("Approved Basic Attack string changed")
    for pos,(a,b) in enumerate(zip(previous,candidate)):
        if a!=b and pos not in whitelist:
            raise ValueError(f"Unexpected drift in frozen executable at {pos:#x}")
    if len(candidate)!=len(previous):
        raise ValueError("Unexpected ELF growth")
    for name in ("SLPM-66511","BISLPM-66511Save"):
        if name.encode() not in candidate: raise ValueError("Save identity changed")
    return bytes(candidate),dict(previous_sha256=sha(previous),sha256=sha(candidate),previous_size=len(previous),
        new_size=len(candidate),modified_offsets=sorted(whitelist),frozen_basic_attack=True,
        restored_67_05_target_geometry=True,
        unresolved=["Full Change target presentation","Vertical ADV history","Old man entry bubble and glyph layout","Lion Statue acquisition card clipping"],
        gameplay_approved=False)

def main():
    p=argparse.ArgumentParser()
    for key in ("baseline","approved-6705","manifest","output","report"):p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise FileExistsError("Refusing overwrite")
    raw,data=apply(a.baseline.read_bytes(),a.approved_6705.read_bytes(),json.loads(a.manifest.read_text()))
    a.output.write_bytes(raw);a.report.write_text(json.dumps(data,indent=2)+"\n")
    print('67.07 containment candidate',data["sha256"])
if __name__=="__main__":main()
