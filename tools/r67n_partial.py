"""Conservative PS4 DC import into native PS2 MTX pointer regions."""
from __future__ import annotations

from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from hashlib import sha256
import json
import re
from typing import Any

from tools.localization import DcLocalization, _cp932_boundaries, encode_ps2_english
from tools.mtx import MtxFile, MtxReplacement


_NAMES = {"(px)": "px", "(pn1)": "pn", "(pm1)": "pm"}
_MACRO = re.compile(r"\(p[a-z0-9_]+\)", re.IGNORECASE)
_GLYPH = r"[^\x00-\x7f\uff61-\uff9f]"
_PRESENTATION = re.compile(rf"{_GLYPH}|r|px|pn|pm|l{_GLYPH}+\({_GLYPH}+\)")
_MARKERS = (b"wc", b"}w", b"rds", b"ds", b"}", b"r", b"c")


@dataclass(frozen=True)
class EntryEvidence:
    entry_id: int
    output_start: int
    output_end: int
    sha256: str


@dataclass(frozen=True)
class PartialSpan:
    entry_ids: tuple[int, ...]
    ps4_start: int
    ps4_end: int
    ps2_start: int
    ps2_end: int
    output_start: int
    output_end: int
    pointer_slots: tuple[int, ...]
    ps4_region: tuple[int, int]
    ps2_region: tuple[int, int]
    ps4_context: tuple[int, int]
    ps2_context: tuple[int, int]
    original_sha256: str
    context_sha256: str
    replacement_sha256: str
    source_name_controls: tuple[str, ...]
    name_controls: tuple[str, ...]
    name_scope: tuple[int, ...]
    right_delimiter_hex: str
    entries: tuple[EntryEvidence, ...]


@dataclass(frozen=True)
class UnresolvedGroup:
    entry_ids: tuple[int, ...]
    ps4_start: int
    ps4_end: int | None
    ps4_span_sha256: str | None
    reason: str
    ps2_candidates: tuple[tuple[int, int], ...] = ()
    detail: str = ""


@dataclass(frozen=True)
class RegionEvidence:
    pointer_slots: tuple[int, ...]
    ps2_start: int
    ps2_end: int
    output_start: int
    output_end: int
    ps2_sha256: str
    output_sha256: str
    alignment_bytes_added: int


@dataclass(frozen=True)
class PartialImportResult:
    data: bytes
    spans: tuple[PartialSpan, ...]
    unresolved: tuple[UnresolvedGroup, ...]
    regions: tuple[RegionEvidence, ...]
    ps2_sha256: str
    ps4_sha256: str
    dc_sha256: str
    output_sha256: str

    @property
    def english_entries(self) -> int:
        return sum(len(span.entry_ids) for span in self.spans)


@dataclass(frozen=True)
class _Region:
    start: int
    end: int
    slots: tuple[int, ...]


class _Source:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.mtx = MtxFile.parse(raw)
        slots = defaultdict(list)
        for index, offset in enumerate(self.mtx.pointer_offsets):
            if offset:
                slots[offset].append(index)
        self.starts = sorted(slots)
        if self.starts[0] != self.mtx.header_size:
            raise ValueError("MTX pointer addresses the header")
        self.regions = tuple(
            _Region(start, end, tuple(slots[start]))
            for start, end in zip(self.starts, self.starts[1:] + [len(raw)], strict=True)
        )
        self.by_slots = {region.slots: region for region in self.regions}
        self.boundaries = _cp932_boundaries(raw, self.mtx.header_size)

    def at(self, offset: int) -> _Region:
        return self.regions[bisect_right(self.starts, offset) - 1]


@dataclass(frozen=True)
class _Group:
    ids: tuple[int, ...]
    start: int
    end: int
    lines: tuple[str, ...]


@dataclass(frozen=True)
class _Match:
    start: int
    end: int
    ps4_context: tuple[int, int]
    ps2_context: tuple[int, int]


@dataclass(frozen=True)
class _Change:
    group: _Group
    match: _Match
    lines: tuple[bytes, ...]
    source_names: tuple[str, ...]
    names: tuple[str, ...]
    delimiter: bytes
    name_scope: tuple[int, ...] = ()

    @property
    def replacement(self) -> bytes:
        return b"r".join(self.lines)


def _digest(value: bytes) -> str:
    return sha256(value).hexdigest()


def _dc_digest(dc: dict[str, Any]) -> str:
    return _digest(json.dumps(dc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())


def _entries(dc: dict[str, Any]) -> dict[int, str]:
    keys, values = dc.get("keys"), dc.get("values")
    if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
        raise ValueError("DC JSON must contain equal-length keys and values arrays")
    if any(type(key) is not int for key in keys) or any(not isinstance(line, str) for line in values):
        raise ValueError("DC must contain integer keys and string values")
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate DC entry IDs")
    return dict(zip(keys, values, strict=True))


def _groups(ps4: _Source, entries: dict[int, str]) -> tuple[_Group, ...]:
    # DcLocalization uses values only for its file-wide macro scan and stored
    # lines. Derive geometry from the complete unchanged key array first,
    # then approve or reject each group's original values against its span.
    geometry = DcLocalization.from_json(
        ps4.raw, {"keys": list(entries), "values": [""] * len(entries)}
    ).groups
    groups = []
    for group in geometry:
        ids = (group.anchor, *group.synthetic_keys)
        groups.append(_Group(ids, group.anchor, group.replace_end, tuple(entries[key] for key in ids)))
    return tuple(groups)


def _left_boundary(source: _Source, region: _Region, start: int) -> bytes | None:
    if start == region.start:
        return b""
    cursor = start
    while (cursor > region.start and cursor - 1 in source.boundaries
           and source.raw[cursor - 1] < 0x80):
        cursor -= 1
    if cursor == start:
        return None
    control = source.raw[cursor:start]
    # A native wait/clear followed by a display break opens a new
    # presented line. Otherwise use the complete literal control run.
    return b"r" if control.endswith(b"wcr") else control


def _right_delimiter(source: _Source, group: _Group) -> bytes:
    region = source.at(group.start)
    for marker in _MARKERS:
        if (source.raw.startswith(marker, group.end, region.end)
                and group.end + len(marker) in source.boundaries):
            return marker
    return b""


def _occurrences(source: _Source, data: bytes, start: int, end: int):
    offset = source.raw.find(data, start, end)
    while offset >= 0:
        if offset in source.boundaries and offset + len(data) in source.boundaries:
            yield offset
        offset = source.raw.find(data, offset + 1, end)


def _unique_at(source: _Source, context: bytes, region: _Region, start: int) -> bool:
    hits = _occurrences(source, context, region.start, region.end)
    return next(hits, None) == start and next(hits, None) is None


def _exact_context(ps4: _Source, ps2: _Source, group: _Group,
                   r4: _Region, r2: _Region, start2: int) -> _Match | None:
    end2 = start2 + group.end - group.start
    left4, left2 = group.start, start2
    while (left4 > r4.start and left2 > r2.start
           and ps4.raw[left4 - 1] == ps2.raw[left2 - 1]):
        left4 -= 1
        left2 -= 1
    while left4 not in ps4.boundaries or left2 not in ps2.boundaries:
        left4 += 1
        left2 += 1
    right4, right2 = group.end, end2
    while (right4 < r4.end and right2 < r2.end
           and ps4.raw[right4] == ps2.raw[right2]):
        right4 += 1
        right2 += 1
    while right4 not in ps4.boundaries or right2 not in ps2.boundaries:
        right4 -= 1
        right2 -= 1
    context = ps4.raw[left4:right4]
    if (_unique_at(ps4, context, r4, left4) and _unique_at(ps2, context, r2, left2)):
        return _Match(start2, end2, (left4, right4), (left2, right2))
    return None


def _find_match(ps4: _Source, ps2: _Source, group: _Group, delimiter: bytes):
    r4 = ps4.at(group.start)
    if group.end > r4.end:
        return None, "ps4_pointer_crossing", ()
    if not delimiter:
        return None, "no_exact_context", ()
    left = _left_boundary(ps4, r4, group.start)
    if left is None:
        return None, "no_exact_context", ()
    r2 = ps2.by_slots.get(r4.slots)
    exact = ps4.raw[group.start:group.end]
    length = len(exact)
    if (r2 is not None and ps4.raw[r4.start:r4.end] == ps2.raw[r2.start:r2.end]
            and r4.start in ps4.boundaries and r2.start in ps2.boundaries
            and r4.end in ps4.boundaries and r2.end in ps2.boundaries):
        start = r2.start + group.start - r4.start
        match = _Match(start, start + length, (r4.start, r4.end), (r2.start, r2.end))
        return match, "", ((match.start, match.end),)

    candidates = tuple((start, start + length) for start in
                       _occurrences(ps2, exact, ps2.mtx.header_size, len(ps2.raw)))
    if not candidates:
        return None, "no_exact_span", ()
    bounded = tuple((start, end) for start, end in candidates if end <= ps2.at(start).end)
    if not bounded:
        return None, "ps2_pointer_crossing", candidates
    same_region = tuple((start, end) for start, end in bounded if ps2.at(start) == r2)
    if not same_region:
        return None, "pointer_identity_mismatch", candidates

    contextual = tuple((start, end) for start, end in same_region
                       if _left_boundary(ps2, r2, start) == left
                       and ps2.raw.startswith(delimiter, end, r2.end)
                       and end + len(delimiter) in ps2.boundaries)
    if not contextual:
        return None, "no_exact_context", candidates
    proofs = tuple(match for start, _ in contextual
                   if (match := _exact_context(ps4, ps2, group, r4, r2, start)) is not None)
    if len(proofs) != 1:
        return None, "ambiguous_context", contextual
    return proofs[0], "", contextual


def _source_names(raw: bytes) -> tuple[str, ...]:
    try:
        original = raw.decode("cp932")
    except UnicodeDecodeError as exc:
        raise ValueError("unsafe_source_control") from exc
    if any(len(char.encode("cp932")) != 2 for char in original if ord(char) >= 0x80):
        raise ValueError("unsafe_source_control")
    tokens = []
    cursor = 0
    while cursor < len(original):
        token = _PRESENTATION.match(original, cursor)
        if token is None:
            raise ValueError("unsafe_source_control")
        if token[0] in _NAMES.values():
            tokens.append(token[0])
        cursor = token.end()
    return tuple(tokens)


def _encode(lines: tuple[str, ...]) -> tuple[tuple[bytes, ...], tuple[str, ...]]:
    macros = tuple(macro for line in lines for macro in _MACRO.findall(line))
    if any(macro not in _NAMES for macro in macros):
        raise ValueError("unsafe_name_control")
    if not any(line.strip() for line in lines):
        raise ValueError("empty_official_text")
    encoded_lines = []
    for line in lines:
        parts = []
        previous_end = 0
        for macro in _MACRO.finditer(line):
            parts.append(encode_ps2_english(line[previous_end:macro.start()]))
            parts.append(_NAMES[macro[0]].encode("ascii"))
            previous_end = macro.end()
        parts.append(encode_ps2_english(line[previous_end:]))
        encoded_lines.append(b"".join(parts))
    return tuple(encoded_lines), tuple(_NAMES[macro] for macro in macros)


def _same_page(ps2: _Source, ps4: _Source, left: _Change, right: _Change) -> bool:
    return (
        ps4.at(left.group.start) == ps4.at(right.group.start)
        and ps2.at(left.match.start) == ps2.at(right.match.start)
        and ps4.raw[left.group.end:right.group.start] == b"r"
        and ps2.raw[left.match.end:right.match.start] == b"r"
    )


def _name_scope(ps2: _Source, ps4: _Source, candidates: list[_Change], index: int) -> tuple[int, ...]:
    """Find the shortest adjacent, same-page scope that conserves name tokens."""
    original, official = Counter(), Counter()
    anchors = []
    for position in range(index, len(candidates)):
        change = candidates[position]
        if position > index and not _same_page(ps2, ps4, candidates[position - 1], change):
            break
        anchors.append(change.group.start)
        original.update(change.source_names)
        official.update(change.names)
        if original == official:
            return tuple(anchors)
    return ()


def _unresolved(ps4: _Source, group: _Group, reason: str,
                candidates: tuple[tuple[int, int], ...] = (), detail: str = "") -> UnresolvedGroup:
    return UnresolvedGroup(group.ids, group.start, group.end,
                           _digest(ps4.raw[group.start:group.end]), reason, candidates, detail)


def _safe_padding(source: _Source, region: _Region) -> bool:
    unpadded = source.raw[region.start:region.end].rstrip(b"\0")
    return unpadded.endswith(b"_") and region.start + len(unpadded) - 1 in source.boundaries


def _compile(ps2: _Source, changes: tuple[_Change, ...]) -> bytes:
    if not changes:
        return ps2.raw
    replacements = tuple(MtxReplacement(change.match.start, change.match.end, change.replacement)
                         for change in changes)
    # The historical compiler aligns the final region even with no changes.
    # An untouched unaligned tail can be carried as-is after relocating its
    # start pointer (represented by an empty final region during compilation).
    last = ps2.regions[-1]
    if len(ps2.raw) % 4 and all(change.match.start < last.start for change in changes):
        prefix = MtxFile.parse(ps2.raw[:last.start]).apply_replacements(replacements).compile()
        return prefix + ps2.raw[last.start:]
    return ps2.mtx.apply_replacements(replacements).compile()


def _output_evidence(ps2: _Source, ps4: _Source, data: bytes,
                     changes: tuple[_Change, ...]) -> tuple[tuple[PartialSpan, ...], tuple[RegionEvidence, ...]]:
    """Audit bytes that were not replaced independently of the native compiler."""
    output = MtxFile.parse(data)
    by_region: dict[_Region, list[_Change]] = defaultdict(list)
    for change in sorted(changes, key=lambda item: item.match.start):
        by_region[ps2.at(change.match.start)].append(change)

    spans = []
    regions = []
    out_cursor = ps2.mtx.header_size
    expected_pointers = [0] * len(ps2.mtx.pointer_words)
    for region in ps2.regions:
        region_out_start = out_cursor
        for slot in region.slots:
            expected_pointers[slot] = region_out_start
        source_cursor = region.start
        for change in by_region[region]:
            group, match = change.group, change.match
            r4 = ps4.at(group.start)
            if not (source_cursor <= match.start < match.end <= region.end):
                raise ValueError("Replacement overlaps another span or crosses a pointer boundary")
            unchanged = ps2.raw[source_cursor:match.start]
            if data[out_cursor:out_cursor + len(unchanged)] != unchanged:
                raise ValueError("Recompiled MTX changed original PS2 bytes outside a proven span")
            out_start = out_cursor + len(unchanged)
            out_cursor = out_start + len(change.replacement)
            if data[out_start:out_cursor] != change.replacement:
                raise ValueError("Recompiled MTX has incorrect localized bytes")
            entries = []
            entry_start = out_start
            for entry_id, line in zip(group.ids, change.lines, strict=True):
                entry_end = entry_start + len(line)
                entries.append(EntryEvidence(entry_id, entry_start, entry_end, _digest(line)))
                entry_start = entry_end + 1  # Native display delimiter between synthetic lines.
            spans.append(PartialSpan(
                group.ids, group.start, group.end, match.start, match.end, out_start, out_cursor,
                region.slots, (r4.start, r4.end), (region.start, region.end),
                match.ps4_context, match.ps2_context, _digest(ps4.raw[group.start:group.end]),
                _digest(ps4.raw[slice(*match.ps4_context)]), _digest(change.replacement),
                change.source_names, change.names, change.name_scope, change.delimiter.hex(),
                tuple(entries),
            ))
            source_cursor = match.end
        unchanged = ps2.raw[source_cursor:region.end]
        if data[out_cursor:out_cursor + len(unchanged)] != unchanged:
            raise ValueError("Recompiled MTX changed the region suffix outside a proven span")
        out_cursor += len(unchanged)
        padding = (-out_cursor) % 4 if by_region[region] else 0
        if padding and (not _safe_padding(ps2, region)
                        or data[out_cursor:out_cursor + padding] != b"\0" * padding):
            raise ValueError("Recompiled MTX contains unproven alignment bytes")
        out_cursor += padding
        regions.append(RegionEvidence(
            region.slots, region.start, region.end, region_out_start, out_cursor,
            _digest(ps2.raw[region.start:region.end]), _digest(data[region_out_start:out_cursor]),
            padding,
        ))

    if out_cursor != len(data) or tuple(expected_pointers) != output.pointer_offsets:
        raise ValueError("Recompiled MTX changed pointer slots or bytes after the final region")
    return tuple(sorted(spans, key=lambda span: span.ps4_start)), tuple(regions)


def _plan(ps2: _Source, ps4: _Source, entries: dict[int, str]):
    unresolved: dict[int, UnresolvedGroup] = {}
    mapped = {}
    try:
        groups = _groups(ps4, entries)
    except ValueError as exc:
        groups = ()
        unresolved = {
            key: UnresolvedGroup((key,), key, None, None, "invalid_dc_geometry", detail=str(exc))
            for key in entries
        }
    for group in groups:
        delimiter = _right_delimiter(ps4, group)
        match, reason, candidates = _find_match(ps4, ps2, group, delimiter)
        unknown = tuple(macro for line in group.lines for macro in _MACRO.findall(line)
                        if macro not in _NAMES)
        if unknown:
            unresolved[group.start] = _unresolved(
                ps4, group, "unsafe_name_control", candidates, ", ".join(unknown)
            )
        elif match is None:
            unresolved[group.start] = _unresolved(ps4, group, reason, candidates)
        else:
            mapped[group.start] = (group, match, delimiter)

    # Reject both claimants to a target overlap or inverted order in one
    # pointer region, including claims that would subsequently fail encoding.
    by_region = defaultdict(list)
    for group, match, _ in mapped.values():
        by_region[ps2.at(match.start)].append((group, match))
    for region_matches in by_region.values():
        for index, (group, match) in enumerate(region_matches):
            for other, other_match in region_matches[index + 1:]:
                if match.end > other_match.start:
                    for claimed, target in ((group, match), (other, other_match)):
                        unresolved[claimed.start] = _unresolved(
                            ps4, claimed, "conflicting_context", ((target.start, target.end),)
                        )

    encodable = []
    for group, match, delimiter in mapped.values():
        if group.start in unresolved:
            continue
        try:
            original_names = _source_names(ps4.raw[group.start:group.end])
            lines, names = _encode(group.lines)
        except ValueError as exc:
            detail = str(exc)
            reason = detail if detail in {
                "unsafe_source_control", "unsafe_name_control", "empty_official_text"
            } else "unsupported_encoding"
            unresolved[group.start] = _unresolved(
                ps4, group, reason, ((match.start, match.end),), detail
            )
            continue
        encodable.append(_Change(group, match, lines, original_names, names, delimiter))

    replacements = defaultdict(list)
    index = 0
    while index < len(encodable):
        scope = _name_scope(ps2, ps4, encodable, index)
        if not scope:
            change = encodable[index]
            group, match = change.group, change.match
            unresolved[group.start] = _unresolved(
                ps4, group, "unsafe_name_control", ((match.start, match.end),),
                f"Source tokens {change.source_names} and official {change.names} "
                "cannot be balanced within an exact presentation run"
            )
            index += 1
            continue
        for change in encodable[index:index + len(scope)]:
            replacements[ps2.at(change.match.start)].append(replace(change, name_scope=scope))
        index += len(scope)

    changes = []
    for region, replacement_group in replacements.items():
        delta = sum(len(change.replacement) - (change.match.end - change.match.start)
                    for change in replacement_group)
        if (region.end - region.start + delta) % 4 and not _safe_padding(ps2, region):
            for change in replacement_group:
                group, match = change.group, change.match
                unresolved[group.start] = _unresolved(
                    ps4, group, "unsafe_alignment", ((match.start, match.end),)
                )
        else:
            changes.extend(replacement_group)

    return tuple(changes), unresolved


def import_partial_mtx(ps2_raw: bytes, ps4_raw: bytes, dc: dict[str, Any]) -> PartialImportResult:
    """Transfer only groups with exact source and control-aware pointer context."""
    ps2, ps4 = _Source(ps2_raw), _Source(ps4_raw)
    changes, unresolved = _plan(ps2, ps4, _entries(dc))
    try:
        data = _compile(ps2, tuple(changes))
        spans, regions = _output_evidence(ps2, ps4, data, tuple(changes))
    except ValueError as exc:
        for change in changes:
            group, match = change.group, change.match
            unresolved[group.start] = _unresolved(
                ps4, group, "unsafe_relocation", ((match.start, match.end),), str(exc)
            )
        data = ps2_raw
        spans, regions = _output_evidence(ps2, ps4, data, ())
    return PartialImportResult(
        data, spans, tuple(unresolved[key] for key in sorted(unresolved)), regions,
        _digest(ps2_raw), _digest(ps4_raw), _dc_digest(dc), _digest(data),
    )


def verify_partial_mtx(ps2_raw: bytes, ps4_raw: bytes, dc: dict[str, Any],
                       result: PartialImportResult) -> None:
    """Verify all accepted entry identities, source evidence and emitted bytes."""
    if (result.ps2_sha256, result.ps4_sha256, result.dc_sha256, result.output_sha256) != (
        _digest(ps2_raw), _digest(ps4_raw), _dc_digest(dc), _digest(result.data)
    ):
        raise ValueError("Partial MTX source, DC or output hash mismatch")

    ps2, ps4 = _Source(ps2_raw), _Source(ps4_raw)
    changes, unresolved = _plan(ps2, ps4, _entries(dc))
    if result.spans:
        expected_spans, expected_regions = _output_evidence(ps2, ps4, result.data, changes)
    else:
        if changes:
            # A no-op is a valid fallback only if the planned relocation
            # actually fails independently on the same source and inputs.
            try:
                compiled = _compile(ps2, changes)
                _output_evidence(ps2, ps4, compiled, changes)
            except ValueError as exc:
                for change in changes:
                    group, match = change.group, change.match
                    unresolved[group.start] = _unresolved(
                        ps4, group, "unsafe_relocation", ((match.start, match.end),), str(exc)
                    )
            else:
                raise ValueError("Partial MTX omitted safely compilable source spans")
        expected_spans, expected_regions = _output_evidence(ps2, ps4, result.data, ())

    expected_unresolved = tuple(unresolved[key] for key in sorted(unresolved))
    if (result.spans, result.regions, result.unresolved) != (
        expected_spans, expected_regions, expected_unresolved
    ):
        raise ValueError("Partial MTX report diverges from verified source or output offsets")
