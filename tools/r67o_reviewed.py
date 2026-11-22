"""Verify source correspondence for the nine inherited semantic-cluster DC entries."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import json
import mmap
from pathlib import Path
import re

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.localization import _cp932_boundaries, encode_ps2_english
from tools.mtx import MtxFile
from tools.r67_15g_route_audit import DATA_CVM_HEADER_SIZE
from tools.r67n_inventory import PRESENT, SEMANTIC, groups_for
from tools.structural_import import _ascii_left_signature, _ascii_right_signature

MANIFEST = Path(__file__).resolve().parents[1] / "translations/r67o_reviewed_correspondence.json"
PROOF = "reviewed source-specific Japanese correspondence and verified inherited installed bytes"
ENTRY_FIELDS = (
    "official_array_index", "dc_key", "official_text_utf8_sha256", "ps4_group_range",
    "ps2_group_or_cluster_range", "installed_offset", "installed_length", "installed_bytes_sha256",
)
RUBY = re.compile(r"l([㐀-鿿々]+)\(([ぁ-ゖァ-ヺー]+)\)")


@dataclass(frozen=True)
class Cluster:
    file: str
    ps4_range: tuple[int, int]
    ps2_range: tuple[int, int]
    dc_keys: tuple[int, ...]
    variants: tuple[tuple[str, str], ...] = ()

    @property
    def id(self) -> str:
        return f"{self.file}:{self.ps4_range[0]}"


CLUSTERS = (
    Cluster("DG/DG13_02.MTX", (7088, 7125), (7088, 7127), (7088, 7113),
            (("ようする", "ようとする"),)),
    Cluster("FN/FN13_16.MTX", (1646, 1691), (1646, 1691), (1646,),
            (("想って", "思って"),)),
    Cluster("MS/MS05_01.MTX", (28761, 28787), (28761, 28785), (28761,),
            (("お前をみたい", "お前みたい"),)),
    Cluster("MS/MS05_03.MTX", (8738, 8767), (8738, 8767), (8738,)),
    Cluster("MS/MS05_03.MTX", (16985, 17043), (16985, 17048), (16985, 17002),
            (("まあ、", "まァ、"), ("利かせて", "効かせて"))),
    Cluster("MS/MS06_01.MTX", (10651, 10676), (10651, 10678), (10651,),
            (("逃げられゃう", "逃げられちゃう"),)),
    Cluster("MS/MS11_03.MTX", (7267, 7304), (7267, 7306), (7267,)),
)


def _digest(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def _check_digest(raw: bytes, expected: str, description: str) -> None:
    if _digest(raw) != expected:
        raise ValueError(f"{description} SHA-256 drift")


def _canonical(raw: bytes) -> str:
    text = raw.decode("cp932")
    index = 0
    base = []
    while index < len(text):
        char = text[index]
        if char == "r":
            index += 1
            continue
        if char == "l":
            ruby = RUBY.match(text, index)
            if ruby:
                base.append(ruby[1])
                index = ruby.end()
                continue
        if char.isascii() or not char.isprintable():
            raise ValueError(f"unsupported display syntax at character {index}")
        base.append(char)
        index += 1
    return "".join(base)


def _variant_text(text: str, variants: tuple[tuple[str, str], ...]) -> str:
    for old, new in variants:
        if text.count(old) != 1:
            raise ValueError("approved PS4 variant must occur exactly once")
        text = text.replace(old, new, 1)
    return text


def _native_context(raw: bytes, span: tuple[int, int]) -> tuple[list[int], tuple[bytes, ...]]:
    mtx = MtxFile.parse(raw)
    start, end = span
    if not mtx.header_size <= start < end <= len(raw):
        raise ValueError("cluster span outside the MTX body")
    boundaries = _cp932_boundaries(raw, mtx.header_size)
    if start not in boundaries or end not in boundaries:
        raise ValueError("cluster span is misaligned in CP932")
    starts = sorted(set(mtx.pointer_offsets) - {0})
    owner = max((pointer for pointer in starts if pointer <= start), default=None)
    if owner is None or any(start < pointer < end for pointer in starts):
        raise ValueError("cluster span crosses MTX pointer regions")
    slots = [slot for slot, pointer in enumerate(mtx.pointer_offsets) if pointer == owner]
    context = (
        _ascii_left_signature(raw, start), _ascii_right_signature(raw, start),
        _ascii_left_signature(raw, end), _ascii_right_signature(raw, end),
    )
    return slots, context


def _native_controls(context: tuple[bytes, ...]) -> tuple[bytes, ...]:
    # DG's end delimiter is followed by different amounts of alignment padding.
    *prefix, ending = context
    unpadded = ending.rstrip(b"\0")
    return (*prefix, unpadded if unpadded.endswith(b"_") else ending)


def _source_evidence(ps2: bytes, ps4: bytes, ps2_range: tuple[int, int],
                     ps4_range: tuple[int, int], variants: tuple[tuple[str, str], ...]) -> dict:
    slots2, context2 = _native_context(ps2, ps2_range)
    slots4, context4 = _native_context(ps4, ps4_range)
    if slots2 != slots4:
        raise ValueError("cluster pointer slots disagree")
    if _native_controls(context2) != _native_controls(context4):
        raise ValueError("cluster native boundary bytes disagree")
    source2 = ps2[slice(*ps2_range)]
    source4 = ps4[slice(*ps4_range)]
    japanese2 = _canonical(source2)
    japanese4 = _variant_text(_canonical(source4), variants)
    if not japanese2 or japanese2 != japanese4:
        raise ValueError("cluster canonical Japanese disagrees")
    return {
        "ps2_range": list(ps2_range),
        "ps4_range": list(ps4_range),
        "ps2_span_sha256": _digest(source2),
        "ps4_span_sha256": _digest(source4),
        "canonical_utf8_sha256": _digest(japanese2.encode("utf-8")),
        "ps2_boundary_sha256": [_digest(part) for part in context2],
        "ps4_boundary_sha256": [_digest(part) for part in context4],
        "pointer_slots": slots2,
    }


def _check_inventory_scope(actual: set[tuple[str, int]], expected: set[tuple[str, int]]) -> None:
    if actual != expected:
        raise ValueError("inherited semantic entry scope drift")


def _installed_rows(rows: list[dict], payload: bytes, iso_offset: int, label: str) -> list[dict]:
    verified = []
    for row in rows:
        start = row["installed_offset"]
        length = row["installed_length"]
        if not 0 <= start < start + length <= len(payload):
            raise ValueError(f"{label}: installed entry outside MTX payload")
        _check_digest(payload[start:start + length], row["installed_bytes_sha256"],
                      f"{label}: installed entry")
        if verified:
            previous = verified[-1]
            end = previous["installed_offset"] + previous["installed_length"]
            if start != end + 1 or payload[end:start] != b"r":
                raise ValueError(f"{label}: installed entry line boundary drift")
        verified.append({**row, "installed_iso_offset": iso_offset + start})
    return verified


def _check_groups(groups: list, dc: dict, cluster: Cluster, rows: list[dict], expected: list[int],
                  ps4: bytes, installed: bytes) -> None:
    start, end = cluster.ps4_range
    matching = [(index, group) for index, group in enumerate(groups) if start <= group.anchor < end]
    if not matching or [index for index, _ in matching] != expected:
        raise ValueError(f"{cluster.id}: official DC groups drift")
    selected = [group for _, group in matching]
    if selected[0].anchor != start or selected[-1].replace_end != end:
        raise ValueError(f"{cluster.id}: official DC group bounds drift")
    if any(ps4[left.replace_end:right.anchor] != b"r" for left, right in zip(selected, selected[1:])):
        raise ValueError(f"{cluster.id}: official DC groups cross a native delimiter")
    group_entries = [(key, [group.anchor, group.replace_end])
                     for group in selected for key in (group.anchor, *group.synthetic_keys)]
    if group_entries != [(row["dc_key"], row["ps4_group_range"]) for row in rows]:
        raise ValueError(f"{cluster.id}: official DC group keys or ranges drift")
    for row in rows:
        index = row["official_array_index"]
        if not 0 <= index < len(dc["keys"]) or dc["keys"][index] != row["dc_key"]:
            raise ValueError(f"{cluster.id}: official DC array index drift")
        official = dc["values"][index]
        _check_digest(official.encode("utf-8"), row["official_text_utf8_sha256"],
                      f"{cluster.id}: official text")
        encoded = encode_ps2_english(official)
        start = row["installed_offset"]
        stop = start + row["installed_length"]
        if installed[start:stop] != encoded:
            raise ValueError(f"{cluster.id}: installed entry differs from encoded official DC text")


def verify_correspondence(iso: Path, ps2_adv: Path, ps4_adv: Path, inventory: Path) -> dict:
    """Verify against the original sources and r67.15n inventory on any candidate ISO."""
    manifest_raw = MANIFEST.read_bytes()
    pins = json.loads(manifest_raw)
    if (pins["schema_version"] != 1
            or set(pins["files"]) != {cluster.file for cluster in CLUSTERS}
            or set(pins["clusters"]) != {cluster.id for cluster in CLUSTERS}):
        raise ValueError("reviewed correspondence manifest scope drift")

    approved = {(cluster.file, key) for cluster in CLUSTERS for key in cluster.dc_keys}
    history = {}
    for row in json.loads((inventory / "entries.json").read_bytes()):
        if row["status"] != SEMANTIC:
            continue
        index = (row["file"], row["dc_key"])
        if index in history:
            raise ValueError("duplicate inherited semantic entry")
        history[index] = {field: row[field] for field in ENTRY_FIELDS}
    _check_inventory_scope(history.keys(), approved)

    clusters_by_file = defaultdict(list)
    for cluster in CLUSTERS:
        clusters_by_file[cluster.file].append(cluster)
    files, clusters, entries = [], [], []
    with iso.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        nested = find_record(index_iso(image)[1], "DATA.CVM").extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        volume = index_iso(image, nested)[1]
        for path, expected in pins["files"].items():
            record = find_record(volume, f"ADV/{path}")
            offset = nested + record.extent * SECTOR_SIZE
            installed = image[offset:offset + record.size]
            if len(installed) != expected["installed_size"]:
                raise ValueError(f"{path}: installed MTX size drift")
            _check_digest(installed, expected["installed_sha256"], f"{path}: installed MTX")

            ps2 = (ps2_adv / path).read_bytes()
            ps4 = (ps4_adv / path).read_bytes()
            dc_raw = (ps4_adv / expected["dc_path"]).read_bytes()
            _check_digest(ps2, expected["ps2_sha256"], f"{path}: PS2 source")
            _check_digest(ps4, expected["ps4_sha256"], f"{path}: PS4 source")
            _check_digest(dc_raw, expected["dc_sha256"], f"{path}: official DC")
            dc = json.loads(dc_raw)
            groups = groups_for(ps4, dc)
            files.append({"file": path, "installed_iso_offset": offset, **expected})
            for cluster in clusters_by_file[path]:
                pin = pins["clusters"][cluster.id]
                evidence = _source_evidence(ps2, ps4, cluster.ps2_range, cluster.ps4_range, cluster.variants)
                if evidence != pin["source"]:
                    raise ValueError(f"{cluster.id}: cluster source fingerprints drift")
                rows = [history[(path, key)] for key in cluster.dc_keys]
                if rows != pin["entries"] or any(
                    row["ps2_group_or_cluster_range"] != list(cluster.ps2_range) for row in rows
                ):
                    raise ValueError(f"{cluster.id}: inherited inventory entry fingerprints drift")
                checked = _installed_rows(rows, installed, offset, cluster.id)
                _check_groups(groups, dc, cluster, rows, pin["group_indices"], ps4, installed)
                entries.extend({"file": path, **row, "correspondence_id": cluster.id,
                                "status": PRESENT, "proof": PROOF} for row in checked)
                clusters.append({"correspondence_id": cluster.id, **evidence,
                                 "group_indices": pin["group_indices"], "dc_keys": list(cluster.dc_keys)})
        iso_sha256 = sha256(image).hexdigest()
    return {"schema_version": 1, "iso_sha256": iso_sha256, "manifest_sha256": _digest(manifest_raw),
            "files": files, "clusters": clusters, "entries": entries}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True, help="final r67.15n inventory directory")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = verify_correspondence(args.iso, args.ps2_adv, args.ps4_adv, args.inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"Verified {len(report['entries'])} inherited entries in {len(report['clusters'])} clusters")


if __name__ == "__main__":
    main()
