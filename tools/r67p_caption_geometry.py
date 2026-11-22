"""Layout normalized English ADV captions at the caption text and backing calls."""

from struct import pack
from unicodedata import normalize

from tools.r67_chamber_story_text_only import Assembly, ELF_BIAS, _float_word, _i, _jal, _r
from tools.r67o_choices import _font_table

TEXT_CALL = 0x250D6C
BACKING_CALL = 0x250E00
NATIVE_TEXT = 0x190A50
NATIVE_BACKING = 0x256B30
FONT_CAPACITY = 100
ROW_CELLS = 30
GLYPH_WIDTH = 16
BACKING_RECT = (0., 6., 512., 60.)


def latin_cells(source):
    """Map native style-0, fixed-width Latin cells to their caption classification."""
    table = bytearray(512)
    for code in _font_table(source):
        if not 0x8100 <= code < 0x8300:
            continue
        text = code.to_bytes(2, "big").decode("cp932")
        folded = normalize("NFKC", text)
        if (len(folded) == 1 and folded.isascii() and folded.isprintable()) or text in "‘’“”":
            table[code - 0x8100] = 2 if folded.isascii() and folded.isalpha() else 1
    return bytes(table)


def _tail(m, target):
    m.emit(0x03E00008)
    m.emit(0)
    data = m.done()
    return data[:-8] + pack("<II", _jal(target) ^ (1 << 26), 0)


def _coordinate(m, target, source):
    m.emit(_i(17, 4, source, target << 11))  # mtc1 source,target
    m.emit(0)
    m.emit((17 << 26) | (20 << 21) | (target << 11) | (target << 6) | 0x20)


def _format_caption(table):
    m = Assembly()
    v0, v1, a1, a3, cursor, classes, letters, length, code, category = 2, 3, 5, 7, 12, 13, 14, 15, 24, 25
    m.emit(_i(9, 29, 29, -0x90))
    m.emit(_i(63, 29, 31, 0x80))
    m.emit(_r(a3, 0, cursor, 0, 33))
    m.emit(_i(15, 0, classes, table >> 16))
    m.emit(_i(13, classes, classes, table & 0xFFFF))
    m.emit(_i(9, 0, letters, 0))
    m.emit(_i(9, 0, length, 0))

    m.label("scan")
    m.emit(_i(36, cursor, code, 0))
    m.branch(4, code, 0, "scan_end")
    m.emit(_i(11, length, v0, FONT_CAPACITY))
    m.branch(4, v0, 0, "native")
    m.emit(_i(9, code, code, -0x81))
    m.emit(_i(11, code, v0, 2))
    m.branch(4, v0, 0, "native")
    m.emit(_r(0, code, code, 8, 0))
    m.emit(_i(36, cursor, v0, 1))
    m.emit(_r(code, v0, code, 0, 33))
    m.emit(_r(classes, code, code, 0, 33))
    m.emit(_i(36, code, category, 0))
    m.branch(4, category, 0, "native")
    m.emit(_r(letters, category, letters, 0, 37))
    m.emit(_i(9, cursor, cursor, 2))
    m.branch(4, 0, 0, "scan")
    m.emit(_i(9, length, length, 2))
    m.label("scan_end")
    m.emit(_i(12, letters, letters, 2))
    m.branch(4, letters, 0, "native")
    m.emit(_r(0, length, length, 1, 2))  # bounded native cell count
    m.emit(_i(11, length, v0, ROW_CELLS + 1))
    m.branch(5, v0, 0, "one_row")
    m.emit(0)

    # Find the most balanced space among the splits with room on both sides.
    # Preserve every glyph even when a future caption has no usable space.
    split, best_width, drop_space, position, other = classes, category, v1, letters, v0
    m.emit(_r(0, length, split, 1, 2))
    m.emit(_i(9, 0, best_width, ROW_CELLS + 1))
    m.emit(_r(0, 0, drop_space, 0, 33))
    m.emit(_i(9, length, position, -ROW_CELLS - 1))
    m.emit(_r(0, position, cursor, 1, 0))
    m.emit(_r(a3, cursor, cursor, 0, 33))
    m.label("find_break")
    m.emit(_i(37, cursor, code, 0))
    m.emit(_i(9, 0, other, 0x4081))  # little-endian fullwidth space
    m.branch(5, code, other, "next_break")
    m.emit(_r(length, position, other, 0, 35))
    m.emit(_i(9, other, other, -1))
    m.emit(_r(other, position, code, 0, 43))
    m.branch(4, code, 0, "consider_break")
    m.emit(0)
    m.emit(_r(position, 0, other, 0, 33))
    m.label("consider_break")
    m.emit(_r(other, best_width, code, 0, 43))
    m.branch(4, code, 0, "next_break")
    m.emit(0)
    m.emit(_r(position, 0, split, 0, 33))
    m.emit(_r(other, 0, best_width, 0, 33))
    m.emit(_i(9, 0, drop_space, 1))
    m.label("next_break")
    m.emit(_i(9, position, position, 1))
    m.emit(_i(11, position, code, ROW_CELLS + 1))
    m.branch(5, code, 0, "find_break")
    m.emit(_i(9, cursor, cursor, 2))

    m.emit(_r(29, 0, cursor, 0, 33))
    m.emit(_r(0, 0, position, 0, 33))
    m.label("copy")
    m.branch(5, position, split, "copy_cell")
    m.emit(0)
    m.emit(_i(9, 0, code, 10))
    m.emit(_i(40, cursor, code, 0))
    m.emit(_i(9, cursor, cursor, 1))
    m.branch(4, drop_space, 0, "copy_cell")
    m.emit(0)
    m.emit(_i(9, a3, a3, 2))
    m.branch(4, 0, 0, "next_cell")
    m.emit(0)
    m.label("copy_cell")
    for index in range(2):
        m.emit(_i(36, a3, code, index))
        m.emit(_i(40, cursor, code, index))
    m.emit(_i(9, cursor, cursor, 2))
    m.emit(_i(9, a3, a3, 2))
    m.label("next_cell")
    m.emit(_i(9, position, position, 1))
    m.branch(5, position, length, "copy")
    m.emit(0)
    m.emit(_i(40, cursor, 0, 0))
    m.emit(_r(29, 0, a3, 0, 33))
    m.branch(5, drop_space, 0, "multi_row")
    m.emit(0)
    m.emit(_r(length, split, best_width, 0, 35))
    m.label("multi_row")
    m.emit(_r(best_width, 0, length, 0, 33))
    m.branch(4, 0, 0, "place")
    m.emit(_i(9, 0, v1, 17))
    m.label("one_row")
    m.emit(_i(9, 0, v1, 26))
    m.label("place")
    m.emit(_r(0, length, length, GLYPH_WIDTH.bit_length() - 1, 0))
    m.emit(_i(9, 0, v0, 512))
    m.emit(_r(v0, length, v0, 0, 35))
    m.emit(_r(0, v0, v0, 1, 2))
    _coordinate(m, 12, v0)
    _coordinate(m, 13, v1)
    m.emit(_i(9, 0, a1, 0))
    m.label("native")
    m.emit(_jal(NATIVE_TEXT))
    m.emit(0)
    m.emit(_i(55, 29, 31, 0x80))
    m.emit(_i(9, 29, 29, 0x90))
    m.emit(0x03E00008)
    m.emit(0)
    return m.done()


def _place_backing():
    m = Assembly()
    m.emit(_i(35, 16, 2, 4))  # caption's just-created font handle
    m.branch(4, 2, 0, "backing")
    m.emit(0)
    m.emit(_i(35, 2, 2, 0x3C))
    m.branch(4, 2, 0, "backing")
    m.emit(0)
    m.emit(_i(35, 2, 3, 0x0C))
    m.branch(5, 3, 0, "backing")  # style 2 keeps the stock vertical backing
    m.emit(0)
    left, top, width, height = BACKING_RECT
    m.const(2, _float_word(left))
    m.emit(_i(17, 4, 2, 12 << 11))
    m.const(5, _float_word(top))
    m.emit(_r(0, 5, 5, 0, 0x3C))  # dsll32 a1,a1,0: packed (x,y)
    for offset, value in ((0, 0), (4, 0), (8, int(width)), (12, int(height))):
        m.emit(_i(9, 0, 3, value))
        m.emit(_i(43, 6, 3, offset))
    m.label("backing")
    return _tail(m, NATIVE_BACKING)


def patch(source: bytes, base: int) -> tuple[bytes, dict[int, tuple[bytes, bytes]]]:
    guards = {
        0x250D38: "ee43023c00608244b041023c0068824400708044803f023c0078824454e2828f2d20200202000524ffff0624067c0046b40847249442060c00000000",
        0x250DEC: "9643023c006082442d2020024000a5df3000a627cc5a090c00000000",
        0x5D77D4: "1012",
    }
    for address, signature in guards.items():
        expected = bytes.fromhex(signature)
        offset = address - ELF_BIAS
        if source[offset:offset + len(expected)] != expected:
            raise ValueError(f"Caption owner preimage differs at {address:#x}")
    backing = _place_backing()
    caption_size = len(_format_caption(0))
    table_va = base + caption_size + len(backing)
    caption = _format_caption(table_va)
    patches = {
        TEXT_CALL - ELF_BIAS: (pack("<I", _jal(NATIVE_TEXT)), pack("<I", _jal(base))),
        BACKING_CALL - ELF_BIAS: (pack("<I", _jal(NATIVE_BACKING)), pack("<I", _jal(base + len(caption)))),
    }
    return caption + backing + latin_cells(source), patches
