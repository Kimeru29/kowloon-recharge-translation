"""Fail-closed regressions for the r67.15q history-only release boundary."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import r67p_history_scroll as history
from tools import r67q_release as release
from tools import r67p_release as previous


ROOT = Path(__file__).resolve().parents[1]
P_ELF = ROOT / "local/r67p-validated-a/installed.elf"


@unittest.skipUnless(P_ELF.is_file() and release.BASELINE_AUDIT.is_file() and release.BASELINE_INVENTORY.is_dir(),
                     "Pinned r67.15p private release fixtures are unavailable")
class QReleaseBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p_elf = P_ELF.read_bytes()

    def test_history_patch_rejects_mutated_row_and_callsite_preimages(self):
        row_mutation = bytearray(self.p_elf)
        row_mutation[history.ROW_START - history.ELF_BIAS] ^= 1
        with self.assertRaisesRegex(ValueError, "row constructor drift"):
            history.patch(bytes(row_mutation), 0xA10000)

        for offset in release.HISTORY_OWNER_OFFSETS:
            with self.subTest(offset=hex(offset)):
                callsite_mutation = bytearray(self.p_elf)
                callsite_mutation[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "preimage drift"):
                    release.compose_native(bytes(callsite_mutation))

    def test_native_owner_audit_rejects_an_unowned_common_prefix_mutation(self):
        candidate, _report = release.compose_native(self.p_elf)
        mutated = bytearray(candidate)
        mutated[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, "Unowned common-prefix"):
            release.verify_native_owners(self.p_elf, bytes(mutated))

    def test_inventory_rebind_rejects_mutated_p_inventory(self):
        p_audit = json.loads(release.BASELINE_AUDIT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in p_audit["inventory_sha256"]:
                (root / name).write_bytes((release.BASELINE_INVENTORY / name).read_bytes())
            entry = root / "entries.json"
            contents = bytearray(entry.read_bytes())
            contents[0] ^= 1
            entry.write_bytes(contents)

            with self.assertRaisesRegex(ValueError, "Baseline inventory differs: entries.json"):
                release.bind_inventory(root, root / "not-built.iso", root / "bound", p_audit,
                                       "0" * 64)

    def test_inventory_summary_records_q_and_exact_p_parent(self):
        p_audit = json.loads(release.BASELINE_AUDIT.read_text())
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "bound"
            output.mkdir()

            def bind(_directory, _stage, destination, _lock, _expected_hash, *, release):
                (destination / "summary.json").write_text(json.dumps({
                    "release": release,
                    "immediate_baseline_iso_sha256": release_module.BASELINE_SHA256,
                }))
                return {"summary.json": "test-hash"}

            release_module = release
            with patch.object(previous, "bind_inventory", side_effect=bind) as binder:
                result = release.bind_inventory(root, root / "unused.iso", output, p_audit, "expected")

            self.assertEqual(result, {"summary.json": "test-hash"})
            self.assertEqual(binder.call_args.kwargs["release"], release.RELEASE)


if __name__ == "__main__":
    unittest.main()
