"""Build and audit the fixed-size, resource-only r67.15l diagnostic ISO."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib
import json
import mmap
from pathlib import Path
from typing import Sequence

from tools import r67_15g_iso_release as g
from tools import r67_15k_approved_lock as k_lock
from tools.iso9660_patch import IsoRecord, find_record, index_iso
from tools.r67_15h_rofs_audit import audit as audit_rofs
from tools.r67_15g_route_audit import ORIGINAL_ISO
from tools.startup_acceptance import verify_startup_candidate

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ISO = k_lock.ISO
SOURCE_ISO_SHA256 = k_lock.manifest()["iso_sha256"]
APPROVED_ELF_SHA256 = k_lock.manifest()["installed_elf_sha256"]
PHYSICAL_BYTES = 2_095_382_528
SECTOR_BYTES = 2048
DATA_CVM_HEADER_BYTES = 0x1800
EXECUTABLE_NAME = "SLPM_665.11"
DATA_CVM_NAME = "DATA.CVM"
GROUP4_PATH = "BLBRD/B_GP004.BIN"
WHEEL_RESOURCE_PATH = "BLBRD/B_GP001.BIN"
WHEEL_RESOURCE_OFFSET = 0x2ED7A800
WHEEL_RESOURCE_SIZE = 603_520

OUTPUT_ISO = ROOT / "local/r67-candidates/67.15l-emotion-wheel.iso"
OUTPUT_ELF = ROOT / "local/r67-15l-emotion-wheel.elf"
OUTPUT_REPORT = ROOT / "local/r67-15l-emotion-wheel.json"
OUTPUT_AUDIT = ROOT / "local/r67-15l-whole-iso-audit.json"
INCOMPLETE_ISO = OUTPUT_ISO.with_suffix(".incomplete")


@dataclass(frozen=True)
class ResourceReplacement:
    path: str
    original: bytes
    replacement: bytes


@dataclass(frozen=True)
class _Inventory:
    executable: IsoRecord
    executable_offset: int
    cvm: IsoRecord
    cvm_offset: int
    cvm_base: int
    group4: IsoRecord
    group4_offset: int
    resources: dict[str, tuple[IsoRecord, int]]
    all_resources: dict[str, IsoRecord]


def prepare() -> tuple[ResourceReplacement, dict]:
    """Compose the approved wheel art and native coverage proofs from r67.15k."""
    _verify_approved_source(SOURCE_ISO)
    with SOURCE_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        inventory = _inventory(image, (WHEEL_RESOURCE_PATH,))
        resource_record, resource_offset = inventory.resources[WHEEL_RESOURCE_PATH]
        if (resource_offset != WHEEL_RESOURCE_OFFSET
                or resource_record.size != WHEEL_RESOURCE_SIZE):
            raise ValueError("approved wheel resource offset or size changed")
        original = bytes(image[resource_offset:resource_offset + resource_record.size])
        executable = bytes(image[inventory.executable_offset:
                                 inventory.executable_offset + inventory.executable.size])
    if hashlib.sha256(executable).hexdigest() != APPROVED_ELF_SHA256:
        raise ValueError("Installed executable is not the exact approved r67.15k ELF")

    artwork = importlib.import_module("tools.r67_15l_emotion_wheel")
    native = importlib.import_module("tools.r67_15l_native_coverage")
    replacement, artwork_report = artwork.apply(original)
    native_report = native.verify(executable)
    row = ResourceReplacement(WHEEL_RESOURCE_PATH, original, replacement)
    _validate_replacements((row,))
    return row, {"artwork": artwork_report, "native_coverage": native_report}


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalized_path(path: str) -> str:
    if not isinstance(path, str) or not path.strip() or "\\" in path or "\0" in path:
        raise ValueError("resource path must be a non-empty nested DATA.CVM ISO path")
    normalized = path.strip("/").upper()
    if any(part in ("", ".", "..") for part in normalized.split("/")):
        raise ValueError(f"invalid nested DATA.CVM resource path: {path!r}")
    return normalized


def _file_inventory(records: Sequence[IsoRecord]) -> dict[str, IsoRecord]:
    files = [record for record in records if not record.is_directory]
    result = {record.path.upper(): record for record in files}
    if len(result) != len(files):
        raise ValueError("duplicate nested DATA.CVM file path")
    if not result:
        raise ValueError("empty nested DATA.CVM file inventory")
    return result


def _inventory(image, replacement_paths: Sequence[str] = ()) -> _Inventory:
    _, outer = index_iso(image)
    executable = find_record(outer, EXECUTABLE_NAME)
    cvm = find_record(outer, DATA_CVM_NAME)
    executable_offset = executable.extent * SECTOR_BYTES
    cvm_offset = cvm.extent * SECTOR_BYTES
    cvm_end = cvm_offset + cvm.size
    cvm_base = cvm_offset + DATA_CVM_HEADER_BYTES
    if (executable_offset + executable.size > len(image)
            or cvm_end > len(image) or cvm_base >= cvm_end):
        raise ValueError("executable or DATA.CVM extends outside the ISO")

    _, nested = index_iso(image, cvm_base)
    files = _file_inventory(nested)
    for record in nested:
        start = cvm_base + record.extent * SECTOR_BYTES
        if start + record.size > cvm_end:
            raise ValueError(f"nested DATA.CVM record outside container: {record.path}")
    group4 = find_record(nested, GROUP4_PATH)
    group4_offset = cvm_base + group4.extent * SECTOR_BYTES

    resources: dict[str, tuple[IsoRecord, int]] = {}
    claimed_spans: list[tuple[int, int, str]] = []
    for raw_path in replacement_paths:
        path = _normalized_path(raw_path)
        matches = [record for key, record in files.items() if key == path]
        if len(matches) != 1:
            raise ValueError(f"expected exactly one nested DATA.CVM file for {raw_path!r}, found {len(matches)}")
        record = matches[0]
        absolute = cvm_base + record.extent * SECTOR_BYTES
        end = absolute + record.size
        for prior_start, prior_end, prior_path in claimed_spans:
            if absolute < prior_end and prior_start < end:
                raise ValueError(f"overlapping resource replacements: {prior_path} and {raw_path}")
        claimed_spans.append((absolute, end, raw_path))
        resources[path] = (record, absolute)

    return _Inventory(executable, executable_offset, cvm, cvm_offset, cvm_base,
                      group4, group4_offset, resources, files)


def _validate_replacements(replacements: Sequence[ResourceReplacement]) -> tuple[ResourceReplacement, ...]:
    rows = tuple(replacements)
    if not rows:
        raise ValueError("at least one resource replacement is required")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, ResourceReplacement):
            raise TypeError("replacements must contain ResourceReplacement values")
        path = _normalized_path(row.path)
        if path in seen:
            raise ValueError(f"duplicate resource replacement path: {row.path}")
        seen.add(path)
        if not isinstance(row.original, bytes) or not isinstance(row.replacement, bytes):
            raise TypeError(f"resource preimage and replacement must be bytes: {row.path}")
        if not row.original or len(row.original) != len(row.replacement):
            raise ValueError(f"resource replacement must be non-empty and same-length: {row.path}")
        if row.original == row.replacement:
            raise ValueError(f"resource replacement has no changed bytes: {row.path}")
    return rows


def _verify_approved_source(source: Path) -> dict:
    if source != SOURCE_ISO or source != k_lock.ISO:
        raise ValueError("Source ISO is not the approved gameplay-tested r67.15k image")
    source_locks = k_lock.verify_sources()
    historical = k_lock.verify_historical_report()
    approved_iso = k_lock.verify_approved_iso()
    actual_sha = _sha_file(source)
    if actual_sha != SOURCE_ISO_SHA256 or approved_iso.get("iso_sha256") != SOURCE_ISO_SHA256:
        raise ValueError("Approved r67.15k source ISO SHA-256 mismatch")
    if source.stat().st_size != PHYSICAL_BYTES:
        raise ValueError("Approved r67.15k source ISO physical size mismatch")
    return {"source_lock": source_locks, "historical_report": historical,
            "approved_iso": approved_iso, "source_iso_sha256": actual_sha}


def _read_installed_locks(image, inventory: _Inventory) -> tuple[bytes, bytes, dict]:
    elf = bytes(image[inventory.executable_offset:
                      inventory.executable_offset + inventory.executable.size])
    group4 = bytes(image[inventory.group4_offset:
                         inventory.group4_offset + inventory.group4.size])
    proof = k_lock.verify_installed(elf, group4)
    if hashlib.sha256(elf).hexdigest() != APPROVED_ELF_SHA256:
        raise ValueError("Installed executable is not the exact approved r67.15k ELF")
    return elf, group4, proof


def _expected_replacements(image, inventory: _Inventory,
                           replacements: Sequence[ResourceReplacement]) -> tuple[dict[int, tuple[int, str]], dict[str, int]]:
    expected: dict[int, tuple[int, str]] = {}
    counts: Counter[str] = Counter()
    for row in replacements:
        path = _normalized_path(row.path)
        record, offset = inventory.resources[path]
        if len(row.original) != record.size:
            raise ValueError(f"resource replacement length does not match ISO record size: {row.path}")
        current = bytes(image[offset:offset + record.size])
        if current != row.original:
            raise ValueError(f"resource preimage mismatch: {row.path}")
        for index, (old, new) in enumerate(zip(row.original, row.replacement, strict=True)):
            if old != new:
                expected[offset + index] = (new, path)
                counts[path] += 1
    return expected, dict(sorted(counts.items()))


def _assert_same_layout(left: _Inventory, right: _Inventory) -> None:
    if (left.executable != right.executable or left.executable_offset != right.executable_offset
            or left.cvm != right.cvm or left.cvm_offset != right.cvm_offset
            or left.cvm_base != right.cvm_base or left.group4 != right.group4
            or left.group4_offset != right.group4_offset
            or left.all_resources != right.all_resources):
        raise ValueError("candidate changed ISO executable/CVM/resource metadata or layout")


def audit_finished_iso(source: Path, candidate: Path,
                       replacements: Sequence[ResourceReplacement]) -> dict:
    """Prove every byte on the approved-size image equals the authorized patch set."""
    rows = _validate_replacements(replacements)
    source_locks = _verify_approved_source(source)
    if not candidate.is_file():
        raise FileNotFoundError(candidate)

    with source.open("rb") as source_stream, candidate.open("rb") as candidate_stream:
        with mmap.mmap(source_stream.fileno(), 0, access=mmap.ACCESS_READ) as original, \
                mmap.mmap(candidate_stream.fileno(), 0, access=mmap.ACCESS_READ) as finished:
            if len(original) != PHYSICAL_BYTES or len(finished) != PHYSICAL_BYTES:
                raise ValueError("finished ISO physical length differs from approved 2,095,382,528 bytes")
            source_inventory = _inventory(original, tuple(row.path for row in rows))
            candidate_inventory = _inventory(finished, tuple(row.path for row in rows))
            _assert_same_layout(source_inventory, candidate_inventory)
            source_elf, source_group4, source_installed_lock = _read_installed_locks(original, source_inventory)
            candidate_elf, candidate_group4, candidate_installed_lock = _read_installed_locks(finished, candidate_inventory)
            if candidate_elf != source_elf:
                raise ValueError("resource-only candidate changed the approved executable")
            if candidate_group4 != source_group4:
                raise ValueError("resource-only candidate changed approved Group-4 artwork")

            expected, counts = _expected_replacements(original, source_inventory, rows)
            changed = g.compare_expected_bytes(original, finished, expected)
            if changed != counts:
                raise ValueError("full-image changed-byte counts differ from resource replacements")
            for row in rows:
                path = _normalized_path(row.path)
                _, source_offset = source_inventory.resources[path]
                _, candidate_offset = candidate_inventory.resources[path]
                actual = bytes(finished[candidate_offset:candidate_offset + len(row.replacement)])
                if actual != row.replacement:
                    raise ValueError(f"candidate resource differs from exact authorized replacement: {row.path}")

            return {
                "status": "PASS_EXACT_RESOURCE_ONLY_ZERO_UNEXPLAINED",
                "baseline_release": "r67.15k",
                "baseline_iso_sha256": source_locks["source_iso_sha256"],
                "candidate_iso_sha256": _sha_file(candidate),
                "complete_disc_bytes_compared": len(original),
                "modified_bytes": sum(changed.values()),
                "resource_changed_bytes": changed,
                "unexplained_bytes": 0,
                "resource_replacements": len(rows),
                "installed_elf_sha256": hashlib.sha256(candidate_elf).hexdigest(),
                "approved_elf_lock": candidate_installed_lock,
                "approved_group4_lock": source_installed_lock,
                "source_approved_group4_sha256": hashlib.sha256(source_group4).hexdigest(),
                "candidate_approved_group4_sha256": hashlib.sha256(candidate_group4).hexdigest(),
                "no_elf_changes": True,
                "no_group4_changes": True,
            }


def _assert_output_paths_available() -> None:
    paths = (OUTPUT_ISO, OUTPUT_ELF, OUTPUT_REPORT, OUTPUT_AUDIT, INCOMPLETE_ISO)
    for path in paths:
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite release artifact: {path}")


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()


def build(replacements: Sequence[ResourceReplacement], components: dict | None = None) -> dict:
    """Build the r67.15l diagnostic from approved k; never edits the ELF."""
    _assert_output_paths_available()
    rows = _validate_replacements(replacements)
    approved = _verify_approved_source(SOURCE_ISO)
    with SOURCE_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as source_image:
        source_inventory = _inventory(source_image, tuple(row.path for row in rows))
        source_elf, source_group4, _ = _read_installed_locks(source_image, source_inventory)
        if source_elf != k_lock.ELF.read_bytes():
            raise ValueError("Installed r67.15k executable differs from its staged ELF")
        _expected_replacements(source_image, source_inventory, rows)

    locks = g._verify_static_locks(source_elf, source_elf)
    if len(locks["history_lock_regions"]) != 4 or locks["save_identity"]["native_save_descriptors"] != 15:
        raise ValueError("Approved history or native save identity checks changed")
    g._copy_on_write(SOURCE_ISO, INCOMPLETE_ISO)
    with INCOMPLETE_ISO.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
        inventory = _inventory(image, tuple(row.path for row in rows))
        _assert_same_layout(source_inventory, inventory)
        for row in rows:
            path = _normalized_path(row.path)
            record, offset = inventory.resources[path]
            if len(row.replacement) != record.size or bytes(image[offset:offset + record.size]) != row.original:
                raise ValueError(f"resource preimage or size changed before patch: {row.path}")
            image[offset:offset + record.size] = row.replacement
        image.flush()

    audit = audit_finished_iso(SOURCE_ISO, INCOMPLETE_ISO, rows)
    resource_lookup = audit_rofs(ORIGINAL_ISO, INCOMPLETE_ISO)
    if resource_lookup["embedded_rofs_file_records"] != 10656:
        raise ValueError("finished ROFS inventory changed")
    startup = verify_startup_candidate(INCOMPLETE_ISO, g.HELP_GRAPHICS)
    static = g._static_reports(source_elf, startup, source_elf)
    if (static["startup_raw"]["checks_passed"], static["startup_scoped"]["checks_passed"]) != (154, 155):
        raise ValueError("startup acceptance changed")

    report = {
        "release": "r67.15l",
        "status": "BUILT_STATIC_VERIFIED_RUNTIME_PENDING",
        "gameplay_approved": False,
        "runtime_verified": False,
        "baseline_gameplay_approved": True,
        "input_iso_sha256": approved["source_iso_sha256"],
        "input_elf_sha256": APPROVED_ELF_SHA256,
        "candidate_iso_sha256": audit["candidate_iso_sha256"],
        "candidate_elf_sha256": APPROVED_ELF_SHA256,
        "resource_replacements": [
            {"path": row.path, "size": len(row.replacement),
             "changed_bytes": audit["resource_changed_bytes"][_normalized_path(row.path)]}
            for row in rows
        ],
        "components": components or {},
        "whole_iso_audit": audit,
        "finished_resource_lookup": resource_lookup,
        "static_locks": locks,
        **static,
        "original_cards_and_savestates_not_modified": True,
    }
    _write_exclusive(OUTPUT_ELF, source_elf)
    _write_exclusive(OUTPUT_AUDIT, (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode())
    _write_exclusive(OUTPUT_REPORT, (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
    INCOMPLETE_ISO.rename(OUTPUT_ISO)
    return report


def main() -> int:
    replacement, components = prepare()
    report = build((replacement,), components=components)
    print(json.dumps({"candidate_iso_sha256": report["candidate_iso_sha256"],
                      "status": report["status"], "report": str(OUTPUT_REPORT)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
