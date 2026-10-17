from __future__ import annotations

import hashlib
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-15g-partial-diagnostic.elf"
SOURCE_SHA256 = "74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee"
ELF_BIAS = 0xFFF80
VIEWPORT_START = 0x28FD60
VIEWPORT_END = 0x28FF08
OWNER = 0x210000
PRIVATE = 0x211000
ROWS = PRIVATE + 0x120
HANDLES = tuple(0x220000 + index * 0x100 for index in range(19))


def _run_native_viewport(elf: bytes, *, row_count: int, scroll: float = 0.0,
                         pool_base: int = 0x17A0, pool_capacity: int = 16,
                         null_slots: set[int] | None = None,
                         row_reads: list[int] | None = None, row_pitch: float = 16.0,
                         state: int = 5, mode: int = 4,
                         blank_rows: set[int] | None = None,
                         neighbor_halfword: int = 0):
    """Execute the native viewport function; intercept only external text effects."""
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import (
        UC_MIPS_REG_A0, UC_MIPS_REG_F12, UC_MIPS_REG_PC, UC_MIPS_REG_RA,
        UC_MIPS_REG_S1, UC_MIPS_REG_S4, UC_MIPS_REG_S5,
        UC_MIPS_REG_SP, UC_MIPS_REG_V0,
    )

    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    for start, size in ((0x100000, 0x100000), (0x200000, 0x100000),
                        (0x2100000, 0x100000)):
        uc.mem_map(start, size)

    native = bytearray(elf[VIEWPORT_START - ELF_BIAS:VIEWPORT_END - ELF_BIAS])
    # Unicorn's MIPS64 backend does not implement EE SQ/LQ. The original
    # instructions remain in the ELF; lower only those save/restore ops here.
    for offset in range(0, len(native), 4):
        word = struct.unpack_from("<I", native, offset)[0]
        if word >> 26 == 0x1F:
            struct.pack_into("<I", native, offset, (word & 0x03FFFFFF) | (43 << 26))
        elif word >> 26 == 0x1E:
            struct.pack_into("<I", native, offset, (word & 0x03FFFFFF) | (35 << 26))
    uc.mem_write(VIEWPORT_START, bytes(native))

    uc.mem_write(OWNER + 0x3C, struct.pack("<I", PRIVATE))
    uc.mem_write(PRIVATE + 0x1A78, struct.pack("<I", row_count))
    uc.mem_write(PRIVATE + 0x1A7C, struct.pack("<f", scroll))
    uc.mem_write(PRIVATE + 0x17E0, struct.pack("<HHH", state, neighbor_halfword, mode))
    for index, handle in enumerate(HANDLES[:pool_capacity]):
        value = 0 if null_slots and index in null_slots else handle
        uc.mem_write(PRIVATE + pool_base + index * 4, struct.pack("<I", value))
    for index in range(min(row_count, 80)):
        y = 131.0 + index * row_pitch - scroll
        record = ROWS + index * 0x48
        text = 0 if blank_rows and index in blank_rows else 0x900000 + index * 0x20
        uc.mem_write(record, struct.pack("<ffI", 64.0, y, text))

    ret = 0x210100
    uc.mem_write(ret, b"\0" * 8)
    stack = 0x210800
    uc.reg_write(UC_MIPS_REG_A0, OWNER)
    uc.reg_write(UC_MIPS_REG_SP, stack)
    uc.reg_write(UC_MIPS_REG_RA, ret)
    uc.reg_write(UC_MIPS_REG_F12, 0)
    accesses: list[tuple[str, int]] = []
    calls: list[tuple[str, int, float | None]] = []
    recent_addresses: list[int] = []

    def intercept(engine, address, size, data):
        if row_reads is not None and address in (0x28FDF4, 0x28FDF8):
            row_reads.append(address)
        recent_addresses.append(address)
        del recent_addresses[:-20]
        if address == ret:
            engine.emu_stop()
        elif address in (0x18AAB0, 0x18AAE0, 0x18A080):
            kind = {0x18AAB0: "x", 0x18AAE0: "y", 0x18A080: "text"}[address]
            handle = engine.reg_read(UC_MIPS_REG_A0)
            raw_f12 = engine.reg_read(UC_MIPS_REG_F12) & 0xFFFFFFFF
            value = struct.unpack("<f", struct.pack("<I", raw_f12))[0]
            if kind == "text" and engine.reg_read(UC_MIPS_REG_RA) == 0x28FDC4:
                accesses.append(("reset", handle))
            else:
                calls.append((kind, handle, value if kind != "text" else None))
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address == 0x1C66D0:  # the old assertion target is a no-op
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address == 0x1A1860:  # external clear-text effect in reset loop
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))

    uc.hook_add(UC_HOOK_CODE, intercept)
    try:
        uc.emu_start(VIEWPORT_START, VIEWPORT_END, count=30000)
    except Exception as error:
        pc = uc.reg_read(UC_MIPS_REG_PC)
        raise AssertionError(
            f"native viewport emulation failed at {pc:#x}, "
            f"s4={uc.reg_read(UC_MIPS_REG_S4)}, s5={uc.reg_read(UC_MIPS_REG_S5)}, "
            f"s1={uc.reg_read(UC_MIPS_REG_S1):#x}, "
            f"v0={uc.reg_read(UC_MIPS_REG_V0)}, "
            f"calls={calls[-6:]}, recent={list(map(hex, recent_addresses))}: {error}"
        ) from error
    return uc, calls, accesses


def _run_native_clear_helper(elf: bytes, helper_va: int, helper_bytes: int):
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import UC_MIPS_REG_PC, UC_MIPS_REG_RA, UC_MIPS_REG_S0

    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x200000, 0x100000)
    uc.mem_map(0x900000, 0x100000)
    uc.mem_write(helper_va, elf[helper_va - 0x902F00 + 0x803150:
                                helper_va - 0x902F00 + 0x803150 + helper_bytes])
    uc.mem_write(PRIVATE + 0x17E0, struct.pack("<HH", 5, 0xA55A))
    uc.mem_write(PRIVATE + 0x1A90, struct.pack("<I", 0xDEADBEEF))
    uc.mem_write(PRIVATE + 0x1A94, b"\xef\xbe\xad\xde" * 19)
    uc.mem_write(PRIVATE + 0x1AE0, struct.pack("<I", 0xC0FFEE11))
    ret = 0x210100
    uc.reg_write(UC_MIPS_REG_S0, PRIVATE)
    uc.reg_write(UC_MIPS_REG_RA, ret)
    uc.hook_add(UC_HOOK_CODE, lambda engine, address, _size, _data:
                engine.emu_stop() if address == ret else None)
    uc.emu_start(helper_va, helper_va + helper_bytes, count=1000)
    return uc


def _run_native_fade_loop(elf: bytes):
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import UC_MIPS_REG_A0, UC_MIPS_REG_PC, UC_MIPS_REG_RA, UC_MIPS_REG_S0, UC_MIPS_REG_V0

    start, stop = 0x290ED0, 0x290F1C
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_map(0x200000, 0x100000)
    uc.mem_write(start, elf[start - ELF_BIAS:stop - ELF_BIAS])
    for index, handle in enumerate(HANDLES[:19]):
        uc.mem_write(PRIVATE + 0x1A94 + index * 4, struct.pack("<I", handle))
    calls = []
    ret = stop

    def intercept(engine, address, _size, _data):
        if address == ret:
            engine.emu_stop()
        elif address == 0x1A1860:
            engine.reg_write(UC_MIPS_REG_V0, 1)
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address == 0x18AD30:
            calls.append(engine.reg_read(UC_MIPS_REG_A0))
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))

    uc.reg_write(UC_MIPS_REG_S0, PRIVATE)
    uc.hook_add(UC_HOOK_CODE, intercept)
    recent = []
    uc.hook_add(UC_HOOK_CODE, lambda _uc, address, _size, _data:
                recent.append(address) if len(recent) < 24 else None)
    try:
        uc.emu_start(start, stop + 4, count=1000)
    except Exception as error:
        raise AssertionError(f"native fade loop failed at {uc.reg_read(UC_MIPS_REG_PC):#x}; "
                             f"s0={uc.reg_read(UC_MIPS_REG_S0):#x}; "
                             f"recent={list(map(hex, recent))}: {error}") from error
    return calls


def _run_native_allocation_failure(elf: bytes):
    from unicorn import Uc, UC_ARCH_MIPS, UC_HOOK_CODE, UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64
    from unicorn.mips_const import UC_MIPS_REG_PC, UC_MIPS_REG_RA, UC_MIPS_REG_SP, UC_MIPS_REG_V0

    start, end = 0x291D90, 0x292084
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_map(0x200000, 0x100000)
    native = bytearray(elf[start - ELF_BIAS:end - ELF_BIAS])
    for offset in range(0, len(native), 4):
        word = struct.unpack_from("<I", native, offset)[0]
        if word >> 26 == 0x1F:
            struct.pack_into("<I", native, offset, (word & 0x03FFFFFF) | (43 << 26))
        elif word >> 26 == 0x1E:
            struct.pack_into("<I", native, offset, (word & 0x03FFFFFF) | (35 << 26))
    uc.mem_write(start, bytes(native))
    stack, ret = 0x2F0800, 0x2F0100
    uc.reg_write(UC_MIPS_REG_SP, stack)
    uc.reg_write(UC_MIPS_REG_RA, ret)
    visits = []

    def intercept(engine, address, _size, _data):
        if address == 0x105170:
            engine.reg_write(UC_MIPS_REG_V0, 0)
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address in (0x291E08, 0x291EA4):
            visits.append(address)
        elif address == ret:
            engine.emu_stop()

    uc.hook_add(UC_HOOK_CODE, intercept)
    uc.emu_start(start, end, count=2000)
    return uc.reg_read(UC_MIPS_REG_V0), visits


@unittest.skipUnless(SOURCE.is_file(), "Requires the pinned local r67.15g ELF")
class HantNativePoolRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()

    def test_pinned_source_and_native_seventeenth_visible_row_reproduce_state_handle(self):
        self.assertEqual(hashlib.sha256(self.source).hexdigest(), SOURCE_SHA256)
        _uc, calls, _accesses = _run_native_viewport(self.source, row_count=19, scroll=5.0)
        invalid = [handle for _kind, handle, _value in calls if handle == 5]
        self.assertEqual(invalid, [5, 5, 5])

    def test_relocated_pool_executes_all_seventeen_visible_rows_without_bad_handle(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        _uc, calls, _accesses = _run_native_viewport(
            patched, row_count=19, scroll=5.0, pool_base=0x1A94, pool_capacity=19
        )
        self.assertEqual(len([call for call in calls if call[0] == "text"]), 17)
        self.assertTrue(all(handle in HANDLES[:19] for _kind, handle, _ in calls))

    def test_owned_source_ranges_are_disjoint(self):
        from tools.r67_15h_hant_pool import ALLOWED_SOURCE_RANGES

        spans = sorted((start, end, name) for name, ranges in ALLOWED_SOURCE_RANGES.items()
                       for start, end in ranges)
        for previous, current in zip(spans, spans[1:]):
            self.assertLessEqual(previous[1], current[0],
                                 f"overlapping HANT ownership: {previous[2]}, {current[2]}")

    def test_over_capacity_row_skips_before_consuming_a_pool_slot(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        _uc, calls, _accesses = _run_native_viewport(
            patched, row_count=24, scroll=40.0, pool_base=0x1A94, pool_capacity=19
        )
        self.assertEqual(len([call for call in calls if call[0] == "text"]), 19)
        self.assertTrue(all(handle in HANDLES[:19] for _kind, handle, _ in calls))
        self.assertEqual([value for kind, _handle, value in calls if kind == "x"], [64.0] * 19)
        self.assertEqual([value for kind, _handle, value in calls if kind == "y"],
                         [91.0 + 16.0 * index for index in range(19)])

    def test_strict_viewport_boundaries_exclude_exact_y_89_and_y_383(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        _uc, lower_calls, _ = _run_native_viewport(
            patched, row_count=1, scroll=42.0, pool_base=0x1A94, pool_capacity=19
        )
        _uc, upper_calls, _ = _run_native_viewport(
            patched, row_count=17, scroll=4.0, pool_base=0x1A94, pool_capacity=19
        )
        self.assertEqual(lower_calls, [])
        self.assertEqual([handle for kind, handle, _ in upper_calls if kind == "text"],
                         list(HANDLES[:16]))

    def test_malformed_row_count_exits_before_loading_any_row_coordinates(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        coordinate_loads = []
        for row_count in (81, 0xFFFFFFFF):
            with self.subTest(row_count=row_count):
                coordinate_loads.clear()
                _uc, calls, _accesses = _run_native_viewport(
                    patched, row_count=row_count, pool_base=0x1A94,
                    pool_capacity=19, row_reads=coordinate_loads
                )
                self.assertEqual(calls, [])
                self.assertEqual(coordinate_loads, [])

    def test_allocation_failure_branch_preserves_native_zero_return_epilogue(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        branch = struct.unpack_from("<I", patched, 0x291E00 - ELF_BIAS)[0]
        target = 0x291E04 + ((branch & 0xFFFF) << 2)
        self.assertEqual(branch >> 26, 4)  # beq s0,zero
        self.assertEqual(target, 0x292054)
        self.assertEqual(struct.unpack_from("<I", patched, 0x291E04 - ELF_BIAS)[0], 0)
        result, visits = _run_native_allocation_failure(patched)
        self.assertEqual(result, 0)
        self.assertEqual(visits, [])

    def test_null_child_is_skipped_and_reset_covers_all_nineteen_pool_slots(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        uc, calls, resets = _run_native_viewport(
            patched, row_count=19, scroll=5.0, pool_base=0x1A94, pool_capacity=19,
            null_slots={4}, neighbor_halfword=0xA55A
        )
        self.assertEqual([handle for kind, handle, _ in calls if kind == "text"],
                         [handle for index, handle in enumerate(HANDLES[:17]) if index != 4])
        for kind in ("x", "y", "text"):
            self.assertEqual(len([call for call in calls if call[0] == kind]), 16)
        self.assertTrue(all(handle != 0 for _kind, handle, _ in calls))
        expected_reset_handles = list(HANDLES[:19])
        expected_reset_handles[4] = 0
        self.assertEqual([handle for kind, handle in resets if kind == "reset"],
                         expected_reset_handles)
        self.assertEqual(struct.unpack_from("<H", uc.mem_read(PRIVATE + 0x17E0, 2))[0], 5)

    def test_fade_loop_visits_all_nineteen_relocated_handles(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        self.assertEqual(_run_native_fade_loop(patched), list(HANDLES[:19]))

    def test_success_initializer_clears_tail_and_preserves_adjacent_canaries(self):
        from tools.r67_15h_hant_pool import build

        patched, report = build(self.source)
        uc = _run_native_clear_helper(
            patched, int(report["pool_zero_initializer_va"], 16),
            report["pool_zero_initializer_bytes"]
        )
        self.assertEqual(bytes(uc.mem_read(PRIVATE + 0x1A94, 19 * 4)), b"\0" * (19 * 4))
        self.assertEqual(struct.unpack("<I", uc.mem_read(PRIVATE + 0x1A90, 4))[0], 0xDEADBEEF)
        self.assertEqual(struct.unpack("<I", uc.mem_read(PRIVATE + 0x1AE0, 4))[0], 0xC0FFEE11)
        self.assertEqual(bytes(uc.mem_read(PRIVATE + 0x17E0, 4)),
                         struct.pack("<HH", 5, 0xA55A))

    def test_report_pins_capacity_pitch_geometry_and_keeps_runtime_claim_unverified(self):
        from tools.r67_15h_hant_pool import build

        _patched, report = build(self.source)
        self.assertEqual(report["pool_capacity"], 19)
        self.assertEqual(report["allocation_size"], hex(0x1AE0))
        self.assertEqual(report["native_row_pitches"], [16, 21])
        self.assertEqual(report["maximum_eligible_rows"], 19)
        self.assertFalse(report["runtime_verified"])
        self.assertFalse(report["door_loading_hang_resolved"])
        from tools.r67_15h_hant_pool import ALLOWED_SOURCE_RANGES
        from tools.r67_15g_iso_release import audit_component

        audit_component("hant_pool", self.source, _patched, report,
                        {f"hant_pool:{name}": ranges
                         for name, ranges in ALLOWED_SOURCE_RANGES.items()})

    def test_build_composes_after_ui_and_reports_exact_stage_delta(self):
        from tools.r67_15h_item_layout import build as build_ui
        from tools.r67_15h_hant_pool import ALLOWED_SOURCE_RANGES, build
        from tools.r67_15g_iso_release import audit_component

        ui_elf, _ui_report = build_ui(self.source)
        patched, report = build(ui_elf)
        self.assertEqual(report["appended_extent"], [len(ui_elf), len(patched)])
        self.assertEqual(report["translation_segment_filesz"], len(patched) - 0x803150)
        audit_component("hant_pool", ui_elf, patched, report,
                        {f"hant_pool:{name}": ranges
                         for name, ranges in ALLOWED_SOURCE_RANGES.items()})

    def test_row_count_boundaries_states_blank_records_and_metadata_canaries(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        for state in (4, 5):
            for row_count in (0, 1, 15, 16, 17, 19, 20, 70, 80):
                with self.subTest(state=state, row_count=row_count):
                    uc, calls, _resets = _run_native_viewport(
                        patched, row_count=row_count, pool_base=0x1A94,
                        pool_capacity=19, state=state,
                        blank_rows={1, 4} if row_count > 4 else set(),
                        neighbor_halfword=0xA55A
                    )
                    visible_rows = [index for index in range(row_count)
                                    if 89 < 131 + index * 16 < 383]
                    self.assertEqual(len([call for call in calls if call[0] == "text"]),
                                     len(visible_rows))
                    if row_count > 4:
                        self.assertIn(131.0 + 16.0, [value for kind, _, value in calls if kind == "y"])
                        self.assertIn(131.0 + 4.0 * 16.0,
                                      [value for kind, _, value in calls if kind == "y"])
                    self.assertEqual(bytes(uc.mem_read(PRIVATE + 0x17E0, 6)),
                                     struct.pack("<HHH", state, 0xA55A, 4))

    def test_native_five_pixel_sweeps_cover_four_pages_and_terminal_clamps(self):
        from tools.r67_15h_hant_pool import build

        patched, _report = build(self.source)
        for page_rows in (34, 18, 55, 70):
            max_scroll = max(0, page_rows * 21 - 222)
            positions = list(range(0, max_scroll + 1, 5))
            if not positions or positions[-1] != max_scroll:
                positions.append(max_scroll)
            for pitch in (16.0, 21.0):
                for scroll in positions:
                    with self.subTest(page_rows=page_rows, pitch=pitch, scroll=scroll):
                        _uc, calls, _resets = _run_native_viewport(
                            patched, row_count=page_rows, scroll=float(scroll),
                            row_pitch=pitch, pool_base=0x1A94, pool_capacity=19
                        )
                        expected = [index for index in range(page_rows)
                                    if 89 < 131 + index * pitch - scroll < 383]
                        emitted = [handle for kind, handle, _ in calls if kind == "text"]
                        self.assertEqual(emitted, list(HANDLES[:len(expected)]))


if __name__ == "__main__":
    unittest.main()
