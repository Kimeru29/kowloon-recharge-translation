"""Read-only ownership audit for 67.04 dialogue renderer investigations.

This does NOT claim visual START-history or story-comment ownership. It verifies
known native constructor callsites, the previously shipped experimental shim,
and byte-frozen code regions before any subsequent binary-editing experiment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.companion_hud_data import COMPANION_COMMENT_DATA
from tools.r67_playtest_history import JAL_FILE_OFFSET, JAL_PREIMAGE, shim_bytes

# Distinct native font-canvas callsites; some belong to the approved ADV/DG UI.
NATIVE_FONT_CALLSITES = (
    0x8B500, 0x8B558, 0x94614, 0x94B1C, 0x94B74,
    0x14F8A4, 0x14F938, 0x14F9DC, 0x14FB90, 0x151614, 0x159D54,
)
EXPECTED_INPUT_SHA256 = (
    "6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794",
    "aba86a5fd8b1f81e12c50f5c1d15cb40fdb44d8fffa50b3ee7530128f77b4727",
    "c65270ff6ff8dcfcd80dcfdcf4e49cb8171080c8e29b710941aad356af586eb8",
    "1913153bc67d4b2febc444cedfa5fb62fdc5aeaed94d077762416f3688cb24a8",
)
PRESERVED_REGIONS = {
    "approved_dg_body": (0x14E940, 0x14E980),
    "approved_dg_speaker": (0x150030, 0x150090),
    "other_two_canvas_constructor": (0x151580, 0x151650),
    "history_constructor_caller": (0x159D20, 0x159D78),
    "approved_l1_visibility": (0x659E0, 0x65C80),
    "approved_afk_table_prefix": (0x360000, 0x365000),
}


def _u32(blob: bytes, offset: int) -> int:
    return struct.unpack_from("<I", blob, offset)[0]


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def audit(pristine: bytes, before_history: bytes, with_history: bytes,
          release_6703: bytes) -> dict:
    """Fail closed if known constructor provenance or accepted bytes drift.

    Input ELF must be the *pre-ROFS* build, not the final ISO executable, because
    the ISO builder legitimately rewrites ROFS file-location records.
    """
    if _u32(before_history, JAL_FILE_OFFSET) != JAL_PREIMAGE:
        raise ValueError("Original history-candidate constructor callsite changed")
    candidates = tuple(i for i in range(0x200, len(pristine) - 3, 4)
                       if _u32(pristine, i) == JAL_PREIMAGE)
    if candidates != NATIVE_FONT_CALLSITES:
        raise ValueError("Pristine native constructor caller inventory changed")
    first_mod = _u32(with_history, JAL_FILE_OFFSET)
    if (first_mod & 0xFC000000) != 0x0C000000:
        raise ValueError("History candidate no longer uses a MIPS JAL")
    if first_mod == JAL_PREIMAGE or _u32(release_6703, JAL_FILE_OFFSET) != first_mod:
        raise ValueError("Shipped 67.03 history shim provenance changed")
    helper_va = (first_mod & 0x03FFFFFF) << 2
    fo, va = _u32(with_history, 0x58), _u32(with_history, 0x5C)
    helper_pos = fo + helper_va - va
    if (with_history[helper_pos:helper_pos + len(shim_bytes())] != shim_bytes() or
            release_6703[helper_pos:helper_pos + len(shim_bytes())] != shim_bytes()):
        raise ValueError("Experimental font-layout helper changed")
    # Separately proven accepted ADV/DG speaker orientation, not another
    # candidate for modifying without runtime attribution.
    if (_u32(release_6703, 0x151614) != JAL_PREIMAGE or
            _u32(release_6703, 0x151608) != 0x24060000):
        raise ValueError("Previously accepted independent canvas path changed")
    preserved = {}
    for label, (begin, end) in PRESERVED_REGIONS.items():
        if with_history[begin:end] != release_6703[begin:end]:
            raise ValueError(f"Previously shipped renderer region changed: {label}")
        preserved[label] = _sha(release_6703[begin:end])
    story = [r for r in COMPANION_COMMENT_DATA if r[0] in (0x3C1A50, 0x3C1F38)]
    if len(story) != 2 or any(len(row[4]) == 0 for row in story):
        raise ValueError("Independent dungeon story-comment text ownership drifted")
    if tuple(_sha(blob) for blob in (pristine, before_history, with_history, release_6703)) != EXPECTED_INPUT_SHA256:
        raise ValueError("67.04 audit input ELF fingerprint mismatch")
    return {
        "candidate_status": "static provenance only; START modal NOT runtime-attributed",
        "pristine_native_constructor_callsites": [hex(n) for n in candidates],
        "experimental_shim_source_file_offset": hex(JAL_FILE_OFFSET),
        "experimental_shim_target_va": hex(helper_va),
        "experimental_shim_unchanged_since_6702": True,
        "independent_approved_constructor": hex(0x151614),
        "accepted_region_sha256": preserved,
        "dungeon_story_comment_sources": [
            {"source": hex(row[0]), "official": row[2], "aliases": [hex(n) for n in row[4]]}
            for row in story
        ],
        "unverified": [
            "START-key history: constructor hook not proven to own visible vertical text",
            "Chamber of Lions: blue background geometry owner not identified",
            "First fight: transition-specific text positioning owner not identified",
        ],
        "release_allowed": False,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("pristine", "before-history", "with-history", "release-6703", "report"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    result = audit(args.pristine.read_bytes(), args.before_history.read_bytes(),
                   args.with_history.read_bytes(), args.release_6703.read_bytes())
    if args.report.exists():
        raise FileExistsError("Refusing to replace audit report")
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
