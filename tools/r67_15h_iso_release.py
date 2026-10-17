"""Deterministic r67.15h diagnostic integration; building is explicit and opt-in."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from tools import r67_15g_iso_release as r67_15g
from tools.r67_lion_statue_iso_patch import sha_file

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = ROOT / "local/r67-15g-partial-diagnostic.elf"
SOURCE_ELF_SHA256 = "74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee"
SOURCE_ISO = ROOT / "local/r67-candidates/67.15g-partial-diagnostic.iso"
SOURCE_ISO_SHA256 = "cb2ef57789d62fc078678285da86e272eaf426740f181d576126be4d1946f267"
SOURCE_MANIFEST = ROOT / "local/r67-15g-partial-diagnostic.json"
OUTPUT_ISO = ROOT / "local/r67-candidates/67.15h-details-transition-diagnostic.iso"
OUTPUT_ELF = ROOT / "local/r67-15h-details-transition-diagnostic.elf"
OUTPUT_REPORT = ROOT / "local/r67-15h-details-transition-diagnostic.json"
OUTPUT_AUDIT = ROOT / "local/r67-15h-details-transition-whole-iso-audit.json"
INCOMPLETE_ISO = OUTPUT_ISO.with_suffix(".incomplete")
PARTIAL_DETAILS_UNRESOLVED = 36
EXPECTED_COMPONENT_ORDER = ("item_layout", "hant_pool")
PARENT_RESOURCE_LOOKUP_EVIDENCE = {
    "audit_kind": "parent_verified_embedded_rofs_against_current_15g_data_cvm",
    "embedded_rofs_file_records": 10656,
    "relocated_or_resized_records": 969,
    "mismatches": 0,
    "unmatched_records": 0,
}

Apply = Callable[[bytes], tuple[bytes, dict[str, Any]]]
Component = tuple[str, Apply, Mapping[str, Any]]


@dataclass(frozen=True)
class Prepared15H:
    source: bytes
    candidate: bytes
    components: tuple[dict[str, Any], ...]
    changed_existing: dict[int, tuple[int, str]]
    input_elf_sha256: str


def _compose_once(source: bytes, components: Sequence[Component]) -> Prepared15H:
    if not components:
        raise ValueError("an explicit ordered component list is required")
    names = [item[0] for item in components]
    if any(not isinstance(name, str) or not name.strip() for name in names):
        raise ValueError("component names must be non-empty strings")
    if len(set(names)) != len(names):
        raise ValueError("duplicate component name")

    owner_map: dict[str, tuple[tuple[int, int], ...]] = {}
    for name, apply, declarations in components:
        if not callable(apply) or not isinstance(declarations, Mapping):
            raise ValueError(f"{name} component requires apply and explicit owner ranges")
        for owner_name, raw_ranges in declarations.items():
            if isinstance(raw_ranges, (tuple, list)) and len(raw_ranges) == 2 and all(
                isinstance(value, int) and not isinstance(value, bool) for value in raw_ranges
            ):
                spans = (raw_ranges,)
            elif isinstance(raw_ranges, (tuple, list)):
                spans = tuple(raw_ranges)
            else:
                raise ValueError(f"invalid half-open owner ranges for {name}:{owner_name}")
            normalized: list[tuple[int, int]] = []
            for span in spans:
                if (not isinstance(span, (tuple, list)) or len(span) != 2
                        or any(not isinstance(value, int) or isinstance(value, bool) for value in span)):
                    raise ValueError(f"invalid half-open owner range for {name}:{owner_name}")
                start, end = span
                if start < 0 or end <= start or end > len(source) or end - start > r67_15g.MAX_SINGLE_OWNER_RANGE:
                    raise ValueError(f"invalid or broad half-open owner range for {name}:{owner_name}")
                if start < 0x68 and end > 0x64:
                    if (start, end) != (0x64, 0x68):
                        raise ValueError(f"owner range crosses ELF segment metadata for {name}:{owner_name}")
                    continue
                normalized.append((start, end))
            if normalized:
                owner_map[f"{name}:{owner_name}"] = tuple(normalized)
    r67_15g._flatten_ranges(owner_map)

    current = source
    component_reports: list[dict[str, Any]] = []
    changed: dict[int, tuple[int, str]] = {}
    for name, apply, _declarations in components:
        after, report = apply(current)
        ranges = {key: value for key, value in owner_map.items() if key.startswith(f"{name}:")}
        audited = r67_15g.audit_component(name, current, after, report, ranges)
        if not audited["_changes"]:
            raise ValueError(f"{name} component made no changes")
        for offset, change in audited["_changes"].items():
            changed[offset] = change
        component_reports.append({key: value for key, value in audited.items() if key != "_changes"})
        current = bytes(after)
    return Prepared15H(source, current, tuple(component_reports), changed,
                       hashlib.sha256(source).hexdigest())


def _prepare_stages(source: bytes, components: Sequence[Component]) -> Prepared15H:
    """Run the exact ordered composition twice and reject any byte/report drift."""
    first = _compose_once(source, components)
    second = _compose_once(source, components)
    if first != second:
        raise ValueError("two independent component preparations were not deterministic")
    return first


def _validate_component_order(components: Sequence[Component]) -> None:
    names = tuple(item[0] for item in components)
    if names != EXPECTED_COMPONENT_ORDER:
        raise ValueError(f"r67.15h components must be explicitly supplied in order {EXPECTED_COMPONENT_ORDER}")


def _compose_pinned_15g() -> tuple[bytes, dict[str, Any]]:
    if not r67_15g.SOURCE_ISO.is_file() or sha_file(r67_15g.SOURCE_ISO) != r67_15g.SOURCE_ISO_SHA256:
        raise ValueError("approved r67.15f ISO is missing or changed")
    if not r67_15g.CORPUS.is_file() or sha_file(r67_15g.CORPUS) != r67_15g.CORPUS_SHA256:
        raise ValueError("official English corpus is missing or changed")
    approved = r67_15g._read_approved_inputs()
    corpus = r67_15g.CORPUS.read_bytes()
    first = r67_15g.compose_components(approved.source_elf, r67_15g.CORPUS, corpus)
    second = r67_15g.compose_components(approved.source_elf, r67_15g.CORPUS, corpus)
    if first != second:
        raise ValueError("independent r67.15g regeneration was not deterministic")
    return first


def _read_route_context() -> dict[str, Any]:
    if not SOURCE_MANIFEST.is_file():
        raise ValueError("pinned r67.15g release manifest is missing")
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    route = manifest.get("route_evidence")
    if (manifest.get("release") != "r67.15g"
            or manifest.get("candidate_iso_sha256") != SOURCE_ISO_SHA256
            or manifest.get("candidate_elf_sha256") != SOURCE_ELF_SHA256
            or not isinstance(route, dict)
            or route.get("read_only") is not True
            or route.get("static_payload_provenance_passed") is not True):
        raise ValueError("pinned r67.15g route/provenance context does not match its inputs")
    return route


def prepare(source_g: bytes, components: Sequence[Component]) -> Prepared15H:
    """Prepare from the immutable 15g ELF after independently rebuilding 15g from 15f."""
    _validate_component_order(components)
    actual = hashlib.sha256(source_g).hexdigest()
    if actual != SOURCE_ELF_SHA256:
        raise ValueError(f"r67.15g input ELF SHA-256 mismatch: {actual}")
    if not SOURCE_ISO.is_file() or sha_file(SOURCE_ISO) != SOURCE_ISO_SHA256:
        raise ValueError("pinned r67.15g diagnostic ISO is missing or changed")
    if not SOURCE_ELF.is_file() or sha_file(SOURCE_ELF) != SOURCE_ELF_SHA256:
        raise ValueError("pinned r67.15g diagnostic ELF is missing or changed")
    if SOURCE_ELF.read_bytes() != source_g:
        raise ValueError("provided ELF differs from the pinned r67.15g executable")
    import mmap
    with SOURCE_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        exe, exe_offset, _cvm, _cvm_offset, _cvm_base, _art, _art_offset = r67_15g._installed_records(image)
        if exe.size != len(source_g) or bytes(image[exe_offset:exe_offset + exe.size]) != source_g:
            raise ValueError("pinned r67.15g ISO executable differs from its approved ELF input")
    regenerated_g, _g_report = _compose_pinned_15g()
    if regenerated_g != source_g:
        raise ValueError("independent r67.15g composition differs from pinned diagnostic ELF")
    return _prepare_stages(source_g, components)


def make_report(prepared: Prepared15H, input_iso_sha256: str,
                input_elf_sha256: str, *, resource_lookup_evidence: Mapping[str, Any] | None = None,
                route_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
    resource_evidence = PARENT_RESOURCE_LOOKUP_EVIDENCE if resource_lookup_evidence is None else resource_lookup_evidence
    evidence = {"source": "parent-provided audit", **dict(resource_evidence),
                "cvm_mutation_planned": False}
    return {
        "release": "r67.15h",
        "status": "PARTIAL_DIAGNOSTIC_NOT_GAMEPLAY_APPROVED",
        "scope_complete": False,
        "release_scope": "prior partial official-source coverage carried forward",
        "unresolved_details_records": PARTIAL_DETAILS_UNRESOLVED,
        "component_order": ["item_layout", "hant_pool"],
        "components": list(prepared.components),
        "input_iso_sha256": input_iso_sha256,
        "input_elf_sha256": input_elf_sha256,
        "candidate_elf_sha256": hashlib.sha256(prepared.candidate).hexdigest(),
        "route_evidence": None if route_context is None else dict(route_context),
        "resource_lookup_consistency": evidence,
        "data_cvm_mutation_planned": False,
        "reported_hant_observation": {
            "opened_and_scrolled_pages": "4-5",
            "door_loading_hang_reported": True,
            "causality_confirmed": False,
            "runtime_hang_verified": False,
        },
        "loading_confirmation": "PENDING",
        "runtime_verified": False,
        "gameplay_approved": False,
    }


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)


def build(components: Sequence[Component], *,
          resource_lookup_evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Explicit future build operation. This function is never called at import time."""
    source_g = SOURCE_ELF.read_bytes()
    prepared_h = prepare(source_g, components)
    if not r67_15g.SOURCE_ISO.is_file() or sha_file(r67_15g.SOURCE_ISO) != r67_15g.SOURCE_ISO_SHA256:
        raise ValueError("approved r67.15f baseline is missing or changed")
    approved_15f = r67_15g._read_approved_inputs()
    regenerated_g, g_report = _compose_pinned_15g()
    combined_changes = dict(g_report["_changed_bytes"])
    combined_changes.update(prepared_h.changed_existing)
    # Recheck all historical accepted locks on the fully composed candidate.
    preservation = r67_15g._verify_15f_preservation(
        approved_15f.source_elf, prepared_h.candidate, r67_15g._source_group4_bytes()
    )
    static_locks = r67_15g._verify_static_locks(approved_15f.source_elf, prepared_h.candidate)
    prepared_iso = r67_15g.PreparedELF(
        approved_15f.source_elf, prepared_h.candidate,
        tuple(g_report["components"]) + prepared_h.components,
        {key: tuple((int(a, 16), int(b, 16)) for a, b in spans)
         for key, spans in g_report["normalized_existing_owners"].items()},
        combined_changes, approved_15f.cvm_sha256, preservation, static_locks,
    )
    output_paths = (OUTPUT_ISO, OUTPUT_ELF, OUTPUT_REPORT, OUTPUT_AUDIT, INCOMPLETE_ISO)
    existing = next((path for path in output_paths if path.exists()), None)
    if existing is not None:
        raise FileExistsError(f"Refusing to overwrite existing r67.15h artifact: {existing}")
    r67_15g.source_executable_capacity(len(prepared_h.candidate))
    r67_15g._copy_on_write(r67_15g.SOURCE_ISO, INCOMPLETE_ISO)
    try:
        from tools.iso9660_patch import find_record, index_iso, patch_directory_record
        import mmap

        with INCOMPLETE_ISO.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
            _, records = index_iso(image)
            executable = find_record(records, r67_15g.EXECUTABLE_NAME)
            start = executable.extent * r67_15g.SECTOR_BYTES
            image[start:start + len(prepared_h.candidate)] = prepared_h.candidate
            patch_directory_record(image, executable.record_offset, size=len(prepared_h.candidate))
            image.flush()
        audit = r67_15g.audit_finished_iso(
            r67_15g.SOURCE_ISO, INCOMPLETE_ISO, prepared_iso, approved_15f.cvm_sha256
        )
        from tools.r67_15g_route_audit import ORIGINAL_ISO
        from tools.r67_15h_rofs_audit import audit as audit_rofs
        finished_rofs = audit_rofs(ORIGINAL_ISO, INCOMPLETE_ISO)
        if finished_rofs["embedded_rofs_file_records"] != 10656:
            raise ValueError("finished image ROFS inventory differs from the diagnosed baseline")
        from tools.startup_acceptance import verify_startup_candidate
        startup = verify_startup_candidate(INCOMPLETE_ISO, r67_15g.HELP_GRAPHICS)
        static = r67_15g._static_reports(prepared_h.candidate, startup, approved_15f.source_elf)
        if static["startup_scoped"].get("checks_passed") != 155:
            raise ValueError("scoped startup report is not 155/155")
        if static["startup_raw"].get("checks_passed") != 154:
            raise ValueError("raw startup report is not the documented 154/155")
        report = make_report(
            prepared_h, SOURCE_ISO_SHA256, SOURCE_ELF_SHA256,
            resource_lookup_evidence=resource_lookup_evidence,
            route_context=_read_route_context(),
        )
        report.update({"candidate_iso_sha256": audit["candidate_iso_sha256"],
                       "whole_iso_audit": audit, "startup_raw": static["startup_raw"],
                       "finished_resource_lookup": finished_rofs,
                       "startup_scoped": static["startup_scoped"],
                       "history": static["history"], "save": static["save"],
                       "r67_15f_preservation": preservation, "static_locks": static_locks})
        _write_exclusive(OUTPUT_ELF, prepared_h.candidate)
        _write_exclusive(OUTPUT_AUDIT, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode())
        _write_exclusive(OUTPUT_REPORT, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
        INCOMPLETE_ISO.rename(OUTPUT_ISO)
        return report
    except Exception:
        # Keep this build's incomplete clone for recovery and forensic inspection.
        raise


if __name__ == "__main__":
    raise SystemExit("Supply the explicit ordered HANT/loading components to build(); no build is run automatically")
