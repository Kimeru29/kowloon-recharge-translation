"""Rebuild the START history window using the locked chronological row constructor."""

from hashlib import sha256
from struct import pack

from tools.r67_chamber_story_text_only import Assembly, ELF_BIAS, _i, _jal, _r
from tools.r67o_choices import _clone, _jump, _patch

NAV_ENTRY = 0x253DB4
ROW_START, ROW_END = 0x253AC0, 0x253D98
ROW_SHA = "88f683cc1b5ee68cef6e3e0fad80bdd420a3953fb2030582e4e370a6df8c0a03"
OWNER_OFFSETS = (NAV_ENTRY - ELF_BIAS, NAV_ENTRY + 4 - ELF_BIAS)


def patch(source: bytes, base: int) -> tuple[bytes, dict]:
    rows = _clone(source, ROW_START, ROW_END)
    if sha256(rows).hexdigest() != ROW_SHA:
        raise ValueError("START history row constructor drift")
    m = Assembly()
    owner, private, ordinal, limit = 20, 17, 18, 22
    key, age, step, test, temp = 3, 9, 10, 11, 12

    def branch(op, rs, rt, label):
        m.branch(op, rs, rt, label)
        m.emit(0)

    # The hook delay slot supplies the pad base. Preserve the stock dispatch
    # registers on fallback (including a1/a2/a3/t0 for the native states).
    m.emit(_i(37, 2, key, 0x39D2))
    m.emit(_i(35, 28, temp, -0x1DAC))
    m.emit(_i(35, temp, limit, 0x3110))
    m.emit(_i(10, limit, test, 13))
    branch(5, test, 0, "native")
    m.emit(_i(10, limit, test, 255))
    branch(5, test, 0, "bounded")
    m.emit(_i(9, 0, limit, 255))
    m.label("bounded")
    m.emit(_i(9, limit, limit, -12))
    m.emit(_i(33, private, age, 0x50))
    # A fast press advances one visible page. The stock renderer counted
    # columns; thirteen records would skip a row in the twelve-row layout.
    m.emit(_i(33, private, step, 0x7A))
    m.emit(_i(12, key, test, 8))
    branch(5, test, 0, "older")
    m.emit(_i(12, key, test, 4))
    branch(5, test, 0, "newer")
    m.emit(_i(37, 2, test, 0x39CC))
    m.emit(_i(12, test, test, 0x10))
    branch(4, test, 0, "single")
    m.emit(_i(37, 2, key, 0x39CE))
    branch(4, 0, 0, "direction")
    m.label("single")
    m.emit(_i(9, 0, step, 1))
    m.label("direction")
    m.emit(_i(12, key, test, 0x2000))
    branch(5, test, 0, "older")
    m.emit(_i(12, key, test, 0x8000))
    branch(4, test, 0, "idle")
    m.label("newer")
    m.emit(_r(age, step, temp, 0, 0x23))
    branch(1, temp, 1, "clamped")  # bgez
    m.emit(_i(9, 0, temp, 0))
    branch(4, 0, 0, "clamped")
    m.label("older")
    m.emit(_r(age, step, temp, 0, 0x21))
    m.emit(_r(limit, temp, test, 0, 0x2A))
    branch(4, test, 0, "clamped")
    m.emit(_r(limit, 0, temp, 0, 0x21))
    m.label("clamped")
    branch(4, age, temp, "idle")
    m.emit(_i(41, private, temp, 0x50))
    m.emit(_jal(0x1697B0))
    m.emit(_i(9, 0, 4, 0))

    # Mirror the history destructor's task-presence check and release.
    # Reset the color-fade state for the new record owning each slot.
    m.emit(_i(9, 0, ordinal, 0))
    m.label("release")
    m.emit(_r(0, ordinal, 16, 2, 0))
    m.emit(_r(16, private, 16, 0, 0x21))
    m.emit(_jal(0x1A1860))
    m.emit(_i(35, 16, 4, 0x20))
    m.emit(_i(9, 0, test, 1))
    branch(5, 2, test, "clear")
    m.emit(_jal(0x1A1430))
    m.emit(_i(35, 16, 4, 0x20))
    m.label("clear")
    m.emit(_i(43, 16, 0, 0x20))
    m.emit(_r(0, ordinal, temp, 4, 0))
    m.emit(_r(private, temp, temp, 0, 0x21))
    for offset in (0xA4, 0xA8, 0xAC):
        m.emit(_i(43, temp, 0, offset))
    m.emit(_i(9, ordinal, ordinal, 1))
    m.emit(_i(10, ordinal, test, 12))
    branch(5, test, 0, "release")
    m.emit(_i(35, private, temp, 0x98))  # approved initial top coordinate
    m.emit(_i(43, private, temp, 0x80))
    m.emit(_i(41, private, 0, 0x64))
    m.emit(_i(9, 0, ordinal, 0))
    m.emit(_i(33, private, 19, 0x7C))
    branch(4, 0, 0, "rows")

    m.label("native")
    m.emit(_jump(NAV_ENTRY + 8))
    m.emit(0)
    m.label("idle")
    m.emit(_jump(0x2541A0))  # original per-frame color update and debug input
    m.emit(0)

    # Local row lookup uses the same ring as the writer, including when a
    # retained window straddles slot 254 and slot zero.
    index_va = base + 4 * len(m.words)
    m.emit(_i(35, 28, 2, -0x1DAC))
    m.emit(_i(33, 2, 2, 0x30FC))
    m.emit(_i(33, private, 3, 0x50))
    m.emit(_r(2, 3, 2, 0, 0x23))
    m.emit(_i(9, 2, 2, -12))
    m.emit(_r(2, ordinal, 2, 0, 0x21))
    m.emit(_i(9, 0, 3, 255))
    m.emit(_r(2, 3, 0, 0, 0x1A))
    m.emit(_r(0, 0, 2, 0, 0x10))
    branch(1, 2, 1, "slot")
    m.emit(_i(9, 2, 2, 255))
    m.label("slot")
    m.emit(_r(0, 2, 3, 2, 0))
    m.emit(0x03E00008)
    m.emit(_r(3, 2, 2, 0, 0x21))

    m.label("rows")
    _patch(rows, 0x253AE8 - ROW_START, _jal(index_va))
    for at in range(0, len(rows), 4):
        m.emit(int.from_bytes(rows[at:at + 4], "little"))

    # Position the original scrollbar sprite on its track. Recompute from
    # absolute age to avoid accumulation and preserve its native thumb size.
    m.emit(_i(35, private, temp, 0x170))
    m.emit(_i(9, 0, test, 465))
    m.emit(_r(test, temp, test, 0, 0x23))
    m.emit(_i(33, private, age, 0x50))
    m.emit(_r(test, age, 0, 0, 0x18))
    m.emit(_r(0, 0, test, 0, 0x12))
    m.emit(_r(test, limit, 0, 0, 0x1A))
    m.emit(_r(0, 0, test, 0, 0x12))
    m.emit(_i(9, test, test, 26))
    m.emit(0x44800000 | test << 16)  # mtc1 test,f0
    m.emit(0x46800020)  # cvt.s.w f0,f0
    m.emit(_i(49, private, 1, 0x184))
    m.emit(0x46010001)  # sub.s f0,f0,f1; native update adds this step back
    m.emit(_i(57, private, 0, 0x160))
    m.emit(_r(owner, 0, 4, 0, 0x21))
    m.emit(_jal(0x256400))
    m.emit(_i(9, 0, 5, 0))
    m.emit(_jump(0x2541A0))
    m.emit(0)
    # Assembly.done requires a terminal return pair.
    m.emit(0x03E00008)
    m.emit(0)
    code = m.done()[:-8]
    expected = (0x3C02007A, 0x944339D2)
    replacements = (_jump(base), expected[0])
    writes = {}
    for offset, old, new in zip(OWNER_OFFSETS, expected, replacements, strict=True):
        original = pack("<I", old)
        if source[offset:offset + 4] != original:
            raise ValueError(f"History navigation preimage drift at {offset:#x}")
        writes[offset] = original, pack("<I", new)
    return code, writes
