from __future__ import annotations

import io
import struct
import unittest

from tools.iso9660_patch import read_both_u32, write_both_u32, patch_directory_record


class BothEndianU32Tests(unittest.TestCase):
    def test_reads_matching_little_and_big_endian_value(self) -> None:
        buffer = struct.pack("<I", 123456) + struct.pack(">I", 123456)

        self.assertEqual(123456, read_both_u32(buffer, 0))

    def test_rejects_mismatched_endian_copies(self) -> None:
        buffer = struct.pack("<I", 1) + struct.pack(">I", 2)

        with self.assertRaisesRegex(ValueError, "endian copies disagree"):
            read_both_u32(buffer, 0)

    def test_writes_both_endian_copies(self) -> None:
        buffer = bytearray(8)

        write_both_u32(buffer, 0, 0x12345678)

        self.assertEqual(bytes.fromhex("78 56 34 12 12 34 56 78"), bytes(buffer))


class DirectoryRecordPatchTests(unittest.TestCase):
    def test_patches_extent_and_size_without_changing_other_record_bytes(self) -> None:
        record = bytearray(range(64))
        record[0] = 64
        original = bytes(record)

        patch_directory_record(record, 0, extent=0x10203040, size=0x50607080)

        self.assertEqual(0x10203040, read_both_u32(record, 2))
        self.assertEqual(0x50607080, read_both_u32(record, 10))
        self.assertEqual(original[:2], record[:2])
        self.assertEqual(original[18:], record[18:])


if __name__ == "__main__":
    unittest.main()
