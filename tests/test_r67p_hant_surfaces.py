"""Installed H.A.N.T. selected-page probe for the Help extent and Anubis row ownership."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import math
from pathlib import Path
import struct
import unicodedata
import unittest

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS64, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
from unicorn import mips_const as reg

from tests.r67_native_geometry import _float_reg, _fword, render
from tests.test_r67_15i_hant_text import run_viewport
from tools.first_save_help_inventory import _CATEGORIES
from tools.r67_15g_help_layout import _va_to_offset
from tools.r67_15g_prologue import HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET, HANT_ANUBIS_DYNAMIC_ROW_INDICES
from tools.r67p_surface_art import O_ISO, read_artwork
from tools.r67m_cumulative import sha_file
from tools.r67_15h_item_layout import APPEND_FILE_OFFSET, APPEND_VA

BLANK = 0x795FB8
EOF = 0x795FBC
BIAS = 0xFFF80
SCROLL_BEGIN = 0x2909F0
SCROLL_END = 0x290A90


def _word(elf, offset):
    return struct.unpack_from("<I", elf, offset)[0]


def page_table(elf: bytes, offset: int) -> tuple[list[str], list[int]]:
    rows = []
    lengths = []
    table = _va_to_offset(elf, _word(elf, offset))
    for index in range(81):
        pointer = _word(elf, table + index * 4)
        if pointer == EOF:
            return rows, lengths
        if pointer == BLANK:
            rows.append("")
            lengths.append(1)
            continue
        text = _va_to_offset(elf, pointer)
        terminator = elf.find(b"\0", text, text + 64)
        if terminator < 0:
            raise ValueError(f"unterminated installed H.A.N.T. row {index} at {text:#x}")
        rows.append(elf[text:terminator].decode("cp932"))
        lengths.append(terminator - text + 1)
    raise ValueError("installed H.A.N.T. page exceeded its 80 slots")


def native_scroll_limit(elf: bytes, mode: int, rows: int) -> tuple[float, float]:
    """Execute the real shared extent/clamp owner with seeded output count and mode."""
    machine = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    machine.mem_map(0x290000, 0x1000)
    machine.mem_map(APPEND_VA & ~0xFFF, 0x200000)
    machine.mem_map(0x1100000, 0x10000)
    machine.mem_write(SCROLL_BEGIN, elf[SCROLL_BEGIN - BIAS:SCROLL_END - BIAS])
    machine.mem_write(APPEND_VA, elf[APPEND_FILE_OFFSET:])
    private = 0x1101000
    machine.mem_write(private + 0x17E4, struct.pack("<I", mode))
    machine.mem_write(private + 0x1A78, struct.pack("<I", rows))
    machine.reg_write(reg.UC_MIPS_REG_S1, private)
    accumulator = 0.0

    def ee_cop1(uc, pc, _size, _context):
        nonlocal accumulator
        if pc == SCROLL_END:
            uc.emu_stop()
            return
        if pc == 0x290A24 and bytes(uc.mem_read(pc, 4)) == bytes.fromhex("18000146"):
            accumulator = _float_reg(uc, reg.UC_MIPS_REG_F0) + _float_reg(uc, reg.UC_MIPS_REG_F1)
        elif pc == 0x290A28 and bytes(uc.mem_read(pc, 4)) == bytes.fromhex("1c180246"):
            value = accumulator + _float_reg(uc, reg.UC_MIPS_REG_F3) * _float_reg(uc, reg.UC_MIPS_REG_F2)
            uc.reg_write(reg.UC_MIPS_REG_F0, _fword(value))
        elif pc in (0x290A24, 0x290A28):
            raise ValueError(f"H.A.N.T. COP1 owner changed at {pc:#x}")
        else:
            return
        uc.reg_write(reg.UC_MIPS_REG_PC, pc + 4)

    machine.hook_add(UC_HOOK_CODE, ee_cop1)
    machine.emu_start(SCROLL_BEGIN, SCROLL_END + 4, count=100)
    if machine.reg_read(reg.UC_MIPS_REG_PC) != SCROLL_END:
        raise ValueError(f"H.A.N.T. extent did not terminate at {machine.reg_read(reg.UC_MIPS_REG_PC):#x}")
    content_height = struct.unpack("<f", machine.mem_read(private + 0x1A88, 4))[0]
    maximum = struct.unpack("<f", machine.mem_read(private + 0x1A90, 4))[0]
    return content_height, maximum


def _icon_bottom(elf: bytes, offset: int) -> float | None:
    table = _va_to_offset(elf, _word(elf, offset))
    bottoms = []
    for index in range(100):
        group, sprite, _x, y = struct.unpack_from("<4h", elf, table + index * 8)
        if group < 0:
            return max(bottoms, default=None)
        descriptor = _word(elf, _va_to_offset(elf, 0x485240 + group * 4))
        address, count = struct.unpack_from("<II", elf, _va_to_offset(elf, descriptor + sprite * 8))
        if not 0 < count <= 256:
            raise ValueError("invalid installed H.A.N.T. sprite animation count")
        for frame in range(count):
            offset = _va_to_offset(elf, address + frame * 48)
            _width, height, _px, py = struct.unpack_from("<4f", elf, offset + 4)
            if not math.isfinite(height) or not math.isfinite(py) or height <= 0:
                raise ValueError("invalid installed H.A.N.T. sprite geometry")
            bottoms.append(119 + y - py + height)
    raise ValueError("unterminated installed H.A.N.T. icon metadata")


def help_pages(elf: bytes) -> list[dict]:
    result = []
    for topics, row_start, icon_start in _CATEGORIES:
        for index, topic in enumerate(topics):
            rows, lengths = page_table(elf, row_start + 4 * index)
            count = len(rows)
            last_text = max((i for i, row in enumerate(rows) if row.strip()), default=None)
            height, terminal = native_scroll_limit(elf, 4, count)
            _, submitted, _, faults = run_viewport(elf, count=count, scroll=terminal)
            if faults:
                raise ValueError(f"Unsafe Help viewport handles: {topic.key}")
            visible = [int(text.decode().removeprefix("row-")) for _handle, text in submitted]
            result.append({"page": topic.key, "rows": count, "row_max_bytes_with_nul": max(lengths),
                           "extent": height, "terminal_scroll": terminal,
                           "last_text_index": last_text, "visible_indices_at_terminal": visible,
                           "last_text_visible_at_terminal": last_text in visible,
                           "last_text_origin_at_terminal": (None if last_text is None else 131 + 16 * last_text - terminal),
                           "last_native_icon_bottom_unscrolled": _icon_bottom(elf, icon_start + 4 * index)})
    return result


def anubis(elf: bytes) -> dict:
    fields = HANT_ANUBIS_RECORD_TABLE_FILE_OFFSET
    words = [_word(elf, fields + index * 4) for index in range(21)]
    if words[-1] != EOF or any(words[index] != BLANK for index in (5, 18, 19)):
        raise ValueError("Anubis record sentinel drift")
    if (_word(elf, 0x5CBB40 + 2 * 4) != 0x6C29B0
            or _word(elf, 0x5C2A30 + 4) != 0x6C2930
            or _word(elf, 0x5C29B0) != 0x6C2390):
        raise ValueError("Anubis selected Enemy route changed")
    rows = []
    for index, pointer in enumerate(words[:-1]):
        if pointer == BLANK:
            continue
        offset = _va_to_offset(elf, pointer)
        end = elf.find(b"\0", offset, offset + 64)
        if end < 0:
            raise ValueError(f"Anubis source row exceeds native 64-byte buffer: {index}")
        line = unicodedata.normalize("NFKC", elf[offset:end].decode("cp932"))
        measured = render(elf, line, scale_x=1., scale_y=1., origin=(85., 131.),
                          font_descriptor=0x5D7800)
        rows.append({"source_index": index, "text": line, "bytes_with_nul": end - offset + 1,
                     "bounds_from_first_row": asdict(measured.bounds),
                     "dynamic_source_index": index in HANT_ANUBIS_DYNAMIC_ROW_INDICES})
    return {"owner": "mode 2 / category 1 / record 0, native 0x291EC0 → 0x2A9FE0",
            "native_copy_owner": "0x290694 → 0x39FCC0",
            "storage_bytes": 64, "dynamic_source_indices": HANT_ANUBIS_DYNAMIC_ROW_INDICES,
            "font_descriptor": "0x5D7800 style 1", "row_origin": [85, 131], "native_row_pitch": 21,
            "conservative_x_right": 421, "actual_frame_clip_x_right": None,
            "rows": rows, "max_installed_static_right": max(row["bounds_from_first_row"]["right"] for row in rows),
            "max_installed_static_bytes": max(row["bytes_with_nul"] for row in rows),
            "drawing_boundary": "Installed static field bytes at the observed row origin, first-row glyph geometry only. Live HP, weak spot, treasure, clip edge and unlock state require gameplay."}


@unittest.skipUnless(O_ISO.is_file(), "Pinned r67.15o ISO is unavailable")
class HantSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf, _ = read_artwork(O_ISO)

    def test_native_help_scroll_extent_uses_the_larger_legacy_pitch(self):
        self.assertEqual(native_scroll_limit(self.elf, 4, 65), (1377., 1155.))
        self.assertEqual(native_scroll_limit(self.elf, 4, 10), (222., 0.))
        self.assertEqual(native_scroll_limit(self.elf, 3, 10), (512., 290.))

    def test_mode_4_extent_has_every_last_row_and_animated_icon_reachable(self):
        from tools.r67p_hant_scroll import patch

        source = self.elf
        output = bytearray(source)
        output.extend(bytes(-len(output) % 16))
        appended_base = APPEND_VA + len(output) - APPEND_FILE_OFFSET
        code, writes = patch(source, appended_base)
        self.assertEqual(set(writes), {0x190A80, 0x190A84})
        for offset, (before, after) in writes.items():
            self.assertEqual(output[offset:offset + 4], before)
            output[offset:offset + 4] = after
        output.extend(code)
        struct.pack_into("<I", output, 0x64, len(output) - APPEND_FILE_OFFSET)
        candidate = bytes(output)
        for mode in (0, 1, 2, 3, 5):
            for count in (0, 10, 11, 23, 71, 80):
                self.assertEqual(native_scroll_limit(candidate, mode, count),
                                 native_scroll_limit(source, mode, count))
        self.assertEqual(native_scroll_limit(candidate, 4, 10), (222., 0.))
        self.assertEqual(native_scroll_limit(candidate, 4, 11), (188., 0.))
        self.assertEqual(native_scroll_limit(candidate, 4, 57), (924., 702.))
        self.assertEqual(native_scroll_limit(candidate, 4, 71), (1148., 926.))
        baseline, patched = help_pages(source), help_pages(candidate)
        for before, after in zip(baseline, patched, strict=True):
            self.assertTrue(after["last_text_visible_at_terminal"], after["page"])
            if before["rows"] < 11:
                self.assertEqual(before, after)
                continue
            self.assertLessEqual(after["last_text_origin_at_terminal"] + 12, 341)
            icon_bottom = after["last_native_icon_bottom_unscrolled"]
            if icon_bottom is not None:
                self.assertLessEqual(icon_bottom - after["terminal_scroll"], 341)

    def test_help_extent_hook_rejects_mutated_neighbor(self):
        from tools.r67p_hant_scroll import patch

        damaged = bytearray(self.elf)
        damaged[0x290A14 - BIAS] ^= 1
        with self.assertRaisesRegex(ValueError, "H.A.N.T. scroll owner"):
            patch(bytes(damaged), 0x9C0000)

    def test_installed_anubis_rows_fit_conservative_geometry_and_native_copy_limit(self):
        evidence = anubis(self.elf)
        self.assertEqual(len(evidence["rows"]), 17)
        self.assertEqual(evidence["dynamic_source_indices"], (5, 7, 18))
        self.assertLess(evidence["max_installed_static_right"], 421)
        self.assertLessEqual(evidence["max_installed_static_bytes"], 57)

    def test_all_installed_help_topics_preserve_their_native_text_and_icon_tables(self):
        pages = help_pages(self.elf)
        self.assertEqual(len(pages), 55)
        self.assertTrue(all(page["row_max_bytes_with_nul"] <= 64 for page in pages))
        self.assertEqual(sum(page["terminal_scroll"] > 0 and not page["last_text_visible_at_terminal"]
                             for page in pages), 12)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=O_ISO)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("use a new report path")
    executable, _ = read_artwork(args.iso)
    pages = help_pages(executable)
    args.report.write_text(json.dumps({
        "iso": str(args.iso), "iso_sha256": sha_file(args.iso),
        "installed_elf_sha256": sha256(executable).hexdigest(),
        "help_pages_with_culled_last_text": [page["page"] for page in pages
                                            if not page["last_text_visible_at_terminal"]],
        "help": pages, "anubis": anubis(executable),
    }, indent=2) + "\n")
