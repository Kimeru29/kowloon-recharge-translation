from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
import unittest

from tools.r67o_reviewed import (
    _canonical, _check_digest, _check_inventory_scope, _installed_rows,
    _source_evidence, _variant_text, verify_correspondence,
)


def raw(text: str) -> bytes:
    return text.encode("cp932")


def mtx(body: bytes, slots: tuple[int, ...] = (2, 2, 0, 0)) -> bytes:
    return struct.pack("<4H", *slots) + body


class ReviewedCorrespondenceTests(unittest.TestCase):
    def test_display_tokens_preserve_ruby_base_and_fullwidth_punctuation(self):
        self.assertEqual("海と空、℃", _canonical(raw("l海(うみ)とrl空(ソラ)、℃")))

    def test_unknown_ascii_or_malformed_ruby_cannot_be_normalized(self):
        for text in ("海px空", "海r00空", "海\0空", "海r_空", "海l空(そ1ら)", "海l(そら)", "海(空)"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "unsupported display syntax"):
                _canonical(raw(text))

    def test_approved_variant_must_occur_once(self):
        variant = (("朝昼", "朝と昼"),)
        self.assertEqual("朝と昼", _variant_text("朝昼", variant))
        for text in ("朝", "朝昼と朝昼"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "exactly once"):
                _variant_text(text, variant)

    def test_unknown_scope_entry_is_rejected(self):
        approved = {("MS/TEST.MTX", 13)}
        for supplied in (approved | {("MS/TEST.MTX", 15)}, set()):
            with self.subTest(supplied=supplied), self.assertRaisesRegex(ValueError, "entry scope"):
                _check_inventory_scope(supplied, approved)

    def test_each_whole_source_and_dc_hash_rejects_drift(self):
        for description in ("PS2 source", "PS4 source", "official DC"):
            with self.subTest(description=description), self.assertRaisesRegex(ValueError, description):
                _check_digest(b"changed", sha256(b"pinned").hexdigest(), description)

    def test_pointer_alias_slot_swap_is_rejected(self):
        body = b"zr" + raw("海") + b"wc_\0"
        with self.assertRaisesRegex(ValueError, "pointer slots"):
            _source_evidence(mtx(body), mtx(body, (2, 0, 2, 0)), (10, 12), (10, 12), ())

    def test_control_operand_drift_is_rejected(self):
        body2 = b"ds01zr" + raw("海") + b"wc_\0"
        body4 = b"ds02zr" + raw("海") + b"wc_\0"
        with self.assertRaisesRegex(ValueError, "native boundary"):
            _source_evidence(mtx(body2), mtx(body4), (14, 16), (14, 16), ())

    def test_unreviewed_text_difference_is_rejected_inside_cluster(self):
        with self.assertRaisesRegex(ValueError, "canonical Japanese"):
            _source_evidence(mtx(b"zr" + raw("海辺") + b"wc_\0"),
                             mtx(b"zr" + raw("川辺") + b"wc_\0"), (10, 14), (10, 14), ())

    def test_only_terminal_native_padding_can_differ(self):
        body = b"zr" + raw("海") + b"wc_"
        evidence = _source_evidence(mtx(body), mtx(body + b"\0"), (10, 12), (10, 12), ())
        self.assertNotEqual(evidence["ps2_boundary_sha256"], evidence["ps4_boundary_sha256"])
        self.assertEqual([0, 1], evidence["pointer_slots"])

    def test_installed_entry_byte_drift_is_rejected_even_with_correct_extent(self):
        expected = {"installed_offset": 2, "installed_length": 2,
                    "installed_bytes_sha256": sha256(b"AB").hexdigest()}
        self.assertEqual(202, _installed_rows([expected], b"xxAB", 200, "test")[0]["installed_iso_offset"])
        with self.assertRaisesRegex(ValueError, "installed entry"):
            _installed_rows([expected], b"xxAC", 200, "test")


class ReviewedCorrespondenceDiscTests(unittest.TestCase):
    def test_final_r67n_proves_all_nine_entries(self):
        iso = Path("local/r67n-release/67.15n-official-script-diagnostic.iso")
        ps2 = Path("local/r67n-sources/assets/ADV")
        ps4 = Path("local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV")
        inventory = Path("local/r67n-inventory-final")
        if not all(path.exists() for path in (iso, ps2, ps4, inventory)):
            self.skipTest("original sources and finalized diagnostic baseline are local fixtures")
        report = verify_correspondence(iso, ps2, ps4, inventory)
        self.assertEqual(7, len(report["clusters"]))
        self.assertEqual(9, len(report["entries"]))
        self.assertEqual(
            {("DG/DG13_02.MTX", 7088), ("DG/DG13_02.MTX", 7113),
             ("FN/FN13_16.MTX", 1646), ("MS/MS05_01.MTX", 28761),
             ("MS/MS05_03.MTX", 8738), ("MS/MS05_03.MTX", 16985),
             ("MS/MS05_03.MTX", 17002), ("MS/MS06_01.MTX", 10651),
             ("MS/MS11_03.MTX", 7267)},
            {(row["file"], row["dc_key"]) for row in report["entries"]},
        )
        self.assertEqual("c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0",
                         report["iso_sha256"])
        self.assertTrue(all(row["status"] == "official English installed" for row in report["entries"]))


if __name__ == "__main__":
    unittest.main()
