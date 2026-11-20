import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.test_build_translation_iso import make_nested_iso
from tools.r67m_cumulative import sha_file
from tools.r67n_release import validate_inputs


class ReleaseProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source.iso"
        make_nested_iso(self.source)
        self.overlay = self.root / "overlay"
        self.ps2 = self.root / "ps2"
        self.ps4 = self.root / "ps4"
        for root in (self.overlay, self.ps2, self.ps4):
            (root / "DG").mkdir(parents=True)
        (self.overlay / "DG/A.MTX").write_bytes(b"English")
        (self.ps2 / "DG/A.MTX").write_bytes(b"Japanese")
        (self.ps4 / "DG/A.MTX").write_bytes(b"Japanese")
        (self.ps4 / "DG/map.json").write_text(json.dumps({"keys": [1], "values": ["English"]}))
        from tools.iso9660_patch import index_iso, find_record
        raw = self.source.read_bytes()
        _, outer = index_iso(raw)
        base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
        _, records = index_iso(raw, base)
        rec = find_record(records, "ADV/DG/A.MTX")
        import hashlib
        before = hashlib.sha256(raw[base + rec.extent * 2048:base + rec.extent * 2048 + rec.size]).hexdigest()
        self.manifest = {"baseline_iso_sha256": sha_file(self.source), "assets": [{
            "path": "DG/A.MTX", "before_sha256": before,
            "output_sha256": sha_file(self.overlay / "DG/A.MTX"),
            "ps2_sha256": sha_file(self.ps2 / "DG/A.MTX"),
            "ps4_sha256": sha_file(self.ps4 / "DG/A.MTX"),
            "map_path": "DG/map.json", "map_sha256": sha_file(self.ps4 / "DG/map.json"),
        }]}
        self.mock = patch("tools.r67n_release.BASELINE_SHA256", sha_file(self.source))
        self.mock.start()
        self.addCleanup(self.mock.stop)

    def validate(self):
        return validate_inputs(self.source, self.overlay, self.manifest, self.ps2, self.ps4)

    def test_binds_overlay_to_disc_original_source_and_official_map(self):
        self.assertEqual(self.validate().entries[0].path, "DG/A.MTX")

    def test_rejects_unrecorded_overlay_and_duplicate_provenance(self):
        (self.overlay / "DG/B.MTX").write_bytes(b"unrecorded")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.validate()
        (self.overlay / "DG/B.MTX").unlink()
        self.manifest["assets"].append(self.manifest["assets"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.validate()

    def test_rejects_installed_preimage_output_source_and_map_drift(self):
        row = self.manifest["assets"][0]
        for field, message in (("before_sha256", "preimage"), ("output_sha256", "output"),
                               ("ps2_sha256", "source"), ("ps4_sha256", "source"),
                               ("map_sha256", "map")):
            with self.subTest(field=field):
                old = row[field]
                row[field] = "0" * 64
                with self.assertRaisesRegex(ValueError, message):
                    self.validate()
                row[field] = old


if __name__ == "__main__":
    unittest.main()
