from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EXPECTED_SERIAL = "SLPM-66511"
EXPECTED_SAVE_DIRECTORY = "BISLPM-66511Save"


class RegressionError(ValueError):
    """Raised when an accepted translation or compatibility invariant regresses."""


@dataclass(frozen=True)
class RegressionResult:
    added: list[str]
    changed: list[str]
    removed: list[str]


def validate_invariants(invariants: dict[str, Any]) -> None:
    serial = invariants.get("serial")
    save_directory = invariants.get("save_directory")
    if serial != EXPECTED_SERIAL:
        raise RegressionError(
            f"serial invariant changed: expected {EXPECTED_SERIAL!r}, got {serial!r}"
        )
    if save_directory != EXPECTED_SAVE_DIRECTORY:
        raise RegressionError(
            "save_directory invariant changed: "
            f"expected {EXPECTED_SAVE_DIRECTORY!r}, got {save_directory!r}"
        )


def _index_entries(manifest: dict[str, Any], label: str) -> dict[str, dict[str, Any]]:
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise RegressionError(f"{label} manifest entries must be a list")

    indexed: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise RegressionError(f"{label} manifest contains an entry without a stable string id")
        stable_id = entry["id"]
        if stable_id in indexed:
            raise RegressionError(f"{label} manifest contains duplicate stable id {stable_id!r}")
        indexed[stable_id] = entry
    return indexed


def compare_manifests(
    baseline: dict[str, Any], current: dict[str, Any]
) -> RegressionResult:
    """Compare cumulative accepted translations and fail on loss or mutation.

    Additions are expected during translation work.  Existing stable entries are
    immutable under this gate; an intentional correction is made by explicitly
    updating the accepted baseline after review, never by silently changing the
    generated current manifest.
    """

    validate_invariants(baseline.get("invariants", {}))
    validate_invariants(current.get("invariants", {}))
    old = _index_entries(baseline, "baseline")
    new = _index_entries(current, "current")

    added = sorted(set(new) - set(old))
    removed = sorted(set(old) - set(new))
    changed = sorted(stable_id for stable_id in set(old) & set(new) if old[stable_id] != new[stable_id])

    if removed:
        raise RegressionError(f"accepted translations removed: {', '.join(removed)}")
    if changed:
        raise RegressionError(f"accepted translations changed: {', '.join(changed)}")

    return RegressionResult(added=added, changed=changed, removed=removed)
