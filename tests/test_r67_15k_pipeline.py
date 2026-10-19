"""Runtime diagnostics for constructor -> converter -> node/glyph builders."""
from __future__ import annotations

import unittest
import struct
from unicorn import mips_const as reg

from tests.r67_native_text_pipeline import (
    CONSTRUCTOR, CONVERTER, GLYPH_BUILDER, MEMCPY,
    NATIVE_NODE_ALLOC, NATIVE_RESOURCE_ACQUIRE, NATIVE_RESOURCE_RELEASE,
    NODE_BUILDER, OUTPUT, RUNTIME_FONT_16X18,
    NativeTextPipeline, decode_native_units, detail_string_addresses,
    direct_calls, load_historical_ee_memory, source_strings,
)


class NativeTextPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipeline = NativeTextPipeline()
        cls.source = cls.pipeline.source

    def test_actual_constructor_call_graph_reaches_conversion_and_node_builders(self):
        calls = direct_calls(self.source, CONSTRUCTOR, 0x18A300)
        targets = {target for _site, target in calls}
        self.assertIn(CONVERTER, targets)
        self.assertIn(NODE_BUILDER, targets)
        self.assertIn(GLYPH_BUILDER, targets)

    def test_official_grenade_and_ammunition_descriptions_are_loaded(self):
        descriptions = source_strings(self.source)
        self.assertIn("grenade", descriptions[20].lower())
        self.assertIn("ammunition", descriptions[334].lower())

    def test_native_converter_runs_on_real_grenade_and_ammo_descriptions(self):
        # Start the constructor's real converter on sparse strings from
        # 0x974EA8. Keep native command and character tables; model only the
        # observed memcpy and bounded-string libc calls.
        addresses = detail_string_addresses(self.source, (20, 334))

        def memcpy(engine):
            registers = (reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1, reg.UC_MIPS_REG_A2)
            dest, src, length = (engine.reg_read(register) & 0xFFFFFFFF
                                 for register in registers)
            engine.mem_write(dest, bytes(engine.mem_read(src, length)))
            engine.reg_write(reg.UC_MIPS_REG_V0, dest)
            engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

        def strlen(engine):
            source = engine.reg_read(reg.UC_MIPS_REG_A0) & 0xFFFFFFFF
            length = 0
            while length < 0x1000:
                if engine.mem_read(source + length, 1)[0] == 0:
                    break
                length += 1
            engine.reg_write(reg.UC_MIPS_REG_V0, length)
            engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

        external = {MEMCPY: memcpy, 0x39F820: strlen}
        for item_id, string_va in addresses.items():
            with self.subTest(item_id=item_id):
                probe = NativeTextPipeline(self.source)
                result = probe.execute(CONVERTER,
                                       args=(0, OUTPUT, string_va),
                                       external=external)
                self.assertTrue(result.returned, (hex(result.pc), result.steps,
                                                   [hex(call[0]) for call in result.calls]))
                units = decode_native_units(probe.uc, OUTPUT)
                controls = [unit for unit in units if unit >= 0xFF00]
                self.assertTrue(units)
                expected_controls = {
                    20: [0xFF0B, 0xFF0B, 0xFF0E, 0xFF0B, 0xFF0B, 0xFF0E,
                         0xFF0B, 0xFF0B, 0xFF0B, 0xFF0E, 0xFF0B, 0xFF0F],
                    334: [0xFF0B, 0xFF0B, 0xFF0E, 0xFF0B, 0xFF0B, 0xFF0E,
                          0xFF0B, 0xFF0B, 0xFF0B, 0xFF0B, 0xFF0E, 0xFF0B,
                          0xFF0B, 0xFF0F],
                }
                self.assertEqual(controls, expected_controls[item_id])
                self.assertNotIn(0xFF10, controls)

    def test_actual_native_nodes_reach_the_current_j_details_helper(self):
        self._assert_native_nodes(use_k=False)

    def test_wrapping_survives_native_conversion_opacity_rebuild_and_final_draw(self):
        self._assert_native_nodes(use_k=True)

    def _assert_native_nodes(self, *, use_k):
        # Historical EE RAM restores live resource pointers erased in the ELF.
        # Its saved font object is real; only the owning +0x3c wrapper is local.
        runtime_ee = load_historical_ee_memory()
        source, lower_ranges = self.source, ()
        if use_k:
            from tools.r67_15k_description_layout import build
            source, report = build(source)
            lower_ranges = ((0x902f00 + len(self.source) - 0x803150,
                             0x902f00 + len(source) - 0x803150),)
        addresses = detail_string_addresses(source, (0, 55, 68, 334))
        for item_id, source_va in addresses.items():
            with self.subTest(item_id=item_id):
                probe = NativeTextPipeline(source, runtime_ee=runtime_ee, lower_ranges=lower_ranges)
                font = RUNTIME_FONT_16X18
                handle = 0x1600000
                probe.uc.mem_write(handle + 0x3C, struct.pack("<I", font))
                probe.uc.mem_write(font + 4, bytes(8))
                probe.uc.mem_write(font + 0x14, struct.pack('<ff', 26., 19.))
                descriptor = struct.unpack(
                    "<I", probe.uc.mem_read(font + 0x10, 4)
                )[0]
                self.assertEqual(descriptor, 0x5D77D0)
                self.assertEqual(bytes(probe.uc.mem_read(descriptor + 4, 2)),
                                 bytes((16, 18)))

                def memcpy(engine):
                    dest, src, length = (engine.reg_read(register) & 0xFFFFFFFF
                                         for register in (reg.UC_MIPS_REG_A0,
                                                          reg.UC_MIPS_REG_A1,
                                                          reg.UC_MIPS_REG_A2))
                    engine.mem_write(dest, bytes(engine.mem_read(src, length)))
                    engine.reg_write(reg.UC_MIPS_REG_V0, dest)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                def strlen(engine):
                    source = engine.reg_read(reg.UC_MIPS_REG_A0) & 0xFFFFFFFF
                    length = 0
                    while length < 0x1000 and engine.mem_read(source + length, 1)[0]:
                        length += 1
                    if length == 0x1000:
                        raise AssertionError("native strlen exceeded its diagnostic guard")
                    engine.reg_write(reg.UC_MIPS_REG_V0, length)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                converted = probe.execute(
                    CONVERTER, args=(0, OUTPUT, source_va),
                    external={MEMCPY: memcpy, 0x39F820: strlen},
                )
                units = decode_native_units(probe.uc, OUTPUT)
                controls = [unit for unit in units if unit >= 0xFF00]
                self.assertNotIn(0xFF10, controls)

                allocations = []
                next_node = [0x1F20000]

                def allocate_node(engine):
                    size = engine.reg_read(reg.UC_MIPS_REG_A0) & 0xFFFFFFFF
                    if size != 0x130:
                        raise AssertionError(f"unexpected native node allocation size {size:#x}")
                    node = next_node[0]
                    next_node[0] += size
                    allocations.append(node)
                    engine.mem_write(node, bytes(size))
                    engine.reg_write(reg.UC_MIPS_REG_V0, node)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                def acquire_resource(engine):
                    # The node builder ignores this resource method's return
                    # except as the atlas-data owner; preserve the real object.
                    resource = engine.reg_read(reg.UC_MIPS_REG_A0) & 0xFFFFFFFF
                    engine.reg_write(reg.UC_MIPS_REG_V0, resource)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                def release_resource(engine):
                    engine.reg_write(reg.UC_MIPS_REG_V0, 0)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                node_result = probe.execute(
                    NODE_BUILDER, args=(handle, OUTPUT),
                    external={NATIVE_NODE_ALLOC: allocate_node,
                              NATIVE_RESOURCE_ACQUIRE: acquire_resource,
                              NATIVE_RESOURCE_RELEASE: release_resource},
                )
                self.assertTrue(node_result.returned, node_result.tail)
                self.assertTrue(allocations)

                nodes = []
                cursor = struct.unpack(
                    "<I", probe.uc.mem_read(font + 4, 4)
                )[0]
                seen = set()
                while cursor and cursor not in seen and len(nodes) < 512:
                    seen.add(cursor)
                    control = struct.unpack("<I", probe.uc.mem_read(cursor, 4))[0]
                    nodes.append((cursor, control))
                    cursor = struct.unpack(
                        "<I", probe.uc.mem_read(nodes[-1][0] + 0x120, 4)
                    )[0]
                    if control == 0xFFFFFF0F:
                        break
                self.assertTrue(nodes)
                self.assertEqual(nodes[-1][1], 0xFFFFFF0F)
                actual_controls = [word for _address, word in nodes
                                   if word >= 0xFFFFFF00]
                self.assertEqual(actual_controls,
                                 [0xFFFFFF00 | unit for unit in controls])

                hook_word = struct.unpack_from("<I", source, 0x1520C)[0]
                details_helper = (hook_word & 0x03FFFFFF) << 2

                def return_existing_handle(engine):
                    # The node chain above is already built. Isolate the fitter
                    # from constructor/lifecycle work while preserving that chain.
                    if use_k:
                        engine.mem_write(font + 0x48, struct.pack('<ff', .5, .5))
                        engine.mem_write(font + 0x28, bytes(8))
                    engine.reg_write(reg.UC_MIPS_REG_V0, handle)
                    engine.reg_write(reg.UC_MIPS_REG_PC,
                                     engine.reg_read(reg.UC_MIPS_REG_RA))

                def render_context(engine):
                    context = 0x1100000
                    engine.mem_write(context + 0x80, struct.pack('<f', 1.))
                    engine.reg_write(reg.UC_MIPS_REG_V0, context)
                    engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

                helper_result = probe.execute(
                    details_helper, args=(handle,),
                    external={0x975A78: return_existing_handle, 0x1A0190: render_context},
                    watch_addresses=(0x18B120,),
                )
                self.assertTrue(helper_result.returned, helper_result.tail)
                scale = struct.unpack("<ff", probe.uc.mem_read(font + 0x48, 8))
                self.assertEqual(len(helper_result.watched), 0 if use_k else 1)
                self.assertGreater(scale[0], 0.)
                self.assertLessEqual(scale[0], .5)
                def bounds():
                    points = [struct.unpack('<ff', probe.uc.mem_read(address + offset, 8))
                              for address, control in nodes if control < 0xFFFFFF00
                              for offset in (0x10, 0x50, 0x90, 0xD0)]
                    return (min(x for x, _ in points), min(y for _, y in points),
                            max(x for x, _ in points), max(y for _, y in points))

                if use_k:
                    self.assertEqual(struct.unpack('<I', probe.uc.mem_read(handle + 0x34, 4))[0],
                                     report['details_draw_va'])
                    rebuilt = probe.execute(GLYPH_BUILDER, args=(font,),
                                            external={0x1A0190: render_context})
                    self.assertTrue(rebuilt.returned)
                    self.assertGreater(bounds()[2], 224.)  # mutation: omitting final wrap fails
                    wrapped = probe.execute(report['details_draw_va'], args=(handle,),
                                            stop_at=(0x188420,), instruction_limit=1000000)
                    self.assertTrue(wrapped.returned)
                fitted = bounds()
                self.assertGreaterEqual(fitted[0], 26. - .001)
                self.assertLessEqual(fitted[2], 224. + .001)
                self.assertGreaterEqual(fitted[1], 19. - .001)
                self.assertLessEqual(fitted[3], 79. + .001)

                # A real subsequent opacity update rebuilds every quad.
                probe.uc.reg_write(reg.UC_MIPS_REG_F12, 0x3F800000)
                opacity = probe.execute(0x18AD30, args=(handle,),
                                        external={0x1A0190: render_context})
                self.assertTrue(opacity.returned)
                if use_k:
                    self.assertNotEqual(bounds(), fitted)
                else:
                    self.assertEqual(bounds(), fitted)

                # Capture the actual native draw callback's submitted vertices.
                state_stub, draw_stub = 0x1F01000, 0x1F01010
                probe.uc.mem_write(0x8DE240, struct.pack('<I', state_stub))
                probe.uc.mem_write(0x8DE250, struct.pack('<I', draw_stub))
                submitted = []

                def draw_noop(engine):
                    engine.reg_write(reg.UC_MIPS_REG_V0, 0)
                    engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))

                def draw_vertices(engine):
                    pointer = engine.reg_read(reg.UC_MIPS_REG_A1) & 0xFFFFFFFF
                    self.assertEqual(engine.reg_read(reg.UC_MIPS_REG_A0), 4)
                    submitted.extend(struct.unpack('<ff', engine.mem_read(pointer + offset, 8))
                                     for offset in (0, 0x40, 0x80, 0xC0))
                    draw_noop(engine)

                drawn = probe.execute(report['details_draw_va'] if use_k else 0x188420,
                                      args=(handle,), instruction_limit=1000000,
                                      external={state_stub: draw_noop, draw_stub: draw_vertices})
                self.assertTrue(drawn.returned)
                self.assertEqual(len(submitted), sum(code < 0xFFFFFF00 for _, code in nodes) * 4)
                self.assertLessEqual(max(x for x, _ in submitted), 224. + .001)
                self.assertLessEqual(max(y for _, y in submitted), 79. + .001)
                if use_k:
                    self.assertEqual(bounds(), fitted)

    def test_helper_whitelist_rejects_unrecognized_control_only(self):
        # Synthetic characterization of the whitelist boundary only. This
        # does not model native conversion or assert a runtime failure cause.
        from tests.test_r67_15j_item_layout import SOURCE as baseline, execute as execute_fitter
        from tools import r67_15j_item_layout as layout

        patched, _report = layout.build(baseline.read_bytes())
        words, scale, _pitch, setter_calls = execute_fitter(
            patched, [0x1160000, 0xFFFFFF10, 0x1160000, 0xFFFFFF0F]
        )
        self.assertEqual(words, [0x1160000, 0xFFFFFF10, 0x1160000, 0xFFFFFF0F])
        self.assertEqual(scale, (1.0, 1.0))
        self.assertEqual(setter_calls, [])


if __name__ == "__main__":
    unittest.main()
