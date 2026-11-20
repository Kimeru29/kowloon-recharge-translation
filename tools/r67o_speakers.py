"""Localize only ADV speaker headers with bidirectional official provenance."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

from tools.localization import encode_ps2_english
from tools.mtx import MtxFile, MtxReplacement
from tools.r67_chamber_story_text_only import Assembly, ELF_BIAS, _i, _jal, _r
from tools.r67_15h_item_layout import (
    APPEND_FILE_OFFSET, APPEND_RESERVE, APPEND_VA, _validate_translation_load,
)
from tools.r67n_partial import _Source, _entries, _groups


SOURCE_SHA256 = "0d5ace47c618c8c9af92f76aecad72dd0da2c4f7588410d2f9d866458a8f38bb"
CALLS = ((0x2506BC, 0x256470), (0x2506E4, 0x256650))
JP_TAG = re.compile(r"【[^【】\x00-\x7f]+】")
EN_TAG = re.compile(r"【[^【】()\x00-\x1f\x7f]+】")
OPEN, CLOSE = ("【".encode("cp932"), "】".encode("cp932"))
MAX_TAG_BYTES = 100
SAFE_BODY_BYTES = 28
PT_LOAD_SIZE = 0x64
GLYPH_NORMALIZER = 0x677480
GLYPH_NORMALIZER_ROWS = 24


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


@dataclass(frozen=True)
class Speaker:
    japanese: str
    english: str
    original: bytes
    localized: bytes
    proofs: tuple[dict, ...]


@dataclass(frozen=True)
class SpeakerCorpus:
    speakers: tuple[Speaker, ...]
    excluded: dict[str, dict]
    source_inventory: dict


def load_corpus(ps4_adv: Path) -> SpeakerCorpus:
    proofs = defaultdict(list)
    failed = []
    inventory = []
    for jp in sorted(ps4_adv.rglob("*.MTX")):
        dc = jp.parent / "EN" / (jp.stem + "DC.json")
        if not dc.is_file():
            continue
        raw, dc_bytes = jp.read_bytes(), dc.read_bytes()
        jp_path, dc_path = (path.relative_to(ps4_adv).as_posix() for path in (jp, dc))
        owners = {"mtx": jp_path, "mtx_sha256": _digest(raw),
                  "dc": dc_path, "dc_sha256": _digest(dc_bytes)}
        inventory.append(owners)
        try:
            source = _Source(raw)
            groups = _groups(source, _entries(json.loads(dc_bytes)))
        except (ValueError, UnicodeError) as error:
            failed.append({"mtx": jp_path, "error": str(error)})
            continue
        for group in groups:
            segment = raw[group.start:group.end]
            try:
                jp_label = segment.decode("cp932")
            except UnicodeDecodeError:
                continue
            region = source.at(group.start)
            if (not JP_TAG.fullmatch(jp_label)
                    or group.start not in source.boundaries or group.end + 1 not in source.boundaries
                    or group.end >= region.end or raw[group.end:group.end + 1] != b"r"):
                continue
            en_label = re.sub(r" +", " ", group.lines[0]) if len(group.lines) == 1 else ""
            safe = bool(EN_TAG.fullmatch(en_label) and
                        not any("\u3040" <= char <= "\u9fff" for char in en_label))
            proof = {**owners, "keys": group.ids, "source_span": [group.start, group.end],
                     "source_span_sha256": _digest(segment),
                     "official_rows_sha256": _digest(json.dumps(group.lines, ensure_ascii=False).encode())}
            proofs[jp_label].append((en_label if safe else None, proof))
    if not inventory:
        raise ValueError("no official ADV/DC owners found")

    excluded, candidates, reverse = {}, {}, defaultdict(list)
    for japanese, rows in sorted(proofs.items()):
        values = {english for english, _ in rows}
        if len(values) != 1 or None in values:
            excluded[japanese] = {"reason": "conflicting_or_nonheader_official_rows",
                                  "official_labels": sorted(value for value in values if value),
                                  "proofs": [proof for _, proof in rows]}
            continue
        english = next(iter(values))
        original, localized = japanese.encode("cp932"), encode_ps2_english(english)
        _validate_pair(original, localized)
        candidates[japanese] = Speaker(japanese, english, original, localized, tuple(proof for _, proof in rows))
        reverse[localized].append(japanese)
    for aliases in reverse.values():
        if len(aliases) > 1:
            for japanese in aliases:
                speaker = candidates.pop(japanese)
                excluded[japanese] = {"reason": "ambiguous_english_reverse", "english": speaker.english,
                                      "competing_japanese": aliases, "proofs": speaker.proofs}
    return SpeakerCorpus(tuple(candidates.values()), excluded, {
        "source_files": len(inventory), "ignored_geometry": failed,
        "inventory_sha256": _digest(json.dumps(inventory, sort_keys=True).encode()),
    })


def _validate_pair(original: bytes, localized: bytes) -> None:
    for data, capacity in ((original, SAFE_BODY_BYTES + 4), (localized, MAX_TAG_BYTES)):
        if (not 4 < len(data) <= capacity or not data.startswith(OPEN) or not data.endswith(CLOSE)
                or data.decode("cp932").encode("cp932") != data
                or len(data.decode("cp932")) * 2 != len(data)
                or OPEN in data[2:-2] or CLOSE in data[2:-2] or b"\0" in data):
            raise ValueError("speaker tag exceeds native capacity or is invalid CP932")


def _jump(address: int) -> int:
    return _jal(address) ^ (1 << 26)


def _normalized_tag(tag: bytes, substitutions: dict[bytes, bytes]) -> bytes:
    return b"".join(substitutions.get(tag[index:index + 2], tag[index:index + 2])
                    for index in range(0, len(tag), 2))


def _glyph_substitutions(source: bytes) -> dict[bytes, bytes]:
    original = GLYPH_NORMALIZER - ELF_BIAS
    words = struct.unpack_from(f"<{2 * GLYPH_NORMALIZER_ROWS}I", source, original)
    glyphs = []
    for address in words:
        offset = address - ELF_BIAS
        if not 0 <= offset < APPEND_FILE_OFFSET - 2 or source[offset + 2]:
            raise ValueError("stock ADV normalization glyph drift")
        glyphs.append(source[offset:offset + 2])
    symbols = dict(zip(glyphs[:GLYPH_NORMALIZER_ROWS], glyphs[GLYPH_NORMALIZER_ROWS:], strict=True))
    if len(symbols) != GLYPH_NORMALIZER_ROWS:
        raise ValueError("stock ADV normalization inputs have duplicate glyphs")
    return symbols


def _native_payload(base: int, speakers: tuple[Speaker, ...], substitutions: dict[bytes, bytes]) -> tuple[bytes, tuple[int, int], int]:
    """Emit a frameless EE bridge, a bounded reverse table, and exact JP tags."""
    if not speakers or len(speakers) >= 0x8000:
        raise ValueError("invalid reverse speaker table length")
    rows = sorted(speakers, key=lambda speaker: speaker.localized)
    if len({row.localized for row in rows}) != len(rows) or len({row.original for row in rows}) != len(rows):
        raise ValueError("reverse speaker table must be bidirectionally unique")
    if {row.localized for row in rows} & {row.original for row in rows}:
        raise ValueError("English and Japanese speaker namespaces overlap")
    for row in rows:
        _validate_pair(row.original, row.localized)
        _validate_pair(_normalized_tag(row.original, substitutions), row.localized)
        if _normalized_tag(row.localized, substitutions) != row.localized:
            raise ValueError("stock ADV normalizer alters a localized speaker tag")

    m = Assembly()

    def imm(op, source, target, value):
        m.emit(_i(op, source, target, value))

    def branch(op, first, second, label):
        m.branch(op, first, second, label)
        m.emit(0)

    zero, v0, a0, ra = 0, 2, 4, 31
    t0, t1, t2, t3, t4, t5, t6, t7, t9 = 8, 9, 10, 11, 12, 13, 14, 15, 25
    entries = []
    # Both call owners supply a0 and have a nop delay slot. Only caller-saved
    # GPRs are used. The original lookup sees the owner's original return address.
    for _, stock in CALLS:
        entries.append(base + len(m.words) * 4)
        m.const(t9, stock)
        branch(4, zero, zero, "scan_header")
    m.label("scan_header")
    branch(4, a0, zero, "unknown")
    imm(36, a0, t2, 0)       # lbu t2, 0(a0)
    imm(9, zero, t3, OPEN[0])
    branch(5, t2, t3, "unknown")
    imm(36, a0, t2, 1)
    imm(9, zero, t3, OPEN[1])
    branch(5, t2, t3, "unknown")
    imm(9, a0, t0, 2)      # pointer to first body byte
    imm(9, zero, t1, MAX_TAG_BYTES - 2)
    m.label("scan_body")
    imm(11, t1, t4, 2)
    branch(5, t4, zero, "unknown")
    imm(36, t0, t2, 0)
    imm(11, t2, t4, 0x20)
    branch(5, t4, zero, "unknown")
    imm(11, t2, t4, 0x7F)
    branch(5, t4, zero, "one_byte")
    imm(11, t2, t4, 0x81)
    branch(5, t4, zero, "unknown")
    imm(11, t2, t4, 0xA0)
    branch(5, t4, zero, "pair")
    imm(11, t2, t4, 0xA1)
    branch(5, t4, zero, "unknown")
    imm(11, t2, t4, 0xE0)
    branch(5, t4, zero, "one_byte")   # CP932 half-width kana
    imm(11, t2, t4, 0xFD)
    branch(4, t4, zero, "unknown")
    m.label("pair")
    imm(36, t0, t3, 1)
    imm(11, t3, t4, 0x40)
    branch(5, t4, zero, "unknown")
    imm(9, zero, t4, 0x7F)
    branch(4, t3, t4, "unknown")
    imm(11, t3, t4, 0xFD)
    branch(4, t4, zero, "unknown")
    imm(9, zero, t4, OPEN[0])
    branch(5, t2, t4, "next_pair")
    imm(9, zero, t4, OPEN[1])
    branch(4, t3, t4, "unknown")
    imm(9, zero, t4, CLOSE[1])
    branch(4, t3, t4, "close")
    m.label("next_pair")
    imm(9, t0, t0, 1)
    imm(9, t1, t1, -1)
    m.label("one_byte")
    imm(9, t0, t0, 1)
    imm(9, t1, t1, -1)
    branch(4, zero, zero, "scan_body")

    m.label("close")
    imm(36, t0, t2, 2)
    branch(5, t2, zero, "unknown")
    m.emit(_r(t0, a0, t6, 0, 0x23))  # subu t6, t0, a0
    imm(9, t6, t6, -2)              # stripped body byte length
    branch(4, t6, zero, "unknown")
    table_slot = len(m.words)
    m.emit(0)
    m.emit(0)
    imm(9, zero, t1, len(rows))
    m.label("entry")
    imm(35, t0, t7, 0)
    imm(9, a0, t2, 0)
    imm(9, t7, t3, 0)
    m.label("compare")
    imm(36, t2, t4, 0)
    imm(36, t3, t5, 0)
    branch(5, t4, t5, "next_entry")
    branch(4, t4, zero, "match")
    imm(9, t2, t2, 1)
    imm(9, t3, t3, 1)
    branch(4, zero, zero, "compare")
    m.label("next_entry")
    imm(9, t0, t0, 8)
    imm(9, t1, t1, -1)
    branch(5, t1, zero, "entry")
    imm(11, t6, t4, SAFE_BODY_BYTES + 1)
    branch(4, t4, zero, "unknown")
    branch(4, zero, zero, "stock")
    m.label("match")
    imm(35, t0, a0, 4)
    m.label("stock")
    m.emit(_r(t9, zero, zero, 0, 8))
    m.emit(0)
    m.label("unknown")
    imm(9, zero, v0, -1)
    m.emit(_r(ra, zero, zero, 0, 8))
    m.emit(0)

    table = base + len(m.words) * 4
    m.words[table_slot:table_slot + 2] = [_i(15, zero, t0, table >> 16), _i(13, t0, t0, table & 0xFFFF)]
    table_data, strings = bytearray(), bytearray()
    string_base = table + 8 * len(rows)
    for row in rows:
        localized = string_base + len(strings)
        strings += row.localized + b"\0"
        original = string_base + len(strings)
        strings += _normalized_tag(row.original, substitutions) + b"\0"
        table_data += struct.pack("<II", localized, original)
    return m.done() + table_data + strings, tuple(entries), table


def build(source: bytes, corpus: SpeakerCorpus, *, base_elf: bytes | None = None,
          choice_report: dict | None = None) -> tuple[bytes, dict]:
    """Append the dictionary and patch only the speaker-owned native calls."""
    _validate_translation_load(source)
    if _digest(source) != SOURCE_SHA256:
        if (base_elf is None or _digest(base_elf) != SOURCE_SHA256
                or choice_report is None or choice_report.get("result_sha256") != _digest(source)):
            raise ValueError("speaker source must be pinned n or its audited choice build")
        from tools.r67o_choices import OWNER_CALLS
        valid_offsets = {offset for owner in (PT_LOAD_SIZE, *(site - ELF_BIAS for site in OWNER_CALLS))
                         for offset in range(owner, owner + 4)}
        if (choice_report.get("source_sha256") != SOURCE_SHA256
                or choice_report.get("appended_extent") != [len(base_elf), len(source)]
                or len(source) <= len(base_elf)
                or any(i not in valid_offsets for i, pair in enumerate(zip(base_elf, source)) if pair[0] != pair[1])):
            raise ValueError("choice build changed bytes outside its audited ownership")
    if struct.unpack_from("<II", source, PT_LOAD_SIZE) != (len(source) - APPEND_FILE_OFFSET, APPEND_RESERVE):
        raise ValueError("speaker translation PT_LOAD header preimage changed")
    out = bytearray(source)
    out.extend(bytes(-len(out) % 16))
    address = APPEND_VA + len(out) - APPEND_FILE_OFFSET
    substitutions = _glyph_substitutions(source)
    payload, targets, table = _native_payload(address, corpus.speakers, substitutions)
    out.extend(payload)
    if len(out) - APPEND_FILE_OFFSET > APPEND_RESERVE:
        raise ValueError("speaker translations exceed the reserved ELF extent")
    call_sites = []
    for (site, stock), target in zip(CALLS, targets, strict=True):
        offset = site - ELF_BIAS
        if struct.unpack_from("<II", source, offset) != (_jal(stock), 0):
            raise ValueError(f"speaker call owner preimage drift at {site:#x}")
        struct.pack_into("<I", out, offset, _jal(target))
        call_sites.append({"address": site, "file_offset": offset, "stock_target": stock, "target": target,
                           "expected": source[offset:offset + 4].hex(), "replacement": out[offset:offset + 4].hex()})
    struct.pack_into("<I", out, PT_LOAD_SIZE, len(out) - APPEND_FILE_OFFSET)
    return bytes(out), {
        "source_sha256": _digest(source), "result_sha256": _digest(out),
        "call_sites": call_sites,
        "load_size": {"file_offset": PT_LOAD_SIZE, "expected": source[PT_LOAD_SIZE:PT_LOAD_SIZE + 4].hex(),
                      "replacement": out[PT_LOAD_SIZE:PT_LOAD_SIZE + 4].hex()},
        "allowed_existing_ranges": [[offset, offset + 4]
                                    for offset in (PT_LOAD_SIZE, *(site - ELF_BIAS for site, _ in CALLS))],
        "appended_extent": [len(source), len(out)], "appended_sha256": _digest(out[len(source):]),
        "translation_reserve": APPEND_RESERVE,
        "reverse_table_address": table, "reverse_table_rows": len(corpus.speakers),
        "normalizer_table_address": GLYPH_NORMALIZER,
        "normalizer_table_sha256": _digest(b"".join(before + after for before, after in substitutions.items())),
    }


# Conservative subset of ADV command runs observed before verified native
# speaker dispatch. Unrecognized runs are reported, including plain line
# breaks and display-name controls inside the body of a message.
_CONTROL_RUN = re.compile(
    rb"(?:wc|entry|dialog[0-9]+|ds[0-9]+s[0-9]+|"
    rb"(?:vo|ci|co|bi|bo|ch|bg|vt|mr|mi|mo|sbr|se|sbi|sbo|bk|w)[0-9]+|bn|n|})+"
)
_HEADER_END = re.compile(rb"r(?:px|l)?(?=[\x81-\x9f\xe0-\xfc])")


def _dispatch_boundary(source: _Source, region, start: int) -> tuple[str, bytes] | None:
    if start == region.start:
        return "pointer_start", b""
    left = start
    while left > region.start and left - 1 in source.boundaries and source.raw[left - 1] < 0x80:
        left -= 1
    control = source.raw[left:start]
    if not _CONTROL_RUN.fullmatch(control):
        return None
    if left == region.start:
        return "initial_commands", control
    if b"wc" in control:
        return "page_flush", control
    return None


def patch_script(raw: bytes, corpus: SpeakerCorpus) -> tuple[bytes, dict]:
    """Project fixed, source-proven labels and check all other bytes by region."""
    source = _Source(raw)
    by_label = {row.original: row for row in corpus.speakers}
    replacements_by_slot = defaultdict(list)
    unresolved = []
    for region in source.regions:
        cursor = region.start
        while (start := raw.find(OPEN, cursor, region.end)) != -1:
            cursor = start + len(OPEN)
            if start not in source.boundaries:
                continue
            close = raw.find(CLOSE, cursor, min(region.end, start + MAX_TAG_BYTES))
            if close == -1 or close not in source.boundaries:
                continue
            end = close + len(CLOSE)
            if not _HEADER_END.match(raw, end, region.end):
                continue
            try:
                japanese = raw[start:end].decode("cp932")
            except UnicodeDecodeError:
                continue
            if not JP_TAG.fullmatch(japanese):
                continue
            speaker = by_label.get(raw[start:end])
            boundary = _dispatch_boundary(source, region, start)
            if speaker is None or boundary is None:
                if speaker is not None or boundary is not None:
                    excluded = corpus.excluded.get(japanese)
                    reason = ("unproven_dispatch_boundary" if boundary is None else
                              excluded["reason"] if excluded else "no_official_header_proof")
                    unresolved.append({"japanese": japanese, "input_span": [start, end],
                                       "pointer_slots": region.slots, "reason": reason})
                continue
            replacements_by_slot[region.slots].append((MtxReplacement(start, end, speaker.localized), speaker, boundary))

    replacements = tuple(replacement for rows in replacements_by_slot.values() for replacement, _, _ in rows)
    last = source.regions[-1]
    terminal_unaligned = bool(replacements and not raw[last.start:last.end].rstrip(b"\0").endswith(b"_"))
    if terminal_unaligned:
        # Last region's start is pointer-aligned; it has no following pointer
        # requiring alignment. Retain its original native EOF, including wc-only
        # endings, and let the standard writer relocate every pointer.
        prefix = MtxFile.parse(raw[:last.start])
        output = prefix.apply_replacements(tuple(r for r in replacements if r.start < last.start)).compile()
        tail, cursor = bytearray(), last.start
        for replacement, _, _ in replacements_by_slot[last.slots]:
            tail.extend(raw[cursor:replacement.start])
            tail.extend(replacement.data)
            cursor = replacement.end
        tail.extend(raw[cursor:last.end])
        output += tail
    else:
        output = source.mtx.apply_replacements(replacements).compile()
    projected = _Source(output)
    if (projected.by_slots.keys() != source.by_slots.keys()
            or len(projected.mtx.pointer_words) != len(source.mtx.pointer_words)
            or tuple(not offset for offset in projected.mtx.pointer_words) !=
               tuple(not offset for offset in source.mtx.pointer_words)):
        raise ValueError("speaker projection changed pointer slot aliases or zero slots")
    if len(source.regions) != len(projected.regions):
        raise ValueError("speaker projection changed pointer region count")

    occurrences, region_evidence = [], []
    for before, after in zip(source.regions, projected.regions, strict=True):
        if before.slots != after.slots:
            raise ValueError("speaker projection changed pointer order")
        rows = replacements_by_slot[before.slots]
        expected = bytearray()
        cursor = before.start
        for replacement, speaker, (boundary_kind, controls) in rows:
            start, end = replacement.start, replacement.end
            expected.extend(raw[cursor:start])
            out_start = after.start + len(expected)
            expected.extend(replacement.data)
            occurrences.append({"japanese": speaker.japanese, "english": speaker.english,
                                "official_proof_id": _digest(speaker.original),
                                "input_span": [start, end], "output_span": [out_start, out_start + len(replacement.data)],
                                "input_span_sha256": _digest(raw[start:end]), "output_span_sha256": _digest(replacement.data),
                                "pointer_slots": before.slots, "boundary": boundary_kind, "control_hex": controls.hex(),
                                "cells": len(speaker.localized) // 2})
            cursor = end
        expected.extend(raw[cursor:before.end])
        padding = (-len(expected)) % 4 if replacements and not (terminal_unaligned and before == last) else 0
        if padding and not raw[before.start:before.end].rstrip(b"\0").endswith(b"_"):
            raise ValueError("speaker projection introduced padding without a native terminator")
        expected.extend(bytes(padding))
        actual = output[after.start:after.end]
        if expected != actual:
            raise ValueError("speaker projection changed bytes outside selected spans or alignment")
        if rows or padding or before.start != after.start:
            region_evidence.append({"slots": before.slots, "input_span": [before.start, before.end],
                                    "output_span": [after.start, after.end], "alignment_nul_added": padding,
                                    "input_sha256": _digest(raw[before.start:before.end]), "output_sha256": _digest(actual)})
    return output, {"input_sha256": _digest(raw), "output_sha256": _digest(output),
                    "occurrences": occurrences, "unresolved": unresolved, "regions": region_evidence}


def emit_overlay(source: bytes, baseline: bytes, corpus: SpeakerCorpus, script_root: Path,
                 script_provenance: Path, output_dir: Path, *, choice_report: dict | None = None) -> dict:
    """Require exact staged owners and verify native semantics before writing."""
    from collections import Counter

    from tests.test_r67o_speakers_native import verify_native

    if output_dir.exists():
        raise ValueError(f"speaker output already exists: {output_dir}")
    provenance = script_provenance.read_bytes()
    manifest = json.loads(provenance)
    if manifest.get("baseline_iso_sha256") != "c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0":
        raise ValueError("expected the exact n ISO in staged ADV provenance")
    inputs = {path.relative_to(script_root).as_posix(): path for path in script_root.rglob("*.MTX")}
    if not inputs or inputs.keys() != manifest["files"].keys():
        raise ValueError("speaker script input inventory differs from staged ADV provenance")
    patched, elf = build(source, corpus, base_elf=baseline, choice_report=choice_report)
    proof = verify_native(baseline, patched, corpus, elf)
    immutable, changed_files, unresolved = {}, {}, {}
    boundary_counts, unresolved_counts = Counter(), Counter()
    staged = {}
    for name, path in sorted(inputs.items()):
        original = path.read_bytes()
        expected = manifest["files"][name]["input_sha256"]
        if _digest(original) != expected:
            raise ValueError(f"speaker script input drift: {name}")
        data, evidence = patch_script(original, corpus)
        held = evidence.pop("unresolved")
        if held:
            unresolved[name] = held
            unresolved_counts.update(row["reason"] for row in held)
        if not evidence["occurrences"]:
            immutable[name] = expected
            continue
        staged[name] = data
        changed_files[name] = evidence
        for item in evidence["occurrences"]:
            boundary_counts[item["boundary"]] += 1
            native = proof["identities"][item["official_proof_id"]]
            item["stock_actor"] = native["stock_actor"]
            item["stock_alias_column"] = native["stock_alias_column"]
            item["native_japanese_sha256"] = native["native_japanese_sha256"]
    if not staged:
        raise ValueError("no native speaker headers were proven in the staged scripts")
    max_japanese_cells = max(len(row.original) // 2 for row in corpus.speakers)
    report = {
        "baseline_iso_sha256": manifest["baseline_iso_sha256"],
        "script_provenance_sha256": _digest(provenance),
        "script_inputs": len(inputs),
        "script_files": changed_files,
        "unchanged_input_sha256": immutable,
        "unresolved": unresolved,
        "summary": {
            "changed_files": len(staged), "occurrences": boundary_counts.total(),
            "dispatch_boundaries": dict(boundary_counts), "unresolved_roles": dict(unresolved_counts),
            "proven_reverse_pairs": len(corpus.speakers),
        },
        "official_source_inventory": corpus.source_inventory,
        "official_labels": {
            _digest(row.original): {"japanese": row.japanese, "english": row.english,
                                    "japanese_sha256": _digest(row.original), "english_sha256": _digest(row.localized),
                                    "ps4_dc": row.proofs}
            for row in corpus.speakers
        },
        "excluded_labels": corpus.excluded,
        "native": {**elf, "proof": proof},
        "header_layout_review": {
            "longest_cells": max(len(row.localized) // 2 for row in corpus.speakers),
            "largest_original_tag_cells": max_japanese_cells,
            "labels_longer_than_any_original_tag": {
                row.english: len(row.localized) // 2
                for row in corpus.speakers if len(row.localized) // 2 > max_japanese_cells
            },
        },
        "runtime_verified": False,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    for name, data in staged.items():
        destination = output_dir / "overlay" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    (output_dir / "patched.elf").write_bytes(patched)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("elf", "ps4-adv", "script-root", "script-provenance", "output-dir"):
        parser.add_argument("--" + option, type=Path, required=True)
    parser.add_argument("--base-elf", type=Path)
    parser.add_argument("--choice-report", type=Path)
    args = parser.parse_args()
    if bool(args.base_elf) != bool(args.choice_report):
        parser.error("--base-elf and --choice-report must be supplied together")
    source = args.elf.read_bytes()
    baseline = args.base_elf.read_bytes() if args.base_elf else source
    choice_report = json.loads(args.choice_report.read_bytes()) if args.choice_report else None
    corpus = load_corpus(args.ps4_adv)
    if corpus.source_inventory["inventory_sha256"] != "f38752ba7a226246ad120205c7ada10dc2d878275bc4395bfdbfdde32397feae":
        raise ValueError("official PS4 speaker source inventory drift")
    report = emit_overlay(source, baseline, corpus, args.script_root, args.script_provenance, args.output_dir,
                          choice_report=choice_report)
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
