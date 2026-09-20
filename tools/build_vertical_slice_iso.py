from __future__ import annotations

import argparse
import hashlib
import mmap
import os
from pathlib import Path
import shutil
import subprocess

from tools.cvm import CvmHeader, HEADER_SIZE
from tools.iso9660_patch import (
    SECTOR_SIZE,
    find_record,
    index_iso,
    patch_directory_record,
    write_both_u32,
)


def _sectors(size: int) -> int:
    return (size + SECTOR_SIZE - 1) // SECTOR_SIZE


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    if result.returncode == 0:
        return
    shutil.copy2(source, destination)


def build(
    source: Path,
    destination: Path,
    translated_mtx: Path,
    translated_ksf: Path,
    translated_elf: Path | None = None,
) -> None:
    mtx_bytes = translated_mtx.read_bytes()
    ksf_bytes = translated_ksf.read_bytes()
    elf_bytes = translated_elf.read_bytes() if translated_elf is not None else None

    _clone_file(source, destination)
    source_size = source.stat().st_size
    if destination.stat().st_size != source_size:
        raise ValueError("Cloned ISO size differs from source before patching")

    with destination.open("r+b") as handle:
        image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_WRITE)
        try:
            outer_volume, outer_records = index_iso(image)
            data_cvm = find_record(outer_records, "DATA.CVM")
            game_elf = find_record(outer_records, "SLPM_665.11")
            if elf_bytes is not None:
                if len(elf_bytes) != game_elf.size:
                    raise ValueError(
                        f"Translated SLPM_665.11 must stay {game_elf.size} bytes, got {len(elf_bytes)}"
                    )
                elf_start = game_elf.extent * SECTOR_SIZE
                image[elf_start:elf_start + len(elf_bytes)] = elf_bytes

            cvm_base = data_cvm.extent * SECTOR_SIZE
            cvm_header = CvmHeader.parse(bytes(image[cvm_base:cvm_base + HEADER_SIZE]))
            if cvm_header.total_size != data_cvm.size:
                raise ValueError("Outer DATA.CVM directory size disagrees with CVM header")
            if cvm_base + cvm_header.total_size > len(image):
                raise ValueError("DATA.CVM extends beyond outer ISO")

            payload_base = cvm_base + HEADER_SIZE
            embedded_volume, embedded_records = index_iso(image, payload_base)
            if embedded_volume * SECTOR_SIZE != cvm_header.payload_size:
                raise ValueError("Embedded ISO volume size disagrees with CVM payload size")

            dg00_ksf = find_record(embedded_records, "ADV/DG/DG00_00.KSF")
            dg00_mtx = find_record(embedded_records, "ADV/DG/DG00_00.MTX")
            dg01_ksf = find_record(embedded_records, "ADV/DG/DG00_01.KSF")

            if len(ksf_bytes) != dg00_ksf.size:
                raise ValueError(
                    f"Translated DG00_00.KSF must stay {dg00_ksf.size} bytes, got {len(ksf_bytes)}"
                )

            old_mtx_sectors = dg00_mtx.sectors
            new_mtx_sectors = _sectors(len(mtx_bytes))
            extra_sectors = new_mtx_sectors - old_mtx_sectors
            if extra_sectors <= 0:
                raise ValueError("This relocation build expects DG00_00.MTX to grow")
            if dg01_ksf.extent != dg00_mtx.extent + old_mtx_sectors:
                raise ValueError("DG00_01.KSF is not directly after DG00_00.MTX")
            if dg01_ksf.sectors != extra_sectors:
                raise ValueError(
                    "DG00_01.KSF allocation does not exactly match the sectors needed by translated DG00_00.MTX"
                )

            growth_bytes = extra_sectors * SECTOR_SIZE
            new_embedded_volume = embedded_volume + extra_sectors
            new_cvm_size = cvm_header.total_size + growth_bytes

            old_cvm_end_sector = data_cvm.extent + _sectors(data_cvm.size)
            appended_outer_sector = (payload_base // SECTOR_SIZE) + embedded_volume
            if appended_outer_sector != old_cvm_end_sector:
                raise ValueError(
                    "Embedded ISO append point does not coincide with the outer DATA.CVM end"
                )

            shifted_records = tuple(
                record for record in outer_records if record.extent >= old_cvm_end_sector
            )
            if not shifted_records:
                raise ValueError("No outer tail records found after DATA.CVM")
            if any(record.is_directory for record in shifted_records):
                raise ValueError("Build does not support relocating an outer ISO directory")
            highest_referenced_sector = max(
                record.extent + record.sectors for record in outer_records
            )
            if highest_referenced_sector + extra_sectors > outer_volume:
                raise ValueError("Outer ISO has insufficient trailing space for CVM growth")

            tail_start = old_cvm_end_sector * SECTOR_SIZE
            tail_end = highest_referenced_sector * SECTOR_SIZE
            tail_bytes = bytes(image[tail_start:tail_end])

            dg01_allocation_start = payload_base + dg01_ksf.extent * SECTOR_SIZE
            dg01_allocation_size = dg01_ksf.sectors * SECTOR_SIZE
            dg01_allocation = bytes(
                image[dg01_allocation_start:dg01_allocation_start + dg01_allocation_size]
            )
            dg01_file_bytes = dg01_allocation[:dg01_ksf.size]

            # Shift only the small outer tail by the amount DATA.CVM is growing.
            shifted_tail_start = tail_start + growth_bytes
            image[shifted_tail_start:shifted_tail_start + len(tail_bytes)] = tail_bytes
            for record in shifted_records:
                patch_directory_record(
                    image,
                    record.record_offset,
                    extent=record.extent + extra_sectors,
                )

            # Expand the outer DATA.CVM record in place.
            patch_directory_record(image, data_cvm.record_offset, size=new_cvm_size)

            # Grow the CVM header using only the fields proven by the Kowloon image.
            grown_header = cvm_header.grow_payload(growth_bytes).compile()
            image[cvm_base:cvm_base + HEADER_SIZE] = grown_header

            # Grow the embedded ISO volume declaration.
            embedded_pvd = payload_base + 16 * SECTOR_SIZE
            write_both_u32(image, embedded_pvd + 80, new_embedded_volume)

            # Relocate DG00_01.KSF to the newly appended two sectors, preserving its full allocation.
            relocated_extent = embedded_volume
            relocated_start = payload_base + relocated_extent * SECTOR_SIZE
            image[relocated_start:relocated_start + dg01_allocation_size] = dg01_allocation
            patch_directory_record(image, dg01_ksf.record_offset, extent=relocated_extent)

            # Patch DG00_00.KSF in-place for the option-string renderer probe.
            dg00_ksf_start = payload_base + dg00_ksf.extent * SECTOR_SIZE
            image[dg00_ksf_start:dg00_ksf_start + len(ksf_bytes)] = ksf_bytes

            # Expand DG00_00.MTX over its old allocation plus the freed DG00_01.KSF sectors.
            dg00_mtx_start = payload_base + dg00_mtx.extent * SECTOR_SIZE
            dg00_mtx_allocation_size = new_mtx_sectors * SECTOR_SIZE
            padded_mtx = mtx_bytes + b"\x00" * (dg00_mtx_allocation_size - len(mtx_bytes))
            image[dg00_mtx_start:dg00_mtx_start + dg00_mtx_allocation_size] = padded_mtx
            patch_directory_record(image, dg00_mtx.record_offset, size=len(mtx_bytes))

            image.flush()
        finally:
            image.close()

    if destination.stat().st_size != source_size:
        raise ValueError("Patched outer ISO unexpectedly changed total file size")

    # Full structural and content validation from the finished image.
    with source.open("rb") as source_handle, destination.open("rb") as output_handle:
        src = mmap.mmap(source_handle.fileno(), 0, access=mmap.ACCESS_READ)
        out = mmap.mmap(output_handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            src_outer_volume, src_outer_records = index_iso(src)
            out_outer_volume, out_outer_records = index_iso(out)
            if src_outer_volume != out_outer_volume:
                raise ValueError("Outer ISO volume size changed")

            src_cvm = find_record(src_outer_records, "DATA.CVM")
            out_cvm = find_record(out_outer_records, "DATA.CVM")
            if elf_bytes is not None:
                out_elf = find_record(out_outer_records, "SLPM_665.11")
                actual_elf = bytes(
                    out[out_elf.extent * SECTOR_SIZE:out_elf.extent * SECTOR_SIZE + out_elf.size]
                )
                if actual_elf != elf_bytes:
                    raise ValueError("SLPM_665.11 validation failed")
            if out_cvm.extent != src_cvm.extent or out_cvm.size != src_cvm.size + growth_bytes:
                raise ValueError("Patched DATA.CVM outer record is inconsistent")

            src_tail = {
                record.path: record
                for record in src_outer_records
                if record.extent >= src_cvm.extent + _sectors(src_cvm.size)
            }
            out_tail = {record.path: record for record in out_outer_records if record.path in src_tail}
            for path, before in src_tail.items():
                after = out_tail[path]
                if after.extent != before.extent + extra_sectors or after.size != before.size:
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
                raise ValueError("Patched CVM header total size disagrees with outer directory")
            out_payload_base = out_cvm_base + HEADER_SIZE
            out_embedded_volume, out_embedded_records = index_iso(out, out_payload_base)
            if out_embedded_volume != embedded_volume + extra_sectors:
                raise ValueError("Patched embedded ISO volume size is incorrect")

            out_mtx = find_record(out_embedded_records, "ADV/DG/DG00_00.MTX")
            out_ksf = find_record(out_embedded_records, "ADV/DG/DG00_00.KSF")
            out_dg01 = find_record(out_embedded_records, "ADV/DG/DG00_01.KSF")
            if out_mtx.size != len(mtx_bytes) or out_dg01.extent != embedded_volume:
                raise ValueError("Patched embedded directory records are incorrect")

            actual_mtx = bytes(
                out[out_payload_base + out_mtx.extent * SECTOR_SIZE:
                    out_payload_base + out_mtx.extent * SECTOR_SIZE + out_mtx.size]
            )
            actual_ksf = bytes(
                out[out_payload_base + out_ksf.extent * SECTOR_SIZE:
                    out_payload_base + out_ksf.extent * SECTOR_SIZE + out_ksf.size]
            )
            actual_dg01 = bytes(
                out[out_payload_base + out_dg01.extent * SECTOR_SIZE:
                    out_payload_base + out_dg01.extent * SECTOR_SIZE + out_dg01.size]
            )
            if actual_mtx != mtx_bytes:
                raise ValueError("DG00_00.MTX validation failed")
            if actual_ksf != ksf_bytes:
                raise ValueError("DG00_00.KSF validation failed")
            if actual_dg01 != dg01_file_bytes:
                raise ValueError("Relocated DG00_01.KSF validation failed")

            print(f"output={destination}")
            print(f"outer_size={destination.stat().st_size} unchanged=True")
            print(f"cvm_size={src_cvm.size}->{out_cvm.size} growth={growth_bytes}")
            print(f"embedded_volume_sectors={embedded_volume}->{out_embedded_volume}")
            print(f"DG00_00.MTX extent={out_mtx.extent} size={out_mtx.size} sha256={_sha256(actual_mtx)}")
            print(f"DG00_00.KSF extent={out_ksf.extent} size={out_ksf.size} sha256={_sha256(actual_ksf)}")
            print(f"DG00_01.KSF relocated={dg01_ksf.extent}->{out_dg01.extent} sha256={_sha256(actual_dg01)}")
            if elf_bytes is not None:
                print(f"SLPM_665.11 size={len(elf_bytes)} sha256={_sha256(elf_bytes)}")
            print(f"outer_tail_files_verified={len(src_tail)}")
        finally:
            src.close()
            out.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--mtx", type=Path, required=True)
    parser.add_argument("--ksf", type=Path, required=True)
    parser.add_argument("--elf", type=Path)
    args = parser.parse_args()
    build(args.source, args.destination, args.mtx, args.ksf, args.elf)


if __name__ == "__main__":
    main()
