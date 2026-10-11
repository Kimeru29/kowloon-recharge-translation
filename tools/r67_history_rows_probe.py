"""r67.10 isolated ADV history horizontal-row diagnostic (not release).

Preserve r67.09 verified history-only horizontal font constructor. The native
history log still places successive Japanese columns at X += 39, with a nearly
constant Y. Swap ONLY the two history-specific position argument loads feeding
the constructor, reinterpreting those positions as horizontal English rows.
This is a bounded proof; scrolling and longer wrapping require visual review.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

INPUT_SHA256 = "76f71fc7eb62fea52ff347b8e1464a7f217066af288eba17802c8a6eb5e4cd02"
VA_MINUS_OFFSET = 0xFFF80
X_LOAD_VA = 0x253CE8
Y_LOAD_VA = 0x253CEC
EXPECTED = {
    X_LOAD_VA - VA_MINUS_OFFSET: (0xC62C0080, 0xC62C0084),  # lwc1 f12,0x80(s1) -> 0x84
    Y_LOAD_VA - VA_MINUS_OFFSET: (0xC62D0084, 0xC62D0080),  # lwc1 f13,0x84(s1) -> 0x80
}

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def apply(baseline:bytes)->tuple[bytes,dict]:
    if sha(baseline) != INPUT_SHA256:
        raise ValueError("Unexpected r67.09 history-only constructor: checksum mismatch")
    output=bytearray(baseline)
    for at,(old,new) in EXPECTED.items():
        if struct.unpack_from("<I",output,at)[0]!=old:
            raise ValueError(f"History X/Y load preimage drift at {at:#x}")
        struct.pack_into("<I",output,at,new)
    diff=[at for at,(a,b) in enumerate(zip(baseline,output)) if a!=b]
    allowed={i for at in EXPECTED for i in range(at,at+4)}
    if set(diff)-allowed:
        raise ValueError("Unexpected changes to approved executable")
    for identifier in (b"SLPM-66511",b"BISLPM-66511Save"):
        if identifier not in output:
            raise ValueError("Save namespace damaged")
    return bytes(output),{
        "status":"DIAGNOSTIC_ONLY_PENDING_VISUAL_TEST",
        "input_sha256":INPUT_SHA256,
        "output_sha256":sha(output),
        "changed_byte_offsets":[hex(i) for i in diff],
        "swapped_history_coordinates":[hex(X_LOAD_VA),hex(Y_LOAD_VA)],
        "history_vertical_flag_fix_preserved":True,
        "protected_basic_attack_untouched":True,
        "shared_constructor_untouched":True,
        "style_ids_unchanged":True,
        "scrolling_and_wrapping_unverified":True,
        "approved_release":False
    }

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    opts=p.parse_args()
    if opts.output.exists() or opts.report.exists():
        raise FileExistsError("Refusing to overwrite diagnostic")
    blob,report=apply(opts.baseline.read_bytes())
    opts.output.write_bytes(blob)
    opts.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__":
    main()
