"""Use the selected Help page's own 16px row pitch in its native scroll extent."""
from __future__ import annotations

from hashlib import sha256
from struct import pack

ELF_BIAS = 0xFFF80
PITCH_OWNER = 0x290A00
CONTINUATION = 0x290A08
PREIMAGES = {
    # Legacy threshold, shared height math, and lower/upper clamp.
    (0x2909F0, 0x290A90): "4eee3119a7cd097ae3281e0c6e91bd3e8c64e564eeccddb162a47bb71b231648",
    # Mode 4 row pitch and origin.
    (0x2907D0, 0x290808): "4812dd7ecc09f961b29344e2529a4c55bd9853a41e4be0682cd82523fb609a7f",
    # Native five-pixel update and terminal snap.
    (0x291128, 0x291170): "9a0bc39bfd67c1f62b83801964d0de970101d6465297405207bcced118359872",
}


def _jump(target: int) -> int:
    return 0x08000000 | (target >> 2)


def patch(source: bytes, base: int) -> tuple[bytes, dict[int, tuple[bytes, bytes]]]:
    for (start, end), expected in PREIMAGES.items():
        if sha256(source[start - ELF_BIAS:end - ELF_BIAS]).hexdigest() != expected:
            raise ValueError(f"H.A.N.T. scroll owner preimage changed at {start:#x}")
    if not 0x902F00 <= base < 0x1000000 or base % 4:
        raise ValueError("H.A.N.T. scroll helper address is outside the translation code region")

    code = pack(
        "<7I",
        0x8E2217E4,  # lw v0, 0x17e4(s1) — current page mode
        0x2442FFFC,  # addiu v0, v0, -4 — compare with the Help mode
        0x14400002,  # bnez v0, finish
        0x3C0241A8,  # lui v0, 0x41a8 — default pitch 21.0 in delay slot
        0x3C024180,  # lui v0, 0x4180 — Help pitch 16.0
        _jump(CONTINUATION),
        0x44821800,  # mtc1 v0, f3 — the original pitch register
    )
    offset = PITCH_OWNER - ELF_BIAS
    return code, {
        offset: (bytes.fromhex("a841023c"), pack("<I", _jump(base))),
        offset + 4: (bytes.fromhex("00188244"), bytes(4)),
    }
