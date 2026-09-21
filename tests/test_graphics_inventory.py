from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.graphics_inventory import load_asset_dictionary, localized_bundle_aliases, inventory_bundle_files


class GraphicsInventoryTests(unittest.TestCase):
    def test_parses_parallel_asset_dictionary_and_extracts_bundle_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "AssetFileDic_en.txt"
            path.write_text(json.dumps({
                "keys": [
                    "b_gp001",
                    "Assets/DATA/BLBRD/GRP001/GP001_00.png",
                    "memo",
                    "Assets/DATA/MEMO/MEMO_000.png",
                ],
                "values": [
                    "b_gp001_en",
                    "assets/data/localizedata/eng/blbrd/grp001/gp001_00.png",
                    "memo_en",
                    "assets/data/localizedata/eng/memo/memo_000.png",
                ],
            }), encoding="utf-8")

            mapping = load_asset_dictionary(path)
            aliases = localized_bundle_aliases(mapping)

            self.assertEqual("b_gp001_en", mapping["b_gp001"])
            self.assertEqual(("b_gp001_en", "memo_en"), aliases)

    def test_inventory_reports_exact_bundle_alias_presence_without_loading_unity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b_gp001_en").write_bytes(b"bundle")
            aliases = ("b_gp001_en", "memo_en")

            rows = inventory_bundle_files(root, aliases)

            self.assertEqual(2, len(rows))
            self.assertEqual({
                "alias": "b_gp001_en",
                "exists": True,
                "size": 6,
            }, rows[0])
            self.assertEqual({
                "alias": "memo_en",
                "exists": False,
                "size": None,
            }, rows[1])

    def test_rejects_mismatched_parallel_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.txt"
            path.write_text('{"keys":["a"],"values":[]}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "equal-length"):
                load_asset_dictionary(path)


if __name__ == "__main__":
    unittest.main()
