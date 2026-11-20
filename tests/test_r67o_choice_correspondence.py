from __future__ import annotations

from hashlib import sha256
import json
import struct
import unittest

from tools.r67o_choice_correspondence import project_record, verify_file_inputs


def ksf_record(labels, *, effect=0, target=1):
    body = bytearray(0x90C)
    body[0] = 2
    body[0x40] = effect
    for slot in range(4):
        struct.pack_into("<H", body, 6 + slot * 2, target)
    return bytes(body) + b"".join(b"\1" + label.ljust(30, b"\0") for label in labels) + bytes(4 - len(labels))


def fixture(*, target4=1, labels4=None, mtx_data=b"Z1_\0", alias4=0, effect4=7):
    labels = tuple(s.encode("cp932") for s in ("はい", "いいえ"))
    if labels4 is None:
        labels4 = labels
    first2 = ksf_record(labels)
    initial_count = b"\2\0"
    chapter1 = ksf_record((labels[1],))
    ps2 = initial_count + first2 + chapter1
    ps4 = initial_count + ksf_record(labels4, target=target4, effect=effect4) + chapter1
    mtx2 = struct.pack("<4H", 2, 3, 0, 0) + b"Z1_\0Z2_\0"
    mtx4 = struct.pack("<4H", 2, 3, alias4, 0) + mtx_data + b"Z2_\0"
    keys = (2 + 0x90C + 1, 2 + 0x90C + 32)
    return ps2, ps4, ps2, mtx2, mtx4, keys


class ProjectionTests(unittest.TestCase):
    def test_type_two_projection_keeps_port_specific_effect_bytes(self):
        ps2, ps4, installed, mtx2, mtx4, keys = fixture()
        result = project_record("MS/MS01_00.KSF", 0, ps2, ps4, installed, mtx2, mtx4, keys)
        self.assertEqual(0, result["ordinal"])
        self.assertEqual("01010000", result["flags_hex"])
        self.assertEqual([1, 1], result["branch_target_ordinals"])
        self.assertEqual([[0x40, 0x41]], result["record_difference_ranges"])
        self.assertEqual([8, 12], result["mtx_region"]["ps2_span"])
        self.assertEqual([8, 12], result["mtx_region"]["ps4_span"])
        self.assertEqual([0], result["mtx_region"]["pointer_slots"])
        self.assertEqual(sha256(installed[2:2382]).hexdigest(), result["installed_record_sha256"])
        self.assertEqual([keys[0], keys[1]], [row["ps2_offset"] for row in result["rows"]])
        self.assertEqual(ps2[keys[1]:keys[1] + 30].hex(), result["rows"][1]["old_payload_hex"])

    def test_changed_branch_destination_is_not_projected(self):
        with self.assertRaisesRegex(ValueError, "choice and branch header differs"):
            project_record("MS/MS01_00.KSF", 0, *fixture(target4=0))

    def test_changed_conditional_branch_link_is_not_treated_as_effect_drift(self):
        ps2, ps4, installed, mtx2, mtx4, keys = fixture()
        changed = bytearray(ps4)
        struct.pack_into("<H", changed, 2 + 0x26 + 0x1C, 1)
        with self.assertRaisesRegex(ValueError, "conditional branch link differs"):
            project_record("MS/MS01_00.KSF", 0, ps2, bytes(changed), installed, mtx2, mtx4, keys)

    def test_changed_active_slot_mask_is_not_projected(self):
        with self.assertRaisesRegex(ValueError, "choice flag bytes differ"):
            project_record("MS/MS01_00.KSF", 0, *fixture(labels4=(b"a",)))

    def test_native_reader_preserves_non_one_inactive_packed_flag(self):
        ps2, ps4, _, mtx2, mtx4, keys = fixture()
        tail = 2 + 0x90C + 4 + 2 * 30 - 1
        old = ps2[:tail] + b"\x8c" + ps2[tail + 1:]
        port = ps4[:tail] + b"\x8c" + ps4[tail + 1:]
        result = project_record("MS/MS01_00.KSF", 0, old, port, old, mtx2, mtx4, keys)
        self.assertEqual("0101008c", result["flags_hex"])
        self.assertEqual(2, len(result["rows"]))
        with self.assertRaisesRegex(ValueError, "choice flag bytes differ"):
            project_record("MS/MS01_00.KSF", 0, old, ps4, old, mtx2, mtx4, keys)

    def test_missing_official_sibling_prevents_projecting_the_entire_record(self):
        args = fixture()
        with self.assertRaisesRegex(ValueError, "do not cover every active sibling"):
            project_record("MS/MS01_00.KSF", 0, *args[:-1], args[-1][:1])

    def test_changed_japanese_sibling_is_not_projected(self):
        with self.assertRaisesRegex(ValueError, "Japanese payload differs"):
            project_record("MS/MS01_00.KSF", 0, *fixture(labels4=tuple(s.encode("cp932") for s in ("はい", "後で"))))

    def test_orthographic_exception_is_bound_to_actual_source_file_hashes(self):
        labels4 = tuple(s.encode("cp932") for s in ("皮ジャン", "いいえ"))
        first = ksf_record(tuple(s.encode("cp932") for s in ("革ジャン", "いいえ")), target=166)
        prior = ksf_record((b"A",))
        ps2 = struct.pack("<H", 167) + prior * 166 + first
        ps4 = struct.pack("<H", 167) + prior * 166 + ksf_record(labels4, target=166, effect=7)
        mtx = struct.pack("<334H", 167, *(0 for _ in range(165)), 167, *(0 for _ in range(167))) + b"Z1_\0"
        start = 2 + len(prior) * 166
        keys = (start + 0x90C + 1, start + 0x90C + 32)
        with self.assertRaisesRegex(ValueError, "Japanese payload differs"):
            project_record("MS/MS04_01.KSF", 166, ps2, ps4, ps2, mtx, mtx, keys)

    def test_full_mtx_region_must_match_at_selected_ordinal(self):
        with self.assertRaisesRegex(ValueError, "entire MTX pointer region differs"):
            project_record("MS/MS01_00.KSF", 0, *fixture(mtx_data=b"D1_\0"))

    def test_pointer_alias_set_must_match_at_same_ordinal(self):
        with self.assertRaisesRegex(ValueError, "MTX pointer slot identity differs"):
            project_record("MS/MS01_00.KSF", 0, *fixture(alias4=2))

    def test_official_key_cannot_move_to_another_record_ordinal(self):
        with self.assertRaisesRegex(ValueError, "do not cover every active sibling"):
            project_record("MS/MS01_00.KSF", 1, *fixture())

    def test_any_installed_record_effect_or_payload_drift_is_rejected(self):
        ps2, ps4, installed, mtx2, mtx4, keys = fixture()
        for offset in (2 + 0x40, keys[1] + 6):
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, "installed record preimage differs"):
                bad = bytearray(installed)
                bad[offset] ^= 1
                project_record("MS/MS01_00.KSF", 0, ps2, ps4, bytes(bad), mtx2, mtx4, keys)

    def test_each_whole_file_and_official_map_hash_is_pinned(self):
        ps2, ps4, installed, _, _, keys = fixture()
        dc = json.dumps({"keys": keys, "values": ["Yes", "No"]}).encode()
        inputs = dict(pristine=ps2, remaster=ps4, dc_raw=dc, installed=installed)
        hashes = {field: sha256(inputs[name]).hexdigest()
                  for name, field in (("pristine", "ps2_sha256"), ("remaster", "ps4_sha256"),
                                      ("dc_raw", "map_sha256"), ("installed", "after_sha256"))}
        verify_file_inputs("MS/MS01_00.KSF", **inputs, historical=hashes)
        for name, data in inputs.items():
            bad = {**inputs, name: data + b" "}
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "SHA-256 drift"):
                verify_file_inputs("MS/MS01_00.KSF", **bad, historical=hashes)


if __name__ == "__main__":
    unittest.main()
