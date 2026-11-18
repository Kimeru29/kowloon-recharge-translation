"""Executable invariants for the r67.15l native coverage contract."""
from __future__ import annotations

import math
import hashlib
import importlib.util
from pathlib import Path
import unittest

from tools.r67_15l_native_coverage import (
    APPROVED_ELF_SHA256, APPROVED_ISO_SHA256, GROUP1_CONTAINER_SHA256,
    _adv_creation_route, _direct_calls, _native_selection_crosswalk,
    _scenario_event_slot_initialization, _wheel_position_coordinates,
    _wheel_variant_routing, verify,
)

ROOT = Path(__file__).resolve().parents[1]
ELF = ROOT / "local/r67-15k-description-word-wrap.elf"
ISO = ROOT / "local/r67-candidates/67.15k-description-word-wrap.iso"


@unittest.skipUnless(ELF.is_file(), "requires the local approved r67.15k executable")
class R6715LNativeCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf = ELF.read_bytes()
        cls.proof = verify(cls.elf)

    def test_fail_closed_to_approved_elf_and_resource_lookup_preimage(self):
        self.assertEqual(self.proof["elf_sha256"], APPROVED_ELF_SHA256)
        changed = bytearray(self.elf)
        changed[0x4391F0 - 0xFFF80] ^= 1
        with self.assertRaisesRegex(ValueError, "requires approved r67.15k ELF"):
            verify(bytes(changed))

    def test_constructor_mapper_and_outcome_direct_call_census(self):
        census = self.proof["direct_call_census"]
        self.assertEqual(census["kanjo_input_ctor"]["callsite_vas"],
                         ["0x2580a8", "0x258120"])
        self.assertEqual(census["kanjo_sub_ctor"]["callsite_vas"], ["0x153b54"])
        self.assertEqual(census["adv_emotion_task_ctor"]["callsite_vas"], ["0x25a58c"])
        self.assertEqual(census["wheel_selection_mapper"]["callsite_vas"], ["0x258144"])
        self.assertIn("0x2581d8", census["adv_emotion_outcome"]["callsite_vas"])

    def test_default_selection_slots_and_sprite_initialization_are_pinned(self):
        selection = self.proof["selection"]
        self.assertEqual(selection["default_slot_values"], [8, 1, 2, 3, 7, 5, 6, 4])
        self.assertEqual([row["selection_id"] for row in selection["position_to_native_selection_id"]],
                         [8, 1, 2, 3, 7, 5, 6, 4])
        self.assertEqual([row["mapper_command"] for row in selection["position_to_native_selection_id"]],
                         [f"0x{i * 0x100:x}" for i in range(1, 9)])
        self.assertEqual(selection["mapper_target_va"], "0x154880")
        self.assertEqual([row["mode"] for row in selection["mode_to_command"]], list(range(1, 9)))
        self.assertEqual([row["command"] for row in selection["mode_to_command"]],
                         [f"0x{i * 0x100:x}" for i in range(1, 9)])
        self.assertEqual(selection["jump_table_va"], "0x77c260")
        self.assertEqual(len(selection["jump_table_sha256"]), 64)
        self.assertEqual(selection["jump_table_words"], [
            "0x154940", "0x1548c0", "0x1548d0", "0x1548e0", "0x1548f0",
            "0x154900", "0x154910", "0x154920", "0x154930",
        ])
        self.assertEqual(selection["fallback_modes"], [0, 9, -1])
        self.assertIn("resolved for ordinary/default mode", selection["official_label_crosswalk"])
        self.assertEqual(selection["sprite_initialization_sequence"],
                         [21, 22, 23, 24, 29, 26, 28, 29, 30, 27, 25, 39, 31, 32, 33, 34, 42])

    def test_adv_emotion_task_state_zero_creator_and_registration_are_pinned(self):
        route = self.proof["adv_task_creation_route"]
        self.assertEqual(route["handler_va"], "0x25a480")
        self.assertEqual(route["handler_direct_jal_callers"], [])
        self.assertEqual(route["state_targets"],
                         ["0x25a4c8", "0x25a6b0", "0x25a6d4", "0x25a8e0", "0x25a8e8", "0x25a8e8"])
        self.assertEqual(route["state_zero_task_create_callsite_va"], "0x25a58c")
        self.assertEqual(route["handler_direct_jal_callers"], [])
        self.assertEqual(route["task_registration"]["register_target_va"], "0x1a1190")
        self.assertEqual(route["task_registration"]["callback_va"], "0x258040")
        self.assertEqual(route["task_registration"]["destructor_va"], "0x2586d0")
        self.assertEqual(route["task_registration"]["name"], "adv emotion task")
        self.assertIn("unresolved", route["script_opcode_origin"])

    def test_scenario_constructor_split_pointer_registrations_and_direct_callers(self):
        route = self.proof["adv_task_creation_route"]
        self.assertEqual(route["scenario_constructor_direct_callers"], [
            "0x15bea4", "0x15bec8", "0x15bf1c", "0x15bf40", "0x15bf94",
            "0x15bfb8", "0x15c024", "0x15c044", "0x16fc3c", "0x16fc74",
            "0x16fcac", "0x16fce4", "0x16fd38", "0x16fd68", "0x2483e4",
        ])
        registrations = route["scenario_constructor_registrations"]
        self.assertEqual([entry["role"] for entry in registrations],
                         ["adv scenario proc", "adv scenario draw"])
        self.assertEqual([entry["callback_split_pointer"]["lui_va"] for entry in registrations],
                         ["0x25a9ac", "0x25aa3c"])
        self.assertEqual([entry["callback_split_pointer"]["addiu_va"] for entry in registrations],
                         ["0x25a9b0", "0x25aa40"])
        self.assertEqual([entry["callback_split_pointer"]["resolved_va"] for entry in registrations],
                         ["0x25a340", "0x25a480"])
        self.assertEqual([entry["name_pointer_split"]["resolved_va"] for entry in registrations],
                         ["0x678780", "0x6787a0"])
        self.assertEqual([entry["destructor_split_pointer"]["resolved_va"] for entry in registrations],
                         ["0x25a450", "0x25a910"])
        self.assertEqual([entry["register_callsite_va"] for entry in registrations],
                         ["0x25a9c0", "0x25aa50"])
        self.assertEqual([entry["register_target_va"] for entry in registrations],
                         ["0x1a1190", "0x1a1190"])
        self.assertEqual([entry["name"] for entry in registrations],
                         ["adv scenario proc", "adv scenario draw"])
        self.assertEqual(route["scenario_source"],
                         {"name_va": "0x678770", "name": "y_AdvMain.c"})
        self.assertIn("0x25a480 state zero calls task constructor 0x258700",
                      route["scenario_registration_chain"])
        self.assertIn("the state handler address", route["callback_address_note"])

    def test_scenario_callback_split_immediates_are_individually_validated(self):
        calls = _direct_calls(self.elf)
        for address in (0x25A9AC, 0x25A9B0, 0x25AA3C, 0x25AA40):
            with self.subTest(address=hex(address)):
                changed = bytearray(self.elf)
                offset = address - 0xFFF80
                changed[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "split-pointer registration tuple"):
                    _adv_creation_route(bytes(changed), calls)

    def test_result_highwords_resolve_sprite_ids_glow_uvs_and_default_event_slots(self):
        crosswalk = self.proof["selection_label_crosswalk"]
        rows = crosswalk["result_slots"]
        self.assertEqual([row["result_highword"] for row in rows],
                         [f"0x{i * 0x100:x}" for i in range(1, 9)])
        self.assertEqual([row["sprite_id"] for row in rows],
                         [88, 89, 94, 95, 92, 93, 90, 91])
        self.assertEqual([row["label"] for row in rows],
                         ["JOY", "LOVE", "SOMBER", "GRIEF", "COLD", "ANGER", "AMITY", "HOT"])
        self.assertEqual([row["default_event_slot_value"] for row in rows],
                         [8, 1, 2, 3, 7, 5, 6, 4])
        self.assertEqual([row["wheel_position_xy"] for row in rows], [
            [257, 311], [257, 281], [227, 341], [197, 341],
            [257, 371], [257, 401], [287, 341], [317, 341],
        ])
        self.assertEqual([row["descriptor_frame_count"] for row in rows], [41] * 8)
        self.assertEqual([row["descriptor_texture_index"] for row in rows], [8] * 8)
        self.assertEqual([row["uv_pixels"] for row in rows], [
            [0, 0, 64, 64], [64, 0, 128, 64], [128, 64, 192, 128],
            [192, 64, 256, 128], [0, 64, 64, 128], [64, 64, 128, 128],
            [128, 0, 192, 64], [192, 0, 256, 64],
        ])

    def test_event_result_branches_load_the_expected_slot_and_store_result(self):
        routes = self.proof["selection_label_crosswalk"]["event_result_routes"]
        self.assertEqual([row["branch_va"] for row in routes], [
            "0x2581e8", "0x258250", "0x258400", "0x258438",
            "0x258470", "0x2584a8", "0x2584e0", "0x258518",
        ])
        self.assertEqual([int(row["event_slot_offset"], 16) for row in routes],
                         list(range(0x0A, 0x12)))
        self.assertEqual([row["result_field_offset"] for row in routes], ["+0x327e"] * 8)
        self.assertEqual(self.proof["scenario_slot_initialization"]["mode_zero_default_event_slot_values"],
                         [8, 1, 2, 3, 7, 5, 6, 4])
        self.assertTrue(self.proof["scenario_slot_initialization"][
            "nonzero_mode_preserves_caller_event_slots"])
        self.assertEqual(self.proof["selection_label_crosswalk"]["scope"],
                         "ordinary/default mode; forced scenario modes preserve caller-owned event slots")

    def test_input_masks_and_strength_threshold_are_pinned_without_direction_names(self):
        proof = self.proof["selection_label_crosswalk"]["input_masks"]
        self.assertEqual([row["mask"] for row in proof["mask_comparisons"]],
                         ["0x1000", "0x8000", "0x4000", "0x2000"])
        self.assertEqual(proof["direction_labels"],
                         "unassigned; masks are reported as native bit values")
        self.assertEqual(proof["strength_private_offset"], "+0x96")
        self.assertEqual(proof["threshold_instruction_vas"],
                         ["0x153c04", "0x153cec", "0x153dbc", "0x153ea4"])

    def test_forced_modes_cover_all_paired_resources_and_completion_glows(self):
        routing = self.proof["wheel_variant_routing"]
        self.assertEqual(routing["ordinary_mode_zero"],
                         {"index_bounds": [12, 16], "resource_ids": [31, 32, 33, 34]})
        self.assertEqual(routing["forced_mode_formula"],
                         "0x6d + 4 * (mode - 1) + (init_index - 12)")
        self.assertEqual([row["resource_ids_by_init_index"] for row in routing["forced_modes"]],
                         [list(range(109 + i * 4, 113 + i * 4)) for i in range(8)])
        self.assertEqual([row["resource_id"] for row in routing["completion_glow_resource_ids"]],
                         list(range(88, 96)))
        self.assertEqual(routing["completion_glow_descriptor_labels"],
                         ["JOY", "LOVE", "AMITY", "HOT", "COLD", "ANGER", "SOMBER", "GRIEF"])

    def test_selection_and_variant_instruction_anchors_fail_closed(self):
        calls = _direct_calls(self.elf)
        frames = self.proof["group1"]["resource_records"]
        anchors = (0x153C10, 0x153C14, 0x153C58, 0x153C64,
                   0x2581EC, 0x2581F4, 0x258254, 0x25825C)
        for address in anchors:
            with self.subTest(address=hex(address)):
                changed = bytearray(self.elf)
                changed[address - 0xFFF80] ^= 1
                with self.assertRaises(ValueError):
                    _native_selection_crosswalk(bytes(changed), frames,
                                                [8, 1, 2, 3, 7, 5, 6, 4], calls)

        for address in (0x153334, 0x1533B4, 0x1533D8, 0x153FF0, 0x154014):
            with self.subTest(address=hex(address)):
                changed = bytearray(self.elf)
                changed[address - 0xFFF80] ^= 1
                with self.assertRaises(ValueError):
                    _wheel_variant_routing(bytes(changed), frames)

        for address in (0x153C18, 0x153C2C, 0x153D00, 0x153D08,
                        0x153D5C, 0x153D64, 0x153F20, 0x153F34):
            with self.subTest(position_anchor=hex(address)):
                changed = bytearray(self.elf)
                changed[address - 0xFFF80] ^= 1
                with self.assertRaisesRegex(ValueError, "wheel position coordinate setup changed"):
                    _wheel_position_coordinates(bytes(changed))

        changed = bytearray(self.elf)
        changed[0x258098 - 0xFFF80] ^= 1
        with self.assertRaisesRegex(ValueError, "scenario mode load/branch"):
            _scenario_event_slot_initialization(bytes(changed), [8, 1, 2, 3, 7, 5, 6, 4])

    def test_native_command_branches_bind_all_eight_native_label_keys(self):
        branches = self.proof["task_command_label_branches"]
        self.assertEqual([int(row["command"], 16) for row in branches],
                         [i * 0x100 for i in range(1, 9)])
        self.assertEqual([row["native_label_format"].split(" =", 1)[0] for row in branches],
                         ["YOROKOBI", "AI", "YUU", "HI", "SAMUI", "OKORU", "TOMO", "MOERU"])

    def test_shared_group_lookup_binds_group_one_path_and_all_eleven_resources(self):
        binding = self.proof["resource_binding"]
        self.assertEqual(binding["group1_filename"], "BLBRD/B_GP001.BIN")
        self.assertEqual(binding["disc_inventory"]["absolute_iso_offset"], "0x2ed7a800")
        self.assertEqual(binding["disc_inventory"]["size_bytes"], 603520)
        self.assertEqual(binding["disc_inventory"]["source_iso_sha256"], APPROVED_ISO_SHA256)
        self.assertEqual(binding["disc_inventory"]["source_container_sha256"], GROUP1_CONTAINER_SHA256)
        self.assertEqual(binding["resource_names"],
                         [f"BLBRD/GRP001/GP001_{i:02d}" for i in range(11)])
        self.assertEqual(binding["resource_names_va"], "0x43a2a0")
        self.assertEqual(binding["resource_pointer_array_va"], "0x43a400")
        self.assertEqual(len(binding["resource_names_sha256"]), 64)
        self.assertEqual(len(binding["resource_pointer_array_sha256"]), 64)

    @unittest.skipUnless(ISO.is_file(), "requires the immutable approved r67.15k ISO")
    def test_group1_container_byte_lock_matches_approved_disc_range(self):
        inventory = self.proof["resource_binding"]["disc_inventory"]
        with ISO.open("rb") as source:
            source.seek(int(inventory["absolute_iso_offset"], 16))
            container = source.read(inventory["size_bytes"])
        self.assertEqual(len(container), 603520)
        self.assertEqual(hashlib.sha256(container).hexdigest(), GROUP1_CONTAINER_SHA256)

    def test_every_group_one_resource_frame_has_hash_transform_and_identity(self):
        group = self.proof["group1"]
        self.assertEqual(group["resource_count"], 146)
        self.assertEqual(group["total_frames"], 820)
        self.assertEqual([r["resource_id"] for r in group["resource_records"]], list(range(146)))
        for resource in group["resource_records"]:
            self.assertEqual(resource["frame_count"], len(resource["frames"]))
            for frame in resource["frames"]:
                with self.subTest(resource=resource["resource_id"], frame=frame["index"]):
                    self.assertEqual(len(frame["sha256"]), 64)
                    self.assertTrue(all(math.isfinite(v) for v in (
                        frame["width"], frame["height"], *frame["pivot"], *frame["uv"],
                        frame["angle"], frame["field"], frame["scale"])))
                    self.assertGreaterEqual(frame["width"], 0)
                    self.assertGreaterEqual(frame["height"], 0)
                    self.assertEqual(len(frame["uv"]), 4)

    def test_dynamic_wheel_descriptor_ids_resolve_to_expected_texture_and_crop(self):
        resources = self.proof["group1"]["resource_records"]
        expected = {
            31: (2, [40, 0, 80, 72]),
            32: (2, [0, 0, 40, 72]),
            33: (10, [160, 160, 232, 200]),
            34: (2, [80, 0, 152, 40]),
        }
        for resource_id, (texture, crop) in expected.items():
            frame = resources[resource_id]["frames"][0]
            self.assertEqual(frame["texture_index"], texture)
            atlas_width, atlas_height = (256, 128) if texture == 2 else (256, 256)
            actual_crop = [round(frame["uv"][0] * atlas_width),
                           round(frame["uv"][1] * atlas_height),
                           round(frame["uv"][2] * atlas_width),
                           round(frame["uv"][3] * atlas_height)]
            self.assertEqual(actual_crop, crop)

        self.assertEqual(group_labels(self.proof),
                         {53: "JOY", 54: "LOVE", 55: "AMITY", 56: "HOT",
                          57: "COLD", 58: "ANGER", 59: "SOMBER", 60: "GRIEF"})

    def test_report_does_not_claim_indirect_or_runtime_route_closure(self):
        limits = self.proof["coverage_limits"]
        self.assertIn("not proof of all indirect callers", limits["direct_calls"])
        self.assertIn("Not closed", limits["indirect_event_routes"])
        self.assertIn("Optional bounded Unicorn function execution", limits["execution"])

    @unittest.skipUnless(importlib.util.find_spec("unicorn"), "optional Unicorn execution dependency unavailable")
    def test_bounded_native_mapper_execution_returns_each_encoded_command(self):
        from tools.r67_15l_native_coverage import execute_selection_mapper

        execution = execute_selection_mapper(self.elf)
        self.assertFalse(execution["full_runtime"])
        self.assertEqual(execution["function_va"], "0x154880")
        rows = execution["results"]
        self.assertEqual([row["mode"] for row in rows], list(range(9)) + [9, -1, 3, 3])
        self.assertEqual([row["command"] for row in rows[:9]],
                         [0x3456] + [i * 0x100 for i in range(1, 9)])
        self.assertEqual([row["return_value"] for row in rows], [1] * 11 + [0, 0])
        self.assertEqual([row["command"] for row in rows[9:]], [0x3456, 0x3456, 0xBEEF, 0xBEEF])
        self.assertFalse(any(row["output_unchanged"] for row in rows[9:11]))
        self.assertTrue(all(row["output_unchanged"] for row in rows[11:]))


def group_labels(proof):
    return {int(key): value for key, value in proof["group1"]["single_label_resources"].items()}


if __name__ == "__main__":
    unittest.main()
