from __future__ import annotations

import hashlib
import importlib
import io
import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.iso9660_patch import SECTOR_SIZE
from tools import r67_15l_iso_release as release


class PrepareCompositionTests(unittest.TestCase):
    def test_prepare_reads_exact_resource_and_verifies_installed_elf(self):
        source = b"installed approved ELF"
        resource = b"old GP001 bytes"
        localized = b"new GP001 bytes"
        artwork_report = {"matched_labels": 8}
        native_report = {"covered_labels": 8}
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source_path = Path(temp.name) / "approved.iso"
        source_path.write_bytes(source + resource)
        inventory = SimpleNamespace(
            resources={"BLBRD/B_GP001.BIN": (SimpleNamespace(size=len(resource)), len(source))},
            executable_offset=0,
            executable=SimpleNamespace(size=len(source)),
        )
        art_module = SimpleNamespace(apply=lambda data: (localized, artwork_report))
        native_module = SimpleNamespace(verify=lambda elf: native_report)

        def load_module(name):
            if name == "tools.r67_15l_emotion_wheel":
                return art_module
            if name == "tools.r67_15l_native_coverage":
                return native_module
            raise AssertionError(name)

        with patch.object(release, "SOURCE_ISO", source_path), \
             patch.object(release, "_verify_approved_source", return_value={"source_iso_sha256": "approved"}), \
             patch.object(release, "APPROVED_ELF_SHA256", hashlib.sha256(source).hexdigest()), \
             patch.object(release, "WHEEL_RESOURCE_OFFSET", len(source)), \
             patch.object(release, "WHEEL_RESOURCE_SIZE", len(resource)), \
             patch.object(release, "_inventory", return_value=inventory) as inventory_call, \
             patch.object(importlib, "import_module", side_effect=load_module):
            replacement, components = release.prepare()

        self.assertEqual(replacement.path, "BLBRD/B_GP001.BIN")
        self.assertEqual(replacement.original, resource)
        self.assertEqual(replacement.replacement, localized)
        self.assertEqual(components, {"artwork": artwork_report, "native_coverage": native_report})
        self.assertEqual(inventory_call.call_args.args[1], ("BLBRD/B_GP001.BIN",))

    def test_cli_passes_prepared_component_proofs_into_build(self):
        replacement = release.ResourceReplacement("BLBRD/B_GP001.BIN", b"before", b"after!")
        components = {"artwork": {"ok": True}, "native_coverage": {"ok": True}}
        build_report = {"candidate_iso_sha256": "candidate-sha", "status": "BUILT"}
        output = io.StringIO()
        with patch.object(release, "prepare", return_value=(replacement, components)), \
             patch.object(release, "build", return_value=build_report) as build, \
             redirect_stdout(output):
            self.assertEqual(release.main(), 0)
        build.assert_called_once_with((replacement,), components=components)
        self.assertEqual(json.loads(output.getvalue()), {
            "candidate_iso_sha256": "candidate-sha", "status": "BUILT",
            "report": str(release.OUTPUT_REPORT),
        })

    def test_build_accepts_g_static_lock_shape_before_cloning(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source_path = Path(temp.name) / "source.iso"
        source_path.write_bytes(b"ELF!!before")
        source_elf = b"ELF!!"
        replacement = release.ResourceReplacement(
            "BLBRD/B_GP001.BIN", b"before", b"after!"
        )
        inventory = SimpleNamespace(resources={
            "BLBRD/B_GP001.BIN": (SimpleNamespace(size=6), 5),
        })
        static_locks = {
            "history_lock_regions": ["history-a", "history-b", "history-c", "history-d"],
            "save_identity": {
                "native_save_descriptors": 15,
                "runtime_verified": False,
            },
            "runtime_save_compatibility_verified": False,
        }
        locks = {
            "q_lock": {}, "t_lock": {},
            "t_lock_in_memory_reconstruction_only": [],
            **static_locks,
        }
        with patch.object(release, "SOURCE_ISO", source_path), \
             patch.object(release, "_assert_output_paths_available"), \
             patch.object(release, "_verify_approved_source", return_value={}), \
             patch.object(release, "_inventory", return_value=inventory), \
             patch.object(release, "_read_installed_locks",
                          return_value=(source_elf, b"group", {})), \
             patch.object(release.k_lock, "ELF", SimpleNamespace(read_bytes=lambda: source_elf)), \
             patch.object(release.g, "_verify_static_locks", return_value=locks), \
             patch.object(release.g, "_copy_on_write",
                          side_effect=RuntimeError("stopped after preservation gate")):
            with self.assertRaisesRegex(RuntimeError, "stopped after preservation gate"):
                release.build((replacement,))


def _record(name: bytes, extent: int, size: int, flags: int = 0) -> bytes:
    padding = b"\0" if len(name) % 2 == 0 else b""
    length = 33 + len(name) + len(padding)
    data = bytearray(length)
    data[0] = length
    data[2:10] = extent.to_bytes(4, "little") + extent.to_bytes(4, "big")
    data[10:18] = size.to_bytes(4, "little") + size.to_bytes(4, "big")
    data[25] = flags
    data[28:32] = b"\x01\0\x01\0"
    data[32] = len(name)
    data[33:33 + len(name)] = name
    return bytes(data)


def _directory(entries: list[bytes], extent: int) -> bytes:
    body = _record(b"\0", extent, SECTOR_SIZE, 2) + _record(b"\1", extent, SECTOR_SIZE, 2)
    body += b"".join(entries)
    if len(body) > SECTOR_SIZE:
        raise AssertionError("fixture directory exceeds one sector")
    return body + bytes(SECTOR_SIZE - len(body))


def _pvd(image: bytearray, base: int, root_extent: int, volume_sectors: int) -> None:
    offset = base + 16 * SECTOR_SIZE
    image[offset] = 1
    image[offset + 1:offset + 6] = b"CD001"
    image[offset + 6] = 1
    image[offset + 80:offset + 88] = (volume_sectors.to_bytes(4, "little")
                                         + volume_sectors.to_bytes(4, "big"))
    root = _record(b"\0", root_extent, SECTOR_SIZE, 2)
    image[offset + 156:offset + 156 + len(root)] = root


def make_iso() -> tuple[bytes, dict[str, int]]:
    """Create a compact outer ISO with a nested DATA.CVM ISO and two resources."""
    image = bytearray(160 * SECTOR_SIZE)
    cvm_base = 40 * SECTOR_SIZE + 0x1800
    outer_entries = [
        _record(b"SLPM_665.11;1", 30, 64),
        _record(b"DATA.CVM;1", 40, 180_000),
    ]
    image[20 * SECTOR_SIZE:21 * SECTOR_SIZE] = _directory(outer_entries, 20)
    _pvd(image, 0, 20, len(image) // SECTOR_SIZE)
    image[30 * SECTOR_SIZE:30 * SECTOR_SIZE + 64] = bytes(range(64))

    nested_root = [
        _record(b"ADV", 21, SECTOR_SIZE, 2),
        _record(b"BLBRD", 23, SECTOR_SIZE, 2),
    ]
    image[cvm_base + 20 * SECTOR_SIZE:cvm_base + 21 * SECTOR_SIZE] = _directory(nested_root, 20)
    image[cvm_base + 21 * SECTOR_SIZE:cvm_base + 22 * SECTOR_SIZE] = _directory(
        [_record(b"TEST.BIN;1", 22, 8), _record(b"ALIAS.BIN;1", 22, 8)], 21)
    image[cvm_base + 23 * SECTOR_SIZE:cvm_base + 24 * SECTOR_SIZE] = _directory(
        [_record(b"B_GP004.BIN;1", 24, 16)], 23)
    _pvd(image, cvm_base, 20, 30)
    resource_offset = cvm_base + 22 * SECTOR_SIZE
    group4_offset = cvm_base + 24 * SECTOR_SIZE
    image[resource_offset:resource_offset + 8] = b"original"
    image[group4_offset:group4_offset + 16] = b"group-four-bytes"
    return bytes(image), {"resource": resource_offset, "group4": group4_offset, "cvm": 40 * SECTOR_SIZE}


def _locked_test_dependencies(iso_sha: str):
    return (
        patch.object(release.k_lock, "verify_sources", return_value={"verified_source_files": 52}),
        patch.object(release.k_lock, "verify_historical_report", return_value={"historical_report_unchanged": True}),
        patch.object(release.k_lock, "verify_approved_iso", return_value={"iso_sha256": iso_sha}),
        patch.object(release.k_lock, "verify_installed", return_value={"locked": True}),
    )


class ResourceOnlyIsoReleaseTests(unittest.TestCase):
    def setUp(self):
        self.source, self.offsets = make_iso()
        self.original = b"original"
        self.replacement = b"replacEd"
        self.resource = release.ResourceReplacement("ADV/TEST.BIN", self.original, self.replacement)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source_path = Path(self.temp.name) / "source.iso"
        self.candidate_path = Path(self.temp.name) / "candidate.iso"
        self.source_path.write_bytes(self.source)

    def _audit(self, candidate: bytes, replacements=None, source_sha=None):
        self.candidate_path.write_bytes(candidate)
        with patch.object(release, "SOURCE_ISO", self.source_path), \
             patch.object(release.k_lock, "ISO", self.source_path), \
             patch.object(release, "SOURCE_ISO_SHA256", source_sha or hashlib.sha256(self.source).hexdigest()), \
             patch.object(release, "PHYSICAL_BYTES", len(self.source)), \
             patch.object(release, "APPROVED_ELF_SHA256", hashlib.sha256(bytes(range(64))).hexdigest()), \
             _locked_test_dependencies(hashlib.sha256(self.source).hexdigest())[0], \
             _locked_test_dependencies(hashlib.sha256(self.source).hexdigest())[1], \
             _locked_test_dependencies(hashlib.sha256(self.source).hexdigest())[2], \
             _locked_test_dependencies(hashlib.sha256(self.source).hexdigest())[3]:
            return release.audit_finished_iso(
                self.source_path, self.candidate_path,
                (self.resource,) if replacements is None else replacements)

    def test_independent_exact_resource_patch_passes_and_counts_changed_bytes(self):
        candidate = bytearray(self.source)
        candidate[self.offsets["resource"]:self.offsets["resource"] + len(self.replacement)] = self.replacement
        report = self._audit(bytes(candidate))
        self.assertEqual(report["complete_disc_bytes_compared"], len(self.source))
        self.assertEqual(report["unexplained_bytes"], 0)
        self.assertEqual(report["resource_changed_bytes"], {
            "ADV/TEST.BIN": sum(left != right for left, right in zip(self.original, self.replacement))})

    def test_truncated_candidate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "physical length"):
            self._audit(self.source[:-1])

    def test_overlapping_replacement_paths_are_rejected(self):
        overlapping = release.ResourceReplacement("ADV/ALIAS.BIN", self.original, self.replacement)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self._audit(self.source, (self.resource, overlapping))

    def test_wrong_preimage_is_rejected(self):
        wrong = release.ResourceReplacement("ADV/TEST.BIN", b"originaL", self.replacement)
        with self.assertRaisesRegex(ValueError, "preimage"):
            self._audit(self.source, (wrong,))

    def test_wrong_source_hash_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self._audit(self.source, source_sha="0" * 64)

    def test_resource_length_change_is_rejected(self):
        wrong_size = release.ResourceReplacement("ADV/TEST.BIN", self.original, b"short")
        with self.assertRaisesRegex(ValueError, "same-length"):
            self._audit(self.source, (wrong_size,))

    def test_unexpected_change_inside_authorized_resource_is_rejected(self):
        candidate = bytearray(self.source)
        candidate[self.offsets["resource"]:self.offsets["resource"] + len(self.replacement)] = self.replacement
        candidate[self.offsets["resource"] + 7] ^= 1
        with self.assertRaisesRegex(ValueError, "unexplained"):
            self._audit(bytes(candidate))

    def test_unexpected_change_outside_authorized_resource_is_rejected(self):
        candidate = bytearray(self.source)
        candidate[self.offsets["resource"]:self.offsets["resource"] + len(self.replacement)] = self.replacement
        candidate[100] ^= 1
        with self.assertRaisesRegex(ValueError, "unexplained"):
            self._audit(bytes(candidate))

    def test_output_collision_is_rejected_before_baseline_reads(self):
        target = Path(self.temp.name) / "existing.iso"
        target.write_bytes(b"keep")
        with patch.object(release, "OUTPUT_ISO", target):
            with self.assertRaises(FileExistsError):
                release.build((self.resource,))
        self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
