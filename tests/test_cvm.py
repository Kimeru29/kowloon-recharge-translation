from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.cvm import CvmHeader
from tests.local_fixtures import require_local_fixture


FIXTURE = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "cvm-header.bin")


class CvmHeaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = FIXTURE.read_bytes()

    def test_parses_proven_kowloon_size_fields(self) -> None:
        header = CvmHeader.parse(self.raw)

        self.assertEqual(2_064_615_424, header.total_size)
        self.assertEqual(2_064_609_280, header.payload_size)
        self.assertEqual(header.total_size - 0x80C, header.zone_chunk_length)
        self.assertEqual(header.total_size - 0x1800, header.payload_size)

    def test_grow_payload_updates_all_three_dependent_big_endian_fields(self) -> None:
        header = CvmHeader.parse(self.raw)
        grown = header.grow_payload(4096).compile()

        self.assertEqual(len(self.raw), len(grown))
        self.assertEqual(2_064_619_520, struct.unpack_from(">I", grown, 0x20)[0])
        self.assertEqual(2_064_617_460, struct.unpack_from(">I", grown, 0x808)[0])
        self.assertEqual(2_064_613_376, struct.unpack_from(">I", grown, 0x834)[0])
        self.assertEqual(self.raw[:0x20], grown[:0x20])
        self.assertEqual(self.raw[0x24:0x808], grown[0x24:0x808])
        self.assertEqual(self.raw[0x80C:0x834], grown[0x80C:0x834])
        self.assertEqual(self.raw[0x838:], grown[0x838:])

    def test_rejects_non_sector_aligned_growth(self) -> None:
        header = CvmHeader.parse(self.raw)

        with self.assertRaisesRegex(ValueError, "2048-byte sector"):
            header.grow_payload(1)


if __name__ == "__main__":
    unittest.main()
