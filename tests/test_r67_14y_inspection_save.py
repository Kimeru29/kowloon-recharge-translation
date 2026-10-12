"""Text ownership, containment and fail-closed mutation tests; no emulator writes."""
from pathlib import Path
import importlib.util
import json
import struct
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-14t-lion-and-tablets.elf"


class InspectionSaveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.available = importlib.util.find_spec("tools.r67_14y_inspection_save") is not None
        if cls.available:
            from tools import r67_14y_inspection_save
            cls.mod = r67_14y_inspection_save

    def setUp(self):
        self.assertTrue(self.available, "bounded inspection/save transform is not implemented")

    def test_full_width_cell_and_row_bounds(self):
        self.mod.validate_lines(("A" * 21,), max_cells=21, max_rows=1)
        for lines in [("A" * 22,), ("A", "B"), ("a\nb",), ("＠改行",), ("\x00",), ("日本語",)]:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                self.mod.validate_lines(lines, max_cells=21, max_rows=1)

    def test_encoded_controls_count_as_rows_not_printable_cells(self):
        from tools.memory_card_ui import encode_memory_card_english
        blob = encode_memory_card_english("\nSaving...\nDo not remove/insert\nmemory card (PS2) or\nturn off the power.")
        self.assertEqual(self.mod.validate_encoded(blob, max_cells=21, max_rows=5), [0, 9, 20, 20, 19])
        for bad in [blob + "＠改行".encode("cp932"), b"A", b"\x81", b"\0", "日本語".encode("cp932")]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.mod.validate_encoded(bad, max_cells=21, max_rows=5)

    def real_source(self):
        if not SOURCE.exists():
            self.skipTest("requires ignored r67.14t ELF")
        return SOURCE.read_bytes()

    def test_all_records_are_english_and_bounded_after_apply(self):
        result, report = self.mod.apply(self.real_source())
        checked = self.mod.validate_result(result)
        self.assertEqual(checked["object_records"], 11)
        self.assertEqual(checked["save_warning_row_cells"], [0, 9, 20, 20, 19])
        self.assertFalse(report["runtime_verified"])
        self.assertEqual(self.mod.read_owner(result, 0x590FFC), "Ｃａｎ　ｂｅ　ｕｓｅｄ．".encode("cp932"))
        self.assertEqual(self.mod.read_owner(result, 0x58FD74), b"")
        self.assertEqual(self.mod.read_owner(result, 0x338A80), "Ｙｅｓ".encode("cp932"))

    def test_different_snake_states_and_wire_requirement_survive(self):
        result, _ = self.mod.apply(self.real_source())
        for owner, english in [(0x58A2C8, "Moving part found."), (0x5910D8, "Moving part fixed."),
                               (0x591EC8, "Connector damaged."), (0x591ECC, "Repair with Wire.")]:
            from tools.localization import encode_ps2_english
            self.assertEqual(self.mod.read_owner(result, owner), encode_ps2_english(english))

    def test_changed_bytes_are_only_registered_pointers_and_filesz(self):
        source = self.real_source()
        result, report = self.mod.apply(source)
        allowed = {i for start, end in report["allowed_source_ranges"] for i in range(start, end)}
        actual = [i for i, (a, b) in enumerate(zip(source, result)) if a != b]
        self.assertEqual(actual, report["changed_source_offsets"])
        self.assertTrue(actual)
        self.assertFalse(set(actual) - allowed)
        self.assertEqual(source[0x80:0x300000], result[0x80:0x300000])
        self.assertEqual(source[0x407130:0x407160], result[0x407130:0x407160])
        for marker in (b"SLPM-66511", b"BISLPM-66511Save"):
            self.assertEqual(source.count(marker), result.count(marker))
        self.assertLess(report["appended_bytes"], 4096)

    def test_accepts_dialogue_patched_source_and_preserves_unknown_bytes(self):
        source = bytearray(self.real_source())
        source[0x200000:0x200008] = b"EVENT-Y!"
        source.extend(b"APPENDED-Y-HELPER" * 3)
        struct.pack_into("<I", source, 0x64, len(source) - 0x803150)
        result, _ = self.mod.apply(bytes(source))
        self.assertEqual(result[0x200000:0x200008], b"EVENT-Y!")
        tail = b"APPENDED-Y-HELPER" * 3
        self.assertEqual(result[len(source)-len(tail):len(source)], tail)

    def test_x_is_also_supported(self):
        path = ROOT / "local/r67-14x-generic-event-bubble.elf"
        if not path.exists():
            self.skipTest("requires ignored x ELF")
        result, _ = self.mod.apply(path.read_bytes())
        self.assertEqual(self.mod.validate_result(result)["object_records"], 11)

    def test_preimages_fail_closed_for_pointer_string_context_and_header(self):
        source = self.real_source()
        for off in [0x58A124, 0x594F84, 0x407460, 0x338A80, 0x2DC, 0x64, 0x58]:
            mutated = bytearray(source)
            mutated[off] ^= 1
            with self.subTest(off=hex(off)), self.assertRaises(ValueError):
                self.mod.apply(bytes(mutated))
        mutated = bytearray(source)
        ptr = struct.unpack_from("<I", source, 0x58A124)[0]
        mutated[0x803150 + ptr - 0x902F00] ^= 1
        with self.assertRaises(ValueError):
            self.mod.apply(bytes(mutated))

    def test_rejects_unterminated_or_out_of_segment_strings(self):
        source = self.real_source()
        for ptr in [0, 0x902F00 + len(source), 0x100]:
            mutant = bytearray(source)
            struct.pack_into("<I", mutant, 0x58A120, ptr)
            with self.assertRaises(ValueError):
                self.mod.read_owner(bytes(mutant), 0x58A120)

    def test_rejects_exhausted_reservation_and_repeat_apply(self):
        source = self.real_source()
        result, _ = self.mod.apply(source)
        with self.assertRaises(ValueError):
            self.mod.apply(result)
        full = source.ljust(0x803150 + 0x100000, b"\0")
        full = bytearray(full)
        struct.pack_into("<I", full, 0x64, 0x100000)
        with self.assertRaisesRegex(ValueError, "reservation"):
            self.mod.apply(bytes(full))

    def test_future_oversized_output_is_rejected_before_write(self):
        with patch.dict(self.mod.REPLACEMENTS, {"anubis_description": "A" * 22}):
            with self.assertRaisesRegex(ValueError, "cells"):
                self.mod.apply(self.real_source())

    def test_validator_rejects_japanese_overwide_and_sixth_warning_row(self):
        from tools.memory_card_ui import encode_memory_card_english
        result, _ = self.mod.apply(self.real_source())
        for owner, payload in [(0x58A124, "Ａ".encode("cp932") * 22),
                               (0x5910D8, "固定".encode("cp932")),
                               (0x407460, encode_memory_card_english("\nSaving...\na\nb\nc\nd"))]:
            mutated = bytearray(result)
            struct.pack_into("<I", mutated, owner, 0x902F00 + len(mutated) - 0x803150)
            mutated.extend(payload + b"\0")
            struct.pack_into("<I", mutated, 0x64, len(mutated) - 0x803150)
            with self.subTest(owner=hex(owner)), self.assertRaises(ValueError):
                self.mod.validate_result(bytes(mutated))

    def test_q_t_approved_owners_pass(self):
        from tools.r67_14t_approved_ui_lock import verify_ui, MANIFEST
        result, _ = self.mod.apply(self.real_source())
        self.assertEqual(verify_ui(result, json.loads(MANIFEST.read_text()))["overwide_rows"], 0)

    def test_official_provenance_matches_owned_corpus(self):
        from tools.inspect_english_bytes import parse
        path = Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
        if not path.exists():
            self.skipTest("requires owned PS4 English corpus")
        import hashlib
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), self.mod.CORPUS_SHA256)
        rows = {off: (jp, en) for jp, en, off in parse(path)}
        for spec in self.mod.FIELDS:
            if spec.official_offset is not None:
                self.assertEqual(rows[spec.official_offset], (spec.japanese, spec.official_english), spec.key)


if __name__ == "__main__":
    unittest.main()
