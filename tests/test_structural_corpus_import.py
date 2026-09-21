from __future__ import annotations

import json
import struct
import tempfile
import unittest
from pathlib import Path

from tools.import_structural_mtx import import_structural_corpus


def make_mtx(text: str) -> tuple[bytes, int]:
    header = struct.pack("<4H", 2, 2, 2, 2)
    raw = header + b"r" + text.encode("cp932") + b"wc_"
    return raw, len(header) + 1


class StructuralCorpusImportTests(unittest.TestCase):
    def test_emits_only_fully_proven_structural_files_and_reports_rejections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"
            out = root / "out"
            for rel in (Path("DG/GOOD.MTX"), Path("DG/BAD.MTX")):
                (ps2 / rel.parent).mkdir(parents=True, exist_ok=True)
                (ps4 / rel.parent / "EN").mkdir(parents=True, exist_ok=True)

            p4_good, key_good = make_mtx("そうなんじゃないかな、ってr思っていたんです。")
            p2_good, _ = make_mtx("そうなんじゃないかな、ってr想っていたんです。")
            (ps4 / "DG/GOOD.MTX").write_bytes(p4_good)
            (ps2 / "DG/GOOD.MTX").write_bytes(p2_good)
            (ps4 / "DG/EN/GOODDC.json").write_text(
                json.dumps({"keys": [key_good], "values": ["I thought so."]}), encoding="utf-8"
            )

            p4_bad, key_bad = make_mtx("復活を妨げる者だ")
            p2_bad, _ = make_mtx("今日は天気が良いです")
            (ps4 / "DG/BAD.MTX").write_bytes(p4_bad)
            (ps2 / "DG/BAD.MTX").write_bytes(p2_bad)
            (ps4 / "DG/EN/BADDC.json").write_text(
                json.dumps({"keys": [key_bad], "values": ["Stop my resurrection"]}), encoding="utf-8"
            )

            corpus = {
                "assets": [
                    {"kind": "MTX", "relation": "structural", "localization": "mapped", "path": "DG/GOOD.MTX", "english_map": "DG/EN/GOODDC.json", "english_entries": 1},
                    {"kind": "MTX", "relation": "structural", "localization": "mapped", "path": "DG/BAD.MTX", "english_map": "DG/EN/BADDC.json", "english_entries": 1},
                ]
            }

            report = import_structural_corpus(ps2, ps4, out, corpus)

            self.assertEqual(2, report["eligible_files"])
            self.assertEqual(1, report["imported_files"])
            self.assertEqual(1, report["rejected_files"])
            self.assertTrue((out / "DG/GOOD.MTX").exists())
            self.assertFalse((out / "DG/BAD.MTX").exists())

    def test_template_files_require_explicit_allowlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ps2 = root / "ps2"
            ps4 = root / "ps4"
            out = root / "out"
            rel = Path("FD/FD00_31.MTX")
            (ps2 / rel.parent).mkdir(parents=True)
            (ps4 / rel.parent / "EN").mkdir(parents=True)
            p4, key = make_mtx("そうなんじゃないかな、ってr思っていたんです。")
            p2, _ = make_mtx("そうなんじゃないかな、ってr想っていたんです。")
            (ps4 / rel).write_bytes(p4)
            (ps2 / rel).write_bytes(p2)
            (ps4 / "FD/EN/FD00_31DC.json").write_text(
                json.dumps({"keys": [key], "values": ["I thought so."]}), encoding="utf-8"
            )
            corpus = {
                "assets": [
                    {"kind": "MTX", "relation": "template", "localization": "mapped", "path": rel.as_posix(), "english_map": "FD/EN/FD00_31DC.json", "english_entries": 1}
                ]
            }

            blocked = import_structural_corpus(ps2, ps4, out, corpus)
            allowed = import_structural_corpus(
                ps2, ps4, out, corpus, allowed_template_paths={"FD/FD00_31.MTX"}
            )

            self.assertEqual(0, blocked["eligible_files"])
            self.assertEqual(1, allowed["eligible_files"])
            self.assertEqual(1, allowed["imported_files"])


if __name__ == "__main__":
    unittest.main()
