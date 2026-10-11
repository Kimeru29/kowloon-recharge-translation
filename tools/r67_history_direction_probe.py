"""r67 START-history ONLY diagnostic: preserve native style, force horizontal flag.

Native 0x190A50 was previously patched to compute a2=(style!=0), then
0x188AD0 stores that direction flag at font object +0x24. History's
styles 3/4/5 therefore remain vertical. Normal DG's style 0 is horizontal.
The paused log's 0x255E88 call is a distinct owner, allowing a private
copy of the 0x190A50 constructor and a two-site patch: clone orientation
and retarget ONLY history's constructor call. No shared renderer mutations.

This emits an experiment, never a release; requires visual approval.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

BASE_SHA = "7d154da2785f49a649df5754a2146085af8fdf2af1a2928d49a2f642ef2c1d4e"
VA_MINUS_OFFSET = 0xFFF80
FACTORY_START_VA = 0x190A50
FACTORY_END_VA = 0x190C90
FLAG_VA = 0x190AB0
HISTORY_JAL_VA = 0x255E88
OLD_HISTORY_JAL = 0x0C064294  # jal 0x190a50
VERTICAL_FLAG_WORD = 0x0010302B  # approved sltu a2,zero,s0 (1 for history styles 3/4/5)
HORIZONTAL_FLAG_WORD = 0x24060000  # addiu a2,zero,0


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _jal(target: int) -> int:
    if target & 3:
        raise ValueError("Unaligned JAL target")
    return 0x0C000000 | ((target >> 2) & 0x03FFFFFF)


def _validate_relocation(blob: bytes, start_va: int, end_va: int) -> dict:
    """Internal MIPS PC-relative branches must remain inside the cloned function."""
    out = {"relative_branches": 0, "external_absolute_calls": 0}
    for offset in range(0, len(blob), 4):
        va = start_va + offset
        word = struct.unpack_from("<I", blob, offset)[0]
        opcode = word >> 26
        # PC-relative branch family, including regimm and COP1 branch variants.
        relative = opcode in (1, 4, 5, 6, 7, 20, 21, 22, 23)
        if opcode == 17 and ((word >> 21) & 0x1F) == 8:
            relative = True
        if relative:
            immediate = word & 0xFFFF
            if immediate & 0x8000:
                immediate -= 0x10000
            dest = va + 4 + (immediate << 2)
            if not start_va <= dest < end_va:
                raise ValueError(f"Clone has relative branch outside function {va:#x} -> {dest:#x}")
            out["relative_branches"] += 1
        if opcode == 2:  # absolute non-linking J cannot be assumed safe
            raise ValueError(f"Clone contains absolute J at {va:#x}")
        if opcode == 3:
            target = ((va + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)
            if start_va <= target < end_va:
                raise ValueError(f"Internal JAL needs relocation: {va:#x} -> {target:#x}")
            out["external_absolute_calls"] += 1
    return out


def apply(baseline: bytes, pristine: bytes) -> tuple[bytes, dict]:
    if _sha(baseline) != BASE_SHA:
        raise ValueError("67.07 staged baseline drift")
    fo, va, size, reserve, flags = (
        struct.unpack_from("<I", baseline, pos)[0]
        for pos in (0x58, 0x5C, 0x64, 0x68, 0x6C)
    )
    if (fo, va, fo + size, reserve, flags) != (0x803150, 0x902F00, len(baseline), 0x100000, 7):
        raise ValueError("Translation PT_LOAD bounds unexpectedly changed")
    original_start = FACTORY_START_VA - VA_MINUS_OFFSET
    original_end = FACTORY_END_VA - VA_MINUS_OFFSET
    original_factory = baseline[original_start:original_end]
    approved_expected = bytearray(pristine[original_start:original_end])
    if struct.unpack_from("<I", approved_expected, FLAG_VA - FACTORY_START_VA)[0] != 0x24060001:
        raise ValueError("Pristine constructor has unexpected original direction word")
    struct.pack_into("<I", approved_expected, FLAG_VA - FACTORY_START_VA, VERTICAL_FLAG_WORD)
    if original_factory != approved_expected:
        raise ValueError("Native constructor has unexpected changes beyond approved direction selector")
    if len(original_factory) != FACTORY_END_VA - FACTORY_START_VA or len(original_factory) & 3:
        raise ValueError("Invalid constructor code size")
    if struct.unpack_from("<I", original_factory, FLAG_VA - FACTORY_START_VA)[0] != VERTICAL_FLAG_WORD:
        raise ValueError("Native constructor orientation preimage mismatch")
    _validate_relocation(original_factory, FACTORY_START_VA, FACTORY_END_VA)
    callsite = HISTORY_JAL_VA - VA_MINUS_OFFSET
    if struct.unpack_from("<I", baseline, callsite)[0] != OLD_HISTORY_JAL:
        raise ValueError("History-only JAL preimage changed")
    staged = bytearray(baseline)
    while len(staged) & 3:
        staged.append(0)
    clone_va = va + len(staged) - fo
    if clone_va & 3 or clone_va >= va + reserve or (clone_va >> 28) != (HISTORY_JAL_VA >> 28):
        raise ValueError("Clone is not executable/reachable")
    clone = bytearray(original_factory)
    struct.pack_into("<I", clone, FLAG_VA - FACTORY_START_VA, HORIZONTAL_FLAG_WORD)
    if len(staged) + len(clone) - fo > reserve:
        raise ValueError("Clone exceeds translation memory reserve")
    staged.extend(clone)
    struct.pack_into("<I", staged, callsite, _jal(clone_va))
    struct.pack_into("<I", staged, 0x64, len(staged) - fo)
    modified = [i for i,(a,b) in enumerate(zip(baseline,staged)) if a!=b]
    allowed = set(range(callsite,callsite+4)) | set(range(0x64,0x68))
    if any(i not in allowed for i in modified):
        raise ValueError("Changed unrelated original ELF byte")
    for identity in (b"SLPM-66511", b"BISLPM-66511Save"):
        if identity not in staged:
            raise ValueError("Save ID lost")
    return bytes(staged), {
        "status": "DIAGNOSTIC_ONLY_NEEDS_VISUAL_TEST",
        "source_elf_sha256": BASE_SHA,
        "result_elf_sha256": _sha(staged),
        "original_constructor": f"{FACTORY_START_VA:#x}-{FACTORY_END_VA:#x}",
        "history_only_callsite_va": f"{HISTORY_JAL_VA:#x}",
        "history_only_callsite_offset": f"{callsite:#x}",
        "clone_va": f"{clone_va:#x}",
        "style_ids_modified": False,
        "constructor_orientation_word": [f"{VERTICAL_FLAG_WORD:#x}",f"{HORIZONTAL_FLAG_WORD:#x}"],
        "callsite_word": [f"{OLD_HISTORY_JAL:#x}",f"{_jal(clone_va):#x}"],
        "instruction_bytes_cloned": len(clone),
        "changed_existing_elf_bytes": modified,
        "preserves_original_dialogue_path": True,
        "preserves_approved_help": True,
        "preserves_saves": True,
        "release_approved": False,
        "scope_note": "Only ADV LOG 0x255E88 calls the horizontally oriented cloned constructor; shared native constructor untouched.",
    }


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--pristine",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing to overwrite history diagnostic")
    output, report=apply(a.baseline.read_bytes(),a.pristine.read_bytes())
    a.output.write_bytes(output)
    a.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True))


if __name__=="__main__":
    main()
