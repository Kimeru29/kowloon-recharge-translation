"""Native metric and patch-bound regressions for r67.15h item text owners."""
from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path

from tools.r67_15h_item_layout import (
    BASE_SHA256,
    SOURCE_ELF,
    ALLOWED_SOURCE_RANGES,
    RECIPE_ICON_RESERVE,
    RECIPE_MAX_ADVANCE,
    RECIPE_NAME_ORIGIN,
    RECIPE_NUMERIC_ORIGIN,
    build,
    recipe_metrics,
)

try:
    from unicorn import (Uc, UC_ARCH_MIPS, UC_HOOK_CODE,
                         UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64)
    from unicorn.mips_const import (
        UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3,
        UC_MIPS_REG_F0, UC_MIPS_REG_F1, UC_MIPS_REG_F12, UC_MIPS_REG_F13,
        UC_MIPS_REG_F14, UC_MIPS_REG_F15, UC_MIPS_REG_F16, UC_MIPS_REG_F20,
        UC_MIPS_REG_F21, UC_MIPS_REG_F25, UC_MIPS_REG_F26, UC_MIPS_REG_F27,
        UC_MIPS_REG_F29, UC_MIPS_REG_PC, UC_MIPS_REG_S3, UC_MIPS_REG_S4,
        UC_MIPS_REG_S5, UC_MIPS_REG_S6, UC_MIPS_REG_SP, UC_MIPS_REG_T0,
    )

    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
STACK = 0x210000
FONT = 0x220000
NODE = 0x230000
NODE_STRIDE = 0x124
ADVANCE_PATH_VA = 0x18DFFC
CONTROL_PATH_VA = 0x18E060
METRIC_RETURN_VA = 0x18E158


def _fword(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _native_metric_step(source: bytes, control: int, *, scale: float,
                        line_pitch: float, cursor_x: float = 0.0,
                        cursor_y: float = 0.0) -> tuple[float, float]:
    """Execute native EE cursor arithmetic from the pinned ELF with Unicorn."""
    bias = 0xFFF80
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_map(0x200000, 0x100000)
    uc.mem_write(ADVANCE_PATH_VA, source[ADVANCE_PATH_VA - bias:0x18E130 - bias])
    uc.reg_write(UC_MIPS_REG_S4, FONT)
    uc.reg_write(UC_MIPS_REG_S3, NODE)
    uc.reg_write(UC_MIPS_REG_S5, 0x240000)
    uc.reg_write(UC_MIPS_REG_S6, 0)
    uc.reg_write(UC_MIPS_REG_SP, STACK + 0x800)
    uc.reg_write(UC_MIPS_REG_A1, control)
    uc.reg_write(UC_MIPS_REG_F21, _fword(cursor_x))
    uc.reg_write(UC_MIPS_REG_F20, _fword(cursor_y))
    uc.reg_write(UC_MIPS_REG_F27, _fword(16.0))
    uc.reg_write(UC_MIPS_REG_F29, _fword(scale))
    uc.reg_write(UC_MIPS_REG_F25, 0)
    uc.reg_write(UC_MIPS_REG_F26, _fword(18.0))
    uc.reg_write(UC_MIPS_REG_PC, CONTROL_PATH_VA)
    uc.mem_write(FONT + 0x48, struct.pack("<f", scale))
    uc.mem_write(FONT + 0x2C, struct.pack("<f", line_pitch))
    uc.mem_write(STACK + 0x800 + 0xBC, struct.pack("<f", 16.0))
    uc.mem_write(STACK + 0x800 + 0xB8, struct.pack("<f", line_pitch))
    uc.mem_write(STACK + 0x800 + 0xC4, struct.pack("<f", line_pitch))
    uc.hook_add(UC_HOOK_CODE,
                lambda engine, address, size, data:
                engine.emu_stop() if address == METRIC_RETURN_VA else None)
    uc.emu_start(CONTROL_PATH_VA, METRIC_RETURN_VA + 4, count=96)
    return (
        struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F21)))[0],
        struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F20)))[0],
    )


def _native_cursor_add(source: bytes, cursor: float, advance: float) -> float:
    from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import UC_MIPS_REG_F0, UC_MIPS_REG_F21

    bias = 0xFFF80
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_write(0x18E018, source[0x18E018 - bias:0x18E01C - bias])
    uc.reg_write(UC_MIPS_REG_F0, _fword(advance))
    uc.reg_write(UC_MIPS_REG_F21, _fword(cursor))
    uc.emu_start(0x18E018, 0x18E01C, count=1)
    return struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F21)))[0]


def _native_ordinary_advance(source: bytes, cursor: float, *, scale: float,
                             spacing: float) -> tuple[float, float]:
    """Execute native cursor add and emulate the EE accumulator instructions."""
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import (
        UC_MIPS_REG_F0, UC_MIPS_REG_F1, UC_MIPS_REG_F21,
        UC_MIPS_REG_F25, UC_MIPS_REG_F27, UC_MIPS_REG_PC,
    )

    bias = 0xFFF80
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_write(0x18E010, source[0x18E010 - bias:0x18E01C - bias])
    uc.reg_write(UC_MIPS_REG_F0, _fword(0.0))
    uc.reg_write(UC_MIPS_REG_F1, _fword(scale))
    uc.reg_write(UC_MIPS_REG_F21, _fword(cursor))
    uc.reg_write(UC_MIPS_REG_F25, _fword(spacing))
    uc.reg_write(UC_MIPS_REG_F27, _fword(16.0))
    accumulator = 0.0
    opcodes = {
        0x18E010: 0x46190018,  # ADDA.S: ACC = f0 + f25
        0x18E014: 0x4601D81C,  # MADD.S: f0 = ACC + f27 * f1
    }

    def emulate_ee_accumulator(engine, address, size, data):
        nonlocal accumulator
        if address not in opcodes:
            return
        word = struct.unpack("<I", source[address - bias:address - bias + 4])[0]
        if word != opcodes[address]:
            raise AssertionError(f"unexpected EE accumulator opcode at {address:#x}: {word:#x}")
        if address == 0x18E010:
            f0 = struct.unpack("<f", struct.pack("<I", engine.reg_read(UC_MIPS_REG_F0)))[0]
            f25 = struct.unpack("<f", struct.pack("<I", engine.reg_read(UC_MIPS_REG_F25)))[0]
            accumulator = f0 + f25
        else:
            f27 = struct.unpack("<f", struct.pack("<I", engine.reg_read(UC_MIPS_REG_F27)))[0]
            f1 = struct.unpack("<f", struct.pack("<I", engine.reg_read(UC_MIPS_REG_F1)))[0]
            engine.reg_write(UC_MIPS_REG_F0, _fword(accumulator + f27 * f1))
        engine.reg_write(UC_MIPS_REG_PC, address + 4)

    uc.hook_add(UC_HOOK_CODE, emulate_ee_accumulator)
    uc.emu_start(0x18E010, 0x18E01C, count=8)
    advance = struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F0)))[0]
    resulting_cursor = struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F21)))[0]
    return advance, resulting_cursor


class R6715HItemLayoutSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SOURCE_ELF.read_bytes()
        cls.after, cls.report = build(cls.before)

    def test_source_identity_and_only_named_hooks_change(self):
        self.assertEqual(hashlib.sha256(self.before).hexdigest(), BASE_SHA256)
        self.assertEqual(ALLOWED_SOURCE_RANGES, {
            "details_text_constructor": ((0x1520C, 0x15210),),
            "recipe_ingredient_constructor": ((0x154D8, 0x154DC),),
            "recipe_success_result_constructor": ((0x155CC, 0x155D0),),
            "recipe_failure_result_constructor": ((0x1563C, 0x15640),),
        })
        self.assertEqual(self.before[0x15210:0x15214], b"\0\0\0\0")
        for offset in (0x154DC, 0x155D0, 0x15640):
            self.assertEqual(self.before[offset:offset + 4], b"\0\0\0\0")
        allowed = {offset for spans in ALLOWED_SOURCE_RANGES.values()
                   for start, end in spans for offset in range(start, end)}
        allowed.update(range(0x64, 0x68))
        changed = {i for i, pair in enumerate(zip(self.before, self.after))
                   if pair[0] != pair[1]}
        self.assertFalse(changed - allowed)

    def test_card_and_action_bubble_accepted_hooks_remain_identical(self):
        self.assertEqual(self.after[0xDB44:0xDB48], self.before[0xDB44:0xDB48])
        self.assertEqual(self.after[0x14B58:0x14B5C], self.before[0x14B58:0x14B5C])

    def test_recipe_scale_budget_reserves_icons_and_numeric_columns(self):
        self.assertEqual(RECIPE_MAX_ADVANCE, 114)
        self.assertEqual(RECIPE_ICON_RESERVE, 16)
        bias = 0xFFF80
        name_origin_word = struct.unpack_from("<I", self.before, 0x1153D0 - bias)[0]
        numeric_origin_word = struct.unpack_from("<I", self.before, 0x115930 - bias)[0]
        font = 0x5D77D0 - bias
        self.assertEqual(name_origin_word, 0x3C02421C)  # native name X = panel X + 39
        self.assertEqual(numeric_origin_word, 0x3C024332)  # panel X - 1 + 178
        self.assertEqual(struct.unpack_from("<BB", self.before, font + 4), (16, 18))
        self.assertEqual(RECIPE_NUMERIC_ORIGIN - RECIPE_NAME_ORIGIN, 138)
        self.assertEqual(RECIPE_NUMERIC_ORIGIN - RECIPE_ICON_RESERVE, 161)
        for count, spaces in ((27, 0), (23, 3), (24, 3), (41, 2)):
            with self.subTest(glyphs=count, spaces=spaces):
                metrics = recipe_metrics(count, spaces)
                self.assertLessEqual(metrics["advance"], 114)
                self.assertGreaterEqual(metrics["right_gap"], 24)

    def test_all_official_card_names_fit_without_shortening(self):
        from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA

        self.assertEqual(len(DUNGEON_ITEM_NAME_DATA), 446)
        for item_id, _source_offset, _japanese, english, _record in DUNGEON_ITEM_NAME_DATA:
            with self.subTest(item_id=item_id, name=english):
                glyphs = sum(character != " " for character in english)
                metrics = recipe_metrics(glyphs, english.count(" "))
                self.assertLessEqual(metrics["advance"], 114)

    def test_details_catalogue_counts_and_mixed_japanese_fallback_remain_intact(self):
        from tools.r67_15g_item_details import (
            collect_catalogue, load_official_rows, map_official_descriptions,
            map_official_lines, _va_to_offset, SOURCE_ELF as ITEM_DETAILS_SOURCE_ELF,
        )

        catalogue_source = ITEM_DETAILS_SOURCE_ELF.read_bytes()
        records = collect_catalogue(catalogue_source)
        corpus_rows = load_official_rows()
        translations, unresolved = map_official_descriptions(records, corpus_rows)
        line_map = map_official_lines(records, corpus_rows)
        self.assertEqual(len(records), 431)
        self.assertEqual(len(translations), 395)  # 391 exact English + 4 empty entries
        self.assertEqual(sum(not record.source_lines for record in records), 4)
        self.assertEqual(len(unresolved), 36)
        by_id = {record.item_id: record for record in records}
        self.assertEqual(set(by_id) & {500, 501, 504, 515, 534},
                         {500, 501, 504, 515, 534})
        self.assertTrue(all(value is None for value in line_map[500][:3]))
        self.assertTrue(all(value is None for value in line_map[501][:3]))
        self.assertTrue(all(value is None for value in line_map[504][:3]))
        self.assertTrue(all(value is None for value in line_map[515][:2]))
        self.assertTrue(all(value is None for value in line_map[534][:2]))
        offset = _va_to_offset(self.before, 0x974EA8)
        self.assertEqual(self.after[offset:offset + 756 * 4],
                         self.before[offset:offset + 756 * 4])

    def test_append_hooks_and_elf_load_size_are_exact(self):
        self.assertEqual(self.after[0xDB44:0xDB48], self.before[0xDB44:0xDB48])
        self.assertEqual(self.after[0x14B58:0x14B5C], self.before[0x14B58:0x14B5C])
        self.assertEqual(struct.unpack_from("<I", self.after, 0x64)[0],
                         len(self.after) - 0x803150)
        self.assertEqual(self.report["accepted_card_hook_unchanged"], True)
        self.assertEqual(self.report["accepted_bubble_hook_unchanged"], True)
        self.assertEqual(self.report["runtime_verified"], False)
        self.assertEqual(self.report["gameplay_approved"], False)
        self.assertEqual(self.report["details_vertical_available"], 60)
        self.assertEqual(self.report["details_max_measured_rows"], 6)
        self.assertEqual(self.report["details_max_measured_ink_height"], 54)
        self.assertEqual(self.report["recipe_width_budget"], 114)
        expected_targets = {
            0x1520C: int(self.report["details_helper_va"], 16),
            0x154D8: int(self.report["recipe_helper_va"], 16),
            0x155CC: int(self.report["recipe_helper_va"], 16),
            0x1563C: int(self.report["recipe_helper_va"], 16),
        }
        for offset, target in expected_targets.items():
            word = struct.unpack_from("<I", self.after, offset)[0]
            self.assertEqual(((word & 0x03FFFFFF) << 2), target)
        sq_words = [struct.unpack_from("<I", self.after,
                    int(self.report["recipe_helper_va"], 16) - 0x902F00 + 0x803150 + i)[0]
                    for i in range(0, self.report["recipe_helper_bytes"], 4)]
        self.assertIn(0x1F, {word >> 26 for word in sq_words})
        self.assertIn(0x1E, {word >> 26 for word in sq_words})


def _run_layout_helper(helper: bytes, helper_va: int, *, details: bool,
                       codes: list[int], malformed: bool = False,
                       head_override: int | None = None):
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import (
        UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3,
        UC_MIPS_REG_F12, UC_MIPS_REG_F13, UC_MIPS_REG_PC, UC_MIPS_REG_RA,
        UC_MIPS_REG_S0, UC_MIPS_REG_S1, UC_MIPS_REG_S2, UC_MIPS_REG_S3,
        UC_MIPS_REG_S4, UC_MIPS_REG_S5, UC_MIPS_REG_SP, UC_MIPS_REG_T0,
        UC_MIPS_REG_T1, UC_MIPS_REG_T2, UC_MIPS_REG_T3, UC_MIPS_REG_T4,
        UC_MIPS_REG_T5, UC_MIPS_REG_T6, UC_MIPS_REG_T7, UC_MIPS_REG_T8,
        UC_MIPS_REG_V0,
    )
    from unicorn import mips_const

    helper_handle = 0x220000
    private = 0x221000
    nodes = 0x230000
    ret = 0x210100
    stack = 0x210800
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    for start in (0x100000, 0x200000, 0x900000):
        uc.mem_map(start, 0x100000)
    # Unicorn lacks EE SQ/LQ. Lower the opcodes for control-flow execution and
    # sidecar-emulate the full two-lane 128-bit values at their saved stack slots.
    lowered = bytearray(helper)
    sq_regs = {}
    lq_after = {}
    for offset in range(0, len(lowered), 4):
        word = struct.unpack_from("<I", lowered, offset)[0]
        opcode = word >> 26
        if opcode == 0x1F:
            reg = (word >> 16) & 31
            sq_regs[offset] = reg
            struct.pack_into("<I", lowered, offset, (word & 0x03FFFFFF) | (43 << 26))
        elif opcode == 0x1E:
            reg = (word >> 16) & 31
            lq_after[helper_va + offset + 4] = reg
            struct.pack_into("<I", lowered, offset, (word & 0x03FFFFFF) | (35 << 26))
    uc.mem_write(helper_va, bytes(lowered))
    uc.mem_write(helper_handle + 0x3C, struct.pack("<I", private))
    uc.mem_write(private + 0x2C, struct.pack("<f", 0.0))
    head = nodes if codes else 0
    if head_override is not None:
        head = head_override
    uc.mem_write(private + 4, struct.pack("<I", head))
    values = codes + ([0x8241] * 257 if malformed else [])
    for index, control in enumerate(values):
        node = nodes + index * 0x124
        next_node = nodes + (index + 1) * 0x124 if index + 1 < len(values) else 0
        uc.mem_write(node, struct.pack("<H", control))
        uc.mem_write(node + 0x120, struct.pack("<I", next_node))
    regs = (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3,
            UC_MIPS_REG_S0, UC_MIPS_REG_S1, UC_MIPS_REG_S2, UC_MIPS_REG_S3,
            UC_MIPS_REG_S4, UC_MIPS_REG_S5, UC_MIPS_REG_T0, UC_MIPS_REG_T1)
    sentinels = {reg: 0x123456789ABC0000 + index for index, reg in enumerate(regs)}
    for reg, value in sentinels.items():
        uc.reg_write(reg, value)
    uc.reg_write(UC_MIPS_REG_SP, stack)
    uc.reg_write(UC_MIPS_REG_RA, ret)
    uc.reg_write(UC_MIPS_REG_F12, _fword(0.75))
    uc.reg_write(UC_MIPS_REG_F13, _fword(1.0))
    uc.reg_write(UC_MIPS_REG_F14, _fword(0.25))
    uc.reg_write(UC_MIPS_REG_F15, _fword(0.5))
    uc.reg_write(UC_MIPS_REG_F16, _fword(0.625))
    constructor_inputs = []
    setter_inputs = []
    recent_addresses = []
    saved_gpr128 = {}
    sidecar_high_lanes = {reg: 0xFEDCBA9876540000 + reg for reg in sq_regs.values()}
    original_high_lanes = sidecar_high_lanes.copy()
    for reg in sidecar_high_lanes:
        saved_gpr128[reg] = (uc.reg_read(getattr(mips_const, f"UC_MIPS_REG_{reg}")),
                             sidecar_high_lanes[reg])

    def clobber_gprs(engine, salt):
        for reg in sidecar_high_lanes:
            engine.reg_write(getattr(mips_const, f"UC_MIPS_REG_{reg}"),
                             (0xA5A5000000000000 | (reg << 16) | salt))
            sidecar_high_lanes[reg] ^= salt

    def intercept(engine, address, size, data):
        if address in lq_after:
            reg = lq_after[address]
            engine.reg_write(getattr(mips_const, f"UC_MIPS_REG_{reg}"), saved_gpr128[reg][0])
            sidecar_high_lanes[reg] = saved_gpr128[reg][1]
        if address in sq_regs:
            reg = sq_regs[address]
            saved_gpr128[reg] = (
                engine.reg_read(getattr(mips_const, f"UC_MIPS_REG_{reg}")),
                sidecar_high_lanes[reg],
            )
        recent_addresses.append(address)
        del recent_addresses[:-12]
        if address in (0x189E40, 0x975A78):
            constructor_inputs.append((address, tuple(engine.reg_read(r) for r in
                (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)),
                engine.reg_read(UC_MIPS_REG_T0), tuple(engine.reg_read(r) for r in
                    (UC_MIPS_REG_F12, UC_MIPS_REG_F13, UC_MIPS_REG_F14,
                     UC_MIPS_REG_F15, UC_MIPS_REG_F16))))
            resume = engine.reg_read(UC_MIPS_REG_RA)
            engine.reg_write(UC_MIPS_REG_PC, resume)
            clobber_gprs(engine, 0x5A)
            engine.reg_write(UC_MIPS_REG_V0, helper_handle)
        elif address == 0x18B120:
            setter_inputs.append((engine.reg_read(UC_MIPS_REG_A0),
                                  engine.reg_read(UC_MIPS_REG_F12),
                                  engine.reg_read(UC_MIPS_REG_F13)))
            # Native setter is permitted to return an unrelated value in V0.
            engine.reg_write(UC_MIPS_REG_V0, 0xDEADBEEF)
            resume = engine.reg_read(UC_MIPS_REG_RA)
            engine.reg_write(UC_MIPS_REG_PC, resume)
            clobber_gprs(engine, 0xA5)
        elif address == ret:
            engine.emu_stop()

    uc.hook_add(UC_HOOK_CODE, intercept)
    try:
        uc.emu_start(helper_va, helper_va + len(helper) + 0x100, count=5000)
    except Exception as error:
        raise AssertionError(f"helper emulation failed near {recent_addresses!r}") from error
    changed_codes = [struct.unpack("<H", uc.mem_read(nodes + i * 0x124, 2))[0]
                     for i in range(len(values))]
    return (uc, helper_handle, codes, changed_codes, constructor_inputs,
            setter_inputs, sentinels, sidecar_high_lanes, original_high_lanes,
            saved_gpr128)


@unittest.skipUnless(UNICORN_AVAILABLE and SOURCE_ELF.is_file(),
                     "Requires Unicorn and the pinned local 15g ELF")
class NativeItemMetricPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE_ELF.read_bytes()

    def test_native_spaces_and_newlines_obey_instance_layout_metrics(self):
        # Execute the native FF0B, FF0A, FF0E and ordinary branches, including
        # their floating-point arithmetic, from the pinned renderer code.
        for control, expected_x, expected_y in (
            (0xFF0B, 16.0, 0.0),
            (0xFF0A, 8.0, 0.0),
            (0xFF0E, 0.0, 9.0),
        ):
            with self.subTest(control=hex(control)):
                x, y = _native_metric_step(self.source, control,
                                           scale=0.5, line_pitch=9.0)
                self.assertAlmostEqual(x, expected_x, places=4)
                self.assertAlmostEqual(y, expected_y, places=4)
        old_x, old_y = _native_metric_step(self.source, 0xFF0E,
                                            scale=0.5, line_pitch=18.0)
        self.assertEqual((old_x, old_y), (0.0, 18.0))

    def test_details_maximum_rows_stay_above_native_recipe_boundary(self):
        # Native paragraph origin is +16; recipe content begins at +76.
        # Scaled glyph ink is 9px high and the proposed explicit pitch is 9px.
        from tools.r67_15g_item_details import _va_to_offset

        table = _va_to_offset(self.source, 0x974EA8)
        observed_row_counts = []
        for item_id in range(756):
            pointer = struct.unpack_from("<I", self.source, table + item_id * 4)[0]
            if pointer == 0:
                continue
            offset = _va_to_offset(self.source, pointer)
            end = self.source.find(b"\0", offset)
            text = self.source[offset:end].decode("cp932")
            rows = [row for row in text.split("＠改行") if row]
            observed_row_counts.append(len(rows))
            for row_index, row in enumerate(rows):
                bottom = 16 + row_index * 9 + 8
                self.assertLessEqual(bottom, 75, msg=f"item {item_id}, row {row_index}")
                normalized_width = len(row) * 8
                self.assertLessEqual(normalized_width, 220,
                                     msg=f"item {item_id}, row {row_index} width")
        self.assertEqual(max(observed_row_counts), 6)
        row_origins = (16, 25, 34, 43, 52, 61)
        self.assertEqual(max(origin + 8 for origin in row_origins), 69)
        self.assertLessEqual(69, 75)
        self.assertGreater(70 + 8, 75)  # a seventh row crosses the boundary

    def test_staged_details_rows_reproduce_native_space_overflow_and_fit_after_normalization(self):
        from tools.r67_15g_item_details import _va_to_offset

        table = _va_to_offset(self.source, 0x974EA8)
        measured = {}
        for item_id in (68, 264):
            pointer = struct.unpack_from("<I", self.source, table + item_id * 4)[0]
            offset = _va_to_offset(self.source, pointer)
            end = self.source.find(b"\0", offset)
            text = self.source[offset:end].decode("cp932")
            rows = [row for row in text.split("＠改行") if row]
            if item_id == 68:
                self.assertEqual(rows[0], "Ｃｏｍｐｒｅｓｓｅｄ\u3000ｇａｓ\u3000ｇｒｅｎａｄｅ\u3000ｔｈａｔ")
                self.assertEqual(rows[1], "ｉｓ\u3000ｖｅｒｙ\u3000ｌｅｔｈａｌ\u3000ｕｐｏｎ\u3000ｉｍｐａｃｔ．")
            widths = []
            for row in rows:
                spaces = row.count("\u3000")
                glyphs = len(row) - spaces
                widths.append((glyphs * 8 + spaces * 16,
                               glyphs * 8 + spaces * 8))
            measured[item_id] = widths
            self.assertTrue(all(fitted <= 220 for _old, fitted in widths))
            self.assertTrue(all(26 + fitted - 1 <= 245 for _old, fitted in widths))

        self.assertEqual(measured[68][0], (240, 216))
        self.assertEqual(measured[68][1], (248, 216))
        self.assertEqual(measured[264][0], (232, 208))
        self.assertEqual(measured[264][1], (232, 208))

    def test_original_grenade_and_aqua_regia_stream_width_exceeds_details_box(self):
        fullwidth, _ = _native_metric_step(self.source, 0xFF0B,
                                            scale=0.5, line_pitch=9.0)
        halfwidth, _ = _native_metric_step(self.source, 0xFF0A,
                                            scale=0.5, line_pitch=9.0)
        width = 0.0
        aqua = 0.0
        for _ in range(24):
            width = _native_cursor_add(self.source, width, 8.0)
        for _ in range(23):
            aqua = _native_cursor_add(self.source, aqua, 8.0)
        width = _native_cursor_add(self.source, width, 3 * fullwidth)
        aqua = _native_cursor_add(self.source, aqua, 3 * fullwidth)
        self.assertGreater(width, 220)
        self.assertGreater(aqua, 220)
        width = 0.0
        aqua = 0.0
        for _ in range(24):
            width = _native_cursor_add(self.source, width, 8.0)
        for _ in range(23):
            aqua = _native_cursor_add(self.source, aqua, 8.0)
        width = _native_cursor_add(self.source, width, 3 * halfwidth)
        aqua = _native_cursor_add(self.source, aqua, 3 * halfwidth)
        self.assertLessEqual(width, 220)
        self.assertLessEqual(aqua, 220)

    def test_native_ordinary_glyph_advance_site_and_ee_accumulator_opcodes_are_pinned(self):
        bias = 0xFFF80
        adda = struct.unpack_from("<I", self.source, 0x18E010 - bias)[0]
        madd = struct.unpack_from("<I", self.source, 0x18E014 - bias)[0]
        add = struct.unpack_from("<I", self.source, 0x18E018 - bias)[0]
        self.assertEqual(adda, 0x46190018)   # EE ADDA.S: ACC = f0 + letter spacing
        self.assertEqual(madd, 0x4601D81C)   # EE MADD.S: f0 = ACC + width * scale
        self.assertEqual(add, 0x4600AD40)    # native cursor += computed advance

        advance, cursor = _native_ordinary_advance(
            self.source, 32.0, scale=0.5, spacing=0.0)
        self.assertAlmostEqual(advance, 8.0, places=5)
        self.assertAlmostEqual(cursor, 40.0, places=5)
        advance, cursor = _native_ordinary_advance(
            self.source, 32.0, scale=0.5, spacing=1.0)
        self.assertAlmostEqual(advance, 9.0, places=5)
        self.assertAlmostEqual(cursor, 41.0, places=5)

    def test_details_fallback_and_all_recipe_branches_run_bounded_helpers(self):
        from unicorn.mips_const import UC_MIPS_REG_V0

        _candidate, report = build(self.source)
        details_va = int(report["details_helper_va"], 16)
        recipe_va = int(report["recipe_helper_va"], 16)
        details_offset = details_va - 0x902F00 + 0x803150
        recipe_offset = recipe_va - 0x902F00 + 0x803150
        candidate, _ = build(self.source)
        details_helper = candidate[details_offset:details_offset + report["details_helper_bytes"]]
        recipe_helper = candidate[recipe_offset:recipe_offset + report["recipe_helper_bytes"]]

        fallback_stream = [0x82A0, 0xFF0B, 0x8341, 0xFF0E, 0x82A2]
        uc, handle, before, after, calls, setters, sentinels, high, original_high, saved = _run_layout_helper(
            details_helper, details_va, details=True, codes=fallback_stream)
        self.assertEqual(calls[0][0], 0x975A78)
        self.assertEqual(calls[0][1], tuple(sentinels[reg] for reg in (
            UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)))
        self.assertEqual(calls[0][2], sentinels[UC_MIPS_REG_T0])
        self.assertEqual(calls[0][3], tuple(_fword(value) for value in
            (0.75, 1.0, 0.25, 0.5, 0.625)))
        self.assertEqual(calls[0][2] & 0xFFFFFFFF,
                         sentinels[UC_MIPS_REG_T0] & 0xFFFFFFFF)
        self.assertEqual(after, [0x82A0, 0xFF0A, 0x8341, 0xFF0E, 0x82A2],
                         msg=f"setters={setters!r}")
        self.assertEqual(setters, [(handle, _fword(0.5), _fword(0.5))])
        self.assertEqual(struct.unpack("<f", uc.mem_read(0x22102C, 4))[0], -9.0)
        self.assertEqual(uc.reg_read(UC_MIPS_REG_V0), handle)
        self.assertEqual(uc.reg_read(UC_MIPS_REG_SP), 0x210800)
        self.assertTrue(all((uc.reg_read(reg) & 0xFFFFFFFF) == (value & 0xFFFFFFFF)
                            for reg, value in sentinels.items()))
        self.assertEqual(high, original_high)
        from unicorn import mips_const
        self.assertTrue(all(uc.reg_read(getattr(mips_const, f"UC_MIPS_REG_{reg}")) == value[0]
                            for reg, value in saved.items() if reg != 2))

        for branch_name, codes in (
            ("ingredient", [0x8241] * 24 + [0xFF0B] + [0x8242] * 3),
            ("success", [0x8241] * 23 + [0xFF0B] * 3),
            ("failure", [0x8241] * 41 + [0xFF0B] * 2),
        ):
            with self.subTest(branch=branch_name):
                uc, handle, before, after, calls, setters, sentinels, high, original_high, saved = _run_layout_helper(
                    recipe_helper, recipe_va, details=False, codes=codes)
                self.assertEqual(calls[0][0], 0x189E40)
                self.assertEqual(calls[0][1], tuple(sentinels[reg] for reg in (
                    UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3)))
                self.assertEqual(calls[0][2], sentinels[UC_MIPS_REG_T0])
                self.assertEqual(calls[0][3], tuple(_fword(value) for value in
                    (0.75, 1.0, 0.25, 0.5, 0.625)))
                self.assertEqual(after, [0xFF0A if code == 0xFF0B else code for code in before],
                                 msg=f"setter={setters!r}")
                scale = struct.unpack("<f", struct.pack("<I", setters[0][1]))[0]
                expected = recipe_metrics(codes.count(0x8241) +
                    sum(code not in (0xFF0A, 0xFF0B, 0xFF0E, 0x8241) for code in codes),
                    codes.count(0xFF0B))
                self.assertAlmostEqual(scale, expected["scale_x"], places=5)
                self.assertEqual(setters[0][0], handle)
                self.assertEqual(setters[0][2], _fword(0.5))
                self.assertEqual(struct.unpack("<f", uc.mem_read(0x22102C, 4))[0], 0.0)
                self.assertEqual(uc.reg_read(UC_MIPS_REG_V0), handle)
                self.assertEqual(uc.reg_read(UC_MIPS_REG_SP), 0x210800)
                self.assertTrue(all((uc.reg_read(reg) & 0xFFFFFFFF) == (value & 0xFFFFFFFF)
                                    for reg, value in sentinels.items()))
                self.assertEqual(high, original_high)
                self.assertTrue(all(uc.reg_read(getattr(mips_const, f"UC_MIPS_REG_{reg}")) == value[0]
                                    for reg, value in saved.items() if reg != 2))

    def test_malformed_streams_are_rejected_before_any_mutation_or_setter_call(self):
        _candidate, report = build(self.source)
        recipe_va = int(report["recipe_helper_va"], 16)
        offset = recipe_va - 0x902F00 + 0x803150
        candidate, _ = build(self.source)
        helper = candidate[offset:offset + report["recipe_helper_bytes"]]
        for codes, chain_too_long, bad_head in (([0x8241, 0xFF20], False, None),
                                                ([0x8241], True, None),
                                                ([], False, 0x02000000),
                                                ([], False, 0x230002)):
            with self.subTest(chain_too_long=chain_too_long, bad_head=bad_head):
                uc, _handle, before, after, _calls, setters, _sentinels, _high, _original_high, _saved = \
                    _run_layout_helper(helper, recipe_va, details=False,
                                       codes=codes, malformed=chain_too_long,
                                       head_override=bad_head)
                self.assertEqual(after[:len(before)], before)
                self.assertEqual(setters, [])
                self.assertEqual(struct.unpack("<f", uc.mem_read(0x22102C, 4))[0], 0.0)


if __name__ == "__main__":
    unittest.main()
