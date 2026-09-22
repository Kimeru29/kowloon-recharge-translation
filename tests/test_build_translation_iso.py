from __future__ import annotations

import mmap
import struct
import tempfile
import unittest
from pathlib import Path

from tools.build_translation_iso import build_translation_iso
from tools.cvm import HEADER_SIZE
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.translation_overlay import collect_overlay


def both_u32(value: int) -> bytes:
    return struct.pack("<I", value) + struct.pack(">I", value)


def both_u16(value: int) -> bytes:
    return struct.pack("<H", value) + struct.pack(">H", value)


def dir_record(name: bytes, extent: int, size: int, *, directory: bool = False) -> bytes:
    length = 33 + len(name) + (0 if len(name) % 2 else 1)
    raw = bytearray(length)
    raw[0] = length
    raw[2:10] = both_u32(extent)
    raw[10:18] = both_u32(size)
    raw[25] = 0x02 if directory else 0
    raw[28:32] = both_u16(1)
    raw[32] = len(name)
    raw[33:33 + len(name)] = name
    return bytes(raw)


def put_dir(image: bytearray, base: int, extent: int, records: list[bytes]) -> None:
    pos = base + extent * SECTOR_SIZE
    payload = b"".join(records)
    image[pos:pos + len(payload)] = payload


def put_pvd(image: bytearray, base: int, volume_sectors: int, root_extent: int) -> None:
    pvd = base + 16 * SECTOR_SIZE
    image[pvd] = 1
    image[pvd + 1:pvd + 6] = b"CD001"
    image[pvd + 80:pvd + 88] = both_u32(volume_sectors)
    root = dir_record(b"\x00", root_extent, SECTOR_SIZE, directory=True)
    image[pvd + 156:pvd + 156 + len(root)] = root


def make_nested_iso(path: Path) -> dict[str, int]:
    outer_volume = 80
    outer_root = 20
    elf_extent = 22
    cvm_extent = 24
    embedded_volume = 40
    cvm_sectors = (HEADER_SIZE // SECTOR_SIZE) + embedded_volume
    tail_extent = cvm_extent + cvm_sectors
    image = bytearray(outer_volume * SECTOR_SIZE)

    put_pvd(image, 0, outer_volume, outer_root)
    put_dir(
        image,
        0,
        outer_root,
        [
            dir_record(b"SLPM_665.11;1", elf_extent, 128),
            dir_record(b"DATA.CVM;1", cvm_extent, cvm_sectors * SECTOR_SIZE),
            dir_record(b"SYSTEM.CNF;1", tail_extent, 64),
        ],
    )
    elf = bytearray(128)
    elf[:32] = (b"SLPM-66511\x00BISLPM-66511Save\x00")[:32]
    # Synthetic ROFS record: size is filename_offset-14, extent is filename_offset-6.
    filename_offset = 86
    struct.pack_into("<I", elf, filename_offset - 14, 100)
    struct.pack_into("<I", elf, filename_offset - 6, 30)
    elf[filename_offset - 2:filename_offset] = b"\x00\xdf"
    elf[filename_offset:filename_offset + 6] = b"A.MTX\x00"
    graphics_filename_offset = 112
    struct.pack_into("<I", elf, graphics_filename_offset - 14, 100)
    struct.pack_into("<I", elf, graphics_filename_offset - 6, 31)
    elf[graphics_filename_offset - 2:graphics_filename_offset] = b"\x00\xdf"
    elf[graphics_filename_offset:graphics_filename_offset + 12] = b"B_GP019.BIN\x00"
    image[elf_extent * SECTOR_SIZE:elf_extent * SECTOR_SIZE + len(elf)] = elf
    tail_payload = b"TAIL-PAYLOAD" + b"T" * 52
    image[tail_extent * SECTOR_SIZE:tail_extent * SECTOR_SIZE + 64] = tail_payload

    cvm_base = cvm_extent * SECTOR_SIZE
    total_size = cvm_sectors * SECTOR_SIZE
    payload_size = embedded_volume * SECTOR_SIZE
    header = bytearray(HEADER_SIZE)
    header[:4] = b"CVMH"
    struct.pack_into(">I", header, 0x20, total_size)
    header[0x800:0x804] = b"ZONE"
    struct.pack_into(">I", header, 0x808, total_size - 0x80C)
    struct.pack_into(">I", header, 0x834, payload_size)
    image[cvm_base:cvm_base + HEADER_SIZE] = header

    embedded_base = cvm_base + HEADER_SIZE
    put_pvd(image, embedded_base, embedded_volume, 20)
    put_dir(
        image,
        embedded_base,
        20,
        [
            dir_record(b"ADV", 21, SECTOR_SIZE, directory=True),
            dir_record(b"BLBRD", 23, SECTOR_SIZE, directory=True),
        ],
    )
    put_dir(image, embedded_base, 21, [dir_record(b"DG", 22, SECTOR_SIZE, directory=True)])
    put_dir(image, embedded_base, 22, [dir_record(b"A.MTX;1", 30, 100)])
    put_dir(image, embedded_base, 23, [dir_record(b"B_GP019.BIN;1", 31, 100)])
    image[embedded_base + 30 * SECTOR_SIZE:embedded_base + 30 * SECTOR_SIZE + 100] = b"J" * 100
    image[embedded_base + 31 * SECTOR_SIZE:embedded_base + 31 * SECTOR_SIZE + 100] = b"G" * 100

    path.write_bytes(image)
    return {
        "tail_extent": tail_extent,
        "embedded_volume": embedded_volume,
        "cvm_extent": cvm_extent,
    }


class WholeIsoOverlayBuildTests(unittest.TestCase):
    def test_relocates_growing_embedded_file_and_preserves_shifted_outer_tail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.iso"
            output = root / "output.iso"
            meta = make_nested_iso(source)
            overlay_root = root / "overlay"
            (overlay_root / "DG").mkdir(parents=True)
            replacement = b"E" * 3000
            (overlay_root / "DG" / "A.MTX").write_bytes(replacement)
            overlay = collect_overlay([("test", overlay_root)])

            report = build_translation_iso(source, output, overlay)

            self.assertEqual(source.stat().st_size, output.stat().st_size)
            self.assertEqual(2, report["appended_sectors"])
            self.assertEqual(1, report["relocated_files"])
            with output.open("rb") as handle:
                image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    _, outer = index_iso(image)
                    cvm = find_record(outer, "DATA.CVM")
                    tail = find_record(outer, "SYSTEM.CNF")
                    self.assertEqual(meta["tail_extent"] + 2, tail.extent)
                    self.assertEqual(
                        b"TAIL-PAYLOAD" + b"T" * 52,
                        bytes(image[tail.extent * SECTOR_SIZE:tail.extent * SECTOR_SIZE + 64]),
                    )
                    embedded_base = cvm.extent * SECTOR_SIZE + HEADER_SIZE
                    volume, records = index_iso(image, embedded_base)
                    translated = find_record(records, "ADV/DG/A.MTX")
                    self.assertEqual(meta["embedded_volume"] + 2, volume)
                    self.assertEqual(meta["embedded_volume"], translated.extent)
                    self.assertEqual(len(replacement), translated.size)
                    self.assertEqual(
                        replacement,
                        bytes(
                            image[
                                embedded_base + translated.extent * SECTOR_SIZE:
                                embedded_base + translated.extent * SECTOR_SIZE + translated.size
                            ]
                        ),
                    )
                finally:
                    image.close()


    def test_replaces_explicit_blbrd_graphics_container_and_patches_rofs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.iso"
            output = root / "output.iso"
            make_nested_iso(source)
            overlay_root = root / "overlay"
            (overlay_root / "BLBRD").mkdir(parents=True)
            replacement = b"L" * 100
            (overlay_root / "BLBRD" / "B_GP019.BIN").write_bytes(replacement)
            overlay = collect_overlay([("startup-graphics", overlay_root)])

            report = build_translation_iso(source, output, overlay)

            self.assertEqual(0, report["appended_sectors"])
            self.assertEqual(1, report["in_place_files"])
            with output.open("rb") as handle:
                image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    _, outer = index_iso(image)
                    cvm = find_record(outer, "DATA.CVM")
                    embedded_base = cvm.extent * SECTOR_SIZE + HEADER_SIZE
                    _, records = index_iso(image, embedded_base)
                    translated = find_record(records, "BLBRD/B_GP019.BIN")
                    self.assertEqual(31, translated.extent)
                    self.assertEqual(replacement, bytes(
                        image[
                            embedded_base + translated.extent * SECTOR_SIZE:
                            embedded_base + translated.extent * SECTOR_SIZE + translated.size
                        ]
                    ))
                    elf_record = find_record(outer, "SLPM_665.11")
                    elf = bytes(image[elf_record.extent * SECTOR_SIZE:elf_record.extent * SECTOR_SIZE + elf_record.size])
                    self.assertEqual(100, struct.unpack_from("<I", elf, 98)[0])
                    self.assertEqual(31, struct.unpack_from("<I", elf, 106)[0])
                finally:
                    image.close()

    def test_updates_embedded_rofs_size_and_extent_in_translated_elf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.iso"
            output = root / "output.iso"
            make_nested_iso(source)
            overlay_root = root / "overlay"
            (overlay_root / "DG").mkdir(parents=True)
            replacement = b"E" * 3000
            (overlay_root / "DG" / "A.MTX").write_bytes(replacement)
            overlay = collect_overlay([("test", overlay_root)])

            source_bytes = source.read_bytes()
            translated_elf = root / "translated.elf"
            translated_elf.write_bytes(source_bytes[22 * SECTOR_SIZE:22 * SECTOR_SIZE + 128])

            build_translation_iso(source, output, overlay, translated_elf)

            with output.open("rb") as handle:
                image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
                try:
                    _, outer = index_iso(image)
                    elf_record = find_record(outer, "SLPM_665.11")
                    actual = bytes(
                        image[
                            elf_record.extent * SECTOR_SIZE:
                            elf_record.extent * SECTOR_SIZE + elf_record.size
                        ]
                    )
                    self.assertEqual(len(replacement), struct.unpack_from("<I", actual, 72)[0])
                    self.assertEqual(40, struct.unpack_from("<I", actual, 80)[0])
                finally:
                    image.close()


if __name__ == "__main__":
    unittest.main()
