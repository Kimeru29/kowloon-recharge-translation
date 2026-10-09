"""Cross-release memory-card snapshot safety checks; no owned assets needed."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.save_compatibility import MAGIC, snapshot, verify


class SaveCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "original.ps2"
        self.source.write_bytes(MAGIC + b"\0" * 8192)
        self.before = self.source.read_bytes()
        self.destination = self.root / "snapshot"

    def test_snapshot_copies_but_never_changes_source(self):
        original_stat = self.source.stat()
        manifest = snapshot(self.source, self.destination)
        self.assertEqual(self.source.read_bytes(), self.before)
        self.assertEqual(self.source.stat().st_mtime_ns, original_stat.st_mtime_ns)
        self.assertEqual(manifest["source_sha256_at_snapshot"],
                         hashlib.sha256(self.before).hexdigest())
        for name in ("reference.ps2", "r66.ps2", "candidate.ps2"):
            self.assertEqual((self.destination / name).read_bytes(), self.before)
        self.assertFalse(manifest["game_save_verified"])
        self.assertFalse(manifest["runtime_cross_release_verified"])
        self.assertEqual(json.loads((self.destination / "manifest.json").read_text()), manifest)
        self.assertEqual(verify(self.destination, preflight=True), manifest)

    def test_snapshot_refuses_to_replace_any_previous_checkpoint(self):
        snapshot(self.source, self.destination)
        with self.assertRaises(FileExistsError):
            snapshot(self.source, self.destination)
        self.assertEqual(verify(self.destination, preflight=True)["schema"], 1)

    def test_reference_corruption_fails_even_without_clone_preflight(self):
        snapshot(self.source, self.destination)
        reference = self.destination / "reference.ps2"
        reference.chmod(0o600)
        reference.write_bytes(b"modified")
        with self.assertRaisesRegex(ValueError, "Golden reference"):
            verify(self.destination)

    def test_runtime_clone_can_change_without_corrupting_baseline(self):
        snapshot(self.source, self.destination)
        (self.destination / "candidate.ps2").write_bytes(b"simulated in-game save")
        self.assertEqual(verify(self.destination)["schema"], 1)
        with self.assertRaisesRegex(ValueError, "Disposable clone"):
            verify(self.destination, preflight=True)

    def test_rejects_unformatted_card_without_creating_destination(self):
        self.source.write_bytes(b"\xff" * 8192)
        with self.assertRaisesRegex(ValueError, "Not a formatted"):
            snapshot(self.source, self.destination)
        self.assertFalse(self.destination.exists())

    def test_rejects_symlink_source(self):
        alias = self.root / "alias.ps2"
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, "non-symlink"):
            snapshot(alias, self.destination)
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
