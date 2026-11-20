from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from tests.test_build_translation_iso import both_u32, dir_record, make_nested_iso, put_dir
from tools.build_translation_iso import build_translation_iso
from tools.cvm import HEADER_SIZE
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.translation_overlay import collect_overlay


class TailElfGrowthTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.source = root / "source.iso"
        self.output = root / "output.iso"
        self.translated_elf = root / "translated.elf"
        self.overlay_root = root / "overlay"
        self.overlay_root.mkdir()
        make_nested_iso(self.source)

        original = self.source.read_bytes()[22 * SECTOR_SIZE:22 * SECTOR_SIZE + 128]
        self.translated = original + b"N" * (3000 - len(original))
        self.translated_elf.write_bytes(self.translated)

    def make_tail_source(self, volume: int, *, alias_elf: bool = False) -> bytes:
        image = bytearray(self.source.read_bytes()[:volume * SECTOR_SIZE])
        elf_start = 68 * SECTOR_SIZE
        image[elf_start:elf_start + SECTOR_SIZE] = image[22 * SECTOR_SIZE:23 * SECTOR_SIZE]
        image[22 * SECTOR_SIZE:23 * SECTOR_SIZE] = bytes(SECTOR_SIZE)
        image[16 * SECTOR_SIZE + 80:16 * SECTOR_SIZE + 88] = both_u32(volume)
        records = [
            dir_record(b"SLPM_665.11;1", 68, 128),
            dir_record(b"DATA.CVM;1", 24, 43 * SECTOR_SIZE),
            dir_record(b"SYSTEM.CNF;1", 67, 64),
        ]
        if alias_elf:
            records.append(dir_record(b"ALIAS.BIN;1", 68, 64))
        put_dir(image, 0, 20, records)
        self.source.write_bytes(image)
        return bytes(image)

    def build(self) -> dict:
        overlay = collect_overlay([("test", self.overlay_root)])
        return build_translation_iso(self.source, self.output, overlay, self.translated_elf)

    def add_growing_overlay(self) -> bytes:
        replacement = b"E" * 3000
        dg = self.overlay_root / "DG"
        dg.mkdir()
        (dg / "A.MTX").write_bytes(replacement)
        return replacement

    def assert_elf(self, image: bytes, extent: int, expected: bytes) -> None:
        _, records = index_iso(image)
        elf = find_record(records, "SLPM_665.11")
        self.assertEqual((extent, len(expected)), (elf.extent, elf.size))
        self.assertEqual(
            both_u32(extent) + both_u32(len(expected)),
            image[elf.record_offset + 2:elf.record_offset + 18],
        )
        self.assertEqual(
            expected.ljust(2 * SECTOR_SIZE, b"\0"),
            image[extent * SECTOR_SIZE:(extent + 2) * SECTOR_SIZE],
        )

    def test_last_elf_extends_when_full_relocation_cannot_fit(self) -> None:
        before = self.make_tail_source(70)

        report = self.build()

        self.assertFalse(report["elf_relocated"])
        self.assertTrue(report["elf_extended_in_place"])
        self.assertEqual((68, 68), (report["elf_input_extent"], report["elf_output_extent"]))
        after = self.output.read_bytes()
        self.assertEqual(len(before), len(after))
        self.assert_elf(after, 68, self.translated)
        self.assertEqual(before[67 * SECTOR_SIZE:68 * SECTOR_SIZE], after[67 * SECTOR_SIZE:68 * SECTOR_SIZE])
        self.assertEqual(before, self.source.read_bytes())

    def test_last_elf_extends_after_cvm_growth_shifts_the_tail(self) -> None:
        before = self.make_tail_source(72)
        replacement = self.add_growing_overlay()

        report = self.build()

        self.assertEqual(2, report["appended_sectors"])
        self.assertEqual((68, 70), (report["elf_input_extent"], report["elf_output_extent"]))
        self.assertTrue(report["elf_extended_in_place"])
        self.assertFalse(report["elf_relocated"])

        after = self.output.read_bytes()
        expected_elf = bytearray(self.translated)
        struct.pack_into("<I", expected_elf, 72, len(replacement))
        struct.pack_into("<I", expected_elf, 80, 40)
        self.assert_elf(after, 70, bytes(expected_elf))
        outer_volume, outer = index_iso(after)
        cvm = find_record(outer, "DATA.CVM")
        tail = find_record(outer, "SYSTEM.CNF")
        self.assertEqual(72, outer_volume)
        self.assertEqual((24, 45 * SECTOR_SIZE), (cvm.extent, cvm.size))
        self.assertEqual((69, 64), (tail.extent, tail.size))
        self.assertEqual(before[67 * SECTOR_SIZE:68 * SECTOR_SIZE], after[69 * SECTOR_SIZE:70 * SECTOR_SIZE])
        embedded_base = cvm.extent * SECTOR_SIZE + HEADER_SIZE
        volume, embedded = index_iso(after, embedded_base)
        translated = find_record(embedded, "ADV/DG/A.MTX")
        self.assertEqual(42, volume)
        self.assertEqual((40, 3000), (translated.extent, translated.size))
        start = embedded_base + 40 * SECTOR_SIZE
        self.assertEqual(replacement, after[start:start + len(replacement)])
        self.assertEqual(len(before), len(after))
        self.assertEqual(before, self.source.read_bytes())

    def test_nonlast_elf_still_relocates(self) -> None:
        before = self.source.read_bytes()

        report = self.build()

        self.assertTrue(report["elf_relocated"])
        self.assertFalse(report["elf_extended_in_place"])
        self.assertEqual((22, 68), (report["elf_input_extent"], report["elf_output_extent"]))
        after = self.output.read_bytes()
        self.assert_elf(after, 68, self.translated)
        self.assertEqual(before[67 * SECTOR_SIZE:68 * SECTOR_SIZE], after[67 * SECTOR_SIZE:68 * SECTOR_SIZE])
        self.assertEqual(before, self.source.read_bytes())

    def test_elf_sharing_a_source_extent_still_relocates(self) -> None:
        before = self.make_tail_source(72, alias_elf=True)

        report = self.build()

        self.assertTrue(report["elf_relocated"])
        self.assertFalse(report["elf_extended_in_place"])
        self.assertEqual((68, 69), (report["elf_input_extent"], report["elf_output_extent"]))
        after = self.output.read_bytes()
        self.assert_elf(after, 69, self.translated)
        self.assertEqual(before[68 * SECTOR_SIZE:69 * SECTOR_SIZE], after[68 * SECTOR_SIZE:69 * SECTOR_SIZE])
        self.assertEqual(before, self.source.read_bytes())

    def test_elf_extension_rejects_slack_consumed_by_cvm_growth(self) -> None:
        before = self.make_tail_source(71)
        self.add_growing_overlay()

        with self.assertRaisesRegex(ValueError, "insufficient trailing slack for translated ELF"):
            self.build()

        self.assertEqual(before, self.source.read_bytes())
