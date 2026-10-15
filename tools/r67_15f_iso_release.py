"""Build and exhaustively audit the diagnostic r67.15f ISO.

The native transformation is owned by r67_15f_item_panel_layout.apply. This
module owns source pinning, declared ELF-byte boundaries, ISO growth safety,
and the finished-disc delta audit.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import mmap
import shutil
import struct
import subprocess
from pathlib import Path

from tools.iso9660_patch import index_iso, find_record, patch_directory_record
from tools.r67_14y_release import check_growth
from tools.r67_lion_statue_iso_patch import sha_file
from tools.tmx import find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
PREVIOUS_ISO = ROOT / "local/r67-candidates/67.15e-compound-bubble.iso"
CANDIDATE_ISO = ROOT / "local/r67-candidates/67.15f-item-panel-layout.iso"
SOURCE_ELF = ROOT / "local/r67-15e-compound-bubble.elf"
SOURCE_ART = ROOT / "local/r67-15d-group4-clean.BIN"
CANDIDATE_ELF = ROOT / "local/r67-15f-item-panel-layout.elf"
MANIFEST = ROOT / "local/r67-15f-release.json"
AUDIT = ROOT / "local/r67-15f-whole-iso-audit.json"
PREVIOUS_SHA = "442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014"
SOURCE_ELF_SHA = "d1dc87b0762465f4aa653e05e07af73cc593d4e716ee2575790edc617a54972e"
SOURCE_ART_SHA = "23dfe4cf48ec3c3ecd2f583fdc2a1fea336442b369cba02264dd9f2f8e7650da"
EXPECTED_ART_TMX = "GRP004/GP004_14.TMX"
PROTECTED_ART_TMX = ("GRP004/GP004_05.TMX", "GRP004/GP004_18.TMX",
                     "GRP004/GP004_19.TMX")
PHYSICAL_BYTES = 2_095_382_528
SECTOR_BYTES = 2048


@dataclass(frozen=True)
class PreparedRelease:
    before: bytes
    after: bytes
    patch_report: dict
    before_art: bytes
    after_art: bytes
    art_report: dict
    art_target_tmx: str
    owners: dict[str, tuple[tuple[int, int], ...]]
    art_owners: dict[str, tuple[tuple[int, int], ...]]
    executable_extent: int
    executable_record_offset: int
    executable_offset: int
    executable_size: int
    art_extent: int
    art_record_offset: int
    art_offset: int
    art_size: int


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _patch_contract():
    """Load the native patch only when release preparation is requested."""
    from tools import r67_15f_item_panel_layout as patch_module

    apply = getattr(patch_module, "apply", None)
    owners = getattr(patch_module, "PERMITTED_EXISTING_RANGES", None)
    if not callable(apply) or not isinstance(owners, dict) or not owners:
        raise ValueError(
            "15f patch module must export apply(old) and named "
            "PERMITTED_EXISTING_RANGES"
        )
    normalized: dict[str, tuple[tuple[int, int], ...]] = {}
    claimed: dict[int, str] = {}
    source_size = SOURCE_ELF.stat().st_size
    for name, ranges in owners.items():
        if not isinstance(name, str) or not name or not isinstance(ranges, (tuple, list)):
            raise ValueError("Invalid named 15f ELF ownership declaration")
        owned = []
        for item in ranges:
            if (not isinstance(item, (tuple, list)) or len(item) != 2
                    or not all(isinstance(v, int) for v in item)):
                raise ValueError(f"Invalid ELF range for owner {name!r}")
            start, end = item
            if start < 0 or end <= start or end > source_size:
                raise ValueError(f"Invalid ELF range for owner {name!r}")
            if start < 0x68 and end > 0x64:
                raise ValueError("Native ELF owner overlaps the segment-length field")
            for offset in range(start, end):
                prior = claimed.setdefault(offset, name)
                if prior != name:
                    raise ValueError(f"Overlapping ELF owners at {offset:#x}")
            owned.append((start, end))
        if not owned:
            raise ValueError(f"ELF owner {name!r} declares no byte ranges")
        normalized[name] = tuple(owned)
    return apply, normalized


def _art_patch_contract():
    from tools import r67_15f_item_panel_art as art_module

    apply = getattr(art_module, "apply", None)
    owners = getattr(art_module, "PERMITTED_ART_RANGES", None)
    target_tmx = getattr(art_module, "TARGET_TMX", None)
    if not callable(apply) or not isinstance(owners, dict) or not owners:
        raise ValueError(
            "15f art module must export apply(old) and named PERMITTED_ART_RANGES"
        )
    if target_tmx != EXPECTED_ART_TMX:
        raise ValueError(f"15f art target must be {EXPECTED_ART_TMX}")
    normalized: dict[str, tuple[tuple[int, int], ...]] = {}
    claimed: dict[int, str] = {}
    for name, ranges in owners.items():
        if not isinstance(name, str) or not name or not isinstance(ranges, (tuple, list)):
            raise ValueError("Invalid named 15f GP004 ownership declaration")
        owned = []
        for item in ranges:
            if (not isinstance(item, (tuple, list)) or len(item) != 2
                    or not all(isinstance(v, int) for v in item)):
                raise ValueError(f"Invalid GP004 range for owner {name!r}")
            start, end = item
            if start < 0 or end <= start:
                raise ValueError(f"Invalid GP004 range for owner {name!r}")
            for offset in range(start, end):
                prior = claimed.setdefault(offset, name)
                if prior != name:
                    raise ValueError(f"Overlapping GP004 owners at {offset:#x}")
            owned.append((start, end))
        if not owned:
            raise ValueError(f"GP004 owner {name!r} declares no byte ranges")
        normalized[name] = tuple(owned)
    return apply, normalized, target_tmx


def _validate_elf_changes(before: bytes, after: bytes,
                          owners: dict[str, tuple[tuple[int, int], ...]]) -> dict[int, tuple[int, str]]:
    if len(after) < len(before):
        raise ValueError("15f transformation unexpectedly shrank the executable")
    changed: dict[int, tuple[int, str]] = {}
    for name, ranges in owners.items():
        for start, end in ranges:
            if start < 0 or end <= start or end > len(before):
                raise ValueError(f"ELF owner {name!r} range exceeds the pinned source")
            if start < 0x68 and end > 0x64:
                raise ValueError("Native ELF owner overlaps the segment-length field")
    for offset, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        if 0x64 <= offset < 0x68:
            owner = "elf_segment_file_length"
        else:
            owner = next((name for name, ranges in owners.items()
                          if any(start <= offset < end for start, end in ranges)), None)
            if owner is None:
                raise ValueError(f"unowned ELF byte {offset:#x}")
        changed[offset] = (new, owner)
    for offset in range(len(before), len(after)):
        changed[offset] = (after[offset], "appended_patch_payload")
    return changed


def _validate_art_changes(before: bytes, after: bytes,
                          owners: dict[str, tuple[tuple[int, int], ...]]) -> dict[int, tuple[int, str]]:
    if len(before) != len(after):
        raise ValueError("15f artwork patch changed GP004 length")
    for name, ranges in owners.items():
        for start, end in ranges:
            if start < 0 or end <= start or end > len(before):
                raise ValueError(f"GP004 owner {name!r} range exceeds the pinned source")
    changed: dict[int, tuple[int, str]] = {}
    for offset, (old, new) in enumerate(zip(before, after)):
        if old == new:
            continue
        owner = next((name for name, ranges in owners.items()
                      if any(start <= offset < end for start, end in ranges)), None)
        if owner is None:
            raise ValueError(f"unowned GP004 byte {offset:#x}")
        changed[offset] = (new, owner)
    return changed


def _check_art_ownership_ranges(owners, target_entry):
    """Keep all art permissions inside the declared target TMX pixels/palette."""
    pixel = (target_entry.pixel_offset,
             target_entry.pixel_offset + target_entry.pixel_bytes)
    palette = (target_entry.palette_offset,
               target_entry.palette_offset + target_entry.palette_bytes)
    for name, ranges in owners.items():
        for start, end in ranges:
            if not ((pixel[0] <= start < end <= pixel[1])
                    or (palette[0] <= start < end <= palette[1])):
                raise ValueError(
                    f"15f art owner {name!r} escapes target TMX pixels/palette"
                )


def _assert_protected_art_chunks(before: bytes, after: bytes) -> None:
    if len(before) != len(after):
        raise ValueError("GP004 length changed while checking protected textures")
    for name in PROTECTED_ART_TMX:
        old_entry = find_tmx_entry(before, name)
        new_entry = find_tmx_entry(after, name)
        start, end = old_entry.base_offset, old_entry.base_offset + old_entry.chunk_size
        if (new_entry != old_entry or before[start:end] != after[start:end]):
            raise ValueError(f"Protected {name} changed")


def _installed_regions(image):
    _, outer = index_iso(image)
    executable = find_record(outer, "SLPM_665.11")
    cvm = find_record(outer, "DATA.CVM")
    cvm_base = cvm.extent * SECTOR_BYTES + 0x1800
    _, nested = index_iso(image, cvm_base)
    group4 = find_record(nested, "BLBRD/B_GP004.BIN")
    return (executable, executable.extent * SECTOR_BYTES,
            group4, cvm_base + group4.extent * SECTOR_BYTES)


def _compare_expected_bytes(baseline, candidate, expected: dict[int, tuple[int, str]]) -> dict[str, int]:
    if len(baseline) != len(candidate):
        raise ValueError("ISO physical length differs")
    if any(offset < 0 or offset >= len(candidate) for offset in expected):
        raise ValueError("Expected change lies outside finished ISO")
    observed: Counter[str] = Counter()
    block_size = 8 * 1024 * 1024
    for block in range(0, len(baseline), block_size):
        left = baseline[block:block + block_size]
        right = candidate[block:block + block_size]
        if left == right:
            continue
        for index, (old, new) in enumerate(zip(left, right)):
            if old == new:
                continue
            offset = block + index
            record = expected.get(offset)
            if record is None or record[0] != new:
                raise ValueError(f"unexplained finished-ISO byte {offset:#x}")
            observed[record[1]] += 1
    if sum(observed.values()) != len(expected):
        missing = next(offset for offset in expected if baseline[offset] == candidate[offset])
        raise ValueError(f"expected finished-ISO change absent at {missing:#x}")
    return dict(sorted(observed.items()))


def preflight() -> PreparedRelease:
    if sha_file(PREVIOUS_ISO) != PREVIOUS_SHA:
        raise ValueError("Pinned 15e source ISO SHA-256 mismatch")
    before = SOURCE_ELF.read_bytes()
    if sha(before) != SOURCE_ELF_SHA:
        raise ValueError("Pinned 15e source ELF SHA-256 mismatch")
    apply, owners = _patch_contract()
    after, patch_report = apply(before)
    if not isinstance(after, bytes) or not isinstance(patch_report, dict):
        raise ValueError("15f apply must return (bytes, report dict)")
    _validate_elf_changes(before, after, owners)
    if sha_file(SOURCE_ART) != SOURCE_ART_SHA:
        raise ValueError("Pinned 15d GP004 source SHA-256 mismatch")
    before_art = SOURCE_ART.read_bytes()
    art_apply, art_owners, art_target = _art_patch_contract()
    after_art, art_report = art_apply(before_art)
    if not isinstance(after_art, bytes) or not isinstance(art_report, dict):
        raise ValueError("15f art apply must return (bytes, report dict)")
    _validate_art_changes(before_art, after_art, art_owners)
    _assert_protected_art_chunks(before_art, after_art)
    target_entry = find_tmx_entry(before_art, art_target)
    _check_art_ownership_ranges(art_owners, target_entry)
    with PREVIOUS_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if len(image) != PHYSICAL_BYTES:
            raise ValueError("Pinned 15e physical ISO size mismatch")
        _, records = index_iso(image)
        entry, offset, group4, art_offset = _installed_regions(image)
        offset = entry.extent * SECTOR_BYTES
        if entry.size != len(before) or image[offset:offset + entry.size] != before:
            raise ValueError("Installed 15e ELF differs from its pinned staged source")
        if len(after) > entry.size:
            check_growth(image, entry, records, len(after))
        elif len(after) > entry.sectors * SECTOR_BYTES:
            raise ValueError("15f executable exceeds its allocated sectors")
        if any(image[offset + len(before):offset + len(after)]):
            raise ValueError("15f appended ELF bytes overlap nonzero ISO data")
        if (group4.size != len(before_art)
                or image[art_offset:art_offset + group4.size] != before_art):
            raise ValueError("Embedded 15e GP004 differs from pinned cleaned 15d fixture")
        embedded_art = image[art_offset:art_offset + group4.size]
        embedded_target = find_tmx_entry(embedded_art, art_target)
        if embedded_target != target_entry:
            raise ValueError("Embedded GP004_14 texture geometry differs from fixture")
        return PreparedRelease(
            before, after, patch_report, before_art, after_art, art_report,
            art_target,
            owners, art_owners, entry.extent, entry.record_offset, offset,
            entry.size, group4.extent, group4.record_offset, art_offset,
            group4.size,
        )


def audit(previous: Path = PREVIOUS_ISO, latest: Path = CANDIDATE_ISO,
          prepared: PreparedRelease | None = None) -> dict:
    if previous != PREVIOUS_ISO or sha_file(previous) != PREVIOUS_SHA:
        raise ValueError("Audit baseline is not the pinned 15e ISO")
    prep = preflight() if prepared is None else prepared
    # Revalidate caller-supplied prepared data against the pinned transform and
    # module-owned range declaration; callers cannot supply audit offsets.
    apply, owners = _patch_contract()
    art_apply, art_owners, art_target = _art_patch_contract()
    if (prep.owners != owners or prep.art_owners != art_owners
            or sha(prep.before) != SOURCE_ELF_SHA
            or apply(prep.before)[0] != prep.after
            or sha(prep.before_art) != SOURCE_ART_SHA
            or art_apply(prep.before_art)[0] != prep.after_art
            or prep.art_target_tmx != art_target):
        raise ValueError("Prepared 15f transformation does not match the pinned patch")
    _assert_protected_art_chunks(prep.before_art, prep.after_art)
    _check_art_ownership_ranges(art_owners,
                                find_tmx_entry(prep.before_art, art_target))
    elf_expected = _validate_elf_changes(prep.before, prep.after, owners)
    art_expected = _validate_art_changes(prep.before_art, prep.after_art, art_owners)
    with previous.open("rb") as left_file, latest.open("rb") as right_file:
        with mmap.mmap(left_file.fileno(), 0, access=mmap.ACCESS_READ) as left, \
                mmap.mmap(right_file.fileno(), 0, access=mmap.ACCESS_READ) as right:
            if len(left) != PHYSICAL_BYTES or len(right) != PHYSICAL_BYTES:
                raise ValueError("ISO physical length differs from the pinned disc size")
            _, old_records = index_iso(left)
            _, new_records = index_iso(right)
            old_entry, _, old_group, art_offset = _installed_regions(left)
            new_entry = find_record(new_records, "SLPM_665.11")
            _, _, new_group, new_art_offset = _installed_regions(right)
            old_offset = old_entry.extent * SECTOR_BYTES
            if len(prep.after) > old_entry.size:
                check_growth(left, old_entry, old_records, len(prep.after))
            elif len(prep.after) > old_entry.sectors * SECTOR_BYTES:
                raise ValueError("15f executable exceeds its allocated sectors")
            if (old_entry.extent != prep.executable_extent
                    or old_entry.record_offset != prep.executable_record_offset
                    or old_entry.size != len(prep.before)
                    or new_entry.extent != old_entry.extent
                    or new_entry.record_offset != old_entry.record_offset
                    or new_entry.size != len(prep.after)
                    or old_group.extent != prep.art_extent
                    or old_group.record_offset != prep.art_record_offset
                    or old_group.size != prep.art_size
                    or new_group.extent != old_group.extent
                    or new_group.record_offset != old_group.record_offset
                    or new_group.size != old_group.size
                    or new_art_offset != art_offset):
                raise ValueError("Executable ISO record extent or length mismatch")
            if left[old_offset:old_offset + len(prep.before)] != prep.before:
                raise ValueError("Pinned 15e executable bytes changed during audit")
            if right[old_offset:old_offset + len(prep.after)] != prep.after:
                raise ValueError("Finished 15f executable differs from deterministic patch")
            if (left[art_offset:art_offset + prep.art_size] != prep.before_art
                    or right[art_offset:art_offset + prep.art_size] != prep.after_art):
                raise ValueError("Finished 15f GP004 differs from deterministic art patch")
            expected = {old_offset + index: value_owner
                        for index, value_owner in elf_expected.items()
                        if left[old_offset + index] != value_owner[0]}
            for index, (value, owner) in art_expected.items():
                if left[art_offset + index] != value:
                    expected[art_offset + index] = (value, owner)
            for index, value in enumerate(struct.pack("<I", len(prep.after))
                                          + struct.pack(">I", len(prep.after))):
                at = old_entry.record_offset + 10 + index
                if left[at] != value:
                    expected[at] = (value, "iso9660_executable_size_both_endians")
            counts = _compare_expected_bytes(left, right, expected)
            return dict(
                status="PASS_EXACT_15E_BASELINE_ZERO_UNEXPLAINED",
                baseline_15e_iso_sha256=PREVIOUS_SHA,
                candidate_iso_sha256=sha_file(latest),
                complete_disc_bytes_compared=len(left),
                modified_bytes=sum(counts.values()),
                byte_owner_summary=counts,
                unexplained_bytes=0,
                all_non_gp004_14_assets_unchanged=True,
                gp004_18_and_gp004_19_unchanged=True,
                unrelated_native_owners_unchanged=True,
                gameplay_approved=False,
            )


def build() -> dict:
    temporary = CANDIDATE_ISO.with_suffix(".incomplete")
    elf_temporary = CANDIDATE_ELF.with_suffix(CANDIDATE_ELF.suffix + ".incomplete")
    manifest_temporary = MANIFEST.with_suffix(MANIFEST.suffix + ".incomplete")
    audit_temporary = AUDIT.with_suffix(AUDIT.suffix + ".incomplete")
    destinations = (CANDIDATE_ISO, CANDIDATE_ELF, MANIFEST, AUDIT,
                    temporary, elf_temporary, manifest_temporary, audit_temporary)
    existing = next((path for path in destinations if path.exists()), None)
    if existing is not None:
        raise FileExistsError(f"Refusing to overwrite prior 15f artifact: {existing}")
    prepared = preflight()
    copy = subprocess.run(["cp", "-c", str(PREVIOUS_ISO), str(temporary)], capture_output=True)
    if copy.returncode:
        shutil.copyfile(PREVIOUS_ISO, temporary)
    with temporary.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
        entry = find_record(index_iso(image)[1], "SLPM_665.11")
        offset = entry.extent * SECTOR_BYTES
        image[offset:offset + len(prepared.after)] = prepared.after
        _, _, group4, art_offset = _installed_regions(image)
        if group4.size != len(prepared.after_art):
            raise ValueError("15f GP004 art length differs from ISO record")
        image[art_offset:art_offset + len(prepared.after_art)] = prepared.after_art
        patch_directory_record(image, entry.record_offset, size=len(prepared.after))
        image.flush()
    proof = audit(PREVIOUS_ISO, temporary, prepared)
    release = dict(
        release="r67.15f",
        status="DIAGNOSTIC_NOT_GAMEPLAY_APPROVED",
        source_iso_sha256=PREVIOUS_SHA,
        source_elf_sha256=SOURCE_ELF_SHA,
        candidate_sha256=proof["candidate_iso_sha256"],
        output_iso=str(CANDIDATE_ISO),
        output_elf=str(CANDIDATE_ELF),
        patch=prepared.patch_report,
        art=prepared.art_report,
        runtime_save_compatibility_verified=False,
        gameplay_approved=False,
    )
    with elf_temporary.open("xb") as stream:
        stream.write(prepared.after)
    with manifest_temporary.open("x") as stream:
        json.dump(release, stream, indent=2, sort_keys=True, default=str)
        stream.write("\n")
    with audit_temporary.open("x") as stream:
        json.dump(proof, stream, indent=2, sort_keys=True)
        stream.write("\n")
    elf_temporary.rename(CANDIDATE_ELF)
    manifest_temporary.rename(MANIFEST)
    audit_temporary.rename(AUDIT)
    temporary.rename(CANDIDATE_ISO)
    print(json.dumps(proof, sort_keys=True))
    return proof


if __name__ == "__main__":
    build()
