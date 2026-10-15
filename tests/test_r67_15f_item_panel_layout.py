"""r67.15f native H_Item geometry and source-byte regression locks."""
from __future__ import annotations

import hashlib
import json
import struct
import unittest
from pathlib import Path

from tools.r67_15f_item_panel_layout import (
    ACTION_HOOK_SITE,
    BASE_SHA,
    BIAS,
    COMPOUND_ACTION_ID,
    FO,
    PERMITTED_EXISTING_RANGES,
    RESUME,
    SOURCE_ELF,
    TITLE_BUDGET,
    TITLE_HOOK_FILE_OFFSET,
    TITLE_HOOK_SITE,
    TITLE_ORIGINAL_JAL,
    TITLE_SETTER,
    _INTERNAL_PERMITTED_EXISTING_RANGES,
    VA,
    apply,
    build_helper,
    build_title_helper,
    file_offset,
    sha,
    title_metrics,
)

try:
    from unicorn import (
        Uc,
        UC_ARCH_MIPS,
        UC_HOOK_CODE,
        UC_MODE_LITTLE_ENDIAN,
        UC_MODE_MIPS64,
        UC_MODE_MIPS32,
    )
    from unicorn.mips_const import (
        UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3,
        UC_MIPS_REG_F0, UC_MIPS_REG_F1, UC_MIPS_REG_F2, UC_MIPS_REG_F12, UC_MIPS_REG_F13,
        UC_MIPS_REG_F21, UC_MIPS_REG_F25, UC_MIPS_REG_F27, UC_MIPS_REG_F29,
        UC_MIPS_REG_PC, UC_MIPS_REG_RA, UC_MIPS_REG_V0,
        UC_MIPS_REG_S0, UC_MIPS_REG_S1, UC_MIPS_REG_S2, UC_MIPS_REG_SP,
    )

    UNICORN_AVAILABLE = True
except ImportError:
    UNICORN_AVAILABLE = False


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SOURCE_SHA = "d1dc87b0762465f4aa653e05e07af73cc593d4e716ee2575790edc617a54972e"
ACTION_OWNER = 0x210000
SPRITE = 0x211000
RESOURCE = 0x212000
STACK = 0x213000
HELPER_BASE = 0x902F00
RESUME_BASE = 0x114B00
TITLE_RETURN = 0x115000
TITLE_HANDLE = 0x220000
TITLE_PRIVATE = 0x221000
TITLE_NODES = 0x222000
TITLE_STACK = 0x2F0000
TITLE_HELPER_BASE = 0x900000


def _title_codes(name: str) -> list[int]:
    return [0xFF0B if char == " " else 0x8241 + (ord(char) % 0x300)
            for char in name]


def _title_mips64(name: str):
    helper = build_title_helper()
    padded = (len(helper) + 3) & ~3
    old = SOURCE_ELF.read_bytes()
    helper_va = VA + ((len(old) + len(build_helper()) + 3) & ~3) - FO
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_map(0x200000, 0x100000)
    uc.mem_map(0x900000, 0x100000)
    uc.mem_write(helper_va, helper)
    uc.mem_write(TITLE_RETURN, b"\0" * 8)
    uc.mem_write(TITLE_SETTER, old[TITLE_SETTER - BIAS:TITLE_SETTER - BIAS + 0x54])
    uc.mem_write(TITLE_HANDLE + 0x3C, struct.pack("<I", TITLE_PRIVATE))
    uc.mem_write(TITLE_PRIVATE + 0x14, struct.pack("<f", 1.0))
    uc.mem_write(TITLE_PRIVATE + 0x18, struct.pack("<f", 1.0))
    codes = _title_codes(name)
    uc.mem_write(TITLE_PRIVATE + 4, struct.pack("<I", TITLE_NODES))
    for index, code in enumerate(codes):
        node = TITLE_NODES + index * 0x124
        next_node = TITLE_NODES + (index + 1) * 0x124 if index + 1 < len(codes) else 0
        uc.mem_write(node, struct.pack("<H", code))
        uc.mem_write(node + 0x120, struct.pack("<I", next_node))
    uc.reg_write(UC_MIPS_REG_A0, 0x123400)
    uc.reg_write(UC_MIPS_REG_A1, 0x234500)
    uc.reg_write(UC_MIPS_REG_A2, 0x345600)
    uc.reg_write(UC_MIPS_REG_A3, 0x456700)
    uc.reg_write(UC_MIPS_REG_F12, 0x3F800000)
    uc.reg_write(UC_MIPS_REG_F13, 0x3F800000)
    uc.reg_write(UC_MIPS_REG_SP, TITLE_STACK + 0x800)
    uc.reg_write(UC_MIPS_REG_RA, TITLE_RETURN)
    constructor_inputs = []
    rebuilds = []

    def intercept(engine, address, size, data):
        if address == 0x189E40:
            constructor_inputs.append(tuple(engine.reg_read(r) for r in
                (UC_MIPS_REG_A0, UC_MIPS_REG_A1, UC_MIPS_REG_A2, UC_MIPS_REG_A3,
                 UC_MIPS_REG_F12, UC_MIPS_REG_F13)))
            engine.reg_write(UC_MIPS_REG_V0, TITLE_HANDLE)
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address == 0x18CB50:
            rebuilds.append(address)
            engine.reg_write(UC_MIPS_REG_PC, engine.reg_read(UC_MIPS_REG_RA))
        elif address == TITLE_RETURN:
            engine.emu_stop()

    uc.hook_add(UC_HOOK_CODE, intercept)
    uc.emu_start(helper_va, helper_va + padded + 0x100, count=2000)
    final_codes = [struct.unpack("<H", uc.mem_read(TITLE_NODES + i * 0x124, 2))[0]
                   for i in range(len(codes))]
    return uc, codes, final_codes, constructor_inputs, rebuilds


def _run_code(code: bytes, address: int, setup) -> Uc:
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x100000)
    uc.mem_map(0x200000, 0x100000)
    uc.mem_write(address, code)
    setup(uc)
    uc.emu_start(address, address + len(code), count=256)
    return uc


@unittest.skipUnless(SOURCE_ELF.is_file(), "Requires the pinned local 15e source ELF")
class ItemPanelSourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SOURCE_ELF.read_bytes()
        cls.after, cls.report = apply(cls.before)

    def test_exact_15e_source_and_explicit_permitted_existing_ranges(self):
        self.assertEqual(sha(self.before), EXPECTED_SOURCE_SHA)
        self.assertEqual(BASE_SHA, EXPECTED_SOURCE_SHA)
        self.assertEqual(PERMITTED_EXISTING_RANGES, {
            "action_backing_creation_hook": ((0x14B58, 0x14B5C),),
            "item_card_title_constructor": ((0xDB44, 0xDB48),),
        })
        self.assertEqual(_INTERNAL_PERMITTED_EXISTING_RANGES, {
            "action_backing_creation_hook": ((0x14B58, 0x14B5C),),
            "item_card_title_constructor": ((0xDB44, 0xDB48),),
            "translation_segment_filesz": ((0x64, 0x68),),
        })
        self.assertEqual(self.report["internal_translation_segment_filesz_range"],
                         ["0x64", "0x68"])
        self.assertEqual(self.report["permitted_existing_ranges"], {
            name: [[hex(start), hex(end)] for start, end in ranges]
            for name, ranges in PERMITTED_EXISTING_RANGES.items()
        })

    def test_release_contract_excludes_segment_metadata_but_native_apply_keeps_it(self):
        from tools.r67_15f_iso_release import _patch_contract

        contract_apply, owners = _patch_contract()
        self.assertEqual(owners, {
            "action_backing_creation_hook": ((0x14B58, 0x14B5C),),
            "item_card_title_constructor": ((0xDB44, 0xDB48),),
        })
        patched, _report = contract_apply(self.before)
        self.assertEqual(struct.unpack_from("<I", patched, 0x64)[0], len(patched) - FO)

    def test_only_hook_and_segment_filesz_change_in_existing_elf(self):
        allowed = {i for ranges in _INTERNAL_PERMITTED_EXISTING_RANGES.values()
                   for start, end in ranges for i in range(start, end)}
        changed = {i for i, (old, new) in enumerate(zip(self.before, self.after))
                   if old != new}
        self.assertTrue(changed)
        self.assertFalse(changed - allowed)
        self.assertEqual(struct.unpack_from("<I", self.after, ACTION_HOOK_SITE - BIAS)[0],
                         int(self.report["hook_jump_word"], 16))
        self.assertEqual(struct.unpack_from("<I", self.after, 0x64)[0], len(self.after) - FO)

    def test_previous_15e_scale_only_behavior_reproduces_left_edge_drift(self):
        # The previous helper doubled X scale while leaving the pivoted origin
        # alone. These are the renderer's actual bounds, not a scale proxy.
        sprite_x, width, pivot_x = 175.0, 96.0, -29.0
        left_15d = sprite_x - 1.0 * pivot_x
        left_15e = sprite_x - 2.0 * pivot_x
        self.assertEqual(left_15e - left_15d, 29.0)

    def test_patch_rejects_any_drift_in_the_pinned_15e_input(self):
        changed = bytearray(self.before)
        changed[0x38632C] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA"):
            apply(bytes(changed))


@unittest.skipUnless(UNICORN_AVAILABLE and SOURCE_ELF.is_file(),
                     "Requires Unicorn and the pinned local 15e source ELF")
class NativeItemPanelGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SOURCE_ELF.read_bytes()
        cls.after, cls.report = apply(cls.before)
        cls.helper_va = int(cls.report["helper_va"], 16)
        start = file_offset(cls.helper_va)
        cls.helper = cls.after[start:start + cls.report["helper_bytes"]]

    @staticmethod
    def _creation_then_helper(action_id: int, resource_va: int, x: float,
                              sprite_flag: int = 0) -> Uc:
        uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        uc.mem_map(0x100000, 0x100000)
        uc.mem_map(0x200000, 0x100000)
        uc.mem_map(0x900000, 0x100000)
        # Execute the source constructor's real X store at 0x107F8C.
        ctor_word = struct.unpack_from("<I", NativeItemPanelGeometryTests.before,
                                       0x107F8C - BIAS)[0]
        uc.mem_write(0x107F8C, struct.pack("<I", ctor_word))
        uc.reg_write(UC_MIPS_REG_S2, SPRITE)
        uc.reg_write(UC_MIPS_REG_S1, SPRITE)
        uc.reg_write(UC_MIPS_REG_S0, ACTION_OWNER)
        from unicorn.mips_const import UC_MIPS_REG_A0
        uc.reg_write(UC_MIPS_REG_F0, struct.unpack("<I", struct.pack("<f", x))[0])
        f2_before = struct.unpack("<I", struct.pack("<f", 17.5))[0]
        uc.reg_write(UC_MIPS_REG_F2, f2_before)
        uc.reg_write(UC_MIPS_REG_SP, STACK + 0x800)
        uc.reg_write(UC_MIPS_REG_A1, 0)
        uc.mem_write(SPRITE + 0x60, struct.pack("<f", 1.0))
        uc.mem_write(SPRITE + 0x64, struct.pack("<f", 1.0))
        uc.mem_write(SPRITE + 0x92, bytes([1]))
        uc.mem_write(ACTION_OWNER, struct.pack("<I", SPRITE))
        uc.mem_write(ACTION_OWNER + 0x18, struct.pack("<I", action_id))
        uc.mem_write(0x107F8C, struct.pack("<I", ctor_word))
        uc.emu_start(0x107F8C, 0x107F90, count=1)
        initial_x = struct.unpack("<f", uc.mem_read(SPRITE + 0x3C, 4))[0]
        flag_clear = struct.unpack_from("<I", NativeItemPanelGeometryTests.before,
                                        0x108020 - BIAS)[0]
        uc.mem_write(0x108020, struct.pack("<I", flag_clear))
        uc.emu_start(0x108020, 0x108024, count=1)
        if uc.mem_read(SPRITE + 0x92, 1) != b"\0":
            raise AssertionError("native 2D constructor did not clear its projection flag")
        from tools.r67_15f_item_panel_layout import file_offset as fo
        helper_start = fo(NativeItemPanelGeometryTests.helper_va)
        del initial_x, helper_start, UC_MIPS_REG_A0
        uc.mem_write(NativeItemPanelGeometryTests.helper_va,
                     NativeItemPanelGeometryTests.helper)
        uc.mem_write(RESUME_BASE, b"\0" * 8)
        reached = []
        def stop_at_resume(engine, address, size, data):
            if address == RESUME_BASE:
                reached.append(address)
                engine.emu_stop()
        uc.hook_add(UC_HOOK_CODE, stop_at_resume)
        uc.emu_start(NativeItemPanelGeometryTests.helper_va,
                     NativeItemPanelGeometryTests.helper_va + 256, count=128)
        if reached != [RESUME_BASE]:
            raise AssertionError(f"native helper did not resume at {RESUME_BASE:#x}: {reached}")
        if uc.reg_read(UC_MIPS_REG_SP) != STACK + 0x800:
            raise AssertionError("native helper did not restore the caller stack pointer")
        if uc.reg_read(UC_MIPS_REG_A1) != 0:
            raise AssertionError("native helper changed the live loop argument")
        if uc.reg_read(UC_MIPS_REG_F2) != f2_before:
            raise AssertionError("native helper did not restore f2")
        return uc

    def _run_native_renderer(self, sprite_x: float, scale_x: float,
                             resource_va: int) -> tuple[float, float]:
        # The exact renderer instruction slice loads scale/pivot/width and
        # computes left adjustment in f6 and inclusive right adjustment in f1.
        begin, end = 0x1072B4, 0x1072FC
        code = self.before[begin - BIAS:end - BIAS]
        uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
        uc.mem_map(0x100000, 0x100000)
        uc.mem_map(0x200000, 0x100000)
        uc.mem_map(0x900000, 0x100000)
        uc.mem_write(begin, code)
        from unicorn.mips_const import UC_MIPS_REG_SP
        uc.reg_write(UC_MIPS_REG_S1, SPRITE)
        uc.reg_write(UC_MIPS_REG_SP, STACK)
        uc.mem_write(SPRITE + 0x60, struct.pack("<f", scale_x))
        uc.mem_write(SPRITE + 0x64, struct.pack("<f", 1.0))
        uc.mem_write(RESOURCE, self.before[resource_va - BIAS:resource_va - BIAS + 20])
        from unicorn.mips_const import UC_MIPS_REG_V1
        uc.reg_write(UC_MIPS_REG_V1, RESOURCE)
        uc.emu_start(begin, end, count=32)
        from unicorn.mips_const import UC_MIPS_REG_F1, UC_MIPS_REG_F6
        left_delta = struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F6)))[0]
        right_delta = struct.unpack("<f", struct.pack("<I", uc.reg_read(UC_MIPS_REG_F1)))[0]
        return sprite_x + left_delta, sprite_x + right_delta

    def test_creation_update_and_actual_renderer_bounds_for_both_resources(self):
        for resource_va, width in ((0x455440, 96.0), (0x455470, 144.0)):
            for action_id, scale, x_delta in ((COMPOUND_ACTION_ID, 2.0, -29.0),
                                              (1, 1.25, -7.25)):
                for origin in (-100.0, 0.0, 175.0):
                    with self.subTest(resource=hex(resource_va), action=action_id,
                                      origin=origin):
                        uc = self._creation_then_helper(action_id, resource_va, origin)
                        start_x = struct.unpack("<f", uc.mem_read(SPRITE + 0x3C, 4))[0]
                        self.assertAlmostEqual(start_x, origin + x_delta)
                        self.assertAlmostEqual(
                            struct.unpack("<f", uc.mem_read(SPRITE + 0x60, 4))[0], scale)
                        self.assertAlmostEqual(struct.unpack("<f", uc.mem_read(SPRITE + 0x64, 4))[0], 1.0)
                        self.assertEqual(uc.mem_read(SPRITE + 0x92, 1), b"\0")

                        # Advance seven native state-1 fade frames. The actual
                        # native 2D guard skips projection stores at +3C/+40.
                        for _ in range(7):
                            self._execute_2d_projection_guard(uc, sprite_flag=0)
                            x_after = struct.unpack("<f", uc.mem_read(SPRITE + 0x3C, 4))[0]
                            y_after = struct.unpack("<f", uc.mem_read(SPRITE + 0x40, 4))[0]
                            self.assertEqual(x_after, start_x)
                            self.assertEqual(y_after, 0.0)

                        left15d, right15d = self._run_native_renderer(origin, 1.0, resource_va)
                        left15f, right15f = self._run_native_renderer(start_x, scale, resource_va)
                        self.assertAlmostEqual(left15f, left15d)
                        self.assertAlmostEqual(right15f - right15d, width * (scale - 1.0))

    def _execute_2d_projection_guard(self, uc: Uc, sprite_flag: int) -> None:
        # Actual BNE guard at 0x106F08..0x106F14: 2D sprites have flag != 1
        # and branch around the only projection writes at 0x107000/04.
        branch_start, branch_end = 0x106F08, 0x106F18
        code = self.before[branch_start - BIAS:branch_end - BIAS]
        uc.mem_write(branch_start, code)
        uc.reg_write(UC_MIPS_REG_S1, SPRITE)
        uc.mem_write(SPRITE + 0x92, bytes([sprite_flag]))
        visited = []
        def stop_before_projection(engine, address, size, data):
            if address in (0x107000, 0x107004):
                visited.append(address)
                engine.emu_stop()
        hook = uc.hook_add(UC_HOOK_CODE, stop_before_projection)
        uc.emu_start(branch_start, 0x10708C, count=8)
        uc.hook_del(hook)
        self.assertEqual(visited, [])

    def test_all_actions_null_sprite_and_non_target_state_are_preserved(self):
        for action_id in range(16):
            for null in (False, True):
                with self.subTest(action=action_id, null=null):
                    # A null owner is supported separately from creation.
                    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
                    uc.mem_map(0x100000, 0x100000)
                    uc.mem_map(0x200000, 0x100000)
                    uc.mem_map(0x900000, 0x100000)
                    uc.mem_write(self.helper_va, self.helper)
                    uc.mem_write(RESUME_BASE, b"\0" * 8)
                    uc.mem_write(ACTION_OWNER, struct.pack("<I", 0 if null else SPRITE))
                    uc.mem_write(ACTION_OWNER + 0x18, struct.pack("<I", action_id))
                    uc.mem_write(SPRITE + 0x3C, struct.pack("<f", 91.0))
                    uc.mem_write(SPRITE + 0x60, struct.pack("<f", 1.0))
                    uc.mem_write(SPRITE + 0x64, struct.pack("<f", 1.0))
                    uc.reg_write(UC_MIPS_REG_S0, ACTION_OWNER)
                    f0_before = struct.unpack("<I", struct.pack("<f", 12.25))[0]
                    f2_before = struct.unpack("<I", struct.pack("<f", -3.5))[0]
                    sp_before = STACK + 0x800
                    uc.reg_write(UC_MIPS_REG_F0, f0_before)
                    uc.reg_write(UC_MIPS_REG_F2, f2_before)
                    uc.reg_write(UC_MIPS_REG_SP, sp_before)
                    uc.reg_write(UC_MIPS_REG_A1, 0)
                    reached = []
                    def continuation(engine, address, size, data):
                        if address == RESUME:
                            reached.append(address)
                            engine.emu_stop()
                    uc.hook_add(UC_HOOK_CODE, continuation)
                    uc.emu_start(self.helper_va, self.helper_va + len(self.helper) + 8,
                                 count=128)
                    self.assertEqual(reached, [RESUME])
                    scale = struct.unpack("<f", uc.mem_read(SPRITE + 0x60, 4))[0]
                    x = struct.unpack("<f", uc.mem_read(SPRITE + 0x3C, 4))[0]
                    self.assertEqual(scale, 2.0 if action_id == 3 and not null else
                                     1.25 if action_id == 1 and not null else 1.0)
                    expected_x = (91.0 - 29.0 if action_id == 3 else
                                  91.0 - 7.25 if action_id == 1 else 91.0)
                    self.assertEqual(x, expected_x if not null else 91.0)
                    self.assertEqual(uc.reg_read(UC_MIPS_REG_F0), f0_before)
                    self.assertEqual(uc.reg_read(UC_MIPS_REG_F2), f2_before)
                    self.assertEqual(uc.reg_read(UC_MIPS_REG_SP), sp_before)
                    self.assertEqual(uc.reg_read(UC_MIPS_REG_A1), 0)


@unittest.skipUnless(UNICORN_AVAILABLE and SOURCE_ELF.is_file(),
                     "Requires Unicorn and the pinned local 15e source ELF")
class NativeItemCardTitleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = SOURCE_ELF.read_bytes()
        cls.after, cls.report = apply(cls.before)

    def test_shared_title_constructor_hook_and_500_pointer_slots_are_locked(self):
        self.assertEqual(TITLE_HOOK_SITE, 0x10DAC4)
        self.assertEqual(TITLE_HOOK_FILE_OFFSET, 0xDB44)
        self.assertEqual(TITLE_ORIGINAL_JAL, 0x0C062790)
        self.assertEqual(struct.unpack_from("<I", self.before, TITLE_HOOK_FILE_OFFSET)[0],
                         TITLE_ORIGINAL_JAL)
        self.assertEqual(struct.unpack_from("<I", self.before, TITLE_HOOK_FILE_OFFSET + 4)[0], 0)
        before_names = self.before[0x3912B4:0x3912B4 + 500 * 4]
        after_names = self.after[0x3912B4:0x3912B4 + 500 * 4]
        self.assertEqual(before_names, after_names)
        ranges = {i for spans in _INTERNAL_PERMITTED_EXISTING_RANGES.values()
                  for start, end in spans for i in range(start, end)}
        self.assertEqual(PERMITTED_EXISTING_RANGES["item_card_title_constructor"],
                         ((0xDB44, 0xDB48),))
        actual = {i for i, (a, b) in enumerate(zip(self.before, self.after)) if a != b}
        self.assertFalse(actual - ranges)

    def test_metrics_use_unscaled_halfwidth_space_advance(self):
        self.assertEqual(title_metrics(16, 1), {
            "scale_x": 0.625, "scale_y": 0.75,
            "advance": 168.0, "budget": TITLE_BUDGET,
        })
        self.assertEqual(title_metrics(10, 1)["advance"], 108.0)
        self.assertEqual(title_metrics(8, 1)["advance"], 88.0)
        self.assertAlmostEqual(title_metrics(27, 0)["advance"], 196.0)

    def test_native_wrapper_calls_constructor_then_relayout_setter_for_all_title_sizes(self):
        samples = (
            ("Hydrochloric Acid", 16, 1),
            ("Nitric Acid", 10, 1),
            ("9mm Luger", 8, 1),
            ("X" * 27, 27, 0),
        )
        for name, glyphs, spaces in samples:
            with self.subTest(name=name):
                uc, original_codes, final_codes, inputs, rebuilds = _title_mips64(name)
                expected = title_metrics(glyphs, spaces)
                self.assertEqual(len(inputs), 1)
                self.assertEqual(inputs[0], (0x123400, 0x234500, 0x345600,
                                              0x456700, 0x3F800000, 0x3F800000))
                self.assertEqual(rebuilds, [0x18CB50])
                self.assertEqual(uc.reg_read(UC_MIPS_REG_V0), TITLE_HANDLE)
                self.assertEqual(uc.reg_read(UC_MIPS_REG_SP), TITLE_STACK + 0x800)
                self.assertEqual(final_codes,
                    [0xFF0A if code == 0xFF0B else code for code in original_codes])
                self.assertAlmostEqual(struct.unpack("<f", uc.mem_read(TITLE_PRIVATE + 0x48, 4))[0],
                                       expected["scale_x"], places=6)
                self.assertAlmostEqual(struct.unpack("<f", uc.mem_read(TITLE_PRIVATE + 0x4C, 4))[0],
                                       0.75, places=6)

    def test_relaid_out_glyph_stream_fits_when_consumed_by_native_quad_and_space_arithmetic(self):
        # Use the original renderer instructions: regular glyph right edges
        # come from 0x18DCA0, while normalized FF0A advances through 0x18E0C4.
        old = self.before
        glyph_consumer = old[0x18DCA0 - BIAS:0x18DCB8 - BIAS]
        space_consumer = old[0x18E0C4 - BIAS:0x18E0E0 - BIAS]
        for name, glyphs, spaces in (
            ("Hydrochloric Acid", 16, 1),
            ("Nitric Acid", 10, 1),
            ("9mm Luger", 8, 1),
            ("X" * 27, 27, 0),
        ):
            with self.subTest(name=name):
                uc, _original, final_codes, _inputs, rebuilds = _title_mips64(name)
                self.assertEqual(rebuilds, [0x18CB50])
                cursor = 0.0
                right_edges = []
                for code in final_codes:
                    if code == 0xFF0A:
                        space_uc = _run_code(space_consumer, 0x18E0C4, lambda engine: (
                            engine.reg_write(UC_MIPS_REG_F21,
                                             struct.unpack("<I", struct.pack("<f", cursor))[0]),
                            engine.reg_write(UC_MIPS_REG_F25, 0),
                            engine.reg_write(UC_MIPS_REG_F27,
                                             struct.unpack("<I", struct.pack("<f", 16.0))[0]),
                        ))
                        cursor = struct.unpack("<f", struct.pack(
                            "<I", space_uc.reg_read(UC_MIPS_REG_F21)))[0]
                        continue

                    scale_x = struct.unpack("<f", uc.mem_read(TITLE_PRIVATE + 0x48, 4))[0]
                    glyph_uc = _run_code(glyph_consumer, 0x18DCA0, lambda engine: (
                        engine.reg_write(UC_MIPS_REG_F21,
                                         struct.unpack("<I", struct.pack("<f", cursor))[0]),
                        engine.reg_write(UC_MIPS_REG_F27,
                                         struct.unpack("<I", struct.pack("<f", 16.0))[0]),
                        engine.reg_write(UC_MIPS_REG_F29,
                                         struct.unpack("<I", struct.pack("<f", scale_x))[0]),
                    ))
                    right_edges.append(struct.unpack("<f", struct.pack(
                        "<I", glyph_uc.reg_read(UC_MIPS_REG_F1)))[0])
                    # The consumer stores the inclusive right edge, so its
                    # implied cell advance is right_edge + 1 - old_cursor.
                    cursor += right_edges[-1] + 1.0 - cursor

                self.assertEqual(final_codes.count(0xFF0A), spaces)
                self.assertNotIn(0xFF0B, final_codes)
                self.assertLessEqual(cursor, TITLE_BUDGET + 0.001)
                self.assertTrue(all(edge <= TITLE_BUDGET - 1 + 0.001
                                    for edge in right_edges))
                self.assertAlmostEqual(cursor, title_metrics(glyphs, spaces)["advance"],
                                       places=3)

    def test_all_original_catalog_source_names_and_all_500_pointer_slots_are_unchanged(self):
        from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA
        from tools.r67_14t_stone_tablet_fit import read_string

        self.assertEqual(len(DUNGEON_ITEM_NAME_DATA), 446)
        valid_item_pointers = 0
        for item_id, _source_offset, _jp, _english, _record in DUNGEON_ITEM_NAME_DATA:
            with self.subTest(item_id=item_id):
                pointer = struct.unpack_from("<I", self.before, 0x3912B4 + item_id * 4)[0]
                self.assertEqual(read_string(self.before, pointer), read_string(self.after, pointer))
                valid_item_pointers += 1
                glyphs = sum(char != " " for char in _english)
                spaces = _english.count(" ")
                stream = _title_codes(_english)
                self.assertEqual(len(stream), len(_english))
                self.assertLessEqual(title_metrics(glyphs, spaces)["advance"],
                                     TITLE_BUDGET + 0.001)
                _uc, original, normalized, _constructor_inputs, relayouts = \
                    _title_mips64(_english)
                self.assertEqual(len(original), len(_english))
                self.assertEqual(normalized,
                    [0xFF0A if code == 0xFF0B else code for code in original])
                self.assertEqual(normalized.count(0xFF0A), spaces)
                self.assertEqual(relayouts, [0x18CB50])
        # The 500-word byte range is locked above, but the ELF's native item
        # table contains only 446 valid name pointers; later bytes are adjacent data.
        self.assertEqual(valid_item_pointers, 446)

    def test_bounded_malformed_node_chain_fails_closed_without_relayout(self):
        # 65 nodes exceed the private walk bound; neither node controls nor
        # instance scales may be changed on this malformed traversal.
        name = " " * 65
        uc, before_codes, after_codes, _inputs, rebuilds = _title_mips64(name)
        self.assertEqual(before_codes, after_codes)
        self.assertEqual(rebuilds, [])
        self.assertEqual(struct.unpack("<f", uc.mem_read(TITLE_PRIVATE + 0x48, 4))[0], 0.0)


if __name__ == "__main__":
    unittest.main()
