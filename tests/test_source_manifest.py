from __future__ import annotations

from hashlib import sha256
import tempfile
import unittest
from pathlib import Path

from tools.source_manifest import build_source_manifest


class SourceManifestTests(unittest.TestCase):
    def test_hashes_source_files_and_records_compatibility_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "game.7z"
            iso = root / "game.iso"
            pkg = root / "game.pkg"
            ps2_adv = root / "ps2-adv"
            ps4_adv = root / "ps4-adv"
            ps2_adv.mkdir()
            ps4_adv.mkdir()
            archive.write_bytes(b"archive")
            iso.write_bytes(b"iso")
            pkg.write_bytes(b"pkg")

            manifest = build_source_manifest(archive, iso, ps2_adv, pkg, ps4_adv)

            self.assertEqual(sha256(b"iso").hexdigest(), manifest["ps2_iso"]["sha256"])
            self.assertEqual(3, manifest["ps2_iso"]["size"])
            self.assertEqual(str(ps2_adv.resolve()), manifest["ps2_adv_root"])
            self.assertEqual("SLPM-66511", manifest["invariants"]["serial"])
            self.assertEqual("BISLPM-66511Save", manifest["invariants"]["save_directory"])
            self.assertEqual("CUSA27034", manifest["ps4_pkg"]["title_id"])


if __name__ == "__main__":
    unittest.main()
