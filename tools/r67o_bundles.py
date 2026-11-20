"""Transfer newly proven exact official MTX bundles onto the installed r67.15n disc."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
import json
import mmap
from pathlib import Path
from typing import Any

from tools.iso9660_patch import find_record, index_iso
from tools.mtx import MtxFile, MtxReplacement
from tools.r67n_partial import (
    _Change, _Group, _Match, _Region, _Source, _dc_digest, _digest,
    _encode, _entries, _groups, _left_boundary, _name_scope, _occurrences,
    _right_delimiter, _safe_padding, _source_names, _unique_at,
)

BASELINE_ISO_SHA256 = "c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0"
BASELINE_REPORT_SHA256 = "554e548e729cb6d1b2881b53a6dee15303e1e4d007e7e6f2b147ac1da51b4899"
PATHS = tuple(Path(f"MS/{stem}.MTX") for stem in ("MS01_00", "MS06_03", "MS13_02"))
MAX_BUNDLE_GROUPS = 12

OMISSION_PATH = Path("MS/MS01_00.MTX")
OMISSION_SOURCE_SHA256 = "bb68bf7d105de51f597bf2a898486119f1951768feb954774d3dc0ad43379759"
OMISSION_SCOPE_SHA256 = "756067b8e1253b5d16f034b3a6758447835954bbf28772179c3eea64266c6505"
OMISSION_TEXT = ("Ah...  Are  you  a  horror  fan?",)
OMISSION_OWNER = {
    "dictionary_read_rva": "0x142b5e1",
    "name_processing_rva": ["0x142b92b", "0x142b941"],
    "name_processing": "Y_AdvOriginalNameChangeProc",
}


@dataclass(frozen=True)
class Anchor:
    entry_ids: tuple[int, ...]
    ps4_start: int
    ps4_end: int
    ps2_start: int
    ps2_end: int
    pointer_slots: tuple[int, ...]


@dataclass(frozen=True)
class BundleScope:
    ps4_start: int
    ps4_end: int
    ps2_start: int
    ps2_end: int
    group_starts: tuple[int, ...]
    entry_ids: tuple[int, ...]
    pointer_slots: tuple[int, ...]
    context_sha256: str
    left_control_hex: str
    right_delimiter_hex: str
    previous_anchor: Anchor | None
    enclosed_anchors: tuple[Anchor, ...]
    next_anchor: Anchor | None


@dataclass(frozen=True)
class BundleMatch:
    ps2_start: int
    ps2_end: int
    scopes: tuple[BundleScope, ...]


def _scope_for_window(ps2: _Source, ps4: _Source, r2: _Region, r4: _Region,
                      window: tuple[_Group, ...], anchors: list[Anchor]) -> tuple[BundleScope | None, str]:
    first, last = window[0], window[-1]
    left = _left_boundary(ps4, r4, first.start)
    right = _right_delimiter(ps4, last)
    if left is None or not right:
        return None, "no_exact_bundle"
    context = ps4.raw[first.start:last.end]
    occurrences = _occurrences(ps2, context, r2.start, r2.end)
    target = next(occurrences, None)
    if target is None:
        return None, "no_exact_bundle"
    if next(occurrences, None) is not None or not _unique_at(ps4, context, r4, first.start):
        return None, "ambiguous_bundle_context"
    delta = target - first.start
    target_end = last.end + delta
    if (_left_boundary(ps2, r2, target) != left
            or not ps2.raw.startswith(right, target_end, r2.end)
            or target_end + len(right) not in ps2.boundaries):
        return None, "no_exact_bundle"
    if any(offset not in ps4.boundaries or offset + delta not in ps2.boundaries
           for group in window for offset in (group.start, group.end)):
        return None, "no_exact_bundle"

    previous, following = None, None
    enclosed = []
    for anchor in anchors:
        if anchor.ps4_end <= first.start:
            if anchor.ps2_end > target:
                return None, "bundle_anchor_conflict"
            previous = anchor
        elif anchor.ps4_start >= last.end:
            if anchor.ps2_start < target_end:
                return None, "bundle_anchor_conflict"
            if following is None:
                following = anchor
        elif (first.start <= anchor.ps4_start and anchor.ps4_end <= last.end
              and anchor.ps2_start == anchor.ps4_start + delta
              and anchor.ps2_end == anchor.ps4_end + delta):
            enclosed.append(anchor)
        else:
            return None, "bundle_anchor_conflict"
    return BundleScope(
        first.start, last.end, target, target_end, tuple(group.start for group in window),
        tuple(key for group in window for key in group.ids), r4.slots, _digest(context),
        left.hex(), right.hex(), previous, tuple(enclosed), following,
    ), ""


def _prove_bundles(ps2: _Source, ps4: _Source, groups: tuple[_Group, ...],
                   anchors: tuple[Anchor, ...], pending: set[int]) -> tuple[dict[int, BundleMatch], dict[int, str]]:
    """Evaluate every bounded, adjacent window before attributing a target."""
    anchors_by_slot: dict[tuple[int, ...], list[Anchor]] = defaultdict(list)
    for anchor in sorted(anchors, key=lambda item: item.ps4_start):
        anchors_by_slot[anchor.pointer_slots].append(anchor)

    proofs: dict[int, list[BundleScope]] = defaultdict(list)
    failures_seen: dict[int, set[str]] = defaultdict(set)
    for index, first in enumerate(groups):
        r4 = ps4.at(first.start)
        r2 = ps2.by_slots.get(r4.slots)
        if r2 is None:
            failures_seen[first.start].add("pointer_identity_mismatch")
            continue
        for stop in range(index + 2, min(index + MAX_BUNDLE_GROUPS, len(groups)) + 1):
            last = groups[stop - 1]
            if last.start >= r4.end or last.end > r4.end:
                break
            window = groups[index:stop]
            affected = tuple(group.start for group in window if group.start in pending)
            if not affected:
                continue
            scope, reason = _scope_for_window(ps2, ps4, r2, r4, window, anchors_by_slot[r4.slots])
            for start in affected:
                if scope is not None:
                    proofs[start].append(scope)
                else:
                    failures_seen[start].add(reason)

    matches, unresolved = {}, {}
    for group in groups:
        if group.start not in pending:
            continue
        scopes = tuple(proofs[group.start])
        if not scopes:
            # Keep the strongest specific failure for diagnostic follow-up.
            unresolved[group.start] = next(
                (reason for reason in ("pointer_identity_mismatch", "bundle_anchor_conflict",
                                       "ambiguous_bundle_context")
                 if reason in failures_seen[group.start]), "no_exact_bundle"
            )
            continue
        targets = {scope.ps2_start + group.start - scope.ps4_start for scope in scopes}
        if len(targets) != 1:
            unresolved[group.start] = "conflicting_bundle_context"
            continue
        target = next(iter(targets))
        matches[group.start] = BundleMatch(target, target + group.end - group.start, scopes)

    # Reject all overlapping or inverted claimants, including claims that
    # would subsequently fail English encoding.
    ordered = sorted(matches)
    for index, start in enumerate(ordered):
        for other in ordered[index + 1:]:
            if matches[start].ps2_end > matches[other].ps2_start:
                unresolved[start] = unresolved[other] = "conflicting_bundle_target"
    for start in unresolved:
        matches.pop(start, None)
    return matches, unresolved


def _read_baseline(ps2: _Source, ps4: _Source, installed: _Source, groups: tuple[_Group, ...],
                   record: dict[str, Any]) -> tuple[Anchor, ...]:
    """Verify pinned baseline report coordinates against source and installed bytes."""
    group_by_start = {group.start: group for group in groups}
    seen = set()
    spans_by_slot: dict[tuple[int, ...], list[dict]] = defaultdict(list)
    anchors_by_slot: dict[tuple[int, ...], list[Anchor]] = defaultdict(list)
    for span in sorted(record["spans"], key=lambda item: item["ps4_start"]):
        group = group_by_start[span["ps4_start"]]
        start, end = span["ps2_start"], span["ps2_end"]
        r4 = ps4.at(group.start)
        slots = tuple(span["pointer_slots"])
        r2 = ps2.by_slots[slots]
        original = ps2.raw[start:end]
        if (group.start in seen or tuple(span["entry_ids"]) != group.ids
                or span["ps4_end"] != group.end or group.end > r4.end
                or r4.slots != slots or not (r2.start <= start < end <= r2.end)
                or [r2.start, r2.end] != list(span["ps2_region"])
                or [r4.start, r4.end] != list(span["ps4_region"])
                or original != ps4.raw[group.start:group.end]
                or _digest(original) != span["original_sha256"]):
            raise ValueError("Baseline anchor identity differs from the source bytes")
        anchors = anchors_by_slot[slots]
        if anchors and (anchors[-1].ps4_end > group.start or anchors[-1].ps2_end > start):
            raise ValueError("Baseline anchors overlap or invert within a pointer region")
        anchors.append(Anchor(group.ids, group.start, group.end, start, end, slots))
        spans_by_slot[slots].append(span)
        seen.add(group.start)

    for row in record["unresolved"]:
        group = group_by_start[row["ps4_start"]]
        if (group.start in seen or tuple(row["entry_ids"]) != group.ids or row["ps4_end"] != group.end
                or row["ps4_span_sha256"] != _digest(ps4.raw[group.start:group.end])):
            raise ValueError("Baseline unresolved group differs from the source")
        seen.add(group.start)
    if seen != set(group_by_start):
        raise ValueError("Baseline report does not account for every official group")

    if len(ps2.regions) != len(installed.regions) or len(record["regions"]) != len(ps2.regions):
        raise ValueError("Baseline region inventory drift")
    for old, new, row in zip(ps2.regions, installed.regions, record["regions"], strict=True):
        if (old.slots != new.slots or tuple(row["pointer_slots"]) != old.slots
                or (row["ps2_start"], row["ps2_end"]) != (old.start, old.end)
                or (row["output_start"], row["output_end"]) != (new.start, new.end)
                or row["ps2_sha256"] != _digest(ps2.raw[old.start:old.end])
                or row["output_sha256"] != _digest(installed.raw[new.start:new.end])):
            raise ValueError("Baseline pointer region or hash drift")
        source_cursor, installed_cursor = old.start, new.start
        for span in spans_by_slot[old.slots]:
            unchanged = ps2.raw[source_cursor:span["ps2_start"]]
            start, end = span["output_start"], span["output_end"]
            if (installed.raw[installed_cursor:start] != unchanged
                    or not (installed_cursor <= start <= end <= new.end)):
                raise ValueError("Baseline installed untouched bytes drift")
            if _digest(installed.raw[start:end]) != span["replacement_sha256"]:
                raise ValueError("Baseline installed translation hash drift")
            source_cursor, installed_cursor = span["ps2_end"], end
        unchanged = ps2.raw[source_cursor:old.end]
        padding = row["alignment_bytes_added"]
        if (not 0 <= padding <= 3 or padding and not _safe_padding(ps2, old)
                or installed.raw[installed_cursor:new.end] != unchanged + b"\0" * padding):
            raise ValueError("Baseline installed untouched suffix or alignment drift")
    return tuple(anchor for rows in anchors_by_slot.values() for anchor in rows)


def _approved_omission(path: Path, change: _Change, match: BundleMatch, original: bytes) -> bool:
    return (
        path == OMISSION_PATH
        and change.group.ids == (33444,)
        and (change.group.start, change.group.end) == (33444, 33481)
        and (match.ps2_start, match.ps2_end) == (33564, 33601)
        and change.group.lines == OMISSION_TEXT
        and change.source_names == ("px",) and not change.names
        and change.delimiter == b"wc" and _digest(original) == OMISSION_SOURCE_SHA256
        and any((scope.ps4_start, scope.ps4_end) == (33433, 33481)
                and (scope.ps2_start, scope.ps2_end) == (33553, 33601)
                and scope.pointer_slots == (119,)
                and scope.group_starts == (33433, 33444)
                and Anchor((33433,), 33433, 33443, 33553, 33563, (119,)) in scope.enclosed_anchors
                and scope.context_sha256 == OMISSION_SCOPE_SHA256
                and scope.right_delimiter_hex == "7763" for scope in match.scopes)
    )


def _installed_range(ps2: _Source, installed: _Source, change: _Change,
                     baseline_spans: list[dict]) -> MtxReplacement:
    match = change.match
    original = ps2.at(match.start)
    target = installed.by_slots[original.slots]
    shift = target.start - original.start
    for span in baseline_spans:
        if tuple(span["pointer_slots"]) != original.slots:
            continue
        if span["ps2_end"] <= match.start:
            shift += (span["output_end"] - span["output_start"]
                      - (span["ps2_end"] - span["ps2_start"]))
        elif span["ps2_start"] < match.end:
            raise ValueError("New span intersects baseline translation")
    start, end = match.start + shift, match.end + shift
    if (not target.start <= start < end <= target.end
            or start not in installed.boundaries or end not in installed.boundaries
            or installed.raw[start:end] != ps2.raw[match.start:match.end]):
        raise ValueError("New span differs from untouched Japanese installed on r67.15n")
    return MtxReplacement(start, end, change.replacement)


def _compile(installed: _Source, replacements: tuple[MtxReplacement, ...]) -> bytes:
    if not replacements:
        return installed.raw
    last = installed.regions[-1]
    # MtxFile automatically aligns its final region. Preserve an untouched
    # unaligned tail after relocating its pointer with the regular compiler.
    if len(installed.raw) % 4 and all(item.start < last.start for item in replacements):
        prefix = MtxFile.parse(installed.raw[:last.start]).apply_replacements(replacements).compile()
        return prefix + installed.raw[last.start:]
    return installed.mtx.apply_replacements(replacements).compile()


def _audit_output(installed: _Source, output: bytes, replacements: tuple[MtxReplacement, ...]
                  ) -> tuple[dict[int, tuple[int, int]], list[dict[str, Any]]]:
    """Independently compare the new bytes, bounded padding, and every original run."""
    by_slots: dict[tuple[int, ...], list[MtxReplacement]] = defaultdict(list)
    for replacement in sorted(replacements, key=lambda item: item.start):
        by_slots[installed.at(replacement.start).slots].append(replacement)
    pointers = [0] * len(installed.mtx.pointer_offsets)
    cursor = installed.mtx.header_size
    offsets, evidence = {}, []
    for region in installed.regions:
        output_start = cursor
        for slot in region.slots:
            pointers[slot] = output_start
        previous = region.start
        region_changes = by_slots[region.slots]
        for replacement in region_changes:
            if not previous <= replacement.start < replacement.end <= region.end:
                raise ValueError("New overlay crosses a pointer region or overlaps another span")
            untouched = installed.raw[previous:replacement.start]
            if output[cursor:cursor + len(untouched)] != untouched:
                raise ValueError("New overlay changed untouched installed bytes")
            start = cursor + len(untouched)
            cursor = start + len(replacement.data)
            if output[start:cursor] != replacement.data:
                raise ValueError("New overlay differs from the proven replacement")
            offsets[replacement.start] = (start, cursor)
            previous = replacement.end
        untouched = installed.raw[previous:region.end]
        if output[cursor:cursor + len(untouched)] != untouched:
            raise ValueError("New overlay changed the installed region suffix")
        cursor += len(untouched)
        padding = (-cursor) % 4 if region_changes else 0
        if padding and (not _safe_padding(installed, region)
                        or output[cursor:cursor + padding] != b"\0" * padding):
            raise ValueError("New overlay contains unproven alignment bytes")
        cursor += padding
        evidence.append({
            "pointer_slots": region.slots,
            "installed_start": region.start,
            "installed_end": region.end,
            "output_start": output_start,
            "output_end": cursor,
            "installed_sha256": _digest(installed.raw[region.start:region.end]),
            "output_sha256": _digest(output[output_start:cursor]),
            "alignment_bytes_added": padding,
        })
    if cursor != len(output) or tuple(pointers) != MtxFile.parse(output).pointer_offsets:
        raise ValueError("New overlay changed pointer slots or data outside the audited regions")
    return offsets, evidence


def apply_bundle_delta(path: Path, ps2_raw: bytes, ps4_raw: bytes, dc_raw: bytes,
                       installed_raw: bytes, record: dict[str, Any]) -> tuple[bytes, dict[str, Any]]:
    """Generate a verified delta in file coordinates from one pinned baseline record."""
    hashes = {
        "ps2_sha256": _digest(ps2_raw),
        "ps4_sha256": _digest(ps4_raw),
        "official_map_sha256": _digest(dc_raw),
        "installed_sha256": _digest(installed_raw),
    }
    official_map = path.parent / "EN" / f"{path.stem}DC.json"
    if (record["path"] != f"ADV/{path.as_posix()}"
            or record["official_map"] != f"ADV/{official_map.as_posix()}"
            or any(record[key] != hashes[key] for key in ("ps2_sha256", "ps4_sha256", "official_map_sha256"))
            or record["output_sha256"] != hashes["installed_sha256"]):
        raise ValueError("Baseline source, official map, or installed file hash drift")
    dc = json.loads(dc_raw)
    if _dc_digest(dc) != record["dc_sha256"]:
        raise ValueError("Baseline parsed official map hash drift")
    ps2, ps4, installed = _Source(ps2_raw), _Source(ps4_raw), _Source(installed_raw)
    entries = _entries(dc)
    groups = _groups(ps4, entries)
    anchors = _read_baseline(ps2, ps4, installed, groups, record)
    pending = {row["ps4_start"]: row for row in record["unresolved"]}
    matches, reasons = _prove_bundles(ps2, ps4, groups, anchors, set(pending))

    encodable, omissions = [], set()
    for group in groups:
        match = matches.get(group.start)
        if match is None:
            continue
        original = ps4.raw[group.start:group.end]
        delimiter = _right_delimiter(ps4, group)
        if not delimiter:
            reasons[group.start] = "no_native_delimiter"
            continue
        try:
            original_names = _source_names(original)
            lines, names = _encode(group.lines)
        except ValueError as exc:
            reason = str(exc)
            reasons[group.start] = reason if reason in {
                "unsafe_source_control", "unsafe_name_control", "empty_official_text"
            } else "unsupported_encoding"
            continue
        scope = match.scopes[0]
        change = _Change(
            group, _Match(match.ps2_start, match.ps2_end, (scope.ps4_start, scope.ps4_end),
                          (scope.ps2_start, scope.ps2_end)), lines, original_names, names, delimiter,
        )
        if _approved_omission(path, change, match, original):
            omissions.add(group.start)
        encodable.append(change)

    region_changes: dict[_Region, list[tuple[_Change, MtxReplacement]]] = defaultdict(list)
    index = 0
    while index < len(encodable):
        current = encodable[index]
        omitted = current.group.start in omissions
        scope = (current.group.start,) if omitted else _name_scope(ps2, ps4, encodable, index)
        if not scope or (not omitted and omissions.intersection(scope)):
            reasons[current.group.start] = "unsafe_name_control"
            index += 1
            continue
        for change in encodable[index:index + len(scope)]:
            replacement = _installed_range(ps2, installed, change, record["spans"])
            region_changes[installed.at(replacement.start)].append((replace(change, name_scope=scope), replacement))
        index += len(scope)

    changes = []
    for region, items in region_changes.items():
        delta = sum(len(item.data) - (item.end - item.start) for _, item in items)
        if (region.end - region.start + delta) % 4 and not _safe_padding(installed, region):
            for change, _ in items:
                reasons[change.group.start] = "unsafe_alignment"
        else:
            changes.extend(items)
    replacements = tuple(item for _, item in changes)
    output = _compile(installed, replacements)
    offsets, regions = _audit_output(installed, output, replacements)

    spans = []
    for change, replacement in sorted(changes, key=lambda item: item[0].group.start):
        group, match = change.group, matches[change.group.start]
        start, end = offsets[replacement.start]
        per_entry = []
        cursor = start
        for key, line in zip(group.ids, change.lines, strict=True):
            per_entry.append({
                "entry_id": key,
                "output_start": cursor,
                "output_end": cursor + len(line),
                "output_sha256": _digest(line),
            })
            cursor += len(line) + 1
        spans.append({
            "entry_ids": group.ids,
            "ps4_start": group.start,
            "ps4_end": group.end,
            "ps2_start": match.ps2_start,
            "ps2_end": match.ps2_end,
            "installed_start": replacement.start,
            "installed_end": replacement.end,
            "output_start": start,
            "output_end": end,
            "pointer_slots": ps2.at(match.ps2_start).slots,
            "original_sha256": _digest(ps4.raw[group.start:group.end]),
            "replacement_sha256": _digest(replacement.data),
            "scopes": [asdict(scope) for scope in match.scopes],
            "source_name_controls": change.source_names,
            "name_controls": change.names,
            "name_scope": change.name_scope,
            "name_omission": OMISSION_OWNER if group.start in omissions else None,
            "right_delimiter_hex": change.delimiter.hex(),
            "entries": per_entry,
        })
    unresolved = [
        {**row, "baseline_reason": row["reason"], "reason": reasons[start]}
        for start, row in sorted(pending.items()) if start in reasons
    ]
    new_ids = {entry_id for span in spans for entry_id in span["entry_ids"]}
    unresolved_ids = {entry_id for row in unresolved for entry_id in row["entry_ids"]}
    previous_ids = {entry_id for anchor in anchors for entry_id in anchor.entry_ids}
    if (new_ids & unresolved_ids or new_ids & previous_ids or unresolved_ids & previous_ids
            or new_ids | unresolved_ids | previous_ids != set(entries)):
        raise ValueError("Exact bundle accounting differs from the official map")
    return output, {
        "path": record["path"],
        "official_map": record["official_map"],
        **hashes,
        "output_sha256": _digest(output),
        "installed_size": len(installed_raw),
        "output_size": len(output),
        "baseline_english_entries": len(previous_ids),
        "new_english_entries": len(new_ids),
        "new_groups": len(spans),
        "unresolved_english_entries": len(unresolved_ids),
        "unresolved_groups": len(unresolved),
        "unresolved_reasons": dict(sorted(Counter(row["reason"] for row in unresolved).items())),
        "spans": spans,
        "unresolved": unresolved,
        "regions": regions,
    }


def run(ps2_adv: Path, ps4_adv: Path, baseline_iso: Path, baseline_report: Path,
        output_dir: Path) -> dict[str, Any]:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Choose a fresh output directory: {output_dir}")
    report_bytes = baseline_report.read_bytes()
    if _digest(report_bytes) != BASELINE_REPORT_SHA256:
        raise ValueError("Baseline partial proof report hash drift")
    baseline = {row["path"]: row for row in json.loads(report_bytes)["results"]}
    rows, payloads = [], {}
    with baseline_iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if sha256(image).hexdigest() != BASELINE_ISO_SHA256:
            raise ValueError("Baseline ISO hash drift")
        _, outer = index_iso(image)
        base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
        _, records = index_iso(image, base)
        for path in PATHS:
            key = f"ADV/{path.as_posix()}"
            record = find_record(records, key)
            start = base + record.extent * 2048
            installed = image[start:start + record.size]
            dc_path = path.parent / "EN" / f"{path.stem}DC.json"
            output, row = apply_bundle_delta(path, (ps2_adv / path).read_bytes(),
                                             (ps4_adv / path).read_bytes(), (ps4_adv / dc_path).read_bytes(),
                                             installed, baseline[key])
            rows.append(row)
            if row["new_groups"]:
                payloads[path] = output

    report = {
        "schema_version": 1,
        "baseline_iso_sha256": BASELINE_ISO_SHA256,
        "baseline_report_sha256": BASELINE_REPORT_SHA256,
        "max_bundle_groups": MAX_BUNDLE_GROUPS,
        "files_examined": len(rows),
        "files_changed": len(payloads),
        "new_groups": sum(row["new_groups"] for row in rows),
        "new_english_entries": sum(row["new_english_entries"] for row in rows),
        "unresolved_groups": sum(row["unresolved_groups"] for row in rows),
        "unresolved_english_entries": sum(row["unresolved_english_entries"] for row in rows),
        "results": rows,
    }
    output_dir.mkdir(parents=True)
    overlay = output_dir / "overlay"
    overlay.mkdir()
    for path, payload in payloads.items():
        destination = overlay / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)
    staged = output_dir / "report.tmp"
    staged.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(output_dir / "report.json")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("ps2-adv", "ps4-adv", "baseline-iso", "baseline-report", "output-dir"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.ps2_adv, args.ps4_adv, args.baseline_iso, args.baseline_report, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
