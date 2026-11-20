"""Import the bounded MS01_03 official text into the native PS2 KWLNSCR owner."""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
import mmap
from pathlib import Path
import struct
from tempfile import TemporaryDirectory

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.mtx import MtxFile, MtxReplacement
from tools.r67n_ksf import DATA_CVM_HEADER_SIZE, native_slots
from tools.r67n_partial import (
    _Change, _Match, _Source, _encode, _entries, _groups, _left_boundary,
    _output_evidence, _right_delimiter, _source_names,
)

SOURCE_MTX = "MS/MS01_03.MTX"
SOURCE_DC = "MS/EN/MS01_03DC.json"
TARGET_MTX = "KWLNSCR.MTX"
TARGET_KSF = "KWLNSCR.KSF"
NO_OWNER = "no bounded alternate owner"
APPROVED = "whole group: exact scene block, delimiters and presentation controls"
CORRESPONDENCE = Path(__file__).resolve().parents[1] / "translations/r67o_kwlnscr_correspondence.json"
CORRESPONDENCE_SHA256 = "0e7c2455998ed3a38098ab65f258542990b088105815e98fc2d7f0c05f09e2c2"


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _object_digest(obj) -> str:
    return _digest(json.dumps(obj, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii"))


def _verified(raw: bytes, expected: str, label: str) -> bytes:
    if _digest(raw) != expected:
        raise ValueError(f"{label} hash drift")
    return raw


def read_verified_files(root: Path, expected: dict[str, str]) -> dict[str, bytes]:
    return {
        name: _verified((root / name).read_bytes(), digest, name)
        for name, digest in expected.items()
    }


def _verify_scene_blocks(ps2: _Source, ps4: _Source, blocks: list[dict]) -> None:
    previous_2 = ps2.mtx.header_size
    previous_4 = ps4.mtx.header_size
    for block in blocks:
        start_2, end_2 = block["ps2"]
        start_4, end_4 = block["ps4"]
        if start_2 < previous_2 or start_4 < previous_4:
            raise ValueError("scene blocks overlap or are out of order")
        if not (start_2 < end_2 <= len(ps2.raw) and start_4 < end_4 <= len(ps4.raw)
                and end_2 - start_2 == end_4 - start_4):
            raise ValueError("invalid scene block ranges")
        if not ({start_2, end_2} <= ps2.boundaries and {start_4, end_4} <= ps4.boundaries):
            raise ValueError("scene block splits a CP932 character")
        payload = ps4.raw[start_4:end_4]
        _verified(payload, block["sha256"], f"PS4 scene block {start_4}")
        if ps2.raw[start_2:end_2] != payload:
            raise ValueError(f"PS2 scene block {start_2} differs from the full PS4 block")
        previous_2, previous_4 = end_2, end_4


def scan_corpus(root: Path, side: str, raw: bytes, blocks: list[dict], *, expected_count: int) -> str:
    """Census every raw occurrence, including a potential overlapping owner."""
    needles = [raw[slice(*block[side])] for block in blocks]
    if any(not needle for needle in needles):
        raise ValueError(f"{side} scene block is empty")
    owners = [[] for _ in needles]
    inventory = []
    for path in sorted(root.rglob("*.MTX")):
        name = path.relative_to(root).as_posix()
        candidate = path.read_bytes()
        inventory.append([name, _digest(candidate)])
        for needle, hits in zip(needles, owners, strict=True):
            first = candidate.find(needle)
            if first >= 0:
                count = 1
                position = candidate.find(needle, first + 1)
                while position >= 0:
                    count += 1
                    position = candidate.find(needle, position + 1)
                hits.append([name, first, count])
    for block, hits in zip(blocks, owners, strict=True):
        if hits != block[f"{side}_owners"]:
            raise ValueError(f"{side} scene block owner census drift for {block[side]}: {hits}")
    if len(inventory) != expected_count:
        raise ValueError(f"{side} corpus file count drift: {len(inventory)}")
    return _object_digest(inventory)


def _describe_span(raw: bytes, start: int, end: int, slots: tuple[int, ...]) -> dict:
    return {"span": [start, end], "sha256": _digest(raw[start:end]), "pointer_slots": list(slots)}


def compile_blocks(ps2_raw: bytes, ps4_raw: bytes, dc: dict, blocks: list[dict],
                   held_anchors: dict[str, str]) -> tuple[bytes, dict]:
    ps2, ps4 = _Source(ps2_raw), _Source(ps4_raw)
    _verify_scene_blocks(ps2, ps4, blocks)
    groups = _groups(ps4, _entries(dc))
    changes = []
    group_rows = {}
    held_matches = {}
    approved = []
    seen_holds = set()
    for group in groups:
        r4 = ps4.at(group.start)
        source = _describe_span(ps4.raw, group.start, group.end, r4.slots)
        block = next((block for block in blocks
                      if block["ps4"][0] <= group.start < group.end <= block["ps4"][1]), None)
        row = {"entry_keys": list(group.ids), "reason": NO_OWNER, "source_ps4": source,
               "original_ps2": None, "installed_ps2": None, "output_ps2": None,
               "scene_block_sha256": None, "native_owner": None}
        group_rows[group.start] = row
        if block is None:
            continue

        target_start = block["ps2"][0] + group.start - block["ps4"][0]
        target_end = target_start + group.end - group.start
        r2 = ps2.at(target_start)
        if not (r4.start <= group.start < group.end <= r4.end
                and r2.start <= target_start < target_end <= r2.end):
            raise ValueError(f"DC group {group.start} crosses a source or target pointer boundary")
        if not ({group.start, group.end} <= ps4.boundaries and {target_start, target_end} <= ps2.boundaries):
            raise ValueError(f"DC group {group.start} splits a CP932 character")
        original = _describe_span(ps2.raw, target_start, target_end, r2.slots)
        if original["sha256"] != source["sha256"]:
            raise ValueError(f"DC group {group.start} target text differs")
        row.update(original_ps2=original, installed_ps2=original, scene_block_sha256=block["sha256"],
                   native_owner={"proof": "#/native_owner", "ksf_record_ordinals": list(r2.slots)})
        match = _Match(target_start, target_end, tuple(block["ps4"]), tuple(block["ps2"]))
        held = held_anchors.get(str(group.start))
        if held is not None:
            row["reason"] = held
            held_matches[group.start] = match
            seen_holds.add(str(group.start))
            continue

        delimiter = _right_delimiter(ps4, group)
        if not (delimiter and ps2.raw.startswith(delimiter, target_end, r2.end)
                and target_end + len(delimiter) in ps2.boundaries):
            raise ValueError(f"DC group {group.start} right delimiter differs")
        left_2 = _left_boundary(ps2, r2, target_start)
        left_4 = _left_boundary(ps4, r4, group.start)
        if left_2 is None or left_2 != left_4:
            raise ValueError(f"DC group {group.start} left control prefix differs")
        original_names = _source_names(ps4.raw[group.start:group.end])
        lines, names = _encode(group.lines)
        # A complete DC group can reorder its own name tokens, but cannot borrow
        # a token across a page boundary or from a neighboring held group.
        if Counter(original_names) != Counter(names):
            raise ValueError(f"DC group {group.start} changes native name ownership")
        change = _Change(group, match, lines, original_names, names, delimiter, (group.start,))
        changes.append(change)
        row.update(reason=APPROVED, left_control_hex=left_2.hex(), right_delimiter_hex=delimiter.hex(),
                   source_name_controls=list(original_names), official_name_controls=list(names))
        approved.append([list(group.ids), source["span"], source["pointer_slots"], original["span"],
                         original["pointer_slots"], source["sha256"], block["sha256"],
                         [_digest(line) for line in lines]])

    if seen_holds != held_anchors.keys():
        raise ValueError("one or more held groups lost their bounded target owner")
    replacements = tuple(MtxReplacement(c.match.start, c.match.end, c.replacement) for c in changes)
    output = ps2.mtx.apply_replacements(replacements).compile()
    # Replay untouched bytes and replacement bytes independently of the compiler.
    # The audit also verifies every zero, alias and nonzero quarter-offset slot.
    audited, regions = _output_evidence(ps2, ps4, output, tuple(changes))
    entry_outputs = {}
    for span in audited:
        row = group_rows[span.ps4_start]
        row["output_ps2"] = _describe_span(output, span.output_start, span.output_end, span.pointer_slots)
        for entry in span.entries:
            entry_outputs[entry.entry_id] = {"span": [entry.output_start, entry.output_end], "sha256": entry.sha256}
    output_regions = {region.pointer_slots: region for region in regions}
    for anchor, match in held_matches.items():
        region = output_regions[ps2.at(match.start).slots]
        delta = region.output_start - region.ps2_start
        delta += sum((span.output_end - span.output_start) - (span.ps2_end - span.ps2_start)
                     for span in audited if region.ps2_start <= span.ps2_start < match.start)
        held_output = _describe_span(output, match.start + delta, match.end + delta, region.pointer_slots)
        row = group_rows[anchor]
        if held_output["sha256"] != row["original_ps2"]["sha256"]:
            raise ValueError(f"held DC group {anchor} was changed")
        row["output_ps2"] = held_output

    row_by_key = {key: row for row in group_rows.values() for key in row["entry_keys"]}
    entries = [
        {**row_by_key[key], "dc_index": index, "key": key,
         "official_utf8_sha256": _digest(value.encode("utf-8")), "output_entry": entry_outputs.get(key)}
        for index, (key, value) in enumerate(zip(dc["keys"], dc["values"], strict=True))
    ]
    output_words = MtxFile.parse(output).pointer_words
    return output, {
        "approved_groups_sha256": _object_digest(approved),
        "spans": [group_rows[span.ps4_start] for span in audited],
        "entries": entries,
        "disposition_entry_counts": dict(sorted(Counter(row["reason"] for row in entries).items())),
        "pointer_slots": [
            {"slot": slot, "original_quarter_offset": before, "output_quarter_offset": after}
            for slot, (before, after) in enumerate(zip(ps2.mtx.pointer_words, output_words, strict=True))
        ],
        "region_alignment_bytes": [
            {"pointer_slots": list(region.pointer_slots), "added_null_bytes": region.alignment_bytes_added}
            for region in regions
        ],
    }


def verify_native_ranges(raw: bytes, ranges: dict[str, str], *, address_to_offset: int = 0x80 - 0x100000) -> None:
    for bounds, expected in ranges.items():
        start, end = (int(value, 16) for value in bounds.split(".."))
        low, high = start + address_to_offset, end + address_to_offset
        if not (0 <= low < high <= len(raw)) or _digest(raw[low:high]) != expected:
            raise ValueError(f"native anchor drift at {start:#x}..{end:#x}")


def verify_installed(pristine: dict[str, bytes], installed: dict[str, bytes]) -> None:
    for name, raw in installed.items():
        if raw != pristine.get(name):
            raise ValueError(f"installed preimage differs from pristine: ADV/{name}")
    if set(installed) != set(pristine):
        raise ValueError("installed preimage asset inventory differs from pristine")


def _ksf_ordinal_proof(ksf: bytes, mtx: bytes) -> tuple[list[dict], list[int]]:
    active_payloads = list(native_slots(ksf))
    offsets = _Source(mtx).mtx.pointer_offsets
    count = struct.unpack_from("<H", ksf)[0]
    if not (0 < count <= len(offsets) and all(offsets[:count]) and not any(offsets[count:])):
        raise ValueError("KSF records and live MTX pointer slots do not share the same ordinals")
    records = []
    cursor = 2
    for ordinal in range(count):
        start = cursor
        cursor += 0x90C
        for _ in range(4):
            flag = ksf[cursor]
            cursor += 1 + (30 if flag == 1 else 0)
        header = [struct.unpack_from("<H", ksf, start + field)[0] for field in range(2, 24, 2)]
        conditional = [struct.unpack_from("<H", ksf, start + 0x26 + choice * 30 + 0x1C)[0]
                       for choice in range(5)]
        if any(not (0 <= target < count or target == 999) for target in header + conditional):
            raise ValueError(f"KSF record {ordinal} has an invalid chapter ordinal")
        records.append({"record": ordinal, "extent": [start, cursor], "typed_choice": ksf[start],
                        "header_defaults_and_alternatives": header, "conditional_targets": conditional})
    return records, active_payloads


def _read_baseline(iso: Path, pin: dict) -> tuple[bytes, dict[str, bytes]]:
    with iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if sha256(image).hexdigest() != pin["iso_sha256"]:
            raise ValueError("baseline ISO hash drift")
        _, outer = index_iso(image)
        executable = find_record(outer, "SLPM_665.11")
        start = executable.extent * SECTOR_SIZE
        elf = _verified(image[start:start + executable.size], pin["elf_sha256"], "installed ELF")
        base = find_record(outer, "DATA.CVM").extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        _, records = index_iso(image, base)
        installed = {}
        for name, expected in pin["entries"].items():
            record = find_record(records, f"ADV/{name}")
            start = base + record.extent * SECTOR_SIZE
            if (start, record.extent, record.size) != (expected["iso_offset"], expected["extent"], expected["bytes"]):
                raise ValueError(f"installed asset extent drift: ADV/{name}")
            installed[name] = _verified(image[start:start + record.size], expected["sha256"],
                                        f"installed preimage ADV/{name}")
    return elf, installed


def _publish(output_dir: Path, output: bytes, report: dict) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output_dir.parent) as temp:
        staging = Path(temp)
        overlay = staging / "overlay"
        overlay.mkdir()
        (overlay / TARGET_MTX).write_bytes(output)
        (staging / "report.json").write_text(json.dumps(report, ensure_ascii=True, indent=2,
                                                       sort_keys=True) + "\n", encoding="ascii")
        # Reserve the destination exclusively, including when two runs race.
        output_dir.mkdir()
        overlay.rename(output_dir / overlay.name)
        (staging / "report.json").rename(output_dir / "report.json")


def run(ps2_adv: Path, ps4_adv: Path, baseline_iso: Path, output_dir: Path) -> dict:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Choose a fresh output directory: {output_dir}")
    contract = json.loads(_verified(CORRESPONDENCE.read_bytes(), CORRESPONDENCE_SHA256, "correspondence"))
    ps2_adv, ps4_adv = ps2_adv.resolve(), ps4_adv.resolve()
    ps2 = read_verified_files(ps2_adv, contract["source_files"]["ps2"])
    ps4 = read_verified_files(ps4_adv, contract["source_files"]["ps4"])
    baseline = contract["baseline"]
    installed_elf, installed = _read_baseline(baseline_iso, baseline)
    verify_installed(ps2, installed)

    native = contract["native"]
    ps2_elf = _verified((ps2_adv.parents[1] / "SLPM_665.11").read_bytes(), native["pristine_ee_sha256"],
                        "pristine ELF")
    for elf in (installed_elf, ps2_elf):
        verify_native_ranges(elf, native["pristine_and_installed_ee_ranges"])
    prx = _verified((ps4_adv.parents[2] / "Modules/Il2CppUserAssemblies.prx").read_bytes(),
                    native["ps4_prx_sha256"], "official PRX")
    verify_native_ranges(prx, native["ps4_prx_ranges"], address_to_offset=0x1F610)

    ksf_records, active_choices = _ksf_ordinal_proof(installed[TARGET_KSF], installed[TARGET_MTX])
    if (_object_digest(ksf_records) != native["ksf_records_sha256"]
            or active_choices != native["ksf_active_choice_payloads"]):
        raise ValueError("KSF ordinal record proof drift")
    blocks = contract["blocks"]
    output, evidence = compile_blocks(installed[TARGET_MTX], ps4[SOURCE_MTX], json.loads(ps4[SOURCE_DC]),
                                      blocks, contract["held_anchors"])
    if (len(evidence["spans"]) != contract["approved_groups"]
            or evidence["approved_groups_sha256"] != contract["approved_groups_sha256"]
            or evidence["disposition_entry_counts"] != contract["disposition_entry_counts"]):
        raise ValueError("approved cross-file group or entry inventory drift")
    for side, root, raw in (("ps2", ps2_adv, ps2[TARGET_MTX]), ("ps4", ps4_adv, ps4[SOURCE_MTX])):
        corpus = contract["corpus"][side]
        if scan_corpus(root, side, raw, blocks, expected_count=corpus["count"]) != corpus["inventory_sha256"]:
            raise ValueError(f"{side} MTX corpus inventory hash drift")

    source = {"ps4_mtx_path": f"ADV/{SOURCE_MTX}", "ps4_mtx_sha256": _digest(ps4[SOURCE_MTX]),
              "official_dc_path": f"ADV/{SOURCE_DC}", "official_dc_sha256": _digest(ps4[SOURCE_DC])}
    target = {"ps2_mtx_path": f"ADV/{TARGET_MTX}", "ps2_mtx_sha256": _digest(ps2[TARGET_MTX]),
              "installed_mtx_sha256": _digest(installed[TARGET_MTX]), "output_mtx_sha256": _digest(output)}
    for row in evidence["entries"]:
        row.update(source, **target)
    report = {
        "schema_version": 1,
        "correspondence_sha256": CORRESPONDENCE_SHA256,
        "research_contract_sha256": contract["research_contract_sha256"],
        "baseline_iso_sha256": baseline["iso_sha256"],
        "baseline_entries": baseline["entries"],
        "source": source,
        "target": target,
        "output_sha256": _digest(output),
        "output_path": f"overlay/{TARGET_MTX}",
        "output_size": len(output),
        "new_groups": len(evidence["spans"]),
        "new_english_entries": evidence["disposition_entry_counts"][APPROVED],
        "unresolved_english_entries": len(evidence["entries"]) - evidence["disposition_entry_counts"][APPROVED],
        "blocks": blocks,
        "corpus": contract["corpus"],
        "native_owner": {
            "loader_mode": 6,
            "path_templates": ["adv/%s.MTX", "adv/%s.KSF"],
            "prefix": "KWLNSCR",
            "chapter_links": "KSF record ordinals select native MTX quarter-offset slots; 999 terminates",
            "pristine_elf_sha256": native["pristine_ee_sha256"],
            "installed_elf_sha256": baseline["elf_sha256"],
            "official_prx_sha256": native["ps4_prx_sha256"],
            "pristine_and_installed_ee_ranges": native["pristine_and_installed_ee_ranges"],
            "official_prx_ranges": native["ps4_prx_ranges"],
            "ksf_path": f"ADV/{TARGET_KSF}",
            "original_and_installed_ksf_sha256": _digest(installed[TARGET_KSF]),
            "ksf_records": ksf_records,
            "ksf_active_choice_payload_offsets": active_choices,
        },
        **evidence,
    }
    _publish(output_dir, output, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("ps2-adv", "ps4-adv", "baseline-iso", "output-dir"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = run(args.ps2_adv, args.ps4_adv, args.baseline_iso, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    fields = ("output_path", "output_sha256", "new_groups", "new_english_entries", "unresolved_english_entries")
    print(json.dumps({field: report[field] for field in fields}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
