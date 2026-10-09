"""Release-r67 first Soul Well translation: all owner pointers fail closed."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import struct
import unittest

from tools.first_save_r67 import patch_first_save

ROOT = Path(__file__).resolve().parent.parent
OWNED_ELF = ROOT.parent / "startup-flow-v10/artifacts/SLPM_665.11.en-early"
OWNED_ENGLISH = Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
GOLDEN_ELF_SHA = "cd5441d3c408ca31d41e682be5bd4c0a8dec723cb481b1896be071822fd3be4f"


def sample() -> tuple[bytes, dict, list[tuple[str, str, int]]]:
    raw = bytearray(0x9020)
    raw[:4] = b"\x7fELF"
    struct.pack_into("<8I", raw, 0x54, 1, 0x9000, 0x902f00, 0x902f00,
                     0x20, 0x100000, 7, 0x10)
    owners = []
    english = []
    p = 0x600
    for index in range(29):
        source = f"試験{index:02d}".encode("cp932") + b"\x00"
        pos = 0x1000 + 0x30 * index
        raw[pos:pos+len(source)] = source
        aliases = 6 if index < 3 else 5  # 3*6 + 26*5 = 148.
        ref = list(range(p, p + aliases*4, 4))
        p += aliases*4
        for ptr in ref:
            struct.pack_into("<I", raw, ptr, 0x100000 + pos - 0x80)
        translated = f"Verified {index}"
        english.append((source[:-1].decode("cp932"), translated, index*100))
        owners.append(dict(key=f"first_save_{index}", source_offset=pos,
                           source_sha256=hashlib.sha256(source).hexdigest(),
                           official_record_offset=index*100,
                           official_english=translated, owner_offsets=ref))
    raw = bytes(raw)
    manifest = dict(schema_version=1, approved_r66_elf_sha256=hashlib.sha256(raw).hexdigest(),
                    official_english_bytes_sha256="corpus-digest", owners=owners)
    return raw, manifest, english


class FirstSaveR67Tests(unittest.TestCase):
    def test_append_only_and_all_148_owners_translated(self):
        raw, manifest, english = sample()
        result, report = patch_first_save(raw, manifest, english, english_corpus_sha256="corpus-digest")
        self.assertEqual(29, report["owner_count"])
        self.assertEqual(148, report["pointer_count"])
        self.assertEqual(0x100000, report["translation_segment_memory_reserved"])
        self.assertEqual(raw[0x9000:], result[0x9000:0x9020])
        for owner in report["owners"]:
            for ptr in owner["owner_offsets"]:
                self.assertEqual(owner["translated_va"], struct.unpack_from("<I", result, ptr)[0])
                self.assertNotEqual(raw[ptr:ptr+4], result[ptr:ptr+4])

    def test_mismatched_corpus_hash_rejected(self):
        raw, manifest, english = sample()
        with self.assertRaisesRegex(ValueError, "Official PS4 English corpus"):
            patch_first_save(raw, manifest, english, english_corpus_sha256="drift")

    def test_missing_alias_fails_closed(self):
        raw, manifest, english = sample()
        bad = copy.deepcopy(manifest)
        bad["owners"][0]["owner_offsets"].pop()
        with self.assertRaisesRegex(ValueError, "Pointer alias set drift"):
            patch_first_save(raw, bad, english, english_corpus_sha256="corpus-digest")

    def test_tampered_source_fails_closed(self):
        raw, manifest, english = sample()
        altered = bytearray(raw)
        altered[0x1001] ^= 0x01
        changed = copy.deepcopy(manifest)
        changed["approved_r66_elf_sha256"] = hashlib.sha256(altered).hexdigest()
        with self.assertRaisesRegex(ValueError, "Japanese source SHA256"):
            patch_first_save(bytes(altered), changed, english, english_corpus_sha256="corpus-digest")

    def test_official_english_key_and_text_drift_fail_closed(self):
        raw, manifest, english = sample()
        altered = english.copy()
        altered[4] = (altered[4][0], "Other", altered[4][2])
        with self.assertRaisesRegex(ValueError, "Official PS4 source correspondence"):
            patch_first_save(raw, manifest, altered, english_corpus_sha256="corpus-digest")

    def test_no_extra_unknown_owners(self):
        raw, manifest, english = sample()
        altered = bytearray(raw)
        struct.pack_into("<I", altered, 0x800, 0x100000 + 0x1000 - 0x80)
        new = copy.deepcopy(manifest)
        new["approved_r66_elf_sha256"] = hashlib.sha256(altered).hexdigest()
        with self.assertRaisesRegex(ValueError, "Pointer alias set drift"):
            patch_first_save(bytes(altered), new, english, english_corpus_sha256="corpus-digest")

    @unittest.skipUnless(OWNED_ELF.exists() and OWNED_ENGLISH.exists(), "Owned r66/PS4 local sources unavailable")
    def test_owned_r66_golden_replay(self):
        from tools.inspect_english_bytes import parse
        manifest = json.loads((ROOT / "translations/first_save_pointer_owners.json").read_text())
        source = OWNED_ELF.read_bytes()
        official = OWNED_ENGLISH.read_bytes()
        translated, report = patch_first_save(
            source, manifest, parse(OWNED_ENGLISH),
            english_corpus_sha256=hashlib.sha256(official).hexdigest(),
        )
        self.assertEqual(GOLDEN_ELF_SHA, hashlib.sha256(translated).hexdigest())
        self.assertGreater(report["appended_bytes"], 731)
        self.assertEqual(148, report["pointer_count"])


if __name__ == "__main__":
    unittest.main()
