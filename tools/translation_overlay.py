from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import re
from typing import Iterable, Mapping

from tools.iso9660_patch import IsoRecord, SECTOR_SIZE


@dataclass(frozen=True)
class OverlayEntry:
    path: str
    provenance: str
    source_path: Path
    size: int
    sha256: str

    @property
    def embedded_path(self) -> str:
        return resolve_embedded_path(self.path)


@dataclass(frozen=True)
class OverlayCollision:
    path: str
    replaced_provenance: str
    replaced_sha256: str
    replacement_provenance: str
    replacement_sha256: str


@dataclass(frozen=True)
class OverlayManifest:
    entries: tuple[OverlayEntry, ...]
    collisions: tuple[OverlayCollision, ...]


@dataclass(frozen=True)
class ReplacementPlanEntry:
    path: str
    input_extent: int
    input_size: int
    input_sectors: int
    output_extent: int
    output_size: int
    output_sectors: int
    relocated: bool


@dataclass(frozen=True)
class ReplacementPlan:
    entries: tuple[ReplacementPlanEntry, ...]
    appended_sectors: int

    @property
    def by_path(self) -> dict[str, ReplacementPlanEntry]:
        return {entry.path: entry for entry in self.entries}


_BLBRD_BIN_RE = re.compile(r"^BLBRD/B_GP\d{3}\.BIN$", re.IGNORECASE)
_INIT_MES_TMX_RE = re.compile(r"^BLBRD/INIT_MES/TR\d{3}\.TMX$", re.IGNORECASE)


def resolve_embedded_path(path: str) -> str:
    """Resolve an overlay-relative path to its DATA.CVM ISO path.

    Historical MTX/KSF roots are ADV-relative.  Localized billboard containers
    are explicit top-level BLBRD paths so binary graphics cannot accidentally be
    written into an arbitrary embedded file.
    """

    normalized = path.replace("\\", "/")
    suffix = Path(normalized).suffix.upper()
    if suffix == ".TMX" and _INIT_MES_TMX_RE.fullmatch(normalized):
        return normalized
    if suffix in {".MTX", ".KSF"}:
        return normalized if normalized.upper().startswith("ADV/") else f"ADV/{normalized}"
    if suffix == ".BIN" and _BLBRD_BIN_RE.fullmatch(normalized):
        return normalized
    raise ValueError(f"Overlay file is not a supported embedded path: {path}")


def _sectors(size: int) -> int:
    return (size + SECTOR_SIZE - 1) // SECTOR_SIZE


def collect_overlay(roots: Iterable[tuple[str, Path]]) -> OverlayManifest:
    """Collect deterministic ADV-relative overlay files.

    Roots are ordered from lowest to highest priority. Later roots may replace an
    earlier path, but the collision remains visible in the manifest.
    """

    selected: dict[str, OverlayEntry] = {}
    collisions: list[OverlayCollision] = []

    for provenance, root in roots:
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Overlay root does not exist or is not a directory: {root}")
        for source in sorted(path for path in root.rglob("*") if path.is_file()):
            rel = source.relative_to(root).as_posix()
            resolve_embedded_path(rel)  # validate before hashing/selecting
            data = source.read_bytes()
            entry = OverlayEntry(
                path=rel,
                provenance=provenance,
                source_path=source,
                size=len(data),
                sha256=sha256(data).hexdigest(),
            )
            previous = selected.get(rel)
            if previous is not None:
                collisions.append(
                    OverlayCollision(
                        path=rel,
                        replaced_provenance=previous.provenance,
                        replaced_sha256=previous.sha256,
                        replacement_provenance=entry.provenance,
                        replacement_sha256=entry.sha256,
                    )
                )
            selected[rel] = entry

    return OverlayManifest(
        entries=tuple(selected[path] for path in sorted(selected)),
        collisions=tuple(collisions),
    )


def plan_replacements(
    records: Mapping[str, IsoRecord],
    output_sizes: Mapping[str, int],
    *,
    append_start: int,
) -> ReplacementPlan:
    """Plan in-place versus append-relocated ADV file replacements."""

    normalized_records = {path.upper(): record for path, record in records.items()}
    cursor = append_start
    planned: list[ReplacementPlanEntry] = []

    for rel in sorted(output_sizes):
        embedded_path = resolve_embedded_path(rel)
        lookup = embedded_path.upper()
        record = normalized_records.get(lookup)
        if record is None:
            raise ValueError(f"Overlay path not found in embedded ISO: {embedded_path}")
        if record.is_directory:
            raise ValueError(f"Overlay path unexpectedly resolves to a directory: {embedded_path}")
        output_size = int(output_sizes[rel])
        if output_size <= 0:
            raise ValueError(f"Overlay output must be non-empty: {rel}")
        output_sectors = _sectors(output_size)
        relocated = output_sectors > record.sectors
        output_extent = cursor if relocated else record.extent
        if relocated:
            cursor += output_sectors
        planned.append(
            ReplacementPlanEntry(
                path=rel,
                input_extent=record.extent,
                input_size=record.size,
                input_sectors=record.sectors,
                output_extent=output_extent,
                output_size=output_size,
                output_sectors=output_sectors,
                relocated=relocated,
            )
        )

    return ReplacementPlan(tuple(planned), cursor - append_start)
