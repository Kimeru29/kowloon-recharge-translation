from __future__ import annotations

import unittest
from pathlib import Path

from tools.mtx import MtxFile
from tests.local_fixtures import require_local_fixture


FIXTURE = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "DG00_00" / "original.MTX")


class MtxHeaderTests(unittest.TestCase):
    def test_parses_header_size_from_first_quarter_offset(self) -> None:
        mtx = MtxFile.parse(FIXTURE.read_bytes())

        self.assertEqual(16, mtx.header_size)
        self.assertEqual((4, 5, 493, 733, 766, 799, 871, 1023), mtx.pointer_words)
        self.assertEqual((16, 20, 1972, 2932, 3064, 3196, 3484, 4092), mtx.pointer_offsets)
        self.assertEqual(b"_\x00\x00\x00", mtx.data[:4])

    def test_round_trip_without_changes_is_byte_identical(self) -> None:
        original = FIXTURE.read_bytes()
        mtx = MtxFile.parse(original)

        self.assertEqual(original, mtx.compile())


if __name__ == "__main__":
    unittest.main()
