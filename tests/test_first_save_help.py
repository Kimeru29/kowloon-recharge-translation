"""Strict translated H.A.N.T. Help corpus, PS2 row and icon provenance gate."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import unittest

from tools.first_save_help import (
    _icon_reservations, _metadata, _raw_rows, _sha,
    append_help_to_p0, manifest_from_owned_sources,
)
from tools.first_save_help_inventory import _BLANK, _EOF
from tools.inspect_english_bytes import parse as parse_english

ROOT = Path(__file__).resolve().parents[1]
PS2 = ROOT.parent / "startup-flow-v10/fixtures/elf/SLPM_665.11"
PS4 = Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
P0 = ROOT / "local/first-save-r67-expanded.elf"
ALL_HELP = ROOT / "local/r67-help-icon-safe.elf"
HELP_MANIFEST = ROOT / "translations/r67_help_owners.json"
GOLDEN_SHA = "26db69bd46e119ecbb7f114ecdafc678976294460f56b7a214861de82c95d76a"


class CompleteFirstSaveHelpTests(unittest.TestCase):
    @unittest.skipUnless(all(x.exists() for x in (PS2, PS4, P0, ALL_HELP)),
                         "Owned PS2 and PS4 corpus or ignored built executable unavailable")
    def test_all_50_translated_pages_controller_holes_and_golden(self):
        src = PS2.read_bytes()
        output = ALL_HELP.read_bytes()
        p0 = P0.read_bytes()
        english = PS4.read_bytes()
        manifest = json.loads(HELP_MANIFEST.read_text())
        self.assertEqual(50, len(manifest["pages"]))
        self.assertEqual(GOLDEN_SHA, hashlib.sha256(output).hexdigest())
        expected, report = append_help_to_p0(
            src, p0, manifest, parse_english(PS4),
            corpus_sha256=hashlib.sha256(english).hexdigest(),
        )
        self.assertEqual(output, expected)
        self.assertEqual(50, report["translated_help_pages"])
        self.assertEqual(99, report["descriptor_aliases"])
        self.assertEqual(18, report["translated_semantic_rows"])
        self.assertEqual(src, PS2.read_bytes())

        phoff = 0x54
        _typ, file_offset, va, _pa, length, _reserve, _flags, _align = struct.unpack_from(
            "<8I", output, phoff
        )
        self.assertEqual(file_offset + length, len(output))
        translated_pages = {p["key"]: p for p in report["pages"]}
        for spec in manifest["pages"]:
            key = spec["key"]
            with self.subTest(page=key):
                self.assertEqual(spec["rows"], translated_pages[key]["rows"])
                table_va = struct.unpack_from("<I", output, spec["descriptor_offset"])[0]
                table = file_offset + table_va - va
                self.assertGreaterEqual(table, len(p0))
                self.assertEqual(_EOF, struct.unpack_from(
                    "<I", output, table + spec["rows"]*4
                )[0])
                reserved, original_transformed = _icon_reservations(
                    spec, _metadata(src, spec)
                )
                for i in range(spec["rows"]):
                    row_va = struct.unpack_from("<I", output, table + i*4)[0]
                    if row_va == _BLANK:
                        continue
                    row_offset = file_offset + row_va - va
                    chars = []
                    for cell in range(29):
                        two = output[row_offset + 2*cell:row_offset + 2*cell + 2]
                        if two == b"\x00\x00":
                            break
                        chars.append(two.decode("cp932"))
                    else:
                        self.fail(f"Unterminated / overwide row {key}/{i}")
                    self.assertLessEqual(len(chars), 28)
                    for column in reserved[i]:
                        if column < len(chars):
                            self.assertEqual(
                                "　", chars[column],
                                f"Sprite overlaps glyph at {key}/{i}/{column}",
                            )
                if spec["icon_records"]:
                    metadata_va = struct.unpack_from(
                        "<I", output, spec["metadata_descriptor_offset"]
                    )[0]
                    metadata_start = file_offset + metadata_va - va
                    self.assertGreaterEqual(metadata_start, len(p0))
                    for j, expected_record in enumerate(original_transformed):
                        actual = struct.unpack_from("<hhhh", output, metadata_start+j*8)
                        self.assertEqual(expected_record, actual)
                    self.assertEqual(
                        (-1, -1, -1, -1),
                        struct.unpack_from("<hhhh", output, metadata_start+len(original_transformed)*8)
                    )

    @unittest.skipUnless(PS2.exists() and PS4.exists(), "Owned PS2/PS4 corpus unavailable")
    def test_hash_pinned_help_manifest_replay(self):
        raw = PS2.read_bytes()
        corpus = PS4.read_bytes()
        manifest = manifest_from_owned_sources(
            raw, parse_english(PS4), _sha(corpus)
        )
        self.assertEqual(
            json.loads(HELP_MANIFEST.read_text()),
            manifest,
        )


if __name__ == "__main__":
    unittest.main()
