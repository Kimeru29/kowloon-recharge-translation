from __future__ import annotations

import struct
import unittest

from tools.exact_import import ExactImportError, import_exact_mtx
from tools.mtx import MtxFile


def synthetic_mtx() -> bytes:
    header = struct.pack("<4H", 2, 4, 0, 0)
    region1 = "あ".encode("cp932") + b"wc___\x00"
    region2 = "い".encode("cp932") + b"wc___\x00"
    assert len(region1) == 8 and len(region2) == 8
    return header + region1 + region2


class ExactMtxImportTests(unittest.TestCase):
    def test_imports_identical_direct_mtx_and_rebuilds_pointers(self) -> None:
        raw = synthetic_mtx()
        dc = {"keys": [8, 16], "values": ["Hello", "World"]}

        result = import_exact_mtx(raw, raw, dc)

        parsed = MtxFile.parse(result)
        self.assertIn("Ｈｅｌｌｏ".encode("cp932"), result)
        self.assertIn("Ｗｏｒｌｄ".encode("cp932"), result)
        self.assertNotIn("あ".encode("cp932"), result)
        self.assertEqual(8, parsed.header_size)
        self.assertTrue(all(offset % 4 == 0 for offset in parsed.pointer_offsets if offset))

    def test_rejects_non_identical_ps2_ps4_sources(self) -> None:
        raw = synthetic_mtx()
        changed = raw[:-1] + b"X"

        with self.assertRaisesRegex(ExactImportError, "byte-identical"):
            import_exact_mtx(raw, changed, {"keys": [8], "values": ["Hello"]})

    def test_rejects_duplicate_or_indirect_dc_key_instead_of_guessing(self) -> None:
        raw = synthetic_mtx()
        dc = {"keys": [8, 8], "values": ["First", "Second"]}

        with self.assertRaises(ExactImportError):
            import_exact_mtx(raw, raw, dc)


if __name__ == "__main__":
    unittest.main()
