"""Official PS4->PS2 English GUI texture ports must preserve every non-owned TMX."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tools.first_save_graphics_port import APPROVED, original_containers
from tools.tmx import iter_tmx_entries

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = Path("/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso")
APPROVED_R66 = Path("/private/tmp/kowloon-recharge-startup-en-v11-r66.iso")
MANIFEST = ROOT / "translations/r67_graphics_owners.json"
GENERATED = ROOT / "local/r67-english-graphics-85"
EVIDENCE = ROOT / "local/r67-english-graphics-85-report.json"


class FirstSaveGraphicsTests(unittest.TestCase):
    @unittest.skipUnless(ORIGINAL.exists() and APPROVED_R66.exists() and EVIDENCE.exists(), "Pristine source/ignored port report missing")
    def test_all_85_ports_only_modify_approved_tmx_chunks(self):
        source = original_containers(ORIGINAL)
        r66_source = original_containers(APPROVED_R66)
        pristine_gp020 = source[20]
        source[20] = r66_source[20]
        # Hard guarantee: the hand-painted English GP020_03 caption is not
        # rebuilt from Japanese even though we port GP020_02 next door.
        original_gp020 = {e.name: e for e in iter_tmx_entries(pristine_gp020)}
        approved_gp020 = {e.name: e for e in iter_tmx_entries(source[20])}
        for name,entry in original_gp020.items():
            a,b=entry.base_offset,entry.base_offset+entry.chunk_size
            if name.endswith("GP020_03.TMX"):
                self.assertNotEqual(pristine_gp020[a:b],source[20][a:b])
            else:
                self.assertEqual(pristine_gp020[a:b],source[20][a:b])
        manifest = json.loads(MANIFEST.read_text())
        report = json.loads(EVIDENCE.read_text())
        self.assertEqual(2, manifest["schema_version"])
        self.assertEqual(set(APPROVED), {(a["group"], a["index"]) for a in manifest["assets"]})
        self.assertEqual(85, len(report["assets"]))
        self.assertEqual(18, len(report["containers"]))
        for c in report["containers"]:
            group = c["group"]
            pristine = source[group]
            final = (GENERATED / "BLBRD" / f"B_GP{group:03d}.BIN").read_bytes()
            with self.subTest(group=group):
                self.assertEqual(len(pristine), len(final))
                self.assertEqual(c["original_source_sha256"], hashlib.sha256(pristine).hexdigest())
                self.assertEqual(c["final_output_sha256"], hashlib.sha256(final).hexdigest())
                allowed = {
                    f"GRP{group:03d}/GP{group:03d}_{idx:02d}.TMX"
                    for grp, idx in APPROVED if grp == group
                }
                entries = iter_tmx_entries(pristine)
                changed = {
                    entry.name for entry in entries
                    if pristine[entry.base_offset:entry.base_offset+entry.chunk_size] !=
                       final[entry.base_offset:entry.base_offset+entry.chunk_size]
                }
                self.assertEqual(allowed, changed)
                for entry in entries:
                    if entry.name in allowed:
                        continue
                    a, b = entry.base_offset, entry.base_offset+entry.chunk_size
                    self.assertEqual(pristine[a:b], final[a:b],
                                     "A non-owned sprite changed (including group-2 AFK/L1)")
        for asset in report["assets"]:
            if not asset["manual_source_layout_review"]:
                self.assertGreaterEqual(asset["jp_geometry_dice"], 0.93)
            if not asset["text_repaint_exception"]:
                self.assertGreaterEqual(asset["en_geometry_dice"], 0.93)
            self.assertGreater(asset["changed_bytes"], 0)
        self.assertEqual(12, sum(bool(x["text_repaint_exception"]) for x in report["assets"]))
        self.assertEqual(6, sum(bool(x["manual_source_layout_review"]) for x in report["assets"]))


if __name__ == "__main__":
    unittest.main()
