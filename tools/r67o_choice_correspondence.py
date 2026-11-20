"""Prove native choice identity for historical KSF record mismatches."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import mmap
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.localization import encode_ps2_english
from tools.r67n_ksf import DATA_CVM_HEADER_SIZE, PAYLOAD, native_slots
from tools.r67n_partial import _Source

BASELINE_ISO_SHA256 = "c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0"
BASELINE_ELF_SHA256 = "0d5ace47c618c8c9af92f76aecad72dd0da2c4f7588410d2f9d866458a8f38bb"
ORIGINAL_ELF_SHA256 = "6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794"
HISTORICAL_REPORT_SHA256 = "a6ca7b10b58297fe506bd7afef61be84cd913de9061db60b6d07564d5623ec57"
MTX_INVENTORY_SHA256 = "bfcd9ee74e9c70f3eec0b9ecebd3bb0928ebfa215712729a521453db09188f02"
ROOT_MTX_SHA256 = "dbde26549add3e1f15c54236f1e8b14bf73031327765dfb16c8036c6a544c685"
ROOT_KSF_SHA256 = "3bc7536ae977375f949cde5376401e348a680e94915a409d54a3c034e7fd3177"

NATIVE_RANGES = {
    "0x215330..0x215374": "9abc7dddcc4df855c39b1c53bc6fb5e1f8455019ecb9ce517fc1b171ac7cb3ad",
    "0x215604..0x2156d0": "3b5bbd9316df11dc362a5d80a9ebcb5eb674ca70e759ec3f31c959eb49d9d5e9",
    "0x215720..0x215758": "791d0bcf368d5601928a584ee3cee941c34f985021af5cc63fb7af53c6f2fb73",
    "0x215820..0x215854": "a1ce3ad03d2c67a444c9d82f6e82028d9af26328245201f3a87b8a62fa01e26a",
    "0x22c2e8..0x22c408": "5b108673b5f63a7e0a535602535b6a896a67f06cedbb85b2a6374b940e7052c6",
    "0x22c598..0x22c7dc": "04042ebfcff17462b3f371017164be5bc2a7feb2add0034035ae6374356b16b7",
    "0x22d0b0..0x22d174": "6cbeb5631329f1df5db142f08bb211040861cdb6445b95eea7878a5f32571a7b",
}
ELF_ADDRESS_BIAS = 0xFFF80
STYLE0_FONT_POINTER = 0x5D7E20
KSF_HEADER_BYTES = 0x26
KSF_FLAGS_OFFSET = 0x90C
APPROVED_ORDINALS = {
    "DG/DG13_02.KSF": (10,),
    "MS/MS01_00.KSF": (22, 47, 60, 78, 182, 216, 233, 237),
    "MS/MS04_01.KSF": (166,),
    "MS/MS13_00.KSF": (11, 13, 37, 41),
    "MS/MS13_03.KSF": (0, 12),
}
NO_NUMBERED_OWNER = "MS/MS01_03.KSF"
JACKET_KSF = "MS/MS04_01.KSF"
JACKET_ORDINAL = 166
JACKET_PS2_SHA256 = "0dd272f90da6c947d5279962e66747f675c89e37742d0331c716a16d8b5af01b"
JACKET_PS4_SHA256 = "e53c80cc6850926c3b63cedb151dd1110f0767708fcabeb5fa70af77808dc3df"
HELD_REASON = "numbered PS2 record has no active choice and PS2 root context differs"


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _verify_hash(raw: bytes, expected: str, label: str) -> bytes:
    if _digest(raw) != expected:
        raise ValueError(f"{label} SHA-256 drift")
    return raw


def verify_file_inputs(path: str, pristine: bytes, remaster: bytes, dc_raw: bytes,
                       installed: bytes, historical: dict) -> dict:
    _verify_hash(pristine, historical["ps2_sha256"], f"{path} original PS2 KSF")
    _verify_hash(remaster, historical["ps4_sha256"], f"{path} official PS4 KSF")
    _verify_hash(dc_raw, historical["map_sha256"], f"{path} raw official DC")
    _verify_hash(installed, historical["after_sha256"], f"{path} installed whole KSF")
    dc = json.loads(dc_raw)
    keys, values = dc["keys"], dc["values"]
    if (len(keys) != len(values) or len(set(keys)) != len(keys)
            or any(type(key) is not int for key in keys) or any(not isinstance(value, str) for value in values)):
        raise ValueError(f"{path} has invalid official DC arrays")
    return dc


def _live_region(mtx: _Source, ordinal: int):
    if not (0 <= ordinal < len(mtx.mtx.pointer_words) and mtx.mtx.pointer_words[ordinal]):
        raise ValueError(f"MTX has no live pointer for chapter {ordinal}")
    region = mtx.at(mtx.mtx.pointer_offsets[ordinal])
    if not (region.start < region.end and {region.start, region.end} <= mtx.boundaries):
        raise ValueError(f"invalid CP932 boundaries for MTX chapter {ordinal}")
    return region


def _record(raw: bytes, ordinal: int) -> tuple[int, int, bytes, tuple[int, ...]]:
    native = [(key, start, slot) for key, (index, start, slot) in native_slots(raw).items()
              if index == ordinal]
    if not native:
        raise ValueError(f"KSF ordinal {ordinal} has no active choice")
    start = native[0][1]
    cursor = start + KSF_FLAGS_OFFSET
    flags = []
    offsets = []
    for _ in range(4):
        flag = raw[cursor]
        # 0x22c338..0x22c340 activates only an exact value of 1.
        flags.append(flag)
        cursor += 1
        if flag == 1:
            offsets.append(cursor)
            cursor += PAYLOAD
    if native != [(key, start, slot) for slot, key in enumerate(offsets)]:
        raise ValueError(f"KSF native label packing differs at ordinal {ordinal}")
    return start, cursor, bytes(flags), tuple(offsets)


def _difference_ranges(first: bytes, second: bytes) -> list[list[int]]:
    differences = []
    for offset, (a, b) in enumerate(zip(first, second, strict=True)):
        if a != b:
            if differences and differences[-1][1] == offset:
                differences[-1][1] += 1
            else:
                differences.append([offset, offset + 1])
    return differences


def project_record(path: str, ordinal: int, pristine: bytes, remaster: bytes, installed: bytes,
                   ps2_mtx: bytes, ps4_mtx: bytes, source_keys: tuple[int, ...]) -> dict:
    start2, end2, flags2, offsets2 = _record(pristine, ordinal)
    start4, end4, flags4, offsets4 = _record(remaster, ordinal)
    header = pristine[start2:start2 + KSF_HEADER_BYTES]
    if header[0] != 2 or header != remaster[start4:start4 + KSF_HEADER_BYTES]:
        raise ValueError(f"{path}:{ordinal} type-2 choice and branch header differs")
    if flags2 != flags4:
        raise ValueError(f"{path}:{ordinal} choice flag bytes differ")
    if set(source_keys) != set(offsets4) or len(source_keys) != len(offsets4):
        raise ValueError(f"{path}:{ordinal} official keys do not cover every active sibling")
    record2, record4 = pristine[start2:end2], remaster[start4:end4]
    # The native link reader at 0x22c678 also consumes one halfword
    # from each conditional record before the header fallback.
    for index in range(5):
        link = KSF_HEADER_BYTES + index * PAYLOAD + 0x1C
        if record2[link:link + 2] != record4[link:link + 2]:
            raise ValueError(f"{path}:{ordinal} conditional branch link differs")
    if installed[start2:end2] != record2 or _record(installed, ordinal) != (start2, end2, flags2, offsets2):
        raise ValueError(f"{path}:{ordinal} installed record preimage differs")

    source2, source4 = _Source(ps2_mtx), _Source(ps4_mtx)
    region2, region4 = _live_region(source2, ordinal), _live_region(source4, ordinal)
    if region2.slots != region4.slots:
        raise ValueError(f"{path}:{ordinal} MTX pointer slot identity differs")
    body2 = ps2_mtx[region2.start:region2.end]
    if body2 != ps4_mtx[region4.start:region4.end]:
        raise ValueError(f"{path}:{ordinal} entire MTX pointer region differs")
    branches = [struct.unpack_from("<H", header, 6 + 2 * slot)[0] for slot in range(len(offsets2))]
    for target in set(branches) - {999}:
        if any(target >= struct.unpack_from("<H", raw)[0] for raw in (pristine, remaster)):
            raise ValueError(f"{path}:{ordinal} branch target is outside KSF records")
        for mtx in (source2, source4):
            _live_region(mtx, target)

    jacket = ((path, ordinal) == (JACKET_KSF, JACKET_ORDINAL)
              and _digest(pristine) == JACKET_PS2_SHA256 and _digest(remaster) == JACKET_PS4_SHA256)
    rows = []
    for slot, (key2, key4) in enumerate(zip(offsets2, offsets4, strict=True)):
        label2, label4 = pristine[key2:key2 + PAYLOAD], remaster[key4:key4 + PAYLOAD]
        if b"\0" not in label2 or b"\0" not in label4:
            raise ValueError(f"{path}:{ordinal}/{slot} Japanese payload is unterminated")
        match = "literal 30-byte payload"
        if label2 != label4:
            if not (jacket and slot in (0, 1) and label2.startswith("革ジャン".encode("cp932"))
                    and label4.startswith("皮ジャン".encode("cp932")) and label2[2:] == label4[2:]):
                raise ValueError(f"{path}:{ordinal}/{slot} Japanese payload differs")
            match = "MS04_01 record 166 leather-jacket spelling"
        rows.append({"key": key4, "slot": slot, "ps2_offset": key2,
                     "ps4_payload_span": [key4, key4 + PAYLOAD], "ps4_payload_sha256": _digest(label4),
                     "ps4_payload_hex": label4.hex(), "pristine_payload_hex": label2.hex(),
                     "old_payload_sha256": _digest(label2), "old_payload_hex": installed[key2:key2 + PAYLOAD].hex(),
                     "installed_payload_span": [key2, key2 + PAYLOAD], "japanese_identity": match})
    return {
        "ordinal": ordinal, "flags_hex": flags2.hex(), "branch_target_ordinals": branches,
        "ps4_record_range": [start4, end4], "ps4_record_sha256": _digest(record4),
        "installed_record_range": [start2, end2], "installed_record_sha256": _digest(record2),
        "installed_header_offset": start2, "installed_header_hex": header.hex(),
        "record_difference_ranges": _difference_ranges(record2, record4),
        "mtx_region": {"ps2_span": [region2.start, region2.end], "ps4_span": [region4.start, region4.end],
                       "sha256": _digest(body2), "pointer_slots": list(region2.slots)},
        "rows": rows,
    }


def _iso_file(image, records, name: str, *, base: int = 0) -> tuple[int, bytes]:
    record = find_record(records, name)
    start = base + record.extent * SECTOR_SIZE
    return start, image[start:start + record.size]


def _check_native(installed_elf: bytes, pristine_elf: bytes) -> None:
    _verify_hash(installed_elf, BASELINE_ELF_SHA256, "installed n ELF")
    _verify_hash(pristine_elf, ORIGINAL_ELF_SHA256, "pristine PS2 ELF")
    for bounds, expected in NATIVE_RANGES.items():
        begin, end = (int(value, 16) - ELF_ADDRESS_BIAS for value in bounds.split(".."))
        for raw in (installed_elf, pristine_elf):
            _verify_hash(raw[begin:end], expected, f"native owner {bounds}")


def _hold_numbered_mismatch(pristine: bytes, remaster_mtx: bytes, rows: list[dict], *,
                            root_mtx: bytes, root_ksf: bytes) -> None:
    numbered_slots = native_slots(pristine)
    root_slots = native_slots(root_ksf)
    root, official = _Source(root_mtx), _Source(remaster_mtx)
    for ordinal in {row["record_ordinal"] for row in rows}:
        if any(ordinal == index for index, _, _ in numbered_slots.values()):
            raise ValueError(f"numbered MS01_03 ordinal {ordinal} unexpectedly has an active PS2 label")
        if any(ordinal == index for index, _, _ in root_slots.values()):
            r2, r4 = _live_region(root, ordinal), _live_region(official, ordinal)
            if root.raw[r2.start:r2.end] == official.raw[r4.start:r4.end]:
                raise ValueError(f"MS01_03 root ordinal {ordinal} unexpectedly matches the PS4 chapter")


def _census(labels: list[tuple[str, int, str]], elf: bytes) -> dict:
    font = struct.unpack_from("<I", elf, STYLE0_FONT_POINTER - ELF_ADDRESS_BIAS)[0] - ELF_ADDRESS_BIAS
    font_size = struct.unpack_from("<H", elf, font)[0]
    style0 = struct.unpack_from(f"<{font_size}H", elf, font + 2)
    chars = set()
    units = {}
    max_cells = max_bytes = max_wrapped_bytes = max_line_width = wraps = 0
    longest = []
    for path, key, label in labels:
        if not label or any(char not in " '-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" for char in label):
            raise ValueError(f"{path}:{key} has an unproven static label character")
        chars.update(label)
        for char in set(label) - {" "}:
            unit = int.from_bytes(encode_ps2_english(char), "big")
            if unit not in style0:
                raise ValueError(f"{path}:{key} lacks a style-0 glyph")
            units[char] = style0.index(unit)
        widths = [0]
        for char in label:
            widths.append(widths[-1] + (8 if char == " " else 16))
        total = widths[-1]
        encoded = 2 * len(label) - label.count(" ")
        if len(label) >= max_cells:
            if len(label) > max_cells:
                longest.clear()
            longest.append({"path": path, "key": key})
        max_cells, max_bytes = max(max_cells, len(label)), max(max_bytes, encoded)
        if total > 448:
            break_at = next((index for index in range(len(label) - 1, 0, -1)
                             if (label[index - 1] == " " or label[index] == " ")
                             and widths[index] <= 448 and total - widths[index] <= 448), None)
            if break_at is None:
                raise ValueError(f"{path}:{key} requires more than two 448-pixel lines")
            max_line_width = max(max_line_width, widths[break_at], total - widths[break_at])
            encoded += 1
            wraps += 1
        else:
            max_line_width = max(max_line_width, total)
        max_wrapped_bytes = max(max_wrapped_bytes, encoded)
    return {"ascii_characters": "".join(sorted(chars)), "style0_glyph_indices": dict(sorted(units.items())),
            "space_advance": 8, "glyph_advance": 16, "max_logical_cells": max_cells,
            "max_encoded_bytes": max_bytes, "max_encoded_bytes_with_wrap": max_wrapped_bytes,
            "max_line_width": max_line_width, "wrapping_rows": wraps, "longest_rows": longest}


def analyze(ps2_adv: Path, ps4_adv: Path, baseline_iso: Path, historical_report: Path) -> dict:
    history = json.loads(_verify_hash(historical_report.read_bytes(), HISTORICAL_REPORT_SHA256,
                                     "historical structural KSF report"))
    pristine_elf = (ps2_adv.resolve().parents[1] / "SLPM_665.11").read_bytes()
    audited_files, held, labels, mtx_inventory = [], [], [], []
    with baseline_iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if sha256(image).hexdigest() != BASELINE_ISO_SHA256:
            raise ValueError("baseline ISO SHA-256 drift")
        _, outer = index_iso(image)
        _, elf = _iso_file(image, outer, "SLPM_665.11")
        _check_native(elf, pristine_elf)
        base = find_record(outer, "DATA.CVM").extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        _, nested = index_iso(image, base)
        for entry in history["files"]:
            path = Path(entry["path"])
            name = path.as_posix()
            map_path = path.parent / "EN" / (path.name + "DC.json")
            pristine = (ps2_adv / path).read_bytes()
            remaster = (ps4_adv / path).read_bytes()
            iso_offset, installed = _iso_file(image, nested, "ADV/" + name, base=base)
            dc = verify_file_inputs(name, pristine, remaster, (ps4_adv / map_path).read_bytes(), installed, entry)
            if len(entry["rows"]) != len(dc["keys"]):
                raise ValueError(f"{path} historical and official entry counts differ")
            pending = []
            for index, (row, key, value) in enumerate(zip(entry["rows"], dc["keys"], dc["values"], strict=True)):
                if (row["official_array_index"], row["key"], row["official_utf8_sha256"]) != (
                    index, key, _digest(value.encode("utf-8"))
                ):
                    raise ValueError(f"{path} historical official identity drift at {index}")
                if row["status"] == "record mismatch":
                    pending.append(row)
            if not pending:
                continue

            mtx = path.with_suffix(".MTX")
            mtx2, mtx4 = (ps2_adv / mtx).read_bytes(), (ps4_adv / mtx).read_bytes()
            mtx_inventory.append([mtx.as_posix(), _digest(mtx2), _digest(mtx4)])
            loaded_name = f"adv/{path.parent.as_posix().lower()}/{path.name}"
            common = {"source_path": name, "map_path": map_path.as_posix(), "map_sha256": entry["map_sha256"],
                      "ps2_sha256": entry["ps2_sha256"], "ps4_sha256": entry["ps4_sha256"],
                      "loaded_name": loaded_name, "installed_sha256": entry["after_sha256"]}
            by_ordinal = defaultdict(list)
            official_slots = native_slots(remaster)
            for row in pending:
                index, key, ordinal, slot = (row[field] for field in
                                              ("official_array_index", "key", "record_ordinal", "choice_index"))
                actual_ordinal, start4, actual_slot = official_slots[key]
                if (ordinal, slot, row["ps4_record_range"][0]) != (actual_ordinal, actual_slot, start4):
                    raise ValueError(f"{path}:{key} historical PS4 native label geometry differs")
                _verify_hash(remaster[slice(*row["ps4_record_range"])], row["ps4_record_sha256"],
                             f"{path}:{key} official choice record")
                by_ordinal[ordinal].append(row)
            if name == NO_NUMBERED_OWNER:
                _, root_mtx = _iso_file(image, nested, "ADV/KWLNSCR.MTX", base=base)
                _, root_ksf = _iso_file(image, nested, "ADV/KWLNSCR.KSF", base=base)
                _verify_hash(root_mtx, ROOT_MTX_SHA256, "installed PS2 root MTX")
                _verify_hash(root_ksf, ROOT_KSF_SHA256, "installed PS2 root KSF")
                _hold_numbered_mismatch(pristine, mtx4, pending, root_mtx=root_mtx, root_ksf=root_ksf)
                held.extend({**common, "reason": HELD_REASON, "index": row["official_array_index"],
                             "key": row["key"], "ordinal": row["record_ordinal"], "slot": row["choice_index"],
                             "official_sha256": row["official_utf8_sha256"]}
                            for row in pending)
                continue
            if tuple(sorted(by_ordinal)) != APPROVED_ORDINALS.get(name):
                raise ValueError(f"{path} mismatch record scope differs")

            records = []
            for ordinal, previous_rows in sorted(by_ordinal.items()):
                record = project_record(name, ordinal, pristine, remaster, installed, mtx2, mtx4,
                                        tuple(row["key"] for row in previous_rows))
                historical_by_key = {row["key"]: row for row in previous_rows}
                for choice in record["rows"]:
                    key = choice["key"]
                    row = historical_by_key[key]
                    if (choice["ps2_offset"], choice["slot"], record["installed_record_range"],
                        record["installed_record_sha256"], choice["old_payload_sha256"]) != (
                        row["ps2_key"], row["choice_index"], row["ps2_record_range"],
                        row["ps2_record_sha256"], row["before_payload_sha256"]
                    ):
                        raise ValueError(f"{path}:{key} historical native preimage drift")
                    index = row["official_array_index"]
                    choice.update(common, index=index, ordinal=ordinal, official_sha256=row["official_utf8_sha256"],
                                  installed_header_offset=record["installed_header_offset"])
                    labels.append((name, key, dc["values"][index]))
                records.append(record)
            audited_files.append({**common, "path": name, "iso_offset": iso_offset, "installed_size": len(installed),
                                  "ps2_mtx_sha256": _digest(mtx2), "ps4_mtx_sha256": _digest(mtx4),
                                  "records": records})

    _verify_hash(json.dumps(mtx_inventory, separators=(",", ":")).encode("ascii"),
                 MTX_INVENTORY_SHA256, "source MTX inventory")
    count = Counter(row["japanese_identity"] for file in audited_files for rec in file["records"] for row in rec["rows"])
    records_count = sum(len(file["records"]) for file in audited_files)
    if ((len(history["files"]), sum(len(entry["rows"]) for entry in history["files"])) != (20, 169)
            or (len(labels), records_count, len(held), len(audited_files)) != (37, 16, 6, 5)
            or count != {"literal 30-byte payload": 35, "MS04_01 record 166 leather-jacket spelling": 2}):
        raise ValueError("bounded choice corpus disposition drift")
    return {
        "schema_version": 1, "baseline_iso_sha256": BASELINE_ISO_SHA256,
        "historical_report_sha256": HISTORICAL_REPORT_SHA256, "mtx_inventory_sha256": MTX_INVENTORY_SHA256,
        "historical_files": 20, "historical_entries": 169, "projected_entries": len(labels),
        "projected_records": records_count, "held_entries": len(held),
        "japanese_identity_counts": dict(sorted(count.items())), "native": {
            "installed_elf_sha256": BASELINE_ELF_SHA256, "original_elf_sha256": ORIGINAL_ELF_SHA256,
            "instruction_ranges": NATIVE_RANGES,
            "choice_record_type": 2, "header_bytes": KSF_HEADER_BYTES, "flags_offset": KSF_FLAGS_OFFSET,
            "payload_bytes": PAYLOAD, "choice_stride": PAYLOAD + 1,
        },
        "census": _census(labels, elf), "files": audited_files, "held": held,
    }


def run(ps2_adv: Path, ps4_adv: Path, baseline_iso: Path, historical_report: Path, output_dir: Path) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Choose a fresh output directory: {output_dir}")
    report = analyze(ps2_adv, ps4_adv, baseline_iso, historical_report)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir.parent) as temp:
        staged = Path(temp) / "report.json"
        staged.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="ascii")
        output_dir.mkdir()
        staged.rename(output_dir / "report.json")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("ps2-adv", "ps4-adv", "baseline-iso", "historical-report", "output-dir"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.ps2_adv, args.ps4_adv, args.baseline_iso, args.historical_report, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({field: report[field] for field in ("projected_entries", "projected_records", "held_entries", "census")},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
