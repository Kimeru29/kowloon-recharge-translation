"""Deterministic integration and exact ISO audit for the future r67.15g image.

The builder is intentionally not invoked as part of component implementation.
It starts only from the immutable gameplay-approved r67.15f disc, composes the
four 15g transformations in order, and audits every changed byte on the disc.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import inspect
import json
import mmap
import struct
import subprocess
from pathlib import Path
from typing import Any, Mapping

from tools.iso9660_patch import find_record, index_iso, patch_directory_record
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST, verify_approved
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST, verify_ui
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_14y_release import check_growth, verify_save_identity
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_RESERVE
from tools.r67_history_layout_lock import read_lock, verify_bytes
from tools.r67_15f_approved_lock import (
    ISO as APPROVED_ISO,
    load_manifest as load_15f_lock,
    verify_approved_iso,
    verify_source_owners,
)
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_lion_statue_ui import item_pointer
from tools.tmx import find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ISO = APPROVED_ISO
SOURCE_ISO_SHA256 = "e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0"
SOURCE_ELF = ROOT / "local/r67-15f-item-panel-layout.elf"
SOURCE_ELF_SHA256 = "418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1"
CORPUS = Path("/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
OUTPUT_ISO = ROOT / "local/r67-candidates/67.15g-prologue-details-help.iso"
OUTPUT_ELF = ROOT / "local/r67-15g-prologue-details-help.elf"
OUTPUT_MANIFEST = ROOT / "local/r67-15g-release.json"
OUTPUT_AUDIT = ROOT / "local/r67-15g-whole-iso-audit.json"
OUTPUT_STARTUP_RAW = ROOT / "local/r67-15g-startup-raw.json"
OUTPUT_STARTUP_SCOPED = ROOT / "local/r67-15g-startup.json"
OUTPUT_HISTORY = ROOT / "local/r67-15g-history.json"
OUTPUT_SAVE = ROOT / "local/r67-15g-save-static.json"
INCOMPLETE_ISO = OUTPUT_ISO.with_suffix(".incomplete")
PARTIAL_OUTPUT_ISO = ROOT / "local/r67-candidates/67.15g-partial-diagnostic.iso"
PARTIAL_OUTPUT_ELF = ROOT / "local/r67-15g-partial-diagnostic.elf"
PARTIAL_OUTPUT_MANIFEST = ROOT / "local/r67-15g-partial-diagnostic.json"
PARTIAL_OUTPUT_AUDIT = ROOT / "local/r67-15g-partial-diagnostic-whole-iso-audit.json"
PARTIAL_OUTPUT_STARTUP_RAW = ROOT / "local/r67-15g-partial-diagnostic-startup-raw.json"
PARTIAL_OUTPUT_STARTUP_SCOPED = ROOT / "local/r67-15g-partial-diagnostic-startup.json"
PARTIAL_OUTPUT_HISTORY = ROOT / "local/r67-15g-partial-diagnostic-history.json"
PARTIAL_OUTPUT_SAVE = ROOT / "local/r67-15g-partial-diagnostic-save-static.json"
PHYSICAL_BYTES = 2_095_382_528
SECTOR_BYTES = 2048
EXECUTABLE_NAME = "SLPM_665.11"
DATA_CVM_NAME = "DATA.CVM"
HELP_GRAPHICS = ROOT.parent / "startup-flow-v10/local/startup-graphics"
COMPONENT_ORDER = ("tablet", "help", "prologue", "details")
MAX_SINGLE_OWNER_RANGE = 0x10000
MAX_TOTAL_OWNER_BYTES = 0x10000
APPROVED_LION_WORDS = (0x14B58, 0xDB44)
NATIVE_NAME_POINTER_TABLE = (0x3912B4, 500 * 4)
APPROVED_TABLET_RECORD = 0x590FB0
TABLET_LAYOUT_OWNERS = (0x590FB8, 0x590FBC, 0x590FC0)


@dataclass(frozen=True)
class PreparedELF:
    source: bytes
    candidate: bytes
    components: tuple[dict[str, Any], ...]
    owners: dict[str, tuple[tuple[int, int], ...]]
    changed_existing: dict[int, tuple[int, str]]
    source_cvm_sha256: str | None = None
    preservation: dict[str, Any] | None = None
    static_locks: dict[str, Any] | None = None


@dataclass(frozen=True)
class ApprovedInputs:
    source_iso: Path
    source_elf: bytes
    executable_extent: int
    executable_record_offset: int
    executable_offset: int
    executable_size: int
    cvm_extent: int
    cvm_record_offset: int
    cvm_offset: int
    cvm_size: int
    cvm_sha256: str


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_view(view: memoryview | mmap.mmap) -> str:
    digest = hashlib.sha256()
    digest.update(view)
    return digest.hexdigest()


def _component_range_format(name: str) -> str:
    # These are explicit per-component adapters, not inferred from tuple shape.
    formats = {
        "tablet": "half_open",
        "help": "half_open",
        "prologue": "half_open",
        "details": "half_open",
    }
    try:
        return formats[name]
    except KeyError as exc:
        raise ValueError(f"unknown component range format: {name}") from exc


def normalize_component_ranges(name: str, declarations: Any, source_size: int) -> dict[str, tuple[tuple[int, int], ...]]:
    """Normalize each known component contract to named half-open ranges.

    Mapping declarations preserve their owner names. Sequence declarations
    receive stable component/index names. PT_LOAD.p_filesz is accepted only as
    its exact four-byte field and is audited separately from native owners.
    """
    if not isinstance(name, str) or not name:
        raise ValueError("component name is required")
    if isinstance(declarations, Mapping):
        raw_items = list(declarations.items())
    elif isinstance(declarations, (tuple, list)):
        raw_items = [(f"{index:03d}", item) for index, item in enumerate(declarations)]
    else:
        raise ValueError("component ranges must be a dict or tuple/list")
    normalized: dict[str, tuple[tuple[int, int], ...]] = {}
    claimed: dict[int, str] = {}
    total = 0
    range_format = _component_range_format(name)
    for raw_owner, raw_ranges in raw_items:
        owner = str(raw_owner)
        if isinstance(raw_ranges, (tuple, list)) and len(raw_ranges) == 2 and all(
            isinstance(value, int) and not isinstance(value, bool) for value in raw_ranges
        ):
            ranges = [raw_ranges]
        elif isinstance(raw_ranges, (tuple, list)):
            ranges = list(raw_ranges)
        else:
            raise ValueError(f"invalid range format for {name}:{owner}")
        spans: list[tuple[int, int]] = []
        for pair in ranges:
            if (not isinstance(pair, (tuple, list)) or len(pair) != 2
                    or not all(isinstance(value, int) and not isinstance(value, bool) for value in pair)):
                raise ValueError(f"invalid range format for {name}:{owner}")
            start, second = pair
            end = second if range_format == "half_open" else start + second
            if start < 0 or end <= start or end > source_size:
                raise ValueError(f"invalid range bounds for {name}:{owner}")
            if start < 0x68 and end > 0x64:
                if (start, end) != (0x64, 0x68):
                    raise ValueError(f"range crosses ELF segment-length metadata for {name}:{owner}")
                continue
            length = end - start
            if length > MAX_SINGLE_OWNER_RANGE:
                raise ValueError(f"broad native owner range for {name}:{owner}")
            total += length
            if total > MAX_TOTAL_OWNER_BYTES:
                raise ValueError(f"broad aggregate native owner ranges for {name}")
            for offset in range(start, end):
                prior = claimed.get(offset)
                if prior is not None:
                    raise ValueError(f"overlapping owner ranges for {name}:{prior} and {owner}")
                claimed[offset] = owner
            spans.append((start, end))
        if spans:
            normalized[f"{name}:{owner}"] = tuple(spans)
    return normalized


def _flatten_ranges(owners: Mapping[str, tuple[tuple[int, int], ...]]) -> dict[int, str]:
    byte_owner: dict[int, str] = {}
    for owner, spans in owners.items():
        for start, end in spans:
            for offset in range(start, end):
                prior = byte_owner.get(offset)
                if prior is not None:
                    raise ValueError(f"overlapping component owner ranges at {offset:#x}")
                byte_owner[offset] = owner
    return byte_owner


def _elf_segment(source: bytes) -> tuple[int, int, int]:
    if len(source) < 0x68 or source[:4] != b"\x7fELF":
        raise ValueError("malformed ELF input")
    kind, file_offset, va, _pa, file_size, memory_size, flags, align = struct.unpack_from(
        "<8I", source, 0x54
    )
    if (kind, file_offset, file_offset + file_size, flags, align) != (
        1, ELF_SEGMENT_FO, len(source), 7, 16
    ):
        raise ValueError("translation PT_LOAD geometry changed")
    return file_offset, memory_size, va


def _reported_extent(report: dict[str, Any], old_size: int, new_size: int) -> None:
    extent = report.get("appended_extent")
    if extent is None:
        return
    if isinstance(extent, Mapping):
        start = extent.get("start")
        end = extent.get("end_exclusive", extent.get("end"))
    elif isinstance(extent, (tuple, list)) and len(extent) == 2:
        start, end = extent
    else:
        raise ValueError("malformed component appended_extent report")
    def number(value):
        return int(value, 0) if isinstance(value, str) else value
    if number(start) != old_size or number(end) != new_size:
        raise ValueError("component appended_extent report disagrees with output bytes")


def audit_component(name: str, before: bytes, after: bytes, report: dict[str, Any],
                    owners: Mapping[str, tuple[tuple[int, int], ...]]) -> dict[str, Any]:
    """Validate one stage's exact prefix delta, append, and PT_LOAD metadata."""
    if not isinstance(after, (bytes, bytearray)) or not isinstance(report, dict):
        raise ValueError(f"{name} apply must return (bytes, report dict)")
    after = bytes(after)
    file_offset, memory_size, _va = _elf_segment(before)
    if len(after) < len(before):
        raise ValueError(f"{name} transformation shrank the ELF")
    if len(after) - file_offset > memory_size:
        raise ValueError(f"{name} append exceeds the reserved PT_LOAD memory")
    after_file_size = struct.unpack_from("<I", after, 0x64)[0]
    if after_file_size != len(after) - file_offset:
        raise ValueError(f"{name} PT_LOAD file size does not match the appended ELF")
    _reported_extent(report, len(before), len(after))
    reported_changes = report.get("modified_existing_offsets")
    if reported_changes is None:
        reported_changes = report.get("existing_elf_changed_offsets")
    if reported_changes is not None:
        normalized_reported = {hex(int(value, 0) if isinstance(value, str) else value)
                               for value in reported_changes}
        # The segment-size word is independently audited, but it remains part
        # of the component's existing-byte delta report when that report lists it.
        actual_reported = {
            hex(offset) for offset in range(len(before))
            if before[offset] != after[offset]
        }
        if normalized_reported != actual_reported:
            raise ValueError(f"{name} modified_existing_offsets report disagrees with output")
    byte_owner = _flatten_ranges(owners)
    changes: dict[int, tuple[int, str]] = {}
    for offset, (old, new) in enumerate(zip(before, after[:len(before)], strict=True)):
        if old == new:
            continue
        if 0x64 <= offset < 0x68:
            changes[offset] = (new, "elf_segment_filesz")
            continue
        owner = byte_owner.get(offset)
        if owner is None:
            raise ValueError(f"unowned {name} ELF byte {offset:#x}")
        changes[offset] = (new, owner)
    for offset in range(len(before), len(after)):
        changes[offset] = (after[offset], f"{name}:appended_payload")
    failures = report.get("mapping_failures", [])
    if failures:
        raise ValueError(f"{name} reports unresolved mapping failures: {failures}")
    if name == "prologue" and report.get("status") != "DIAGNOSTIC_STATIC_PROLOGUE_TEXT_ONLY":
        raise ValueError("Prologue component report is not the expected static transformation")
    return {
        "component": name,
        "changed_existing_offsets": [hex(offset) for offset in sorted(changes) if offset < len(before)],
        "appended_extent": [len(before), len(after)],
        "appended_bytes": len(after) - len(before),
        "report": report,
        "_changes": changes,
    }


def check_elf_growth(image: Any, executable: Any, records: Any,
                     previous_size: int, proposed_size: int) -> None:
    """Use the 14y ISO-space guard and verify same-sector growth bytes are zero."""
    if proposed_size < previous_size or previous_size != executable.size:
        raise ValueError("invalid executable growth sizes")
    check_growth(image, executable, records, proposed_size)
    start = executable.extent * SECTOR_BYTES
    if proposed_size > previous_size and any(image[start + previous_size:start + proposed_size]):
        raise ValueError("ELF growth would overwrite nonzero ISO slack")


def source_executable_capacity(proposed_size: int | None = None) -> int:
    """Index the pinned source through a live read-only mapping and audit growth."""
    with SOURCE_ISO.open("rb") as stream, mmap.mmap(
        stream.fileno(), 0, access=mmap.ACCESS_READ
    ) as image:
        _, records = index_iso(image)
        executable = find_record(records, EXECUTABLE_NAME)
        if proposed_size is not None and proposed_size > executable.size:
            check_elf_growth(image, executable, records, executable.size, proposed_size)
        return executable.size


def _get_component_modules() -> dict[str, Any]:
    from tools import r67_15g_help_layout, r67_15g_prologue, r67_15g_tablet_layout
    try:
        from tools import r67_15g_item_details
    except ImportError as exc:
        raise ValueError("r67.15g Details component is not ready") from exc
    return {
        "tablet": r67_15g_tablet_layout,
        "help": r67_15g_help_layout,
        "prologue": r67_15g_prologue,
        "details": r67_15g_item_details,
    }


def _apply_component(name: str, module: Any, source: bytes,
                     corpus_path: Path, corpus_bytes: bytes):
    """Adapt the explicitly documented corpus argument for each component."""
    if name in ("tablet", "prologue"):
        return module.apply(source, corpus_path)
    if name == "help":
        return module.apply(source, corpus_bytes)
    if name == "details":
        parameters = inspect.signature(module.apply).parameters
        corpus = parameters.get("corpus_path")
        if corpus is None or corpus.kind not in (
            inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD
        ):
            raise ValueError("Details apply must expose corpus_path as a named parameter")
        return module.apply(source, corpus_path=corpus_path)
    raise ValueError(f"Unknown 15g component {name}")


def compose_components(source: bytes, official_corpus: Path, official_english_bytes: bytes,
                       components: Mapping[str, Any] | None = None) -> tuple[bytes, dict[str, Any]]:
    """Apply tablet, Help, prologue, then Details with exact owner auditing."""
    modules = dict(_get_component_modules() if components is None else components)
    if tuple(name for name in COMPONENT_ORDER if name in modules) != COMPONENT_ORDER:
        raise ValueError("All four 15g components are required")
    if set(modules) != set(COMPONENT_ORDER):
        raise ValueError("Unexpected 15g component name")
    if hashlib.sha256(official_english_bytes).hexdigest() != CORPUS_SHA256:
        raise ValueError("Official English corpus identity mismatch")

    base_size = len(source)
    normalized: dict[str, tuple[tuple[int, int], ...]] = {}
    for name in COMPONENT_ORDER:
        module = modules[name]
        apply = getattr(module, "apply", None)
        declarations = getattr(module, "PERMITTED_EXISTING_RANGES", None)
        if not callable(apply) or declarations is None:
            raise ValueError(f"{name} component lacks apply or PERMITTED_EXISTING_RANGES")
        normalized.update(normalize_component_ranges(name, declarations, base_size))
    _flatten_ranges(normalized)

    current = source
    reports: list[dict[str, Any]] = []
    aggregate_changes: dict[int, tuple[int, str]] = {}
    stages = []
    for name in COMPONENT_ORDER:
        module = modules[name]
        after, report = _apply_component(name, module, current, official_corpus, official_english_bytes)
        stage_ranges = {key: value for key, value in normalized.items() if key.startswith(f"{name}:")}
        stage = audit_component(name, current, after, report, stage_ranges)
        for offset, change in stage["_changes"].items():
            previous = aggregate_changes.get(offset)
            if previous is not None and not (0x64 <= offset < 0x68):
                raise ValueError(f"component stages disagree on ELF byte {offset:#x}")
            aggregate_changes[offset] = change
        reports.append({key: value for key, value in stage.items() if key != "_changes"})
        stages.append((name, current, after, report))
        current = after

    return current, {
        "component_order": list(COMPONENT_ORDER),
        "components": reports,
        "normalized_existing_owners": {
            name: [[hex(start), hex(end)] for start, end in spans]
            for name, spans in normalized.items()
        },
        "modified_existing_offsets": [hex(offset) for offset in sorted(aggregate_changes) if offset < base_size],
        "appended_extents": [report["appended_extent"] for report in reports],
        "mapping_failures": [],
        "gameplay_approved": False,
        "_changed_bytes": aggregate_changes,
        "_stages": stages,
    }


def _read_approved_inputs(path: Path = SOURCE_ISO) -> ApprovedInputs:
    if path != SOURCE_ISO:
        raise ValueError("Source ISO is not the approved gameplay-tested r67.15f image")
    verify_source_owners()
    source_lock = verify_approved_iso(path)
    if source_lock.get("iso") != SOURCE_ISO_SHA256:
        raise ValueError("Approved source ISO lock does not match r67.15f")
    installed_manifest = load_15f_lock()
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if len(image) != PHYSICAL_BYTES:
            raise ValueError("Approved r67.15f ISO physical size changed")
        _, records = index_iso(image)
        executable = find_record(records, EXECUTABLE_NAME)
        cvm = find_record(records, DATA_CVM_NAME)
        exe_offset = executable.extent * SECTOR_BYTES
        cvm_offset = cvm.extent * SECTOR_BYTES
        installed_elf = bytes(image[exe_offset:exe_offset + executable.size])
        if sha(installed_elf) != SOURCE_ELF_SHA256:
            raise ValueError("Installed r67.15f executable hash mismatch")
        if installed_elf != SOURCE_ELF.read_bytes():
            raise ValueError("Staged r67.15f ELF differs from installed executable")
        if len(image[0:]) != installed_manifest["iso_size_bytes"]:
            raise ValueError("Approved source ISO length differs from its lock")
        return ApprovedInputs(
            path, installed_elf, executable.extent, executable.record_offset,
            exe_offset, executable.size, cvm.extent, cvm.record_offset,
            cvm_offset, cvm.size, _sha_view(memoryview(image)[cvm_offset:cvm_offset + cvm.size]),
        )


def _verify_15f_preservation(source: bytes, candidate: bytes, atlas: bytes) -> dict[str, Any]:
    lock = load_15f_lock()
    for raw_offset, expected in lock["native_hook_words"].items():
        offset = int(raw_offset, 16)
        if source[offset:offset + 4] != bytes.fromhex(expected):
            raise ValueError(f"Pinned r67.15f native hook preimage drift at {raw_offset}")
        if candidate[offset:offset + 4] != source[offset:offset + 4]:
            raise ValueError(f"Accepted r67.15f native hook changed at {raw_offset}")
    table_offset, table_size = NATIVE_NAME_POINTER_TABLE
    if candidate[table_offset:table_offset + table_size] != source[table_offset:table_offset + table_size]:
        raise ValueError("Accepted 500-slot native item-name pointer table changed")
    from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA
    for item_id, _source_offset, _japanese, _english, _record in DUNGEON_ITEM_NAME_DATA:
        pointer_offset = table_offset + item_id * 4
        pointer = struct.unpack_from("<I", source, pointer_offset)[0]
        if struct.unpack_from("<I", candidate, pointer_offset)[0] != pointer:
            raise ValueError(f"Accepted item catalogue pointer changed for id {item_id}")
        if read_string(candidate, pointer) != read_string(source, pointer):
            raise ValueError(f"Accepted item catalogue string changed for id {item_id}")
    if item_pointer(candidate) != item_pointer(source):
        raise ValueError("Accepted Lion Statue catalog name changed")
    if sha(atlas) != lock["installed_group4_sha256"]:
        raise ValueError("Accepted r67.15f Group-4 art changed")
    for name, expected in lock["protected_tmx_sha256"].items():
        entry = find_tmx_entry(atlas, name)
        fragment = atlas[entry.base_offset:entry.base_offset + entry.chunk_size]
        if sha(fragment) != expected:
            raise ValueError(f"Accepted r67.15f art changed: {name}")
    return {
        "source_15f_approved_lock_verified": True,
        "native_hook_words_preserved": len(lock["native_hook_words"]),
        "item_name_pointer_slots_preserved": table_size // 4,
        "valid_item_catalogue_entries_preserved": len(DUNGEON_ITEM_NAME_DATA),
        "lion_statue_name_preserved": True,
        "group4_art_sha256": sha(atlas),
        "protected_art_chunks_preserved": len(lock["protected_tmx_sha256"]),
        "approved_15f_whole_elf_hash_claimed_for_candidate": False,
    }


def _restore_14t_owners_for_verification(candidate: bytes) -> bytes:
    manifest = json.loads(T_MANIFEST.read_text(encoding="utf-8"))
    from tools.r67_lion_statue_ui import ELF_BIAS
    restored = bytearray(candidate)
    for raw_va, word in manifest["item_label_native_callsites"].items():
        struct.pack_into("<I", restored, int(raw_va, 16) - ELF_BIAS, int(word, 16))
    tablet = manifest["accepted_tablet_records"][hex(APPROVED_TABLET_RECORD)]
    expected = tuple(int(value, 16) for value in tablet["pointer_words"])
    if tuple(TABLET_LAYOUT_OWNERS) != tuple(APPROVED_TABLET_RECORD + index * 4 for index in (2, 3, 4)):
        raise ValueError("Tablet lock exception does not match the exact western row pointers")
    for index in (2, 3, 4):
        struct.pack_into("<I", restored, APPROVED_TABLET_RECORD + index * 4, expected[index])
    return bytes(restored)


def _verify_static_locks(source: bytes, candidate: bytes) -> dict[str, Any]:
    restored = _restore_14t_owners_for_verification(candidate)
    q = verify_approved(restored, json.loads(Q_MANIFEST.read_text(encoding="utf-8")))
    t = verify_ui(restored, json.loads(T_MANIFEST.read_text(encoding="utf-8")))
    history = verify_bytes(candidate, read_lock())
    save = verify_save_identity(candidate)
    return {
        "q_lock": q,
        "t_lock": t,
        "t_lock_in_memory_reconstruction_only": [
            "two original Lion callsite words changed by the accepted 15f chain",
            "three western tablet row pointer words changed by r67.15g",
        ],
        "history_lock_regions": history,
        "save_identity": save,
        "runtime_save_compatibility_verified": False,
    }


def prepare_elf(source: bytes, official_corpus: Path = CORPUS,
                components: Mapping[str, Any] | None = None) -> PreparedELF:
    inputs = _read_approved_inputs()
    if source != inputs.source_elf:
        raise ValueError("Provided ELF differs from the installed approved 15f executable")
    if sha(source) != SOURCE_ELF_SHA256:
        raise ValueError("Input ELF is not the approved r67.15f extracted executable")
    if not official_corpus.is_file() or sha_file(official_corpus) != CORPUS_SHA256:
        raise ValueError("Official English.bytes corpus missing or changed")
    official_bytes = official_corpus.read_bytes()
    output, report = compose_components(source, official_corpus, official_bytes, components)
    require_release_ready(report)
    preservation = _verify_15f_preservation(source, output, _source_group4_bytes())
    locks = _verify_static_locks(source, output)
    report["r67_15f_preservation"] = preservation
    report["static_locks"] = locks
    changes = report.pop("_changed_bytes")
    report.pop("_stages")
    report["r67_15f_preservation"] = preservation
    report["static_locks"] = locks
    return PreparedELF(source, output, tuple(report["components"]),
                       {key: tuple((int(a, 16), int(b, 16)) for a, b in spans)
                        for key, spans in report["normalized_existing_owners"].items()},
                       changes, inputs.cvm_sha256, preservation, locks)


def _source_group4_bytes() -> bytes:
    """Read the locked item UI atlas from the approved source image."""
    with SOURCE_ISO.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        cvm = find_record(outer, DATA_CVM_NAME)
        cvm_base = cvm.extent * SECTOR_BYTES + 0x1800
        _, nested = index_iso(image, cvm_base)
        group = find_record(nested, "BLBRD/B_GP004.BIN")
        start = cvm_base + group.extent * SECTOR_BYTES
        return bytes(image[start:start + group.size])


def compare_expected_bytes(baseline: bytes | mmap.mmap | memoryview,
                           candidate: bytes | mmap.mmap | memoryview,
                           expected: Mapping[int, tuple[int, str]],
                           block_size: int = 8 * 1024 * 1024) -> dict[str, int]:
    """Compare every byte; reject unexplained, wrong-value, or missing deltas."""
    if len(baseline) != len(candidate):
        raise ValueError("finished ISO physical length differs")
    if block_size <= 0 or any(offset < 0 or offset >= len(candidate) for offset in expected):
        raise ValueError("invalid expected finished-ISO byte map")
    observed: Counter[str] = Counter()
    for block in range(0, len(baseline), block_size):
        left = baseline[block:block + block_size]
        right = candidate[block:block + block_size]
        if left == right:
            continue
        for index, (old, new) in enumerate(zip(left, right, strict=True)):
            if old == new:
                continue
            offset = block + index
            wanted = expected.get(offset)
            if wanted is None or wanted[0] != new:
                raise ValueError(f"unexplained finished-ISO byte {offset:#x}")
            observed[wanted[1]] += 1
    if sum(observed.values()) != len(expected):
        missing = next(offset for offset in expected if baseline[offset] == candidate[offset])
        raise ValueError(f"expected finished-ISO change absent at {missing:#x}")
    return dict(sorted(observed.items()))


def _installed_records(image):
    _, outer = index_iso(image)
    executable = find_record(outer, EXECUTABLE_NAME)
    cvm = find_record(outer, DATA_CVM_NAME)
    cvm_base = cvm.extent * SECTOR_BYTES + 0x1800
    _, nested = index_iso(image, cvm_base)
    group4 = find_record(nested, "BLBRD/B_GP004.BIN")
    return (executable, executable.extent * SECTOR_BYTES, cvm, cvm.extent * SECTOR_BYTES,
            cvm_base, group4, cvm_base + group4.extent * SECTOR_BYTES)


def audit_finished_iso(previous: Path, candidate: Path, prepared: PreparedELF,
                       source_cvm_sha256: str) -> dict[str, Any]:
    if previous != SOURCE_ISO or sha_file(previous) != SOURCE_ISO_SHA256:
        raise ValueError("Audit baseline is not the approved r67.15f ISO")
    with previous.open("rb") as left_stream, candidate.open("rb") as right_stream:
        with mmap.mmap(left_stream.fileno(), 0, access=mmap.ACCESS_READ) as left, \
                mmap.mmap(right_stream.fileno(), 0, access=mmap.ACCESS_READ) as right:
            if len(left) != PHYSICAL_BYTES or len(right) != PHYSICAL_BYTES:
                raise ValueError("finished ISO physical length differs from approved baseline")
            old_exe, old_exe_offset, old_cvm, old_cvm_offset, cvm_base, old_group4, group4_offset = _installed_records(left)
            new_exe, new_exe_offset, new_cvm, new_cvm_offset, new_cvm_base, new_group4, new_group4_offset = _installed_records(right)
            if new_exe.size < old_exe.size:
                raise ValueError("candidate executable shrank below approved 15f size")
            if (old_exe_offset != new_exe_offset or old_exe.extent != new_exe.extent
                    or old_exe.record_offset != new_exe.record_offset
                    or new_exe.size != len(prepared.candidate)
                    or old_cvm != new_cvm or old_cvm_offset != new_cvm_offset
                    or cvm_base != new_cvm_base or old_group4 != new_group4
                    or group4_offset != new_group4_offset):
                raise ValueError("unexpected ISO executable/CVM/art record metadata change")
            if left[old_exe_offset:old_exe_offset + len(prepared.source)] != prepared.source:
                raise ValueError("approved 15f installed ELF differs from prepared source")
            if right[new_exe_offset:new_exe_offset + len(prepared.candidate)] != prepared.candidate:
                raise ValueError("finished ISO executable differs from deterministic component output")
            if _sha_view(memoryview(right)[new_cvm_offset:new_cvm_offset + new_cvm.size]) != source_cvm_sha256:
                raise ValueError("DATA.CVM changed; art, ADV, and other resources must remain byte-identical")
            if any(left[old_exe_offset + old_exe.size:new_exe_offset + new_exe.size]):
                raise ValueError("ELF growth overlaps nonzero ISO slack")
            if new_exe.size > old_exe.size:
                _, old_records = index_iso(left)
                check_elf_growth(left, old_exe, old_records, old_exe.size, new_exe.size)

            expected: dict[int, tuple[int, str]] = {}
            for offset, (value, owner) in prepared.changed_existing.items():
                absolute = old_exe_offset + offset
                if left[absolute] != value:
                    expected[absolute] = (value, f"elf/{owner}")
            for offset in range(len(prepared.source), len(prepared.candidate)):
                value = prepared.candidate[offset]
                absolute = old_exe_offset + offset
                if left[absolute] != value:
                    expected[absolute] = (value, "elf/appended_component_payload")
            for index, value in enumerate(struct.pack("<I", new_exe.size) + struct.pack(">I", new_exe.size)):
                absolute = old_exe.record_offset + 10 + index
                if left[absolute] != value:
                    expected[absolute] = (value, "iso9660_executable_size_both_endians")
            counts = compare_expected_bytes(left, right, expected)
            return {
                "status": "PASS_EXACT_15F_BASELINE_ZERO_UNEXPLAINED",
                "baseline_15f_iso_sha256": SOURCE_ISO_SHA256,
                "candidate_iso_sha256": sha_file(candidate),
                "complete_disc_bytes_compared": len(left),
                "modified_bytes": sum(counts.values()),
                "byte_owner_summary": counts,
                "unexplained_bytes": 0,
                "data_cvm_byte_identical": True,
                "all_art_and_adv_resources_unchanged": True,
                "gameplay_approved": False,
            }


def _verify_memory_card_8_exception(raw_startup: dict[str, Any], source: bytes, candidate: bytes) -> dict[str, Any]:
    failed = [check for check in raw_startup.get("checks", []) if not check.get("ok")]
    if (raw_startup.get("checks_passed") != 154 or raw_startup.get("checks_total") != 155
            or len(failed) != 1 or failed[0].get("name") != "memory_card_8"):
        raise ValueError("Raw startup result must be 154/155 with only memory_card_8 failing")
    pointer_offset = 0x407440 + 8 * 4
    source_pointer = struct.unpack_from("<I", source, pointer_offset)[0]
    if struct.unpack_from("<I", candidate, pointer_offset)[0] != source_pointer:
        raise ValueError("The existing bounded memory_card_8 text owner changed")
    text = read_string(candidate, source_pointer).decode("cp932")
    lines = [line for line in text.split("＠改行")]
    normalized = [line.translate(str.maketrans({"　": " ", **{chr(0xFF01 + i): chr(0x21 + i) for i in range(94)}})) for line in lines]
    if len(lines) != 5 or any(len(line) > 20 or not line.isascii() for line in normalized):
        raise ValueError("Explicit memory_card_8 exception is no longer bounded to five rows/20 cells")
    return {
        "name": "memory_card_8",
        "legacy_detail": failed[0].get("detail"),
        "reason": "approved 15f bounded English wording is not in the legacy Japanese expectation",
        "row_count": len(lines),
        "maximum_cells": max(map(len, normalized)),
        "source_owner_unchanged": True,
    }


def _static_reports(candidate_elf: bytes, raw_startup: dict[str, Any], source_elf: bytes) -> dict[str, Any]:
    exception = _verify_memory_card_8_exception(raw_startup, source_elf, candidate_elf)
    scoped = dict(raw_startup)
    scoped["checks"] = [dict(item) for item in raw_startup["checks"]]
    for item in scoped["checks"]:
        if item["name"] == "memory_card_8" and not item["ok"]:
            item.update(ok=True, detail="PASS exact preserved bounded 15f wording; explicit legacy exception")
    scoped.update(checks_passed=155, raw_checks_passed=154,
                  explicit_legacy_wording_exceptions=[exception],
                  q_t_lock_exceptions=["western tablet pointers plus 14t Lion callsites reconstructed only in memory"])
    return {
        "startup_raw": raw_startup,
        "startup_scoped": scoped,
        "history": {"verified_regions": verify_bytes(candidate_elf, read_lock()), "runtime_verified": False},
        "save": {**verify_save_identity(candidate_elf),
                 "status": "STATIC_ONLY_NO_GOLDEN_CHECKPOINT",
                 "original_cards_and_savestates_not_modified": True,
                 "cross_release_runtime_test_performed": False},
    }


def _copy_on_write(source: Path, destination: Path) -> None:
    result = subprocess.run(["cp", "-c", str(source), str(destination)], capture_output=True)
    if result.returncode:
        raise RuntimeError(f"APFS clone failed ({result.returncode}): {result.stderr.decode(errors='replace')}")


def validate_route_evidence(evidence: Mapping[str, Any] | Path) -> dict[str, Any]:
    """Validate the read-only route-audit report before any ISO output is made."""
    if isinstance(evidence, Path):
        if not evidence.is_file():
            raise ValueError("Parent route/provenance report is missing")
        parsed = json.loads(evidence.read_text(encoding="utf-8"))
    else:
        parsed = dict(evidence)
    if not isinstance(parsed, dict):
        raise ValueError("Parent route/provenance report must be a JSON object")
    if parsed.get("audit_kind") != "finished_iso_exact_payload_audit" or parsed.get("read_only") is not True:
        raise ValueError("Parent route evidence is not the expected read-only finished-image audit")
    assets = parsed.get("assets")
    choices = parsed.get("choice_assets")
    required_assets = {
        "ADV/DG/DG00_00.MTX": 195,
        "ADV/DG/DG00_01.MTX": 34,
        "ADV/MS/MS00_02.MTX": 593,
    }
    if not isinstance(assets, Mapping) or not isinstance(choices, Mapping):
        raise ValueError("Parent route report lacks script provenance inventories")
    for name, entries in required_assets.items():
        item = assets.get(name, {})
        if (item.get("verification") != "official_exact"
                or item.get("official_import_entries") != entries
                or not item.get("official_ps4_source_sha256")
                or not item.get("official_map_sha256")
                or not item.get("official_regenerated_sha256")):
            raise ValueError(f"Official source/map/regeneration evidence is incomplete for {name}")
    ms00 = choices.get("ADV/MS/MS00_02.KSF", {})
    dg00 = choices.get("ADV/DG/DG00_00.KSF", {})
    if (ms00.get("official_choice_entries") != 10
            or ms00.get("counts", {}).get("fit") != 10
            or ms00.get("counts", {}).get("approved_compaction") != 0
            or ms00.get("counts", {}).get("unresolved") != 0
            or ms00.get("finished_sha256") != ms00.get("regenerated_sha256")):
        raise ValueError("MS00_02.KSF ten-choice exact-import evidence is incomplete")
    if (dg00.get("official_choice_entries") != 5
            or dg00.get("counts", {}).get("fit") != 3
            or dg00.get("counts", {}).get("approved_compaction") != 2
            or dg00.get("counts", {}).get("unresolved") != 0
            or not dg00.get("approved_compaction_offsets")):
        raise ValueError("DG00_00.KSF exact-row/historical-compaction evidence is incomplete")
    if parsed.get("unresolved_choice_entries") != []:
        raise ValueError("Parent route report contains unresolved choice mappings")
    if not parsed.get("endpoint_capture_checklist"):
        raise ValueError("Parent route report is missing its runtime endpoint checklist")
    parsed["static_payload_provenance_passed"] = True
    parsed["runtime_route_captures_complete"] = False
    return parsed


def require_release_ready(component_report: Mapping[str, Any]) -> None:
    """Reject a diagnostic partial Details pass before any candidate file exists."""
    components = component_report.get("components")
    if not isinstance(components, list):
        raise ValueError("Component report lacks its ordered component inventory")
    details = [item.get("report", {}) for item in components
               if isinstance(item, Mapping) and item.get("component") == "details"]
    if len(details) != 1:
        raise ValueError("Component report must contain exactly one Details result")
    report = details[0]
    if (report.get("status") != "PATCHED_ALL_OFFICIAL_DESCRIPTIONS"
            or report.get("unresolved_records") != 0):
        raise ValueError("Details catalogue is incomplete; release build is not eligible")


def release_scope(component_report: Mapping[str, Any], *,
                  allow_partial_diagnostic: bool = False) -> dict[str, Any]:
    """Return manifest scope metadata, narrowly allowing preserved native gaps."""
    if type(allow_partial_diagnostic) is not bool:
        raise ValueError("allow_partial_diagnostic must be a bool")
    try:
        require_release_ready(component_report)
    except ValueError as exc:
        if not allow_partial_diagnostic:
            raise
        if str(exc) != "Details catalogue is incomplete; release build is not eligible":
            raise
        components = component_report.get("components")
        details = [item.get("report", {}) for item in components
                   if isinstance(item, Mapping) and item.get("component") == "details"]
        if len(details) != 1:
            raise ValueError("Partial diagnostic requires exactly one Details report")
        report = details[0]
        if (report.get("status") != "PARTIAL_OFFICIAL_SUBSET"
                or report.get("release_eligibility") != "PARTIAL_NOT_FULL_SCOPE"):
            raise ValueError("Partial diagnostic requires the exact partial Details status")
        unresolved_count = report.get("unresolved_records")
        unresolved_ids = report.get("unresolved_item_ids")
        preserved_ids = report.get("preserved_native_japanese_item_ids")
        preserved_rows = report.get("preserved_native_japanese_source_rows")
        row_count = report.get("preserved_native_japanese_source_row_count")
        if (not isinstance(unresolved_count, int) or isinstance(unresolved_count, bool)
                or unresolved_count <= 0 or not isinstance(unresolved_ids, list)
                or len(unresolved_ids) != unresolved_count
                or any(not isinstance(item, int) or isinstance(item, bool) for item in unresolved_ids)
                or len(set(unresolved_ids)) != len(unresolved_ids)):
            raise ValueError("Partial Details unresolved count does not match unique item IDs")
        if (not isinstance(preserved_ids, list) or preserved_ids != unresolved_ids
                or not isinstance(preserved_rows, Mapping)
                or set(preserved_rows) != {str(item) for item in unresolved_ids}):
            raise ValueError("Partial Details preserved native rows do not match unresolved items")
        actual_row_count = 0
        for item_id, rows in preserved_rows.items():
            if (not isinstance(rows, list) or not rows
                    or any(not isinstance(row, str) or not row for row in rows)):
                raise ValueError(f"Partial Details native source rows are invalid for item {item_id}")
            actual_row_count += len(rows)
        if (not isinstance(row_count, int) or isinstance(row_count, bool)
                or row_count <= 0 or row_count != actual_row_count):
            raise ValueError("Partial Details preserved source-row count does not match row metadata")
        blocker = report.get("actionable_blocker")
        if not isinstance(blocker, str) or not blocker.strip():
            raise ValueError("Partial Details report lacks its official-source coverage blocker")
        partially_translated = report.get("partially_translated_records")
        fully_japanese = report.get("fully_japanese_preserved_item_ids")
        if (not isinstance(partially_translated, list) or not isinstance(fully_japanese, list)
                or any(not isinstance(item, int) or isinstance(item, bool)
                       for item in partially_translated + fully_japanese)
                or set(partially_translated) & set(fully_japanese)
                or sorted(partially_translated + fully_japanese) != sorted(unresolved_ids)):
            raise ValueError("Partial Details translation categories do not partition unresolved items")
        catalogue_count = report.get("valid_catalogue_records")
        exact_count = report.get("official_exact_records")
        source_rows = report.get("source_rows")
        exact_source_rows = report.get("official_exact_source_rows")
        if (not isinstance(catalogue_count, int) or isinstance(catalogue_count, bool)
                or catalogue_count <= 0 or not isinstance(exact_count, int)
                or isinstance(exact_count, bool) or exact_count < 0
                or exact_count + unresolved_count > catalogue_count
                or not isinstance(source_rows, int) or isinstance(source_rows, bool)
                or source_rows < row_count or not isinstance(exact_source_rows, int)
                or isinstance(exact_source_rows, bool) or exact_source_rows < 0
                or exact_source_rows + row_count != source_rows):
            raise ValueError("Partial Details catalogue/source-row coverage counts are inconsistent")
        return {
            "status": "PARTIAL_DIAGNOSTIC_NOT_GAMEPLAY_APPROVED",
            "scope_complete": False,
            "coverage_gap": {
                "component": "details",
                "kind": "official_corpus_coverage_gap",
                "release_eligibility": "PARTIAL_NOT_FULL_SCOPE",
                "details_status": "PARTIAL_OFFICIAL_SUBSET",
                "unresolved_records": unresolved_count,
                "unresolved_item_ids": list(unresolved_ids),
                "preserved_native_japanese_item_ids": list(preserved_ids),
                "preserved_native_japanese_source_rows": {
                    key: list(value) for key, value in sorted(preserved_rows.items())
                },
                "preserved_native_japanese_source_row_count": row_count,
                "partially_translated_item_ids": list(partially_translated),
                "fully_japanese_preserved_item_ids": list(fully_japanese),
                "catalogue_records": catalogue_count,
                "official_exact_records": exact_count,
                "source_rows": source_rows,
                "official_exact_source_rows": exact_source_rows,
                "actionable_blocker": blocker,
            },
        }
    return {
        "status": "DIAGNOSTIC_NOT_GAMEPLAY_APPROVED",
        "scope_complete": True,
        "coverage_gap": None,
    }


def build(route_evidence: Mapping[str, Any] | Path | None = None, *,
          allow_partial_diagnostic: bool = False) -> dict[str, Any]:
    """Build full coverage by default; the partial diagnostic needs explicit opt-in."""
    if type(allow_partial_diagnostic) is not bool:
        raise ValueError("allow_partial_diagnostic must be a bool")
    if route_evidence is None:
        raise ValueError("Parent route/provenance evidence is required before an ISO build")
    route_report = validate_route_evidence(route_evidence)
    if not SOURCE_ISO.is_file() or sha_file(SOURCE_ISO) != SOURCE_ISO_SHA256:
        raise ValueError("Approved r67.15f source ISO is missing or changed")
    corpus_bytes = CORPUS.read_bytes()
    if hashlib.sha256(corpus_bytes).hexdigest() != CORPUS_SHA256:
        raise ValueError("Official English corpus missing or changed")
    inputs = _read_approved_inputs()
    first = compose_components(inputs.source_elf, CORPUS, corpus_bytes)
    second = compose_components(inputs.source_elf, CORPUS, corpus_bytes)
    if first != second:
        raise ValueError("Two independent component preparations were not deterministic")
    candidate_elf, component_report = first
    scope = release_scope(component_report, allow_partial_diagnostic=allow_partial_diagnostic)
    owners = {key: tuple((int(a, 16), int(b, 16)) for a, b in spans)
              for key, spans in component_report["normalized_existing_owners"].items()}
    changes = component_report.pop("_changed_bytes")
    component_report.pop("_stages")
    preservation = _verify_15f_preservation(inputs.source_elf, candidate_elf, _source_group4_bytes())
    static_locks = _verify_static_locks(inputs.source_elf, candidate_elf)
    prepared = PreparedELF(inputs.source_elf, candidate_elf, tuple(component_report["components"]), owners, changes,
                           inputs.cvm_sha256)
    if not scope["scope_complete"]:
        output_iso, output_elf, output_manifest, output_audit = (
            PARTIAL_OUTPUT_ISO, PARTIAL_OUTPUT_ELF, PARTIAL_OUTPUT_MANIFEST, PARTIAL_OUTPUT_AUDIT
        )
        output_startup_raw, output_startup_scoped = (
            PARTIAL_OUTPUT_STARTUP_RAW, PARTIAL_OUTPUT_STARTUP_SCOPED
        )
        output_history, output_save = PARTIAL_OUTPUT_HISTORY, PARTIAL_OUTPUT_SAVE
    else:
        output_iso, output_elf, output_manifest, output_audit = (
            OUTPUT_ISO, OUTPUT_ELF, OUTPUT_MANIFEST, OUTPUT_AUDIT
        )
        output_startup_raw, output_startup_scoped = OUTPUT_STARTUP_RAW, OUTPUT_STARTUP_SCOPED
        output_history, output_save = OUTPUT_HISTORY, OUTPUT_SAVE
    incomplete_iso = output_iso.with_suffix(".incomplete")
    destinations = (output_iso, output_elf, output_manifest, output_audit,
                    output_startup_raw, output_startup_scoped, output_history, output_save,
                    incomplete_iso)
    existing = next((path for path in destinations if path.exists()), None)
    if existing is not None:
        raise FileExistsError(f"Refusing to overwrite existing r67.15g artifact: {existing}")
    source_executable_capacity(len(candidate_elf))
    _copy_on_write(SOURCE_ISO, incomplete_iso)
    try:
        with incomplete_iso.open("r+b") as stream, mmap.mmap(stream.fileno(), 0) as image:
            _, target_records = index_iso(image)
            target = find_record(target_records, EXECUTABLE_NAME)
            executable_offset = target.extent * SECTOR_BYTES
            image[executable_offset:executable_offset + len(candidate_elf)] = candidate_elf
            patch_directory_record(image, target.record_offset, size=len(candidate_elf))
            image.flush()
        audit_report = audit_finished_iso(SOURCE_ISO, incomplete_iso, prepared, inputs.cvm_sha256)
        from tools.startup_acceptance import verify_startup_candidate
        raw_startup = verify_startup_candidate(incomplete_iso, HELP_GRAPHICS)
        static = _static_reports(candidate_elf, raw_startup, inputs.source_elf)
        for output, data in (
            (output_elf, candidate_elf),
            (output_manifest, json.dumps({"release": "r67.15g", "status": scope["status"],
                                         "scope_complete": scope["scope_complete"],
                                         "coverage_gap": scope["coverage_gap"],
                                         "output_iso": str(output_iso),
                                         "source_iso_sha256": SOURCE_ISO_SHA256,
                                         "source_elf_sha256": SOURCE_ELF_SHA256,
                                         "candidate_elf_sha256": sha(candidate_elf),
                                         "candidate_iso_sha256": audit_report["candidate_iso_sha256"],
                                         "components": component_report,
                                         "r67_15f_preservation": preservation,
                                         "locks": static_locks,
                                         "route_evidence": route_report,
                                         "startup_scoped": static["startup_scoped"],
                                         "runtime_verified": False, "gameplay_approved": False},
                                        indent=2, sort_keys=True).encode() + b"\n"),
            (output_audit, json.dumps(audit_report, indent=2, sort_keys=True).encode() + b"\n"),
            (output_startup_raw, json.dumps(static["startup_raw"], indent=2, sort_keys=True).encode() + b"\n"),
            (output_startup_scoped, json.dumps(static["startup_scoped"], indent=2, sort_keys=True).encode() + b"\n"),
            (output_history, json.dumps(static["history"], indent=2, sort_keys=True).encode() + b"\n"),
            (output_save, json.dumps(static["save"], indent=2, sort_keys=True).encode() + b"\n"),
        ):
            with output.open("xb") as handle:
                handle.write(data)
        incomplete_iso.rename(output_iso)
        return audit_report
    except Exception:
        # The temporary is this build's own uniquely named output. Keep it for
        # forensic inspection if validation failed; never touch the baseline.
        raise


if __name__ == "__main__":
    raise SystemExit("Call build(route_evidence=...) after all 15g components are ready")
