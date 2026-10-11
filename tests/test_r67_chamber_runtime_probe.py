"""Fail-closed regression for the read-only Chamber scene evidence collector."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.r67_chamber_runtime_probe import (
    StateMemory, LiveMemory, snapshot, describe_text, TASK_ADDRESS,
    SOURCE_PTR_RECORDS, KNOWN_OFFICIAL_PTRS, NODE_LIMIT, EE_SIZE, identify_revision,
)

ROOT = Path(__file__).resolve().parents[1]
SLOT3 = ROOT / "local/pcsx2-67.06-isolated/slot3-chamber-oldman-20261010.p2s"

class R67ReadOnlyProbe(unittest.TestCase):
    def test_pine_operation_is_read_only_and_address_checked(self):
        self.assertEqual(LiveMemory.READ32, 2)
        reader = LiveMemory(Path("/nonexistent-test-only-pcsx2.sock"))
        for invalid in (-4, EE_SIZE, EE_SIZE-3, 0x1_0000_0000):
            with self.subTest(address=invalid):
                with self.assertRaises(ValueError):
                    reader.read32(invalid)
        with self.assertRaises(ValueError):
            StateMemory.__new__(StateMemory).read32(-1)

    @unittest.skipUnless(SLOT3.exists(), "original copied slot-3 unavailable")
    def test_known_slot3_read_only_fixture_and_glyph_coordinates(self):
        memory = StateMemory(SLOT3)
        result = snapshot(memory, TASK_ADDRESS)
        self.assertEqual(tuple(int(v, 16) for v in result["source_pointers"]),
                         KNOWN_OFFICIAL_PTRS)
        self.assertEqual(len(SOURCE_PTR_RECORDS), 3)
        self.assertTrue(result["official_source_ptrs_match"])
        self.assertEqual(result["comment_index"], 2)
        self.assertEqual(result["comment_line"], 2)
        self.assertEqual(result["callsite_words"]["0x1661bc"], "0xc062790")
        self.assertEqual(result["callsite_words"]["0x16628c"], "0xc062790")
        self.assertEqual(result["callsite_words"]["0x18e004"], "0xc6810048")
        active = result["text_owners"][0]
        self.assertEqual(active["owner"], "0x14e80c0")
        self.assertEqual(active["font"], "0x14e7dc0")
        self.assertEqual(active["font_origin_x"], 117.0)
        self.assertEqual(active["font_origin_y"], 313.0)
        self.assertEqual(active["font_scale_x"], 1.0)
        self.assertEqual(active["font_scale_y"], 1.0)
        self.assertEqual(active["orientation_low_byte"], 0)
        self.assertEqual([node["x"] for node in active["nodes"][:3]],
                         [117.0, 133.0, 149.0])
        self.assertEqual([node["y"] for node in active["nodes"][:3]],
                         [313.0, 313.0, 313.0])
        self.assertLessEqual(len(active["nodes"]), NODE_LIMIT)
        self.assertEqual(result["text_owners"][1]["error"],
                         "owner pointer absent/out of EE range")

    def test_build_signature_does_not_conflate_14h_with_14g(self):
        signatures = {
            "0x18e004": "0xc258f30",
            "0x189ed8": "0xc062250",
        }
        self.assertIn("r67.14h", identify_revision(signatures))
        self.assertIn("NOT r67.14g", identify_revision(signatures))
        signatures["0x18e004"] = "0xc6810048"
        signatures["0x189ed8"] = "0xc258f30"
        self.assertIn("pre-layout", identify_revision(signatures))
        signatures["0x189ed8"] = "0xc062250"
        self.assertIn("no hook", identify_revision(signatures))

    @unittest.skipUnless((ROOT / "local/r67-14h-20261011-live-bubble-slot1-copy.p2s").exists(),
                         "new user-provided slot-1 archive unavailable")
    def test_new_saved_slot1_carries_14h_instructions_and_unmodified_glyph_positions(self):
        reader = StateMemory(ROOT / "local/r67-14h-20261011-live-bubble-slot1-copy.p2s")
        record = snapshot(reader)
        self.assertIn("r67.14h", record["instruction_fingerprint"])
        self.assertEqual(record["comment_index"], 2)
        self.assertEqual(record["source_pointers"], [hex(v) for v in KNOWN_OFFICIAL_PTRS])
        self.assertTrue(record["official_source_ptrs_match"])
        target = record["text_owners"][0]
        self.assertEqual(target["font_origin_y"], 313.0)
        self.assertEqual(target["font_scale_x"], 1.0)
        self.assertEqual(target["font_scale_y"], 1.0)
        self.assertEqual([(n["x"], n["y"]) for n in target["nodes"][:3]],
                         [(117.0, 313.0), (133.0, 313.0), (149.0, 313.0)])

    @unittest.skipUnless(SLOT3.exists(), "original copied slot-3 unavailable")
    def test_task_address_is_not_assumed_globally_valid(self):
        memory = StateMemory(SLOT3)
        result = snapshot(memory, 0)
        self.assertIn("task_warning", result)
        self.assertIsNone(result["comment_index"])
        self.assertIsNone(result["comment_line"])

if __name__ == "__main__":
    unittest.main()
