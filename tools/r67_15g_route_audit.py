"""Read-only route-content proof for r67.15g's finished ISO candidate.

The audit compares installed nested-DATA.CVM records with independently
regenerated official imports from pristine PS2 and recovered PS4 sources. It
does not modify an ISO or make a closed-world reachability claim.
"""
from __future__ import annotations

import hashlib
import json
import mmap
from pathlib import Path
from typing import Any

from tools.accepted_overrides import apply_ksf_override_manifest
from tools.exact_import import import_exact_mtx
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.ksf_import import import_exact_ksf, summarize_ksf_analyses
from tools.mtx import MtxFile

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_ISO = Path("/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso")
PS4_ADV_ROOT = Path(
    "/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/"
    "Media/StreamingAssets/data/ADV"
)
CHOICE_MANIFEST = ROOT / "translations/DG00_00.vertical-slice.json"
DATA_CVM_HEADER_SIZE = 0x1800

MTX_SPECS: dict[str, dict[str, Any]] = {
    "ADV/DG/DG00_00.MTX": {
        "source_sha256": "ed15d0402b8fc05fe21657a5d63962cd63e96206bb19b6bdb743013e9753819b",
        "official_sha256": "ed15d0402b8fc05fe21657a5d63962cd63e96206bb19b6bdb743013e9753819b",
        "map_path": "DG/EN/DG00_00DC.json",
        "map_sha256": "f338cdf660f7169519bafaea16b785ecbff9dbe1d3183aeb36d9d2cb3073ad04",
        "output_sha256": "eba4a22adc59b12857c0ecde22025608ccd5533c28def6ee7ffae5b74c5cfd6e",
        "entries": 195,
    },
    "ADV/DG/DG00_01.MTX": {
        "source_sha256": "5e91a8ff3e73e0cec3fa81f699b6cf6cea38d0f196040f0c0a1fae1326e54a7c",
        "official_sha256": "5e91a8ff3e73e0cec3fa81f699b6cf6cea38d0f196040f0c0a1fae1326e54a7c",
        "map_path": "DG/EN/DG00_01DC.json",
        "map_sha256": "f087398101e28ce576f3da04464d14875417fdc5c5abe9fd02117d6449c098a8",
        "output_sha256": "eb5b6a17501ada0e684c2c984727d3c5f04b5059963506a97c61888b5825b04b",
        "entries": 34,
    },
    "ADV/MS/MS00_02.MTX": {
        "source_sha256": "d1ff7c51c4012426266b0aa9b607a2d6f185460fdf661420178fe65ae68ea654",
        "official_sha256": "d1ff7c51c4012426266b0aa9b607a2d6f185460fdf661420178fe65ae68ea654",
        "map_path": "MS/EN/MS00_02DC.json",
        "map_sha256": "76fa5fef468ce1a3fb6d03c729a75c21a5905b80a39f8c32c0a418aa11987746",
        "output_sha256": "e53e5b3e3da54e608020da5e8f105b11309b6a104cef9646abfbf1bc1a4ac095",
        "entries": 593,
        "scope_note": (
            "This MTX contains the post-Salah-escape military attack and later "
            "hospital material; its 593 official map entries are not an "
            "ambush-only count."
        ),
    },
}

UNCHANGED_MTX: dict[str, dict[str, Any]] = {
    "ADV/DG/DG00_02.MTX": {
        "size": 32,
        "sha256": "381b9c97bf14fb1d53ba50eebeeea9ad21ffb59751ce166d917909c240d87a54",
        "classification": "control_only",
    },
    "ADV/MS/MS00_00.MTX": {
        "size": 28,
        "sha256": "317426ccf3e4300485ae55b45bec7dd6876490990f62b6320c18f2291ea01d80",
        "classification": "control_only",
    },
    "ADV/MS/MS00_01.MTX": {
        "size": 104,
        "sha256": "4d48327f65411186c5619ef122ad4f331e4cce1912c4664a74ac4f7d941ce61d",
        "classification": "ps2_control_script_preserved",
    },
}

KSF_SPECS: dict[str, dict[str, Any]] = {
    "ADV/DG/DG00_00.KSF": {
        "source_sha256": "93462741f2c724c4c096ed463f6b14dc8e3a08d2fb7bf35f8f990eebd3190e31",
        "official_sha256": "93462741f2c724c4c096ed463f6b14dc8e3a08d2fb7bf35f8f990eebd3190e31",
        "map_path": "DG/EN/DG00_00.KSFDC.json",
        "map_sha256": "6b1f6d30e7fe14f8b79849d116c3305c2f9ffb624eee95d968dd009c5b84658c",
        "output_sha256": "db445fbce3a0fc6111ca2e0f121ba29bbd40dcab646eb4ce43b2db9bd6179ecd",
        "expected_fit": 3,
        "approved_overflow_offsets": [9339, 11689],
    },
    "ADV/MS/MS00_02.KSF": {
        "source_sha256": "fd94179eef6d309eb98521f319632defb244298b8c43576fd17227a142c47ad9",
        "official_sha256": "fd94179eef6d309eb98521f319632defb244298b8c43576fd17227a142c47ad9",
        "map_path": "MS/EN/MS00_02.KSFDC.json",
        "map_sha256": "40773538be2edfd4731c686e9b38e931f16aedda1f0732e87650f9c1308e2912",
        "output_sha256": "1f5deba52374c7a72f92968a003bc7f1cd7b57dd4cbe722f4021e5368e01192e",
        "expected_fit": 10,
        "approved_overflow_offsets": [],
    },
}

UNCHANGED_KSF: dict[str, str] = {
    "ADV/DG/DG00_01.KSF": "5c72874bfb27150f2b4c9c013487c1d252b7cca7fffa3fe43e70b341d81ad898",
    "ADV/DG/DG00_02.KSF": "5c72874bfb27150f2b4c9c013487c1d252b7cca7fffa3fe43e70b341d81ad898",
    "ADV/MS/MS00_00.KSF": "5c72874bfb27150f2b4c9c013487c1d252b7cca7fffa3fe43e70b341d81ad898",
    "ADV/MS/MS00_01.KSF": "e5b8bf29a1f507d5468ef3b90cc35cec3ce33d76ee9c1ea914eed30b53e2d1c9",
}

MS00_01_PS4 = {
    "path": "MS/MS00_01.MTX",
    "size": 1432,
    "sha256": "b3272bc0f5ed75707b209c54d2d317ad414f9e9c02d4e816a3c4ebf8c3aa28bc",
    "map_path": "MS/EN/MS00_01DC.json",
    "map_sha256": "07d2cd434f617dc11c24ac16ef7a812968b16e0629e071ff92c65baaa39c6aff",
    "map_entries": 43,
}

CHOICE_MANIFEST_SHA256 = "8d2147111579cc224408b93f24eb9ae4804286f1626751f3d5f83dd8c5350d9a"
EXPECTED_ACCEPTED_CHOICES = (
    (9339, 31, "Pick  up  the  device  on  the  ground", "Pick up device on the ground", True),
    (11689, 31, "Pick  up  the  device  on  the  ground", "Pick up device on the ground", True),
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _read_iso_records(iso_path: Path) -> tuple[Any, Any, int, tuple[Any, ...]]:
    stream = Path(iso_path).open("rb")
    image = mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ)
    _volume_sectors, outer_records = index_iso(image)
    cvm = find_record(outer_records, "DATA.CVM")
    nested_base = cvm.extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
    if nested_base >= len(image):
        image.close()
        stream.close()
        raise ValueError("DATA.CVM nested ISO base lies outside the image")
    _nested_sectors, nested_records = index_iso(image, nested_base)
    return stream, image, nested_base, nested_records


def _record_bytes(image: mmap.mmap, base: int, records: tuple[Any, ...], path: str) -> bytes:
    record = find_record(records, path)
    start = base + record.extent * SECTOR_SIZE
    end = start + record.size
    if start < base or end > len(image):
        raise ValueError(f"ISO record {path} lies outside its containing image")
    return bytes(image[start:end])


def _require_exact_payload(installed: bytes, expected: bytes, message: str) -> None:
    if installed != expected:
        raise ValueError(message)


def _read_pinned_map(relative: str, expected_sha256: str) -> tuple[bytes, dict[str, Any]]:
    path = PS4_ADV_ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing official localization map: {path}")
    raw = path.read_bytes()
    if _sha(raw) != expected_sha256:
        raise ValueError(f"official localization map preimage mismatch: {relative}")
    try:
        parsed = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"official localization map is malformed: {relative}") from exc
    if (not isinstance(parsed, dict) or not isinstance(parsed.get("keys"), list)
            or not isinstance(parsed.get("values"), list)
            or len(parsed["keys"]) != len(parsed["values"])):
        raise ValueError(f"official localization map schema mismatch: {relative}")
    return raw, parsed


def _read_pinned_source(relative: str, expected_sha256: str) -> bytes:
    path = PS4_ADV_ROOT / relative
    if not path.is_file():
        raise ValueError(f"missing official source asset: {path}")
    raw = path.read_bytes()
    if _sha(raw) != expected_sha256:
        raise ValueError(f"official source asset preimage mismatch: {relative}")
    return raw


def _audit_mtx(
    original_image: mmap.mmap, finished_image: mmap.mmap,
    original_records: tuple[Any, ...], original_base: int,
    finished_records: tuple[Any, ...], finished_base: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    assets: dict[str, dict[str, Any]] = {}
    for relative, spec in MTX_SPECS.items():
        source_path = relative.removeprefix("ADV/")
        source = _record_bytes(original_image, original_base, original_records, relative)
        if _sha(source) != spec["source_sha256"]:
            raise ValueError(f"pristine PS2 MTX source preimage mismatch: {relative}")
        official = _read_pinned_source(source_path, spec["official_sha256"])
        if official != source:
            raise ValueError(f"exact-source MTX binary differs from pristine PS2: {relative}")
        _map_raw, dc = _read_pinned_map(spec["map_path"], spec["map_sha256"])
        if len(dc["keys"]) != spec["entries"]:
            raise ValueError(f"official MTX import-entry count mismatch: {relative}")
        regenerated = import_exact_mtx(source, official, dc)
        if _sha(regenerated) != spec["output_sha256"]:
            raise ValueError(f"official MTX regeneration preimage mismatch: {relative}")
        installed = _record_bytes(finished_image, finished_base, finished_records, relative)
        _require_exact_payload(
            installed, regenerated,
            f"finished ISO MTX differs from official regeneration: {relative}",
        )
        assets[relative] = {
            "verification": "official_exact",
            "finished_size": len(installed),
            "finished_sha256": _sha(installed),
            "official_import_entries": len(dc["keys"]),
            "pristine_ps2_sha256": _sha(source),
            "official_ps4_source_sha256": _sha(official),
            "official_map_sha256": spec["map_sha256"],
            "official_regenerated_sha256": _sha(regenerated),
            "scope_note": spec.get("scope_note"),
        }

    for relative, spec in UNCHANGED_MTX.items():
        source = _record_bytes(original_image, original_base, original_records, relative)
        installed = _record_bytes(finished_image, finished_base, finished_records, relative)
        if len(source) != spec["size"] or _sha(source) != spec["sha256"]:
            raise ValueError(f"pristine PS2 control MTX preimage mismatch: {relative}")
        _require_exact_payload(installed, source, f"finished ISO changed PS2 control MTX: {relative}")
        evidence: dict[str, Any] = {
            "verification": "unchanged_control_only" if relative != "ADV/MS/MS00_01.MTX"
            else "unchanged_ps2_control_script",
            "finished_size": len(installed),
            "finished_sha256": _sha(installed),
            "pristine_ps2_sha256": _sha(source),
        }
        if relative == "ADV/MS/MS00_01.MTX":
            ps4_raw = _read_pinned_source(MS00_01_PS4["path"], MS00_01_PS4["sha256"])
            _map_raw, ps4_map = _read_pinned_map(MS00_01_PS4["map_path"], MS00_01_PS4["map_sha256"])
            if len(ps4_raw) != MS00_01_PS4["size"] or len(ps4_map["keys"]) != MS00_01_PS4["map_entries"]:
                raise ValueError("PS4 MS00_01 structural-difference preimage mismatch")
            evidence.update({
                "ps2_equals_ps4": installed == ps4_raw,
                "ps4_comparison_size": len(ps4_raw),
                "ps4_comparison_sha256": _sha(ps4_raw),
                "ps4_localization_map_entries": len(ps4_map["keys"]),
                "ps4_localization_map_sha256": MS00_01_PS4["map_sha256"],
                "ps4_comparison_note": (
                    "PS4 MS00_01 is a structurally different 1432-byte MTX with 43 "
                    "localization-map entries; the 104-byte PS2 control script is "
                    "preserved, and PS4-only content is not imported or counted as missing."
                ),
            })
        assets[relative] = evidence
    return assets, {}


def _read_choice_manifest() -> tuple[bytes, dict[str, Any]]:
    if not CHOICE_MANIFEST.is_file():
        raise ValueError(f"missing approved KSF choice manifest: {CHOICE_MANIFEST}")
    raw = CHOICE_MANIFEST.read_bytes()
    if _sha(raw) != CHOICE_MANIFEST_SHA256:
        raise ValueError("approved KSF choice manifest preimage mismatch")
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("approved KSF choice manifest is malformed") from exc
    rows = manifest.get("ksf", [])
    if not isinstance(rows, list):
        raise ValueError("approved KSF choice manifest schema mismatch")
    actual = tuple(
        (int(row["offset"]), int(row["capacity"]), str(row["official"]),
         str(row["text"]), bool(row.get("constrained", False)))
        for row in rows
        if int(row["offset"]) in {9339, 11689}
    )
    if actual != EXPECTED_ACCEPTED_CHOICES:
        raise ValueError("approved KSF choice instructions differ from pinned decisions")
    return raw, manifest


def _audit_ksf(
    original_image: mmap.mmap, finished_image: mmap.mmap,
    original_records: tuple[Any, ...], original_base: int,
    finished_records: tuple[Any, ...], finished_base: int,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    choices: dict[str, dict[str, Any]] = {}
    unchanged: dict[str, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    _manifest_raw, manifest = _read_choice_manifest()

    for relative, spec in KSF_SPECS.items():
        source_path = relative.removeprefix("ADV/")
        source = _record_bytes(original_image, original_base, original_records, relative)
        if _sha(source) != spec["source_sha256"]:
            raise ValueError(f"pristine PS2 KSF source preimage mismatch: {relative}")
        official = _read_pinned_source(source_path, spec["official_sha256"])
        if official != source:
            raise ValueError(f"exact-source KSF binary differs from pristine PS2: {relative}")
        _map_raw, dc = _read_pinned_map(spec["map_path"], spec["map_sha256"])
        regenerated, analyses = import_exact_ksf(source, official, dc)
        summary = summarize_ksf_analyses(analyses)
        if summary["fit"] != spec["expected_fit"]:
            raise ValueError(f"official KSF fit count mismatch: {relative}")

        overflow_offsets = sorted(field.key for field in analyses if field.status == "overflow")
        approved = spec["approved_overflow_offsets"]
        unexpected = [field for field in analyses
                      if field.status == "ambiguous"
                      or (field.status == "overflow" and field.key not in approved)]
        for field in unexpected:
            unresolved.append({
                "asset": relative, "key": field.key, "status": field.status,
                "reason": field.reason,
            })
        if overflow_offsets != approved:
            raise ValueError(f"KSF overflow/approval set mismatch: {relative}")
        if relative == "ADV/DG/DG00_00.KSF":
            regenerated = apply_ksf_override_manifest(regenerated, manifest)
        if _sha(regenerated) != spec["output_sha256"]:
            raise ValueError(f"official KSF regeneration preimage mismatch: {relative}")
        installed = _record_bytes(finished_image, finished_base, finished_records, relative)
        _require_exact_payload(
            installed, regenerated,
            f"finished ISO KSF differs from official/approved regeneration: {relative}",
        )
        choices[relative] = {
            "verification": "official_exact_with_approved_compaction" if approved else "official_exact",
            "finished_size": len(installed),
            "finished_sha256": _sha(installed),
            "official_choice_entries": summary["entries"],
            "pristine_ps2_sha256": _sha(source),
            "official_ps4_source_sha256": _sha(official),
            "official_map_sha256": spec["map_sha256"],
            "counts": {
                "fit": summary["fit"], "approved_compaction": len(approved),
                "unresolved": len(unexpected),
            },
            "approved_compaction_offsets": approved,
            "approved_compaction_text": "Pick up device on the ground" if approved else None,
            "analysis": [
                {"key": field.key, "status": field.status,
                 "capacity": field.capacity, "reason": field.reason}
                for field in analyses
            ],
            "regenerated_sha256": _sha(regenerated),
        }

    for relative, expected_sha in UNCHANGED_KSF.items():
        source = _record_bytes(original_image, original_base, original_records, relative)
        installed = _record_bytes(finished_image, finished_base, finished_records, relative)
        if _sha(source) != expected_sha:
            raise ValueError(f"pristine PS2 control KSF preimage mismatch: {relative}")
        _require_exact_payload(installed, source, f"finished ISO changed control KSF: {relative}")
        unchanged[relative] = {
            "verification": "unchanged_control_only",
            "finished_size": len(installed), "finished_sha256": _sha(installed),
        }
    return choices, unchanged, unresolved


def audit(iso_path: Path) -> dict[str, Any]:
    """Audit route-owned records in a finished image without writing to it."""
    original_path = Path(ORIGINAL_ISO)
    finished_path = Path(iso_path)
    if not original_path.is_file():
        raise ValueError(f"missing pristine PS2 ISO: {original_path}")
    if not finished_path.is_file():
        raise ValueError(f"missing finished ISO: {finished_path}")
    original_stream, original_image, original_base, original_records = _read_iso_records(original_path)
    finished_stream, finished_image, finished_base, finished_records = _read_iso_records(finished_path)
    try:
        assets, _ = _audit_mtx(
            original_image, finished_image, original_records, original_base,
            finished_records, finished_base,
        )
        choices, unchanged_ksf, unresolved = _audit_ksf(
            original_image, finished_image,
            original_records, original_base, finished_records, finished_base
        )
        return {
            "schema_version": 1,
            "audit_kind": "finished_iso_exact_payload_audit",
            "finished_iso": str(finished_path),
            "read_only": True,
            "nested_iso_base_rule": "DATA.CVM.extent * 2048 + 0x1800",
            "assets": assets,
            "choice_assets": choices,
            "unchanged_control_ksf_assets": unchanged_ksf,
            "unresolved_choice_entries": unresolved,
            "route_claim": (
                "Bounded file-payload provenance and exact finished-image match only; "
                "not a closed-world reachability or runtime-completion claim."
            ),
            "endpoint_capture_checklist": [
                "Capture the Heracleion Shrine route start and Salah encounter/escape transition.",
                "Capture the initial H.A.N.T. setup and its route handoff.",
                "Capture Chamber of Lions: pedestal/door transition, encounter, and exit.",
                "Capture Gate of Anubis: raised stepping stone, wire-gun crossing, Snake Staff lever, and east inscription door.",
                "Capture the optional Soul Well branch separately; do not treat optional entry as mandatory-route proof.",
                "Capture the storeroom: nitric acid and hydrochloric acid pickups, aqua-regia synthesis, and golden-chain door.",
                "Capture Anubis Altar: ladder/encounter, throne inscription, and boss transition.",
                "Capture the post-Salah-escape military attack, including the wheelchair man and soldiers; stop before later hospital content.",
                "For each capture, retain the full-screen image plus scene/room label and the immediately preceding transition; do not infer a missing screen from file hashes.",
            ],
            "known_platform_difference": assets["ADV/MS/MS00_01.MTX"]["ps4_comparison_note"],
            "lexical_scan_caveat": (
                "No lexical-zero statistic is used as a reachability boundary; script dependencies and optional/conditional runtime paths may remain."
            ),
        }
    finally:
        original_image.close()
        original_stream.close()
        finished_image.close()
        finished_stream.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read-only r67.15g route ISO evidence")
    parser.add_argument("iso", type=Path)
    arguments = parser.parse_args()
    result = audit(arguments.iso)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(encoded, end="")
