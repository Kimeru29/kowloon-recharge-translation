"""Compose and audit the cumulative r67.15o diagnostic from the pinned n disc."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import mmap
from pathlib import Path

from tools.build_translation_iso import build_translation_iso
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.r67_15h_rofs_audit import audit as audit_rofs
from tools import r67_15k_approved_lock as approved
from tools.r67n_release import verify_installed
from tools.r67o_bundles import BASELINE_ISO_SHA256
from tools.r67o_iso import CVM_HEADER, HOOKS, audit_candidate, validate_native_delta
from tools.translation_overlay import OverlayCollision, OverlayManifest, collect_overlay

RELEASE = "67.15o-cumulative-official-diagnostic"
CHOICE_ELF = "67.15o-ksf-choice-diagnostic.elf"
BUNDLES = "r67o-bundles"
KWLNSCR = "r67o-kwlnscr"
SPEAKERS = "r67o-speakers"
CHOICES = "r67o-choices"
REPORT_HASHES = {
    BUNDLES: "879ab842981954c52f1b0df60c466f0dcba5161b7379818b694609ac22395938",
    KWLNSCR: "4f7c0671e09ea26f916d6d3bb675021f2a202f7fd5a52b33e342fe76e1afa4ab",
    SPEAKERS: "548b58519e885b34f8c536e11dbe4dcd3f5bcfb5c53e50e3fc80c6aa71543bf9",
    CHOICES: "3dc1400704f2a68ce32578febcbbf47b578dc6780596a81ecaa70fb1ae811ba3",
}
STAGED_REPORT_SHA256 = "54c4c87ea8d7d847fdd6324e00e951e7f727b46fa718a2dfe4f0313a6b78392f"


def _read_pinned(path: Path, expected: str) -> bytes:
    raw = path.read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError(f"Pinned input hash drift: {path}")
    return raw


def _collect_mtx_layer(label: str, root: Path, expected: dict[str, str]):
    entries = collect_overlay([(label, root)]).entries
    if any(not item.path.endswith(".MTX") or item.embedded_path != f"ADV/{item.path}"
           or item.path != item.path.upper() for item in entries):
        raise ValueError(f"Only canonical ADV MTX paths are permitted in {label}")
    indexed = {item.path: item for item in entries}
    if indexed.keys() != expected.keys():
        raise ValueError(f"Unexpected MTX inventory in {label}")
    for path, digest in expected.items():
        if indexed[path].sha256 != digest:
            raise ValueError(f"{label} payload hash drift: {path}")
    return indexed


def compose_mtx_overlay(roots, upstream, speakers, unchanged, staged_root, provenance, baseline, report_hashes
                        ) -> OverlayManifest:
    """Allow a speaker overwrite only on the exact preceding bytes."""
    if (provenance.keys() != baseline.keys() or speakers.keys() & unchanged.keys()
            or speakers.keys() | unchanged.keys() != baseline.keys()):
        raise ValueError("Staged and speaker MTX inventories differ from the installed baseline")

    expected_stage = {
        path: {"n_sha256": digest, "input_sha256": digest} for path, digest in baseline.items()
    }
    selected = {}
    for label in (BUNDLES, KWLNSCR):
        contract = upstream[label]
        if selected.keys() & contract.keys():
            raise ValueError("Bundle and KWLNSCR overlays overlap")
        layer = _collect_mtx_layer(label, roots[label], {path: after for path, (_, after) in contract.items()})
        for path, (before, after) in contract.items():
            if baseline.get(path) != before:
                raise ValueError(f"{label} baseline preimage hash drift: {path}")
            expected_stage[path].update(input_sha256=after, producer=label,
                                        producer_report_sha256=report_hashes[label])
        selected.update(layer)

    for path, expected in expected_stage.items():
        if provenance[path] != expected:
            raise ValueError(f"Invalid staged provenance for {path}")
    stage_hashes = {path: row["input_sha256"] for path, row in expected_stage.items()}
    _collect_mtx_layer("staged speaker input", staged_root, stage_hashes)
    for path, digest in unchanged.items():
        if stage_hashes[path] != digest:
            raise ValueError(f"Unchanged speaker input hash drift: {path}")

    speaker_layer = _collect_mtx_layer(
        SPEAKERS, roots[SPEAKERS], {path: row["output_sha256"] for path, row in speakers.items()},
    )
    collisions = []
    for path, item in speaker_layer.items():
        if stage_hashes[path] != speakers[path]["input_sha256"]:
            raise ValueError(f"Invalid speaker input hash for {path}")
        if path in selected:
            previous = selected[path]
            collisions.append(OverlayCollision(path, previous.provenance, previous.sha256,
                                               item.provenance, item.sha256))
    selected.update(speaker_layer)
    return OverlayManifest(tuple(selected[key] for key in sorted(selected)), tuple(collisions))


def _baseline_mtx_and_elf(source: Path) -> tuple[dict[str, str], bytes]:
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if sha256(image).hexdigest() != BASELINE_ISO_SHA256:
            raise ValueError("r67.15n baseline ISO hash drift")
        _, outer = index_iso(image)
        exe = find_record(outer, "SLPM_665.11")
        exe_offset = exe.extent * SECTOR_SIZE
        cvm = find_record(outer, "DATA.CVM").extent * SECTOR_SIZE + CVM_HEADER
        _, records = index_iso(image, cvm)
        hashes = {}
        for record in records:
            if record.is_directory or not record.path.startswith("ADV/") or not record.path.endswith(".MTX"):
                continue
            path = record.path.removeprefix("ADV/")
            if path in hashes:
                raise ValueError(f"Duplicate installed MTX record: {path}")
            start = cvm + record.extent * SECTOR_SIZE
            hashes[path] = sha256(image[start:start + record.size]).hexdigest()
        return hashes, image[exe_offset:exe_offset + exe.size]


def _validate_native_chain(source, choice_elf, native, choice_report, speaker_report) -> dict:
    report = validate_native_delta(source, native)
    if (report["source_elf_sha256"] != choice_report["source_sha256"]
            or sha256(choice_elf).hexdigest() != choice_report["result_sha256"]
            or choice_report["result_sha256"] != speaker_report["source_sha256"]
            or report["native_elf_sha256"] != speaker_report["result_sha256"]):
        raise ValueError("Native producer executable hash chain differs")

    call_addresses = []
    for stage, before, after, digest_key in (
        (choice_report, source, choice_elf, "append_sha256"),
        (speaker_report, choice_elf, native, "appended_sha256"),
    ):
        start, end = stage["appended_extent"]
        if (start, end) != (len(before), len(after)) or sha256(native[start:end]).hexdigest() != stage[digest_key]:
            raise ValueError("Native executable append differs from the producer report")
        for hook in stage["call_sites"]:
            offset = hook["file_offset"]
            if (before[offset:offset + 4].hex() != hook["expected"]
                    or native[offset:offset + 4].hex() != hook["replacement"]):
                raise ValueError(f"Native executable call differs at {hook['address']:#x}")
            call_addresses.append(hook["address"])
    if tuple(sorted(call_addresses)) != HOOKS or report["changed_hook_addresses"] != list(HOOKS):
        raise ValueError("Native executable does not contain all required call owners")
    return report


def release(source: Path, output_dir: Path, producers: dict[str, Path], staged_inputs: Path,
            graphics: Path) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Choose a fresh output directory: {output_dir}")
    source_locks = approved.verify_sources()
    historical_lock = approved.verify_historical_report()
    baseline, source_elf = _baseline_mtx_and_elf(source)

    reports = {label: json.loads(_read_pinned(producers[label] / "report.json", digest))
               for label, digest in REPORT_HASHES.items()}
    staged = json.loads(_read_pinned(staged_inputs / "provenance.json", STAGED_REPORT_SHA256))
    bundle, kwlnscr, speaker, choices = (reports[label] for label in (BUNDLES, KWLNSCR, SPEAKERS, CHOICES))
    for report in (bundle, kwlnscr, speaker, staged):
        if report["baseline_iso_sha256"] != BASELINE_ISO_SHA256:
            raise ValueError("Producer baseline ISO identities differ")
    if speaker["script_provenance_sha256"] != STAGED_REPORT_SHA256 or speaker["script_inputs"] != len(baseline):
        raise ValueError("Speaker source manifest differs from the staged inventory")

    bundle_files = {
        row["path"].removeprefix("ADV/"): (row["installed_sha256"], row["output_sha256"])
        for row in bundle["results"] if row["new_groups"]
    }
    if len(bundle_files) != bundle["files_changed"]:
        raise ValueError("Bundle report contains duplicate MTX paths")
    kwlnscr_files = {"KWLNSCR.MTX": (
        kwlnscr["target"]["installed_mtx_sha256"], kwlnscr["target"]["output_mtx_sha256"],
    )}
    overlay = compose_mtx_overlay(
        {label: producers[label] / "overlay" for label in (BUNDLES, KWLNSCR, SPEAKERS)},
        {BUNDLES: bundle_files, KWLNSCR: kwlnscr_files}, speaker["script_files"],
        speaker["unchanged_input_sha256"], staged_inputs / "ADV", staged["files"], baseline, REPORT_HASHES,
    )

    choice_elf = _read_pinned(producers[CHOICES] / CHOICE_ELF, choices["result_sha256"])
    native_path = producers[SPEAKERS] / "patched.elf"
    native = _read_pinned(native_path, speaker["native"]["result_sha256"])
    native_audit = _validate_native_chain(source_elf, choice_elf, native, choices, speaker["native"])

    output_dir.mkdir(parents=True)
    candidate = output_dir / f"{RELEASE}.iso"
    elf_path = output_dir / f"{RELEASE}.elf"
    staging = candidate.with_suffix(".incomplete")
    build = build_translation_iso(source, staging, overlay, native_path)
    audit = audit_candidate(source, staging, overlay, native)
    installed, elf = verify_installed(staging, overlay, approved.ELF.read_bytes(), graphics)
    rofs = audit_rofs(source, staging)
    startup = installed["static_reports"]
    baseline_hash = approved.sha256_file(source)
    if baseline_hash != BASELINE_ISO_SHA256:
        raise ValueError("r67.15n baseline changed during composition")
    if (audit["unexplained_bytes"] or audit["complete_disc_bytes_compared"] != source.stat().st_size
            or rofs["mismatches"] or rofs["unmatched_records"]
            or len({build["elf_sha256"], audit["installed_elf_sha256"], rofs["installed_elf_sha256"],
                    installed["elf_sha256"]}) != 1
            or audit["expected_and_actual_iso_sha256"] != startup["startup_raw"]["sha256"]):
        raise ValueError("Disc, ROFS, installed ELF, or startup audit differs")
    if approved.verify_sources() != source_locks or approved.verify_historical_report() != historical_lock:
        raise ValueError("Protected source or historical report changed during composition")

    for key in ("startup_raw", "startup_scoped"):
        startup[key]["candidate"] = str(candidate)
    report = {
        "schema_version": 1,
        "release": RELEASE,
        "candidate_iso": str(candidate),
        "candidate_iso_sha256": audit["expected_and_actual_iso_sha256"],
        "source_iso_sha256": baseline_hash,
        "producer_report_sha256": REPORT_HASHES,
        "staged_provenance_sha256": STAGED_REPORT_SHA256,
        "validated_speaker_input_files": len(baseline),
        "build": build,
        "whole_iso_audit": audit,
        "native_delta": native_audit,
        "rofs": rofs,
        "source_locks": source_locks,
        "historical_lock": historical_lock,
        "summary": {
            "bundle_entries": bundle["new_english_entries"],
            "kwlnscr_entries": kwlnscr["new_english_entries"],
            "speaker_occurrences": speaker["summary"]["occurrences"],
            "speaker_files": speaker["summary"]["changed_files"],
            "ksf_payload_writes": 0,
        },
        "runtime_verified": False,
        "gameplay_approved": False,
        **installed,
    }
    elf_path.write_bytes(elf)
    staged_report = output_dir / "release-report.tmp"
    staged_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(candidate)
    staged_report.rename(output_dir / "release-report.json")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("source", "output-dir", "bundles", "kwlnscr", "speakers", "choices", "staged-inputs", "graphics"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = release(
            args.source, args.output_dir,
            {BUNDLES: args.bundles, KWLNSCR: args.kwlnscr, SPEAKERS: args.speakers, CHOICES: args.choices},
            args.staged_inputs, args.graphics,
        )
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: report[key] for key in ("candidate_iso", "candidate_iso_sha256", "summary")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
