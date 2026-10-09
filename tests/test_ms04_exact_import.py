"""Regression for adjacent synthetic DC keys, independent of English phrases."""
from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path
import struct
import unittest

from tools.exact_import import ExactImportError, import_exact_mtx
from tools.import_exact_mtx import approved_synthetic_dc_rules
from tools.localization import DcLocalization, encode_ps2_english
from tools.mtx import MtxFile


PS2_MS04 = Path("/private/tmp/khc-ps2-assets/ADV/MS/MS04_00.MTX")
PS4_ADV = Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/ADV")
SOURCE_SHA256 = "221fac0fa1172104310cf10079161247bf6d217556d01f65cc6bfd9772f49701"
MAP_SHA256 = "3b8902ee75fe0e83aa2de3b2f69e93795f4b815c179417418e0af69f2bfb65f1"
OUTPUT_SHA256 = "20c2132ce2e9e22823bfd3452fea917bec493b3a85b9ebf17886c69603dcc4d4"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class AdjacentSyntheticDcKeyTests(unittest.TestCase):
    def test_contiguous_keys_crossing_a_second_cp932_boundary_are_one_group(self):
        raw = struct.pack("<4H", 2, 0, 0, 0) + "明日".encode("cp932") + b"wc__"
        dc = {"keys": [8, 9, 10], "values": ["Morning", "practice", "tomorrow"]}
        with self.assertRaises(ExactImportError):
            import_exact_mtx(raw, raw, dc)
        groups = DcLocalization.from_json(raw, dc, allow_adjacent_synthetic_keys=True).groups
        self.assertEqual(1, len(groups))
        self.assertEqual(8, groups[0].anchor)
        self.assertEqual((9, 10), groups[0].synthetic_keys)
        self.assertEqual(12, groups[0].replace_end)
        output = import_exact_mtx(raw, raw, dc, allow_adjacent_synthetic_keys=True)
        self.assertIn(
            b"r".join(encode_ps2_english(t) for t in dc["values"]),
            output,
        )
        self.assertIn(b"wc__", output)
        self.assertEqual(8, MtxFile.parse(output).header_size)

    def test_adjacent_real_script_control_is_not_silently_absorbed(self):
        raw = struct.pack("<4H", 2, 0, 0, 0) + "明".encode("cp932") + b"r" + "日".encode("cp932") + b"wc_"
        dc = {"keys": [8, 9, 10], "values": ["One", "Two", "Three"]}
        with self.assertRaises(ExactImportError):
            import_exact_mtx(raw, raw, dc, allow_adjacent_synthetic_keys=True)

    @unittest.skipUnless(
        PS2_MS04.is_file()
        and (PS4_ADV / "MS/MS04_00.MTX").is_file()
        and (PS4_ADV / "MS/EN/MS04_00DC.json").is_file(),
        "Owned PS2/PS4 ADV sources not extracted",
    )
    def test_owned_ms04_official_source_and_output_golden(self):
        ps2 = PS2_MS04.read_bytes()
        ps4 = (PS4_ADV / "MS/MS04_00.MTX").read_bytes()
        map_bytes = (PS4_ADV / "MS/EN/MS04_00DC.json").read_bytes()
        self.assertEqual(SOURCE_SHA256, sha(ps2))
        self.assertEqual(ps2, ps4)
        self.assertEqual(MAP_SHA256, sha(map_bytes))
        dc = json.loads(map_bytes)
        self.assertEqual(40, len(dc["keys"]))
        with self.assertRaises(ExactImportError):
            import_exact_mtx(ps2, ps4, dc)
        groups = DcLocalization.from_json(ps2, dc, allow_adjacent_synthetic_keys=True).groups
        self.assertEqual(40, sum(len(g.lines) for g in groups))
        self.assertEqual(38, len(groups))
        self.assertEqual(OUTPUT_SHA256, sha(import_exact_mtx(
            ps2, ps4, dc, allow_adjacent_synthetic_keys=True
        )))

    def test_approved_manifest_is_exactly_scoped_to_ms04(self):
        root = Path(__file__).resolve().parent.parent
        rules = approved_synthetic_dc_rules(root / "translations/approved_adjacent_dc.json")
        self.assertEqual({"MS/MS04_00.MTX"}, set(rules))
        self.assertEqual(SOURCE_SHA256, rules["MS/MS04_00.MTX"]["ps2_sha256"])
        self.assertEqual(MAP_SHA256, rules["MS/MS04_00.MTX"]["dc_sha256"])
        self.assertEqual(OUTPUT_SHA256, rules["MS/MS04_00.MTX"]["output_sha256"])

    def test_approval_manifest_fails_closed_on_duplicate_or_unsafe_paths(self):
        root = Path(__file__).resolve().parent.parent
        real = json.loads((root / "translations/approved_adjacent_dc.json").read_text())
        with tempfile.TemporaryDirectory() as d:
            destination = Path(d) / "approved.json"
            for duplicate in (True, False):
                altered = json.loads(json.dumps(real))
                if duplicate:
                    altered["assets"].append(altered["assets"][0].copy())
                else:
                    altered["assets"][0]["path"] = "../unsafe.mtx"
                destination.write_text(json.dumps(altered))
                with self.assertRaisesRegex(ValueError, "Duplicate or unsafe"):
                    approved_synthetic_dc_rules(destination)


if __name__ == "__main__":
    unittest.main()
