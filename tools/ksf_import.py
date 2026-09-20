from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any


class KsfImportError(ValueError):
    """Raised when a KSF file cannot enter the exact-source tier."""


@dataclass(frozen=True)
class KsfFieldAnalysis:
    key: int
    text: str
    status: str
    capacity: int | None = None
    reason: str | None = None


def _normalized_ascii(text: str) -> bytes:
    normalized = re.sub(r" +", " ", text)
    try:
        return normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("official KSF text is not ASCII") from exc


def analyze_ksf_exact(
    ps2_raw: bytes, ps4_raw: bytes, dc: dict[str, Any]
) -> tuple[KsfFieldAnalysis, ...]:
    """Prove fixed-width PS2 KSF fields for an exact PS2/PS4 source pair.

    The known KSF string records use a 0x01 byte immediately before the DC key,
    followed by CP932 text, a NUL terminator/padding run, then the next nonzero
    structural byte.  Only that pattern is accepted.  Anything else is reported
    ambiguous instead of inferring a writable region from proximity alone.
    """

    if ps2_raw != ps4_raw:
        raise KsfImportError("Exact KSF analysis requires byte-identical PS2 and PS4 sources")

    keys = dc.get("keys")
    values = dc.get("values")
    if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
        raise KsfImportError("KSF DC JSON must contain equal-length keys and values arrays")

    int_keys = [int(key) for key in keys]
    duplicate_counts = Counter(int_keys)
    analyses: list[KsfFieldAnalysis] = []

    for key, value in zip(int_keys, values):
        text = re.sub(r" +", " ", str(value))
        if duplicate_counts[key] > 1:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="duplicate DC key")
            )
            continue
        if key <= 0 or key >= len(ps2_raw) or ps2_raw[key - 1] != 0x01:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="missing 0x01 string-record marker")
            )
            continue

        terminator = ps2_raw.find(b"\x00", key)
        if terminator < 0:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="source field has no NUL terminator")
            )
            continue

        source = ps2_raw[key:terminator]
        if not source:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="empty source field")
            )
            continue
        try:
            source.decode("cp932")
        except UnicodeDecodeError:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="source field is not valid CP932")
            )
            continue

        next_nonzero = terminator + 1
        while next_nonzero < len(ps2_raw) and ps2_raw[next_nonzero] == 0:
            next_nonzero += 1
        if next_nonzero >= len(ps2_raw):
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", reason="field has no following structural boundary")
            )
            continue

        capacity = next_nonzero - key
        try:
            encoded = _normalized_ascii(text)
        except ValueError as exc:
            analyses.append(
                KsfFieldAnalysis(key, text, "ambiguous", capacity=capacity, reason=str(exc))
            )
            continue

        status = "fit" if len(encoded) <= capacity else "overflow"
        reason = None if status == "fit" else f"needs {len(encoded)} bytes; capacity is {capacity}"
        analyses.append(KsfFieldAnalysis(key, text, status, capacity=capacity, reason=reason))

    return tuple(analyses)


def summarize_ksf_analyses(
    analyses: tuple[KsfFieldAnalysis, ...],
) -> dict[str, int]:
    counts = Counter(field.status for field in analyses)
    return {
        "entries": len(analyses),
        "fit": counts["fit"],
        "overflow": counts["overflow"],
        "ambiguous": counts["ambiguous"],
    }


def import_exact_ksf(
    ps2_raw: bytes, ps4_raw: bytes, dc: dict[str, Any]
) -> tuple[bytes, tuple[KsfFieldAnalysis, ...]]:
    analyses = analyze_ksf_exact(ps2_raw, ps4_raw, dc)
    result = bytearray(ps2_raw)

    fit_ranges: list[tuple[int, int]] = []
    for field in analyses:
        if field.status != "fit" or field.capacity is None:
            continue
        start = field.key
        end = start + field.capacity
        if any(not (end <= old_start or start >= old_end) for old_start, old_end in fit_ranges):
            # A proven fixed field must not overlap another proven fixed field.
            # Fail the whole import rather than silently choosing one entry.
            raise KsfImportError(f"proven KSF fields overlap at DC key {field.key}")
        encoded = _normalized_ascii(field.text)
        result[start:end] = encoded + (b"\x00" * (field.capacity - len(encoded)))
        fit_ranges.append((start, end))

    return bytes(result), analyses
