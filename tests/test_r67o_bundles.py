from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import struct
import unittest

from tools.mtx import MtxFile, MtxReplacement
from tools.r67n_partial import (
    _Change, _Group, _Match, _Source, _dc_digest, _entries, _groups, import_partial_mtx,
)
from tools.r67n_partial_corpus import _record
from tools.r67o_bundles import (
    Anchor, BundleMatch, BundleScope, _approved_omission, _audit_output, _prove_bundles, apply_bundle_delta,
)


A = "朝市".encode("cp932")
B = "昼食".encode("cp932")
C = "夕立".encode("cp932")
D = "夜風".encode("cp932")
CP932 = "cp932"


def region(*parts: bytes, terminator: bytes = b"_") -> bytes:
    body = b"".join(parts) + terminator
    return body + b"\0" * (-len(body) % 4)


def page(*items: bytes, opener: bytes = b"r", terminator: bytes = b"_") -> bytes:
    return region(opener, b"wcr".join(items), b"wc", terminator=terminator)


def script(first: bytes, last: bytes | None = None) -> bytes:
    return struct.pack("<4H", 2, 2, (8 + len(first)) // 4 if last is not None else 0, 0) + first + (last or b"")


def keys_for(raw: bytes, items: tuple[bytes, ...]) -> list[int]:
    end = 8
    starts = []
    for item in items:
        start = raw.index(item, end)
        starts.append(start)
        end = start + len(item)
    return starts


def discover(ps2: bytes, ps4: bytes, items: tuple[bytes, ...],
             pending: tuple[int, ...], anchor_positions: tuple[tuple[int, int], ...] = ()):
    source2, source4 = _Source(ps2), _Source(ps4)
    keys = keys_for(ps4, items)
    groups = _groups(source4, _entries({"keys": keys, "values": ["Text"] * len(keys)}))
    anchors = tuple(
        Anchor(groups[index].ids, groups[index].start, groups[index].end,
               target, target + len(items[index]), source4.at(groups[index].start).slots)
        for index, target in anchor_positions
    )
    proven, failures = _prove_bundles(source2, source4, groups, anchors, {keys[i] for i in pending})
    return keys, proven, failures


def baseline(ps2: bytes, ps4: bytes, items: tuple[bytes, ...],
             values: tuple[str, ...], unresolved: tuple[int, ...]):
    relative = Path("MS/MS13_02.MTX")
    dc_relative = Path("MS/EN/MS13_02DC.json")
    dc = {"keys": keys_for(ps4, items), "values": list(values)}
    dc_raw = json.dumps(dc).encode()
    before_values = [value if index not in unresolved else "(punknown)"
                     for index, value in enumerate(values)]
    before = import_partial_mtx(ps2, ps4, {"keys": dc["keys"], "values": before_values})
    record = _record(relative, dc_relative, ps2, ps4, dc_raw, dc,
                     replace(before, dc_sha256=_dc_digest(dc)))
    return relative, dc_raw, before.data, record


class BundleProofTests(unittest.TestCase):
    def test_exact_joint_text_and_native_gaps_identify_the_repeated_text(self):
        ps4 = script(page(A, B, C))
        ps2 = script(page(A, D, A, B, C))
        keys, matches, failures = discover(ps2, ps4, (A, B, C), (0,))

        self.assertEqual({}, failures)
        self.assertEqual(23, matches[keys[0]].ps2_start)
        self.assertEqual({2, 3}, {len(scope.group_starts) for scope in matches[keys[0]].scopes})

    def test_repeated_exact_context_is_ambiguous(self):
        ps4 = script(page(A, B))
        ps2 = script(page(A, B, A, B))
        keys, matches, failures = discover(ps2, ps4, (A, B), (0, 1))

        self.assertEqual({}, matches)
        self.assertEqual({key: "ambiguous_bundle_context" for key in keys}, failures)

    def test_raw_occurrence_beginning_inside_cp932_character_is_rejected(self):
        ps4 = script(page(A, B))
        ps2 = script(page(A, B, opener=b"r\x81"))
        keys, matches, failures = discover(ps2, ps4, (A, B), (0,))

        self.assertEqual({}, matches)
        self.assertEqual("no_exact_bundle", failures[keys[0]])

    def test_native_gap_change_blocks_entire_bundle(self):
        ps4 = script(region(b"r", A, b"wcr", B, b"wc"))
        ps2 = script(region(b"r", A, b"wcsr", B, b"wc"))
        keys, matches, failures = discover(ps2, ps4, (A, B), (0,))

        self.assertEqual({}, matches)
        self.assertEqual("no_exact_bundle", failures[keys[0]])

    def test_changed_speaker_prefix_blocks_entire_bundle(self):
        ps4 = script(page(A, B, opener=b"s0301r"))
        ps2 = script(page(A, B, opener=b"s0401r"))
        keys, matches, failures = discover(ps2, ps4, (A, B), (0,))

        self.assertEqual({}, matches)
        self.assertEqual("no_exact_bundle", failures[keys[0]])

    def test_pointer_alias_identity_must_match(self):
        ps4 = script(page(A, B))
        ps2 = ps4[:2] + b"\0\0" + ps4[4:]
        keys, matches, failures = discover(ps2, ps4, (A, B), (0,))

        self.assertEqual({}, matches)
        self.assertEqual("pointer_identity_mismatch", failures[keys[0]])

    def test_scope_crossing_pointer_split_is_unproven(self):
        ps4 = script(page(A, B))
        ps2 = script(page(A), page(B))
        keys, matches, failures = discover(ps2, ps4, (A, B), (1,))

        self.assertEqual({}, matches)
        self.assertEqual("no_exact_bundle", failures[keys[1]])

    def test_larger_unique_window_disagrees_with_shorter_unique_window(self):
        ps4 = script(page(D, C, A, B))
        ps2 = script(page(A, B, D, C, A, C, A))
        keys, matches, failures = discover(ps2, ps4, (D, C, A, B), (2,))

        self.assertEqual({}, matches)
        self.assertEqual("conflicting_bundle_context", failures[keys[2]])

    def test_prior_anchor_excludes_inverted_window(self):
        ps4 = script(page(A, B, C))
        ps2 = script(page(B, C, A, B))
        anchor = ps2.rindex(A)
        keys, matches, failures = discover(ps2, ps4, (A, B, C), (1,), ((0, anchor),))

        self.assertEqual({}, failures)
        self.assertEqual(30, matches[keys[1]].ps2_start)
        self.assertEqual((9,), tuple(anchor.ps4_start for anchor in matches[keys[1]].scopes[0].enclosed_anchors))

    def test_window_cannot_assign_an_enclosed_anchor_to_another_occurrence(self):
        ps4 = script(page(A, B, C))
        ps2 = script(page(A, D, A, B, C))
        keys, matches, failures = discover(ps2, ps4, (A, B, C), (1,), ((0, 9),))

        self.assertEqual({}, failures)
        self.assertEqual(30, matches[keys[1]].ps2_start)
        self.assertTrue(all(scope.ps4_start > keys[0] for scope in matches[keys[1]].scopes))

    def test_conflicting_group_claims_are_both_rejected(self):
        ps4 = script(page(A, B, A))
        ps2 = script(page(B, A, B))
        keys, matches, failures = discover(ps2, ps4, (A, B, A), (0, 2))

        self.assertEqual({}, matches)
        self.assertEqual({keys[0]: "conflicting_bundle_target",
                          keys[2]: "conflicting_bundle_target"}, failures)


class BundleDeltaTests(unittest.TestCase):
    def test_applies_only_new_ranges_and_keeps_aliases_zeros_and_unaligned_tail(self):
        ps2 = script(page(A, B), b"final tail")
        relative, dc, installed, record = baseline(ps2, ps2, (A, B), ("Earlier", "X"), (1,))

        output, report = apply_bundle_delta(relative, ps2, ps2, dc, installed, record)

        target = report["spans"][0]
        self.assertEqual((16, 26, 26), (target["ps2_start"], target["installed_start"], target["output_start"]))
        self.assertEqual((8, 8, 36, 0), MtxFile.parse(output).pointer_offsets)
        self.assertEqual(b"r" + "Ｅａｒｌｉｅｒ".encode(CP932) + b"wcr" + "Ｘ".encode(CP932)
                         + b"wc_\0\0\0\0\0final tail", output[8:])
        self.assertEqual(2, report["regions"][0]["alignment_bytes_added"])
        self.assertEqual(1, report["new_english_entries"])

    def test_unproven_alignment_emits_no_delta_for_the_region(self):
        ps2 = script(page(A, B, terminator=b"S"))
        relative, dc, installed, record = baseline(ps2, ps2, (A, B), ("Before", "X"), (0, 1))

        output, report = apply_bundle_delta(relative, ps2, ps2, dc, installed, record)

        self.assertEqual(installed, output)
        self.assertEqual({"unsafe_alignment": 2}, report["unresolved_reasons"])

    def test_changed_sources_map_or_installed_file_are_rejected_before_writes(self):
        ps2 = script(page(A, B))
        relative, dc, installed, record = baseline(ps2, ps2, (A, B), ("Earlier", "X"), (1,))
        inputs = (ps2, ps2, dc, installed)
        for index in range(len(inputs)):
            with self.subTest(index=index):
                changed = list(inputs)
                changed[index] += b" "
                with self.assertRaisesRegex(ValueError, "hash"):
                    apply_bundle_delta(relative, *changed, record)

    def test_rehashed_installed_fallback_drift_cannot_pass_the_byte_audit(self):
        ps2 = script(page(A, B))
        relative, dc, installed, record = baseline(ps2, ps2, (A, B), ("Earlier", "X"), (1,))
        changed = installed.replace(B, C)
        output_hash = sha256(changed).hexdigest()
        record["output_sha256"] = output_hash
        record["regions"][0]["output_sha256"] = sha256(changed[8:]).hexdigest()

        with self.assertRaisesRegex(ValueError, "untouched"):
            apply_bundle_delta(relative, ps2, ps2, dc, changed, record)

    def test_name_order_comes_from_official_lines(self):
        original = b"pm" + A + b"pn"
        ps2 = script(page(original, B))
        relative, dc, installed, record = baseline(ps2, ps2, (original, B), ("(pn1) (pm1)", "Text"), (0,))

        output, report = apply_bundle_delta(relative, ps2, ps2, dc, installed, record)

        span = report["spans"][0]
        self.assertEqual(b"pn" + "　".encode(CP932) + b"pm", output[span["output_start"]:span["output_end"]])

    def test_balances_name_movement_only_across_exact_same_page_runs(self):
        original = b"px" + B
        ps2 = script(region(b"r", A, b"r", original, b"wc"))
        relative, dc, installed, record = baseline(ps2, ps2, (A, original), ("(px)", "Text"), (0, 1))

        output, report = apply_bundle_delta(relative, ps2, ps2, dc, installed, record)

        self.assertEqual(2, report["new_english_entries"])
        self.assertEqual(b"rpxr", output[8:12])
        self.assertEqual((9, 14), report["spans"][0]["name_scope"])

    def test_compiler_audit_rejects_changed_native_runs_and_pointer_aliases(self):
        installed = script(page(A, B))
        replacement = MtxReplacement(16, 20, "ＡＢ".encode(CP932))
        output = installed[:16] + replacement.data + installed[20:]
        changed_gap = output[:14] + b"G" + output[15:]
        changed_alias = output[:2] + b"\0\0" + output[4:]
        with self.assertRaisesRegex(ValueError, "untouched"):
            _audit_output(_Source(installed), changed_gap, (replacement,))
        with self.assertRaisesRegex(ValueError, "pointer slots"):
            _audit_output(_Source(installed), changed_alias, (replacement,))

    def test_ms01_00_px_omission_needs_the_exact_page_and_published_speaker_anchor(self):
        path = Path("MS/MS01_00.MTX")
        speaker = bytes.fromhex("817994aa90e795e4817a")
        original = bytes.fromhex(
            "82a482ed8160814182e082b582a982b582c472707882c182c4837a8389815b8d4482ab8148"
        )
        group = _Group((33444,), 33444, 33481, ("Ah...  Are  you  a  horror  fan?",))
        change = _Change(
            group, _Match(33564, 33601, (33433, 33481), (33553, 33601)),
            (b"encoded",), ("px",), (), b"wc",
        )
        anchor = Anchor((33433,), 33433, 33443, 33553, 33563, (119,))
        scope = BundleScope(
            33433, 33481, 33553, 33601, (33433, 33444), (33433, 33444), (119,),
            sha256(speaker + b"r" + original).hexdigest(), "6473303173336369353063683030333034",
            "7763", None, (anchor,), None,
        )
        match = BundleMatch(33564, 33601, (scope,))

        self.assertTrue(_approved_omission(path, change, match, original))
        self.assertFalse(_approved_omission(path, change, match, original + b"r"))
        self.assertFalse(_approved_omission(path, change, replace(match, ps2_start=33563), original))
        self.assertFalse(_approved_omission(
            path, change, replace(match, scopes=(replace(scope, enclosed_anchors=()),)), original,
        ))

    def test_other_official_px_omission_stays_unresolved(self):
        original = b"px" + B
        ps2 = script(page(A, original))
        relative, dc, installed, record = baseline(ps2, ps2, (A, original), ("Earlier", "Text"), (1,))

        output, report = apply_bundle_delta(relative, ps2, ps2, dc, installed, record)

        self.assertEqual(installed, output)
        self.assertEqual({"unsafe_name_control": 1}, report["unresolved_reasons"])


if __name__ == "__main__":
    unittest.main()
