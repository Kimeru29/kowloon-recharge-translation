from __future__ import annotations

import unittest

from tools.ksf_import import KsfImportError, analyze_ksf_exact, import_exact_ksf


def field_blob(japanese: str, capacity: int, trailer: bytes = b"\x02END") -> tuple[bytes, int]:
    source = japanese.encode("cp932")
    if len(source) >= capacity:
        raise ValueError("test field capacity must leave a NUL/padding byte")
    key = 2
    raw = b"\x00\x01" + source + (b"\x00" * (capacity - len(source))) + trailer
    return raw, key


class ConservativeKsfImportTests(unittest.TestCase):
    def test_proven_fitting_field_is_patched_and_zero_filled(self) -> None:
        raw, key = field_blob("見る", 20)
        dc = {"keys": [key], "values": ["Look  around"]}

        result, report = import_exact_ksf(raw, raw, dc)

        self.assertEqual("fit", report[0].status)
        self.assertEqual(20, report[0].capacity)
        self.assertEqual(b"Look around", result[key:key + 11])
        self.assertEqual(b"\x00" * 9, result[key + 11:key + 20])
        self.assertEqual(raw[key + 20:], result[key + 20:])

    def test_overflow_is_reported_without_mutating_field(self) -> None:
        raw, key = field_blob("見る", 8)
        dc = {"keys": [key], "values": ["This is much too long"]}

        result, report = import_exact_ksf(raw, raw, dc)

        self.assertEqual("overflow", report[0].status)
        self.assertEqual(raw, result)

    def test_key_without_record_marker_is_ambiguous_and_unchanged(self) -> None:
        raw = b"\x00\x00" + "見る".encode("cp932") + b"\x00" * 12 + b"\x02END"
        dc = {"keys": [2], "values": ["Look"]}

        result, report = import_exact_ksf(raw, raw, dc)

        self.assertEqual("ambiguous", report[0].status)
        self.assertEqual(raw, result)

    def test_non_identical_sources_reject_exact_tier(self) -> None:
        raw, key = field_blob("見る", 20)

        with self.assertRaisesRegex(KsfImportError, "byte-identical"):
            analyze_ksf_exact(raw, raw[:-1] + b"X", {"keys": [key], "values": ["Look"]})

    def test_duplicate_keys_are_ambiguous_not_double_patched(self) -> None:
        raw, key = field_blob("見る", 20)
        dc = {"keys": [key, key], "values": ["Look", "See"]}

        result, report = import_exact_ksf(raw, raw, dc)

        self.assertEqual(raw, result)
        self.assertTrue(all(item.status == "ambiguous" for item in report))


if __name__ == "__main__":
    unittest.main()
