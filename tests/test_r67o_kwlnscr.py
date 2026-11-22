from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import struct
from tempfile import TemporaryDirectory
import unittest

from tools.mtx import MtxFile
from tools.r67o_kwlnscr import (
    TARGET_MTX,
    compile_blocks,
    read_verified_files,
    run,
    scan_corpus,
    verify_installed,
    verify_native_ranges,
)


def aligned(raw):
    return raw + b"\0" * (-len(raw) % 4)


def mtx(*regions, alias=None):
    header_size = 12
    offsets = [header_size]
    for region in regions[:-1]:
        offsets.append(offsets[-1] + len(region))
    if alias is not None:
        offsets.append(offsets[alias])
    offsets.extend([0] * (6 - len(offsets)))
    return struct.pack("<6H", *(offset // 4 for offset in offsets)) + b"".join(regions)


def build_fixture(*, fourth_value="Original only"):
    japanese = [
        b"px" + "春風".encode("cp932"),
        b"pm" + "夏".encode("cp932"),
        b"pn" + "秋".encode("cp932"),
        "冬".encode("cp932"),
    ]
    scenes = [b"wcr" + item + b"wc_" for item in japanese]
    after = b"wc_"
    source = mtx(aligned(scenes[3]), aligned(b"rds11" + scenes[0]),
                 aligned(b"rds22" + scenes[1]), aligned(b"rds33" + scenes[2]))
    target = mtx(aligned(b"rds01" + scenes[0]), aligned(b"rds02" + scenes[1]),
                 aligned(b"rds03" + scenes[2]), alias=1)
    proofs = []
    for scene in scenes[:3]:
        org, dest = source.index(scene), target.index(scene)
        proofs.append({"ps4": [org, org + len(scene)], "ps2": [dest, dest + len(scene)],
                       "sha256": sha256(scene).hexdigest()})
    keys = [source.index(item + after) for item in japanese]
    dc = {"keys": keys, "values": ["(px)Spring festival", "(pm1)Summer", "(pn1)Autumn", fourth_value]}
    return target, source, dc, proofs


class CrossFileTests(unittest.TestCase):
    def test_three_exact_blocks_relocate_and_preserve_names_and_aliases(self):
        target, source, dc, proofs = build_fixture()
        output, evidence = compile_blocks(target, source, dc, proofs, {})
        self.assertEqual(3, len(evidence["spans"]))
        self.assertEqual(4, len(evidence["entries"]))
        first, second, third, unmatched = evidence["entries"]
        self.assertEqual((0, dc["keys"][0]), (first["dc_index"], first["key"]))
        self.assertEqual([1], first["source_ps4"]["pointer_slots"])
        self.assertEqual([0], first["original_ps2"]["pointer_slots"])
        self.assertEqual([1, 3], second["original_ps2"]["pointer_slots"])
        self.assertEqual([2], third["original_ps2"]["pointer_slots"])
        self.assertEqual("no bounded alternate owner", unmatched["reason"])
        self.assertIsNone(unmatched["installed_ps2"])
        self.assertIsNone(unmatched["output_ps2"])
        self.assertIn(b"px" + "Ｓｐｒｉｎｇ　ｆｅｓｔｉｖａｌ".encode("cp932"), output)
        self.assertIn(b"pm" + "Ｓｕｍｍｅｒ".encode("cp932"), output)
        self.assertIn(b"pn" + "Ａｕｔｕｍｎ".encode("cp932"), output)
        words = MtxFile.parse(output).pointer_words
        self.assertGreater(words[1], MtxFile.parse(target).pointer_words[1])
        self.assertEqual(words[1], words[3])
        self.assertEqual((0, 0), words[4:])

    def test_held_mapped_group_stays_identical_after_earlier_relocations(self):
        target, source, dc, proofs = build_fixture()
        dc["values"][2] = "(pmyh)Autumn"
        held = {str(dc["keys"][2]): "unsupported official phonetic macro and native one-glyph controls"}
        output, evidence = compile_blocks(target, source, dc, proofs, held)
        kept = evidence["entries"][2]
        start, end = kept["output_ps2"]["span"]
        before = kept["original_ps2"]
        self.assertEqual(2, len(evidence["spans"]))
        self.assertNotEqual(before["span"][0], start)
        self.assertEqual(target[slice(*before["span"])], output[start:end])
        self.assertEqual(before["sha256"], kept["output_ps2"]["sha256"])

    def test_entire_scene_digest_drift_fails_even_when_dialogue_is_equal(self):
        target, source, dc, proofs = build_fixture()
        proofs[0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "scene block.*hash"):
            compile_blocks(target, source, dc, proofs, {})

    def test_overlapping_blocks_fail_before_compiling(self):
        target, source, dc, proofs = build_fixture()
        proofs[1] = proofs[0].copy()
        with self.assertRaisesRegex(ValueError, "overlap"):
            compile_blocks(target, source, dc, proofs, {})

    def test_unknown_official_macro_cannot_enter_approved_span(self):
        target, source, dc, proofs = build_fixture()
        dc["values"][1] = "(punknown)Summer"
        with self.assertRaisesRegex(ValueError, "unsafe_name_control"):
            compile_blocks(target, source, dc, proofs, {})

    def test_official_cannot_drop_native_name_token(self):
        target, source, dc, proofs = build_fixture()
        dc["values"][1] = "Summer"
        with self.assertRaisesRegex(ValueError, "name ownership"):
            compile_blocks(target, source, dc, proofs, {})

    def test_approved_group_cannot_cross_target_pointer(self):
        target, source, dc, proofs = build_fixture()
        first_body = 12
        script = bytearray(target)
        struct.pack_into("<H", script, 8, (first_body + 12) // 4)
        with self.assertRaisesRegex(ValueError, "pointer boundary"):
            compile_blocks(bytes(script), source, dc, proofs, {})

    def test_source_and_dc_hash_drift_fails(self):
        files = {"MS/MS01_03.MTX": b"script", "MS/EN/MS01_03DC.json": b"map"}
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for path, content in files.items():
                (root / path).parent.mkdir(parents=True, exist_ok=True)
                (root / path).write_bytes(content)
            expected = {path: sha256(content).hexdigest() for path, content in files.items()}
            for path, content in files.items():
                with self.subTest(path=path):
                    (root / path).write_bytes(content + b" drift")
                    with self.assertRaisesRegex(ValueError, "hash drift"):
                        read_verified_files(root, expected)
                    (root / path).write_bytes(content)

    def test_census_rejects_unexpected_exact_owner(self):
        target, source, dc, proofs = build_fixture()
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / TARGET_MTX).write_bytes(target)
            (root / "other.MTX").write_bytes(target)
            first = proofs[0]
            first["ps2_owners"] = [[TARGET_MTX, first["ps2"][0], 1]]
            with self.assertRaisesRegex(ValueError, "scene block owner census"):
                scan_corpus(root, "ps2", target, [first], expected_count=2)

    def test_changed_installed_payload_is_rejected(self):
        raw = b"pristine"
        with self.assertRaisesRegex(ValueError, "installed preimage"):
            verify_installed({TARGET_MTX: raw}, {TARGET_MTX: raw + b"!"})

    def test_native_ordinal_anchor_drift_is_rejected(self):
        offset = 0x215820 - 0x100000 + 0x80
        anchor = bytes.fromhex("08008694")
        elf = b"\0" * offset + anchor
        ranges = {"0x215820..0x215824": sha256(anchor).hexdigest()}
        verify_native_ranges(elf, ranges)
        with self.assertRaisesRegex(ValueError, "native anchor drift at 0x215820"):
            verify_native_ranges(elf[:-1] + b"\x95", ranges)

    def test_output_destination_is_never_overwritten(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            sentinel = root / "report.json"
            sentinel.write_text("prior")
            with self.assertRaises(FileExistsError):
                run(root / "ps2", root / "ps4", root / "baseline.iso", root)
            self.assertEqual("prior", sentinel.read_text())


if __name__ == "__main__":
    unittest.main()
