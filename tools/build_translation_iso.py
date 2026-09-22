from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import mmap
from pathlib import Path
import shutil
import subprocess
from typing import Any

from tools.cvm import CvmHeader, HEADER_SIZE
from tools.elf_rofs import RofsFileUpdate, find_rofs_record, patch_rofs_records
from tools.iso9660_patch import (
    SECTOR_SIZE,
    find_record,
    index_iso,
    patch_directory_record,
    write_both_u32,
)
from tools.translation_overlay import OverlayManifest, collect_overlay, plan_replacements


def _clone_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    result = subprocess.run(
        ["cp", "-c", str(source), str(destination)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        shutil.copy2(source, destination)


def _sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def build_translation_iso(
    source: Path,
    destination: Path,
    overlay: OverlayManifest,
    translated_elf: Path | None = None,
) -> dict[str, Any]:
    """Apply an ADV translation overlay to the nested DATA.CVM ISO.

    Growing files are append-relocated inside the embedded ISO. The CVM grows
    into the source ISO's existing trailing slack by shifting only the small
    outer tail. The outer ISO file length/declared volume is intentionally kept
    unchanged; insufficient slack is a hard failure.
    """

    if not source.is_file():
        raise ValueError(f"Source ISO does not exist: {source}")
    replacement_data = {entry.path: entry.source_path.read_bytes() for entry in overlay.entries}
    for entry in overlay.entries:
        if len(replacement_data[entry.path]) != entry.size:
            raise ValueError(f"Overlay file changed while building: {entry.source_path}")
        if sha256(replacement_data[entry.path]).hexdigest() != entry.sha256:
            raise ValueError(f"Overlay hash changed while building: {entry.source_path}")

    supplied_elf_bytes = translated_elf.read_bytes() if translated_elf is not None else None
    elf_bytes: bytes | None = None
    rofs_records_patched = 0
    _clone_file(source, destination)
    source_size = source.stat().st_size
    if destination.stat().st_size != source_size:
        raise ValueError("Cloned ISO size differs from pristine source")

    build_rows: list[dict[str, Any]] = []
    growth_sectors = 0
    embedded_volume_before = 0
    outer_volume_before = 0
    old_cvm_size = 0
    old_cvm_end_sector = 0
    highest_outer_sector = 0
    shifted_outer_paths: list[str] = []
    elf_input_extent = 0
    elf_output_extent = 0
    elf_relocated = False

    with destination.open("r+b") as handle:
        image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_WRITE)
        try:
            outer_volume, outer_records = index_iso(image)
            outer_volume_before = outer_volume
            data_cvm = find_record(outer_records, "DATA.CVM")
            old_cvm_size = data_cvm.size
            old_cvm_end_sector = data_cvm.extent + data_cvm.sectors
            highest_outer_sector = max(record.extent + record.sectors for record in outer_records)

            game_elf = find_record(outer_records, "SLPM_665.11")
            elf_input_extent = game_elf.extent
            elf_start = game_elf.extent * SECTOR_SIZE
            pristine_elf_bytes = bytes(image[elf_start:elf_start + game_elf.size])
            base_elf_bytes = supplied_elf_bytes if supplied_elf_bytes is not None else pristine_elf_bytes
            if len(base_elf_bytes) < game_elf.size:
                raise ValueError(
                    f"Translated SLPM_665.11 may not shrink below pristine size "
                    f"{game_elf.size}, got {len(base_elf_bytes)}"
                )

            cvm_base = data_cvm.extent * SECTOR_SIZE
            cvm_header = CvmHeader.parse(bytes(image[cvm_base:cvm_base + HEADER_SIZE]))
            if cvm_header.total_size != data_cvm.size:
                raise ValueError("Outer DATA.CVM directory size disagrees with CVM header")
            payload_base = cvm_base + HEADER_SIZE
            embedded_volume, embedded_records = index_iso(image, payload_base)
            embedded_volume_before = embedded_volume
            if embedded_volume * SECTOR_SIZE != cvm_header.payload_size:
                raise ValueError("Embedded ISO volume size disagrees with CVM payload size")

            records_by_path = {record.path: record for record in embedded_records}
            plan = plan_replacements(
                records_by_path,
                {path: len(data) for path, data in replacement_data.items()},
                append_start=embedded_volume,
            )
            growth_sectors = plan.appended_sectors

            if growth_sectors:
                shifted_records = tuple(
                    record for record in outer_records if record.extent >= old_cvm_end_sector
                )
                if not shifted_records:
                    raise ValueError("No outer tail records found after DATA.CVM")
                if any(record.is_directory for record in shifted_records):
                    raise ValueError("Build does not support relocating an outer ISO directory")
                if highest_outer_sector + growth_sectors > outer_volume:
                    raise ValueError(
                        "Outer ISO has insufficient trailing slack for translated CVM growth: "
                        f"need {growth_sectors} sectors, have {outer_volume - highest_outer_sector}"
                    )

                tail_start = old_cvm_end_sector * SECTOR_SIZE
                tail_end = highest_outer_sector * SECTOR_SIZE
                tail_bytes = bytes(image[tail_start:tail_end])
                shifted_start = tail_start + growth_sectors * SECTOR_SIZE
                image[shifted_start:shifted_start + len(tail_bytes)] = tail_bytes
                for record in shifted_records:
                    patch_directory_record(
                        image,
                        record.record_offset,
                        extent=record.extent + growth_sectors,
                    )
                    shifted_outer_paths.append(record.path)

                growth_bytes = growth_sectors * SECTOR_SIZE
                patch_directory_record(
                    image,
                    data_cvm.record_offset,
                    size=data_cvm.size + growth_bytes,
                )
                grown_header = cvm_header.grow_payload(growth_bytes).compile()
                image[cvm_base:cvm_base + HEADER_SIZE] = grown_header
                embedded_pvd = payload_base + 16 * SECTOR_SIZE
                write_both_u32(image, embedded_pvd + 80, embedded_volume + growth_sectors)

            plan_by_path = plan.by_path
            overlay_by_path = {entry.path: entry for entry in overlay.entries}
            for rel in sorted(replacement_data):
                item = plan_by_path[rel]
                data = replacement_data[rel]
                start = payload_base + item.output_extent * SECTOR_SIZE
                allocation_size = item.output_sectors * SECTOR_SIZE
                if item.relocated:
                    image[start:start + allocation_size] = data + b"\x00" * (allocation_size - len(data))
                else:
                    image[start:start + len(data)] = data

                manifest_entry = overlay_by_path[rel]
                source_record = records_by_path[manifest_entry.embedded_path]
                patch_directory_record(
                    image,
                    source_record.record_offset,
                    extent=item.output_extent if item.relocated else None,
                    size=len(data),
                )
                build_rows.append(
                    {
                        "path": rel,
                        "embedded_path": manifest_entry.embedded_path,
                        "provenance": manifest_entry.provenance,
                        "sha256": manifest_entry.sha256,
                        "size": len(data),
                        "input_size": source_record.size,
                        "input_extent": item.input_extent,
                        "output_extent": item.output_extent,
                        "input_sectors": item.input_sectors,
                        "output_sectors": item.output_sectors,
                        "relocated": item.relocated,
                    }
                )

            rofs_updates = tuple(
                RofsFileUpdate(
                    path=row["embedded_path"],
                    expected_size=row["input_size"],
                    expected_extent=row["input_extent"],
                    size=row["size"],
                    extent=row["output_extent"],
                )
                for row in build_rows
            )
            elf_bytes, rofs_records = patch_rofs_records(base_elf_bytes, rofs_updates)
            rofs_records_patched = len(rofs_records)
            if b"SLPM-66511" not in elf_bytes or b"BISLPM-66511Save" not in elf_bytes:
                raise ValueError("Serial/save identity missing from translated SLPM_665.11")

            elf_output_sectors = (len(elf_bytes) + SECTOR_SIZE - 1) // SECTOR_SIZE
            if elf_output_sectors <= game_elf.sectors:
                elf_output_extent = game_elf.extent
            else:
                elf_relocated = True
                elf_output_extent = highest_outer_sector + growth_sectors
                if elf_output_extent + elf_output_sectors > outer_volume:
                    raise ValueError(
                        "Outer ISO has insufficient trailing slack for translated ELF relocation: "
                        f"need {elf_output_sectors} sectors after {elf_output_extent}, "
                        f"volume ends at {outer_volume}"
                    )

            elf_output_start = elf_output_extent * SECTOR_SIZE
            elf_allocation = elf_output_sectors * SECTOR_SIZE
            image[elf_output_start:elf_output_start + elf_allocation] = (
                elf_bytes + b"\x00" * (elf_allocation - len(elf_bytes))
            )
            patch_directory_record(
                image,
                game_elf.record_offset,
                extent=elf_output_extent if elf_relocated else None,
                size=len(elf_bytes),
            )

            image.flush()
        finally:
            image.close()

    if destination.stat().st_size != source_size:
        raise ValueError("Translated ISO unexpectedly changed total file size")

    # Validate the finished image against pristine source metadata/payloads.
    with source.open("rb") as source_handle, destination.open("rb") as output_handle:
        src = mmap.mmap(source_handle.fileno(), 0, access=mmap.ACCESS_READ)
        out = mmap.mmap(output_handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            src_outer_volume, src_outer_records = index_iso(src)
            out_outer_volume, out_outer_records = index_iso(out)
            if src_outer_volume != out_outer_volume or out_outer_volume != outer_volume_before:
                raise ValueError("Outer ISO declared volume changed")

            src_cvm = find_record(src_outer_records, "DATA.CVM")
            out_cvm = find_record(out_outer_records, "DATA.CVM")
            expected_cvm_size = old_cvm_size + growth_sectors * SECTOR_SIZE
            if out_cvm.extent != src_cvm.extent or out_cvm.size != expected_cvm_size:
                raise ValueError("Finished DATA.CVM metadata is inconsistent")

            if growth_sectors:
                src_tail = {
                    record.path: record
                    for record in src_outer_records
                    if record.extent >= old_cvm_end_sector
                }
                out_tail = {record.path: record for record in out_outer_records}
                for path, before in src_tail.items():
                    after = out_tail[path]
                    if after.extent != before.extent + growth_sectors or after.size != before.size:
                        raise ValueError(f"Outer tail metadata mismatch for {path}")
                    before_bytes = bytes(
                        src[before.extent * SECTOR_SIZE:before.extent * SECTOR_SIZE + before.size]
                    )
                    after_bytes = bytes(
                        out[after.extent * SECTOR_SIZE:after.extent * SECTOR_SIZE + after.size]
                    )
                    if before_bytes != after_bytes:
                        raise ValueError(f"Outer tail payload changed for {path}")

            out_cvm_base = out_cvm.extent * SECTOR_SIZE
            out_header = CvmHeader.parse(bytes(out[out_cvm_base:out_cvm_base + HEADER_SIZE]))
            if out_header.total_size != out_cvm.size:
                raise ValueError("Finished CVM header disagrees with outer directory size")
            out_payload_base = out_cvm_base + HEADER_SIZE
            out_embedded_volume, out_embedded_records = index_iso(out, out_payload_base)
            if out_embedded_volume != embedded_volume_before + growth_sectors:
                raise ValueError("Finished embedded ISO volume size is incorrect")
            out_records = {record.path: record for record in out_embedded_records}

            for entry in overlay.entries:
                record = out_records.get(entry.embedded_path)
                if record is None:
                    raise ValueError(f"Translated output record disappeared: {entry.embedded_path}")
                actual = bytes(
                    out[
                        out_payload_base + record.extent * SECTOR_SIZE:
                        out_payload_base + record.extent * SECTOR_SIZE + record.size
                    ]
                )
                if len(actual) != entry.size or sha256(actual).hexdigest() != entry.sha256:
                    raise ValueError(f"Translated output validation failed for ADV/{entry.path}")

            if elf_bytes is None:
                raise ValueError("Translated SLPM_665.11 was not generated")
            elf_record = find_record(out_outer_records, "SLPM_665.11")
            actual_elf = bytes(
                out[elf_record.extent * SECTOR_SIZE:elf_record.extent * SECTOR_SIZE + elf_record.size]
            )
            if actual_elf != elf_bytes:
                raise ValueError("Translated SLPM_665.11 validation failed")
            if b"SLPM-66511" not in actual_elf or b"BISLPM-66511Save" not in actual_elf:
                raise ValueError("Serial/save identity missing from translated SLPM_665.11")
            for row in build_rows:
                # Re-resolve each finished record against its output metadata.
                # This is the runtime lookup path the previous builder omitted.
                find_rofs_record(actual_elf, row["embedded_path"], row["size"], row["output_extent"])
        finally:
            src.close()
            out.close()

    return {
        "schema_version": 1,
        "source_size": source_size,
        "output_size": destination.stat().st_size,
        "outer_volume_sectors": outer_volume_before,
        "embedded_volume_sectors_before": embedded_volume_before,
        "embedded_volume_sectors_after": embedded_volume_before + growth_sectors,
        "appended_sectors": growth_sectors,
        "overlay_files": len(build_rows),
        "in_place_files": sum(1 for row in build_rows if not row["relocated"]),
        "relocated_files": sum(1 for row in build_rows if row["relocated"]),
        "shifted_outer_files": len(shifted_outer_paths),
        "elf_rofs_records_patched": rofs_records_patched,
        "elf_input_extent": elf_input_extent,
        "elf_output_extent": elf_output_extent,
        "elf_relocated": elf_relocated,
        "elf_size": len(elf_bytes) if elf_bytes is not None else None,
        "collisions": [asdict(collision) for collision in overlay.collisions],
        "files": build_rows,
        "elf_sha256": sha256(elf_bytes).hexdigest() if elf_bytes is not None else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic whole-game PS2 translation ISO")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--overlay",
        nargs=2,
        action="append",
        metavar=("PROVENANCE", "ROOT"),
        required=True,
        help="ADV-relative overlay root; may be repeated in increasing priority order",
    )
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    roots = [(provenance, Path(root)) for provenance, root in args.overlay]
    overlay = collect_overlay(roots)
    report = build_translation_iso(args.source, args.destination, overlay, args.elf)
    report["output_sha256"] = _sha256_file(args.destination)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"files", "collisions"}}, sort_keys=True))
    print(f"output={args.destination}")
    print(f"report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
