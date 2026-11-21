"""Compose and independently audit an r67.15p diagnostic stage from exact r67.15o."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import mmap
from pathlib import Path
from struct import pack_into, unpack_from

from tools import r67_15k_approved_lock as approved
from tools import r67p_caption_geometry as captions
from tools import r67p_choice_geometry as choices
from tools import r67p_dialogue_geometry as dialogue
from tools import r67p_hant_scroll as help_scroll
from tools import r67p_speaker_geometry as speakers
from tools import r67p_surface_art as artwork
from tools.build_translation_iso import build_translation_iso
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.r67_15h_item_layout import APPEND_FILE_OFFSET, APPEND_VA, _validate_translation_load
from tools.r67_15h_rofs_audit import audit_records
from tools.r67n_release import verify_installed
from tools.r67o_inventory import Disc
from tools.r67o_iso import CVM_HEADER, audit_candidate
from tools.translation_overlay import collect_overlay

LOCK = Path(__file__).resolve().parents[1] / "translations/r67o_release_lock.json"
BASELINE = Path("local/r67o-release/67.15o-cumulative-official-diagnostic.iso")
BASELINE_INVENTORY = Path("local/r67o-inventory-final")
RELEASE = "67.15p-cumulative-geometry-diagnostic"
RESOURCE_COUNT = 10656
ELF = "SLPM_665.11"
ELF_BIAS = 0xFFF80


def digest(data):
    return sha256(data).hexdigest()


def baseline_elf(source, lock):
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if len(image) != lock["iso_bytes"] or digest(image) != lock["iso_sha256"]:
            raise ValueError("Expected the exact r67.15o baseline ISO")
        elf = Disc(image).elf
    if digest(elf) != lock["installed_elf_sha256"]:
        raise ValueError("Unexpected executable in the r67.15o baseline")
    _validate_translation_load(elf)
    return elf


def geometry_components():
    return (
        ("ADV scene caption", captions.patch, {0x250D6C - ELF_BIAS, 0x250E00 - ELF_BIAS}),
        ("ADV primary dialogue", dialogue.patch, {0x24EA20 - ELF_BIAS, 0x24EA58 - ELF_BIAS}),
        ("ADV speaker header", speakers.patch, {0x250010 - ELF_BIAS}),
        ("ADV stock choice geometry", choices.patch, {0x251594 - ELF_BIAS, 0x2516A8 - ELF_BIAS}),
        ("H.A.N.T. Help scroll extent", help_scroll.patch, {0x290A00 - ELF_BIAS, 0x290A04 - ELF_BIAS}),
    )


def compose_native(source, components):
    result = bytearray(source)
    claimed = set()
    report = []
    for name, producer, allowed_offsets in components:
        result.extend(bytes(-len(result) % 16))
        base = APPEND_VA + len(result) - APPEND_FILE_OFFSET
        code, writes = producer(source, base)
        if writes.keys() != allowed_offsets:
            raise ValueError(f"Unexpected native owner set for {name}")
        mutations = []
        for offset, (preimage, replacement) in sorted(writes.items()):
            if len(preimage) != 4 or len(replacement) != 4 or not 0x80 <= offset < APPEND_FILE_OFFSET:
                raise ValueError(f"Invalid word extent for {name} at {offset:#x}")
            if offset % 4 or offset in claimed or source[offset:offset + 4] != preimage:
                raise ValueError(f"Native hook overlaps or differs from its preimage at {offset:#x}")
            result[offset:offset + 4] = replacement
            claimed.add(offset)
            mutations.append({"file_offset": offset, "ee_address": offset + ELF_BIAS,
                              "before_hex": preimage.hex(), "after_hex": replacement.hex()})
        report.append({"owner": name, "appended_at": base, "appended_bytes": len(code),
                       "code_sha256": digest(code), "writes": mutations})
        result.extend(code)
    file_size = len(result) - APPEND_FILE_OFFSET
    reserve = unpack_from("<I", source, 0x68)[0]
    if file_size > reserve:
        raise ValueError("Native layout exceeds the inherited translation reserve")
    pack_into("<I", result, 0x64, file_size)
    _validate_translation_load(result)
    return bytes(result), {"owners": report, "original_size": len(source), "size": len(result),
                           "translation_reserve_bytes": reserve,
                           "translation_load_bytes": file_size,
                           "remaining_translation_reserve_bytes": reserve - file_size,
                           "heap_reserve_unchanged": True}


def verify_native_owners(before, after, components):
    allowed = {0x64}
    for _, _, offsets in components:
        allowed.update(offsets)
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
        raise ValueError("At least one required native owner did not change")
    return {
        "common_prefix_changed_bytes": sum(changed.values()),
        "verified_file_offsets": sorted(changed),
        "appended_bytes": len(after) - len(before),
    }


def _index(image):
    volume, outer = index_iso(image)
    cvm = find_record(outer, "DATA.CVM")
    start = cvm.extent * SECTOR_SIZE + CVM_HEADER
    nested_volume, records = index_iso(image, start)
    if volume * SECTOR_SIZE != len(image) or cvm.size != CVM_HEADER + nested_volume * SECTOR_SIZE:
        raise ValueError("ISO/CVM volume declarations differ from their allocated sizes")
    for total, listing in ((volume, outer), (nested_volume, records)):
        extents = sorted((row.extent, row.extent + row.sectors, row.path) for row in listing if row.sectors)
        previous_end = 0
        for lo, hi, path in extents:
            if lo < previous_end or hi > total:
                raise ValueError(f"Overlapping or out-of-bounds sector-aligned extent: {path}")
            previous_end = hi
    executable = find_record(outer, ELF)
    offset = executable.extent * SECTOR_SIZE
    return start, records, image[offset:offset + executable.size]


def audit_resources(source, stage, overlay):
    overrides = {entry.embedded_path: entry.sha256 for entry in overlay.entries}
    with source.open("rb") as af, stage.open("rb") as bf, \
            mmap.mmap(af.fileno(), 0, access=mmap.ACCESS_READ) as old, \
            mmap.mmap(bf.fileno(), 0, access=mmap.ACCESS_READ) as new:
        old_cvm, old_records, old_elf = _index(old)
        new_cvm, new_records, new_elf = _index(new)
        rofs = audit_records(old_elf, new_elf, old_records, new_records)
        before = {row.path: row for row in old_records if not row.is_directory}
        fingerprints = {}
        for after in new_records:
            if after.is_directory:
                continue
            prior = before[after.path]
            offset = new_cvm + after.extent * SECTOR_SIZE
            start = old_cvm + prior.extent * SECTOR_SIZE
            old_hash = digest(old[start:start + prior.size])
            new_hash = digest(new[offset:offset + after.size])
            if after.path not in overrides and (after.extent, after.size) != (prior.extent, prior.size):
                raise ValueError(f"Unowned resource extent or size changed: {after.path}")
            if new_hash != overrides.get(after.path, old_hash):
                raise ValueError(f"Unexpected resource fingerprint: {after.path}")
            fingerprints[after.path] = {"before_sha256": old_hash, "after_sha256": new_hash,
                                        "extent": after.extent, "size": after.size}
    if len(fingerprints) != RESOURCE_COUNT:
        raise ValueError("Resource count drift")
    return rofs, fingerprints


def _verify_row(image, offset, size, expected, owner):
    if digest(image[offset:offset + size]) != expected:
        raise ValueError(f"Installed inventory span differs for {owner} at {offset:#x}")


def _write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def bind_inventory(directory, stage, output, lock, expected_hash):
    data = {}
    for name, expected in lock["inventory_sha256"].items():
        raw = (directory / name).read_bytes()
        if digest(raw) != expected:
            raise ValueError(f"Baseline inventory differs: {name}")
        data[name] = json.loads(raw)

    with stage.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if digest(image) != expected_hash:
            raise ValueError("Inventory is binding a different ISO")
        disc = Disc(image)
        new_offsets = {ELF: disc.elf_offset}
        previous_elf_offset = None
        for row in data["files.json"]:
            path = row["path"]
            offset, payload = disc.asset(path)
            if len(payload) != row["size"] or digest(payload) != row["installed_sha256"]:
                raise ValueError(f"ADV payload preservation failed: {path}")
            if row["iso_offset"] != offset:
                raise ValueError(f"ADV record moved during geometry-only composition: {path}")
            new_offsets[path] = offset

        verified = 0
        for row in data["entries.json"]:
            if "installed_iso_offset" not in row:
                continue
            asset = row["installed_asset"]
            offset = new_offsets[asset] + row["installed_offset"]
            if asset == ELF:
                previous = row["installed_iso_offset"] - row["installed_offset"]
                if previous_elf_offset is not None and previous != previous_elf_offset:
                    raise ValueError("Baseline guarded choice inventory has inconsistent ELF offsets")
                previous_elf_offset = previous
                row["installed_iso_offset"] = offset
                _verify_row(image, new_offsets[row["native_ksf_asset"]] + row["native_ksf_offset"], 30,
                            row["native_ksf_preimage_sha256"], row["file"])
            elif offset != row["installed_iso_offset"]:
                raise ValueError(f"Inconsistent installed offset: {asset}")
            _verify_row(image, offset, row["installed_length"], row["installed_bytes_sha256"], asset)
            verified += 1
        if previous_elf_offset is None:
            raise ValueError("Guarded choices missing from the pinned inventory")
        delta = disc.elf_offset - previous_elf_offset

        for row in data["ksf-labels.json"]:
            _verify_row(image, row["iso_offset"], 30, row["installed_payload_sha256"], row["file"])
            if row.get("operative_owner") == ELF:
                row["operative_label_iso_offset"] += delta
                _verify_row(image, row["operative_label_iso_offset"], row["operative_label_length"],
                            row["operative_label_sha256"], row["file"])

        for row in data["japanese.json"]:
            _verify_row(image, row["iso_offset"], row["byte_length"], row["installed_bytes_sha256"], row["file"])
            if row.get("operative_owner") == ELF:
                row["operative_label_iso_offset"] += delta

        for row in data["speakers.json"]["occurrences"]:
            start, end = row["output_span"]
            _verify_row(image, row["installed_iso_offset"], end - start, row["output_span_sha256"], row["file"])

        summary = data["summary.json"]
        summary.update(release=RELEASE, iso_sha256=expected_hash, installed_elf_sha256=digest(disc.elf),
                       immediate_baseline_iso_sha256=lock["iso_sha256"],
                       inventory_preservation={"base_inventory_sha256": lock["inventory_sha256"],
                                               "asset_files_verified": len(new_offsets) - 1,
                                               "installed_ranges_verified": verified})
    output.mkdir()
    for name, content in data.items():
        _write_json(output / name, content)
    _write_json(output / "remaining-official-entries.json",
                [row for row in data["entries.json"] if row["status"] == "correspondence unresolved"])
    return {path.name: approved.sha256_file(path) for path in sorted(output.glob("*.json"))}


def build(source, inventory, graphics, output):
    lock = json.loads(LOCK.read_bytes())
    elf = baseline_elf(source, lock)
    source_locks = approved.verify_sources()
    historical_report = approved.verify_historical_report()
    components = geometry_components()
    native, native_report = compose_native(elf, components)
    artwork_payloads = artwork.build_overlays(source)
    if {path: digest(raw) for path, raw in artwork_payloads.items()} != {
        "BLBRD/B_GP059.BIN": "f0ba2ba39ea16940c46e3a73d3966b41a346448f06a536f04dcd68c99c55ffb3"
    }:
        raise ValueError("Unexpected installed artwork write set")

    output.mkdir(parents=True, exist_ok=False)
    art_root = output / "artwork"
    for path, raw in artwork_payloads.items():
        target = art_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    overlay = collect_overlay([("PS4 H.A.N.T. recording popup", art_root)])
    native_path = output / "geometry.elf"
    native_path.write_bytes(native)
    stage = output / "stage.iso"
    build_report = build_translation_iso(source, stage, overlay, native_path)
    # The auditor derives expected directory writes, ROFS changes and padding
    # from the exact baseline and composable inputs. It never reads build_report.
    bytes_report = audit_candidate(source, stage, overlay, native)
    rofs, fingerprints = audit_resources(source, stage, overlay)
    installed, installed_elf = verify_installed(stage, overlay, approved.ELF.read_bytes(), graphics)
    native_report["installed_owner_audit"] = verify_native_owners(elf, installed_elf, components)
    artwork_elf, installed_artwork = artwork.read_artwork(stage)
    if installed_elf != artwork_elf:
        raise ValueError("Artwork proof used a different executable")
    wheel = artwork.verify_wheel(installed_elf, installed_artwork["BLBRD/B_GP001.BIN"])
    popup = artwork.verify_hant_recording_owner(installed_elf)
    if installed_artwork["BLBRD/B_GP059.BIN"] != artwork_payloads["BLBRD/B_GP059.BIN"]:
        raise ValueError("H.A.N.T. recording texture was not installed")
    if len({build_report["elf_sha256"], bytes_report["installed_elf_sha256"], rofs["installed_elf_sha256"],
            installed["elf_sha256"], digest(installed_elf)}) != 1:
        raise ValueError("Installed ELF identities disagree")
    iso_hash = bytes_report["expected_and_actual_iso_sha256"]
    if iso_hash != installed["static_reports"]["startup_raw"]["sha256"]:
        raise ValueError("Startup verification used a different ISO")
    if (approved.verify_sources() != source_locks or approved.verify_historical_report() != historical_report
            or approved.sha256_file(source) != lock["iso_sha256"]):
        raise ValueError("Protected release inputs changed during composition")

    inventory_hashes = bind_inventory(inventory, stage, output / "inventory", lock, iso_hash)
    (output / "installed.elf").write_bytes(installed_elf)
    _write_json(output / "resource-fingerprints.json", fingerprints)
    report = {"release": RELEASE, "iso_sha256": iso_hash, "source_iso_sha256": lock["iso_sha256"],
              "installed_elf_sha256": digest(installed_elf), "native": native_report,
              "build": build_report, "whole_disc_audit": bytes_report, "rofs": rofs,
              "resource_fingerprints_sha256": approved.sha256_file(output / "resource-fingerprints.json"),
              "inventory_sha256": inventory_hashes, "protected_sources": source_locks,
              "historical_report": historical_report, "approved_k_iso": approved.verify_approved_iso(),
              "emotion_wheel": wheel, "hant_recording_popup": popup, "runtime_verified": False, **installed}
    _write_json(output / "audit.json", report)
    return report


def main():
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
