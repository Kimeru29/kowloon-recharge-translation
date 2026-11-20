from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


class ReleaseMTXChainTests(unittest.TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.roots = {label: self.root / label for label in (
            "r67o-bundles", "r67o-kwlnscr", "r67o-speakers",
        )}
        self.staged = self.root / "staged"
        self.stage_for = {
            "MS/A.MTX": b"bundled body",
            "KWLNSCR.MTX": b"script intro",
            "MS/B.MTX": b"stock body",
            "MS/C.MTX": b"already English",
        }
        self.baseline = {path: sha(data) for path, data in {
            **self.stage_for,
            "MS/A.MTX": b"stock A",
            "KWLNSCR.MTX": b"stock intro",
        }.items()}
        self.upstream = {
            "r67o-bundles": {
                "MS/A.MTX": (self.baseline["MS/A.MTX"], sha(self.stage_for["MS/A.MTX"])),
            },
            "r67o-kwlnscr": {
                "KWLNSCR.MTX": (self.baseline["KWLNSCR.MTX"], sha(self.stage_for["KWLNSCR.MTX"])),
            },
        }
        self.speakers = {
            "MS/A.MTX": {
                "input_sha256": sha(self.stage_for["MS/A.MTX"]),
                "output_sha256": sha(b"new name | bundled body"),
            },
            "MS/B.MTX": {
                "input_sha256": sha(self.stage_for["MS/B.MTX"]),
                "output_sha256": sha(b"new name | stock body"),
            },
        }
        self.unchanged = {path: sha(self.stage_for[path]) for path in ("MS/C.MTX", "KWLNSCR.MTX")}
        self.report_hashes = {"r67o-bundles": sha(b"bundles"), "r67o-kwlnscr": sha(b"kwlnscr")}
        self.provenance = {path: {
            "input_sha256": sha(data),
            "n_sha256": self.baseline[path],
        } for path, data in self.stage_for.items()}
        for label, rows in self.upstream.items():
            for path in rows:
                self.provenance[path].update(producer=label, producer_report_sha256=self.report_hashes[label])
                self.write(self.roots[label] / path, self.stage_for[path])
        for path, raw in self.stage_for.items():
            self.write(self.staged / path, raw)
        self.write(self.roots["r67o-speakers"] / "MS/A.MTX", b"new name | bundled body")
        self.write(self.roots["r67o-speakers"] / "MS/B.MTX", b"new name | stock body")

    @staticmethod
    def write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def compose(self):
        from tools.r67o_release import compose_mtx_overlay

        return compose_mtx_overlay(
            self.roots, self.upstream, self.speakers, self.unchanged, self.staged,
            self.provenance, self.baseline, self.report_hashes,
        )

    def test_uses_final_speaker_only_after_verified_intermediate_preimage(self):
        overlay = self.compose()

        self.assertEqual({
            "KWLNSCR.MTX": b"script intro",
            "MS/A.MTX": b"new name | bundled body",
            "MS/B.MTX": b"new name | stock body",
        }, {entry.path: entry.source_path.read_bytes() for entry in overlay.entries})
        self.assertEqual(1, len(overlay.collisions))
        collision = overlay.collisions[0]
        self.assertEqual(("MS/A.MTX", "r67o-bundles", sha(b"bundled body"), "r67o-speakers"),
                         (collision.path, collision.replaced_provenance, collision.replaced_sha256,
                          collision.replacement_provenance))

    def test_rejects_speaker_collision_against_pre_bundle_input(self):
        self.speakers["MS/A.MTX"]["input_sha256"] = self.baseline["MS/A.MTX"]
        with self.assertRaisesRegex(ValueError, "speaker input hash"):
            self.compose()

    def test_rejects_wrong_report_digest_on_staged_collision(self):
        self.provenance["MS/A.MTX"]["producer_report_sha256"] = self.report_hashes["r67o-kwlnscr"]
        with self.assertRaisesRegex(ValueError, "staged provenance"):
            self.compose()

    def test_rejects_drift_in_superseded_payload(self):
        self.write(self.roots["r67o-bundles"] / "MS/A.MTX", b"fake new body")
        with self.assertRaisesRegex(ValueError, "payload hash"):
            self.compose()

    def test_rejects_drift_in_installed_baseline_preimage(self):
        self.baseline["MS/A.MTX"] = sha(b"other preimage")
        with self.assertRaisesRegex(ValueError, "baseline preimage"):
            self.compose()

    def test_rejects_drift_in_staged_unchanged_payload(self):
        self.write(self.staged / "MS/C.MTX", b"different text")
        with self.assertRaisesRegex(ValueError, "payload hash"):
            self.compose()

    def test_rejects_ksf_in_speaker_overlay(self):
        self.write(self.roots["r67o-speakers"] / "KWLNSCR.KSF", b"KSF")
        with self.assertRaisesRegex(ValueError, "Only canonical ADV MTX"):
            self.compose()


class ReleaseDestinationTests(unittest.TestCase):
    def test_existing_output_is_rejected_before_reading_inputs(self):
        from tools.r67o_release import release

        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            keep = directory / "existing.iso"
            keep.write_bytes(b"existing evidence")
            with self.assertRaises(FileExistsError):
                release(Path("missing.iso"), directory, {}, Path("missing"), Path("missing"))
            self.assertEqual(b"existing evidence", keep.read_bytes())
