from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import struct
import unittest

from tools.mtx import MtxFile
from tools.r67n_partial import import_partial_mtx, verify_partial_mtx


SAME = "同じ話".encode("cp932")
DIFFERENT = "別の話".encode("cp932")
ORIGINAL = "元の話".encode("cp932")


def region(*parts: bytes, terminator: bytes = b"_") -> bytes:
    data = b"".join(parts) + terminator
    return data + b"\0" * ((-len(data)) % 4)


def script(*regions: bytes) -> bytes:
    # Two active/zero-or-alias words for a four-byte header.
    if len(regions) == 1:
        words = (1, 0)
    elif len(regions) == 2:
        words = (1, (4 + len(regions[0])) // 4)
    else:
        raise ValueError("Test MTX supports one or two regions")
    return struct.pack("<2H", *words) + b"".join(regions)


def dc_for(raw: bytes, items: list[tuple[bytes, str]]) -> dict:
    return {"keys": [raw.index(value) for value, _ in items],
            "values": [line for _, line in items]}


class PartialMtxTests(unittest.TestCase):
    def test_copies_only_proven_group_and_relocates_untouched_region(self) -> None:
        ps4 = script(region(b"r", SAME, b"wc"), region(b"r", DIFFERENT, b"wc"))
        ps2 = script(region(b"r", SAME, b"wc"), region(b"r", ORIGINAL, b"wc"))
        dc = dc_for(ps4, [(SAME, "A longer line"), (DIFFERENT, "Leave alone")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(1, result.english_entries)
        self.assertEqual([((5,), 5, 5)], [
            (span.entry_ids, span.ps4_start, span.ps2_start) for span in result.spans
        ])
        self.assertEqual([((17,), "no_exact_span")], [
            (group.entry_ids, group.reason) for group in result.unresolved
        ])
        self.assertEqual((4, 36), MtxFile.parse(result.data).pointer_offsets)
        self.assertEqual(ps2[16:], result.data[36:])
        self.assertEqual("Ａ　ｌｏｎｇｅｒ　ｌｉｎｅ".encode("cp932"),
                         result.data[result.spans[0].output_start:result.spans[0].output_end])
        self.assertEqual(sha256(ps2).hexdigest(), result.ps2_sha256)
        self.assertEqual(sha256(ps4).hexdigest(), result.ps4_sha256)
        self.assertEqual(sha256(result.data).hexdigest(), result.output_sha256)
        verify_partial_mtx(ps2, ps4, dc, result)

    def test_rejects_repeated_target_context_when_no_occurrence_is_distinguishable(self) -> None:
        ps4 = script(region(b"r", SAME, b"wc"))
        ps2 = script(region(b"r", SAME, b"wc", b"r", SAME, b"wc", b"vz4"))
        dc = dc_for(ps4, [(SAME, "Same")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual("ambiguous_context", result.unresolved[0].reason)
        self.assertEqual(((5, 11), (14, 20)), result.unresolved[0].ps2_candidates)

    def test_disambiguates_repeated_line_with_distinct_exact_neighboring_context(self) -> None:
        ps4 = script(region(b"r", SAME, b"wc", b"r", ORIGINAL, b"wc"))
        ps2 = script(region(b"r", SAME, b"wc", b"r", DIFFERENT, b"wc",
                            b"r", SAME, b"wc", b"r", ORIGINAL, b"wc"))
        dc = dc_for(ps4, [(SAME, "This exact line"), (ORIGINAL, "Origin")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(23, result.spans[0].ps2_start)
        self.assertEqual(2, result.english_entries)
        self.assertEqual(ps2[4:22], result.data[4:22])
        verify_partial_mtx(ps2, ps4, dc, result)

    def test_rejects_source_group_crossing_a_pointer_target(self) -> None:
        ps4 = struct.pack("<2H", 1, 2) + b"s1" + ORIGINAL + b"wc_\0"
        ps2 = ps4
        dc = dc_for(ps4, [(ORIGINAL, "Crossing")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual("ps4_pointer_crossing", result.unresolved[0].reason)

    def test_rejects_target_group_crossing_a_pointer_target(self) -> None:
        ps4 = script(region(b"s1", SAME, b"wc"))
        ps2 = struct.pack("<2H", 1, 2) + ps4[4:]
        dc = dc_for(ps4, [(SAME, "Crossing")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual("ps2_pointer_crossing", result.unresolved[0].reason)

    def test_rejects_same_text_at_different_pointer_slot(self) -> None:
        ps4 = script(region(b"r", SAME, b"wc"), region(b"r", ORIGINAL, b"wc"))
        ps2 = script(region(b"r", ORIGINAL, b"wc"), region(b"r", SAME, b"wc"))
        dc = dc_for(ps4, [(SAME, "Crossed slot")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual("pointer_identity_mismatch", result.unresolved[0].reason)

    def test_does_not_normalize_changed_speaker_operands(self) -> None:
        ps4 = script(region(b"s0301", SAME, b"wc"))
        ps2 = script(region(b"s0401", SAME, b"wc"))
        dc = dc_for(ps4, [(SAME, "Ambiguous speaker")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual("no_exact_context", result.unresolved[0].reason)

    def test_rejects_overlapping_claims_on_the_same_target_range(self) -> None:
        ps4 = script(region(b"r", ORIGINAL, b"wc", b"r", SAME, b"wc",
                            b"r", SAME, b"wc", b"r", DIFFERENT, b"wc"))
        ps2 = script(region(b"r", ORIGINAL, b"wc", b"r", SAME, b"wc",
                            b"r", DIFFERENT, b"wc"))
        dc = {"keys": [14, 23], "values": ["First", "Second"]}

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual(["conflicting_context", "conflicting_context"],
                         [group.reason for group in result.unresolved])

    def test_keeps_other_groups_when_one_has_an_unproven_name_macro(self) -> None:
        ps4 = script(region(b"r", b"px", SAME, b"wc", b"r", ORIGINAL, b"wc"))
        dc = dc_for(ps4, [(b"px", "(pmyh)"), (ORIGINAL, "Origin")])

        result = import_partial_mtx(ps4, ps4, dc)

        self.assertEqual("unsafe_name_control", result.unresolved[0].reason)
        self.assertEqual(b"rpx" + SAME + b"wc", result.data[4:15])
        self.assertEqual(1, result.english_entries)

    def test_native_macro_must_belong_to_the_replaced_span(self) -> None:
        jp = script(region(b"r", SAME, b"wc", b"rpx", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "(px)"), (b"px", "(px) says so.")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual("unsafe_name_control", result.unresolved[0].reason)
        self.assertEqual(1, result.english_entries)
        self.assertEqual(1, result.data.count(b"px"))
        verify_partial_mtx(jp, jp, dc, result)

    def test_moves_native_name_only_between_exact_lines_on_one_page(self) -> None:
        jp = script(region(b"r", SAME, b"rpx", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "Hello (px)"), (b"px", "Again")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual(2, result.english_entries)
        self.assertEqual([(5, 12), (5, 12)], [s.name_scope for s in result.spans])
        self.assertEqual((5,), result.spans[0].entry_ids)
        self.assertEqual(b"pxr", result.data[result.spans[0].output_end - 2:result.spans[0].output_end + 1])
        self.assertEqual(b"wc", result.data[result.spans[1].output_end:result.spans[1].output_end + 2])
        verify_partial_mtx(jp, jp, dc, result)

    def test_keeps_native_names_when_official_english_reorders_them(self) -> None:
        jp = script(region(b"r", b"pm", SAME, b"pn", b"wc"))
        dc = dc_for(jp, [(b"pm", "(pn1) (pm1)")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual(("pm", "pn"), result.spans[0].source_name_controls)
        self.assertEqual(("pn", "pm"), result.spans[0].name_controls)
        self.assertEqual(b"pn" + "　".encode("cp932") + b"pm",
                         result.data[result.spans[0].output_start:result.spans[0].output_end])
        verify_partial_mtx(jp, jp, dc, result)

    def test_does_not_move_name_from_unproven_adjacent_line(self) -> None:
        ps4 = script(region(b"r", SAME, b"rpx", ORIGINAL, b"wc"))
        ps2 = script(region(b"r", SAME, b"rpx", DIFFERENT, b"wc"))
        dc = dc_for(ps4, [(SAME, "Hello (px)"), (b"px", "Again")])

        result = import_partial_mtx(ps2, ps4, dc)

        self.assertEqual(ps2, result.data)
        self.assertEqual(["unsafe_name_control", "no_exact_span"],
                         [u.reason for u in result.unresolved])

    def test_can_relocate_an_untouched_unaligned_tail_without_altering_it(self) -> None:
        jp = script(region(b"r", SAME, b"wc"), b"ending")
        dc = dc_for(jp, [(SAME, "A longer line")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual((4, 36), MtxFile.parse(result.data).pointer_offsets)
        self.assertEqual(b"ending", result.data[36:])
        verify_partial_mtx(jp, jp, dc, result)

    def test_rejects_unknown_gameplay_control_inside_an_exact_span(self) -> None:
        jp = script(region(b"r", SAME, b"va+1", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "Would accidentally drop an event")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual(jp, result.data)
        self.assertEqual("unsafe_source_control", result.unresolved[0].reason)

    def test_reflows_ruby_and_preserves_official_synthetic_entry_ids(self) -> None:
        ruby = b"l" + "漢字(かんじ)".encode("cp932")
        jp = script(region(b"r", SAME, ruby, b"r", ORIGINAL, b"wc"))
        dc = {"keys": [5, 6], "values": ["First", "Second"]}

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual(2, result.english_entries)
        self.assertEqual((5, 6), result.spans[0].entry_ids)
        self.assertEqual([(5, 5, 15), (6, 16, 28)],
                         [(row.entry_id, row.output_start, row.output_end)
                          for row in result.spans[0].entries])
        self.assertEqual("Ｆｉｒｓｔ".encode("cp932") + b"r" + "Ｓｅｃｏｎｄ".encode("cp932"),
                         result.data[5:result.spans[0].output_end])
        verify_partial_mtx(jp, jp, dc, result)

    def test_drops_only_region_that_cannot_be_safely_padded(self) -> None:
        jp = script(region(b"r", SAME, b"wc", terminator=b"S"),
                    region(b"r", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "AB"), (ORIGINAL, "A longer line")])

        result = import_partial_mtx(jp, jp, dc)

        self.assertEqual("unsafe_alignment", result.unresolved[0].reason)
        self.assertEqual(1, result.english_entries)
        self.assertEqual(jp[4:16], result.data[4:16])
        verify_partial_mtx(jp, jp, dc, result)

    def test_verifier_rejects_stale_source_and_dc_hashes(self) -> None:
        jp = script(region(b"r", SAME, b"wc"))
        dc = dc_for(jp, [(SAME, "In English")])
        result = import_partial_mtx(jp, jp, dc)
        with self.assertRaises(ValueError):
            verify_partial_mtx(jp + b"\0", jp, dc, result)
        with self.assertRaises(ValueError):
            verify_partial_mtx(jp, jp, {**dc, "values": ["changed"]}, result)

    def test_verifier_rejects_changed_fallback_even_with_updated_output_hash(self) -> None:
        jp = script(region(b"r", SAME, b"wc"), region(b"r", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "In English")])
        result = import_partial_mtx(jp, jp, dc)
        changed = result.data.replace(ORIGINAL, DIFFERENT)
        tampered = replace(result, data=changed, output_sha256=sha256(changed).hexdigest())

        with self.assertRaises(ValueError):
            verify_partial_mtx(jp, jp, dc, tampered)

    def test_verifier_rejects_pointer_changes_with_unchanged_payload(self) -> None:
        jp = script(region(b"r", SAME, b"wc"), region(b"r", ORIGINAL, b"wc"))
        dc = dc_for(jp, [(SAME, "In English")])
        result = import_partial_mtx(jp, jp, dc)
        changed = result.data[:2] + b"\0\0" + result.data[4:]
        tampered = replace(result, data=changed, output_sha256=sha256(changed).hexdigest())

        with self.assertRaises(ValueError):
            verify_partial_mtx(jp, jp, dc, tampered)


if __name__ == "__main__":
    unittest.main()
