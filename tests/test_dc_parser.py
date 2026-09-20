from __future__ import annotations

import struct
import unittest

from tools.localization import DcLocalization


def one_entry_mtx(segment: bytes) -> bytes:
    return struct.pack("<2H", 1, 0) + segment


class DcTerminatorFallbackTests(unittest.TestCase):
    def test_accepts_standalone_brace_control_boundary(self) -> None:
        raw = one_entry_mtx("場所".encode("cp932") + b"}sbr1w60_")
        loc = DcLocalization.from_json(raw, {"keys": [4], "values": ["Location"]})
        self.assertEqual(4 + len("場所".encode("cp932")), loc.groups[0].replace_end)

    def test_accepts_rds_control_boundary(self) -> None:
        raw = one_entry_mtx("【人】".encode("cp932") + b"rds01s3_")
        loc = DcLocalization.from_json(raw, {"keys": [4], "values": ["【Person】"]})
        self.assertEqual(4 + len("【人】".encode("cp932")), loc.groups[0].replace_end)

    def test_accepts_ds_control_boundary(self) -> None:
        raw = one_entry_mtx("まあ".encode("cp932") + b"ds01s3_")
        loc = DcLocalization.from_json(raw, {"keys": [4], "values": ["Well"]})
        self.assertEqual(4 + len("まあ".encode("cp932")), loc.groups[0].replace_end)

    def test_accepts_trailing_c_control_boundary(self) -> None:
        raw = one_entry_mtx("本".encode("cp932") + b"c")
        loc = DcLocalization.from_json(raw, {"keys": [4], "values": ["Book"]})
        self.assertEqual(4 + len("本".encode("cp932")), loc.groups[0].replace_end)


if __name__ == "__main__":
    unittest.main()
