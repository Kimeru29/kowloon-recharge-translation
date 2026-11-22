"""Compose and independently audit an r67.15q history-scroll diagnostic from exact r67.15p."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import mmap
from pathlib import Path
from struct import pack_into, unpack_from

from tools import r67p_history_scroll as history
from tools import r67p_release as previous
from tools import r67_15k_approved_lock as approved
from tools.build_translation_iso import build_translation_iso
from tools.r67_15h_item_layout import APPEND_FILE_OFFSET, APPEND_VA, _validate_translation_load
from tools.r67n_release import verify_installed
from tools.r67o_inventory import Disc
from tools.r67o_iso import audit_candidate
from tools.translation_overlay import collect_overlay

BASELINE = Path("local/r67p-validated-a/stage.iso")
BASELINE_INVENTORY = Path("local/r67p-validated-a/inventory")
BASELINE_AUDIT = Path("local/r67p-validated-a/audit.json")
RELEASE = "67.15q-history-scroll-diagnostic"
BASELINE_SHA256 = "00a3396b40e3c241b81b7852c49284551eebab7d3280d0aa9c41028454f26379"
BASELINE_ELF_SHA256 = "c6bd4b0bfe359ebcff107f9e23fa65d365567cff36e747b578a06dfb7ed088fa"
BASELINE_AUDIT_SHA256 = "c52cec99e5a28d876827192a17ef3b113e3319a2acc97411f9c6806aa1cb61f6"
RESOURCE_COUNT = 10656
ELF_BIAS = 0xFFF80
HISTORY_OWNER_OFFSETS = {0x253DB4 - ELF_BIAS, 0x253DB8 - ELF_BIAS}


def digest(data: bytes | mmap.mmap) -> str:
    return sha256(data).hexdigest()


def baseline_elf(source: Path) -> bytes:
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if len(image) != 2_095_382_528 or digest(image) != BASELINE_SHA256:
            raise ValueError("Expected the exact published r67.15p baseline ISO")
        elf = Disc(image).elf
    if digest(elf) != BASELINE_ELF_SHA256:
        raise ValueError("Unexpected executable in the r67.15p baseline")
    _validate_translation_load(elf)
    return elf


def compose_native(source: bytes) -> tuple[bytes, dict]:
    result = bytearray(source)
    result.extend(bytes(-len(result) % 16))
    base = APPEND_VA + len(result) - APPEND_FILE_OFFSET
    code, writes = history.patch(source, base)
    allowed_offsets = HISTORY_OWNER_OFFSETS
    if writes.keys() != allowed_offsets:
        raise ValueError("Unexpected native owner set for ADV history scroll")
    mutations = []
    for offset, (preimage, replacement) in sorted(writes.items()):
        if len(preimage) != 4 or len(replacement) != 4 or not 0x80 <= offset < APPEND_FILE_OFFSET:
            raise ValueError(f"Invalid history owner word at {offset:#x}")
        if offset % 4 or source[offset:offset + 4] != preimage:
            raise ValueError(f"History owner preimage mismatch at {offset:#x}")
        result[offset:offset + 4] = replacement
        mutations.append({"file_offset": offset, "before_hex": preimage.hex(), "after_hex": replacement.hex()})
    result.extend(code)
    file_size = len(result) - APPEND_FILE_OFFSET
    reserve = unpack_from("<I", source, 0x68)[0]
    if file_size > reserve:
        raise ValueError("History helper exceeds the inherited translation reserve")
    pack_into("<I", result, 0x64, file_size)
    _validate_translation_load(result)
    return bytes(result), {
        "owner": "ADV history scroll",
        "appended_at": base,
        "appended_bytes": len(code),
        "code_sha256": digest(code),
        "writes": mutations,
        "original_size": len(source),
        "size": len(result),
        "translation_reserve_bytes": reserve,
        "translation_load_bytes": file_size,
        "remaining_translation_reserve_bytes": reserve - file_size,
        "heap_reserve_unchanged": True,
    }


def verify_native_owners(before: bytes, after: bytes) -> dict:
    allowed = HISTORY_OWNER_OFFSETS | {0x64}
    if len(after) <= len(before):
        raise ValueError("Expected a bounded native append")
    _validate_translation_load(after)
    changed = Counter()
    for offset, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        word = offset & ~3
        if word not in allowed:
            raise ValueError(f"Unowned common-prefix executable byte at {offset:#x}")
        changed[word] += 1
    if changed.keys() != allowed:
        raise ValueError("At least one required history owner did not change")
    return {"common_prefix_changed_bytes": sum(changed.values()),
            "verified_file_offsets": sorted(changed), "appended_bytes": len(after) - len(before)}


def audit_resources(source: Path, stage: Path, overlay) -> tuple[dict, dict]:
    # The p baseline carries all 10,656 resources; q owns no resource overlay.
    rofs, fingerprints = previous.audit_resources(source, stage, overlay)
    if len(fingerprints) != RESOURCE_COUNT:
        raise ValueError("Resource count drift")
    for path, row in fingerprints.items():
        if row["before_sha256"] != row["after_sha256"]:
            raise ValueError(f"Unowned resource changed: {path}")
    return rofs, fingerprints


def bind_inventory(directory: Path, stage: Path, output: Path, p_audit: dict, expected_hash: str):
    lock = {"inventory_sha256": p_audit["inventory_sha256"], "iso_sha256": BASELINE_SHA256}
    inventory_hashes = previous.bind_inventory(directory, stage, output, lock, expected_hash,
                                               release=RELEASE)
    summary = json.loads((output / "summary.json").read_text())
    if summary.get("release") != RELEASE:
        raise ValueError("Rebound inventory summary has the wrong release label")
    if summary.get("immediate_baseline_iso_sha256") != BASELINE_SHA256:
        raise ValueError("Rebound inventory summary has the wrong parent ISO")
    return inventory_hashes


def build(source: Path, inventory: Path, graphics: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("Output directory exists; preserve historical artifacts")
    elf = baseline_elf(source)
    if digest(BASELINE_AUDIT.read_bytes()) != BASELINE_AUDIT_SHA256:
        raise ValueError("The pinned r67.15p audit report changed")
    p_audit = json.loads(BASELINE_AUDIT.read_text())
    if (p_audit.get("iso_sha256") != BASELINE_SHA256 or
            p_audit.get("installed_elf_sha256") != BASELINE_ELF_SHA256):
        raise ValueError("The r67.15p release audit does not match the pinned baseline")
    native, native_report = compose_native(elf)
    overlay = collect_overlay([])
    output.mkdir(parents=True)
    native_path = output / "history-scroll.elf"
    native_path.write_bytes(native)
    stage = output / "stage.iso"
    build_report = build_translation_iso(source, stage, overlay, native_path)
    # Independently audit against the exact p input; the builder report is not input to either audit.
    bytes_report = audit_candidate(source, stage, overlay, native)
    rofs, fingerprints = audit_resources(source, stage, overlay)
    installed, installed_elf = verify_installed(stage, overlay, approved.ELF.read_bytes(), graphics)
    native_report["installed_owner_audit"] = verify_native_owners(elf, installed_elf)
    if digest(installed_elf) != digest(native):
        raise ValueError("Installed executable differs from the composed history candidate")
    if len({build_report["elf_sha256"], bytes_report["installed_elf_sha256"],
            rofs["installed_elf_sha256"], installed["elf_sha256"], digest(installed_elf)}) != 1:
        raise ValueError("Installed ELF identities disagree")
    iso_hash = bytes_report["expected_and_actual_iso_sha256"]
    if iso_hash != installed["static_reports"]["startup_raw"]["sha256"]:
        raise ValueError("Startup verification used a different ISO")

    inventory_hashes = bind_inventory(inventory, stage, output / "inventory", p_audit, iso_hash)
    (output / "installed.elf").write_bytes(installed_elf)
    fingerprints_path = output / "resource-fingerprints.json"
    fingerprints_path.write_text(json.dumps(fingerprints, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    report = {
        "release": RELEASE,
        "iso_sha256": iso_hash,
        "source_iso_sha256": BASELINE_SHA256,
        "immediate_baseline_iso_sha256": BASELINE_SHA256,
        "installed_elf_sha256": digest(installed_elf),
        "native": native_report,
        "build": build_report,
        "whole_disc_audit": bytes_report,
        "rofs": rofs,
        "resource_fingerprints_sha256": approved.sha256_file(fingerprints_path),
        "inventory_sha256": inventory_hashes,
        "immediate_baseline_inventory_sha256": p_audit["inventory_sha256"],
        "static_reports": installed["static_reports"],
        "static_locks": installed["static_locks"],
        "runtime_verified": False,
        "gameplay_approved": False,
    }
    (output / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BASELINE)
    parser.add_argument("--inventory", type=Path, default=BASELINE_INVENTORY)
    parser.add_argument("--graphics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = build(args.source, args.inventory, args.graphics, args.output_dir)
    print(f"{report['iso_sha256']}  {args.output_dir / 'stage.iso'}")


if __name__ == "__main__":
    main()
