from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import r67_15g_route_audit as route_audit


ROOT = Path(__file__).resolve().parents[1]
FINISHED_ISO = ROOT / "local/r67-candidates/67.15f-item-panel-layout.iso"
SOURCE_ADV = Path(
    "/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/"
    "Media/StreamingAssets/data/ADV"
)


class R6715GRouteAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = route_audit.audit(FINISHED_ISO)

    def _copy_inputs(self, root: Path) -> Path:
        for relative in (
            "DG/DG00_00.MTX",
            "DG/DG00_01.MTX",
            "DG/DG00_00.KSF",
            "MS/MS00_02.MTX",
            "MS/MS00_02.KSF",
            "MS/MS00_01.MTX",
            "MS/EN/MS00_01DC.json",
            "DG/EN/DG00_00DC.json",
            "DG/EN/DG00_01DC.json",
            "DG/EN/DG00_00.KSFDC.json",
            "MS/EN/MS00_02DC.json",
            "MS/EN/MS00_02.KSFDC.json",
        ):
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ADV / relative, destination)
        return root

    def test_finished_image_matches_exact_official_regeneration(self) -> None:
        self.assertTrue(self.report["read_only"])
        self.assertEqual("finished_iso_exact_payload_audit", self.report["audit_kind"])
        assets = self.report["assets"]
        self.assertEqual(195, assets["ADV/DG/DG00_00.MTX"]["official_import_entries"])
        self.assertEqual(34, assets["ADV/DG/DG00_01.MTX"]["official_import_entries"])
        self.assertEqual(593, assets["ADV/MS/MS00_02.MTX"]["official_import_entries"])
        self.assertEqual("official_exact", assets["ADV/DG/DG00_00.MTX"]["verification"])
        self.assertEqual("official_exact", assets["ADV/DG/DG00_01.MTX"]["verification"])
        self.assertEqual("official_exact", assets["ADV/MS/MS00_02.MTX"]["verification"])
        self.assertEqual("unchanged_control_only", assets["ADV/DG/DG00_02.MTX"]["verification"])
        self.assertEqual("unchanged_control_only", assets["ADV/MS/MS00_00.MTX"]["verification"])
        ms01 = assets["ADV/MS/MS00_01.MTX"]
        self.assertEqual("unchanged_ps2_control_script", ms01["verification"])
        self.assertEqual(104, ms01["finished_size"])
        self.assertEqual(1432, ms01["ps4_comparison_size"])
        self.assertEqual(43, ms01["ps4_localization_map_entries"])
        self.assertFalse(ms01["ps2_equals_ps4"])
        self.assertEqual(2322, self.report["unchanged_control_ksf_assets"]["ADV/MS/MS00_00.KSF"]["finished_size"])
        self.assertEqual(2322, self.report["unchanged_control_ksf_assets"]["ADV/MS/MS00_01.KSF"]["finished_size"])

    def test_choice_imports_and_approved_overrides_are_accounted_for(self) -> None:
        ksf = self.report["choice_assets"]
        dg = ksf["ADV/DG/DG00_00.KSF"]
        self.assertEqual({"fit": 3, "approved_compaction": 2, "unresolved": 0}, dg["counts"])
        self.assertEqual([9339, 11689], dg["approved_compaction_offsets"])
        self.assertEqual("Pick up device on the ground", dg["approved_compaction_text"])
        ms = ksf["ADV/MS/MS00_02.KSF"]
        self.assertEqual({"fit": 10, "approved_compaction": 0, "unresolved": 0}, ms["counts"])
        self.assertEqual([], self.report["unresolved_choice_entries"])

    def test_changed_scenario_instruction_map_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_inputs(Path(directory))
            path = root / "DG/EN/DG00_01DC.json"
            obj = json.loads(path.read_text(encoding="utf-8"))
            obj["values"][0] = str(obj["values"][0]) + " changed"
            path.write_text(json.dumps(obj), encoding="utf-8")
            with patch.object(route_audit, "PS4_ADV_ROOT", root):
                with self.assertRaisesRegex(ValueError, "official localization map.*mismatch"):
                    route_audit.audit(FINISHED_ISO)

    def test_altered_installed_script_payload_fails_exact_comparison(self) -> None:
        original = b"official scenario instruction"
        altered = b"changed scenario instruction"
        with self.assertRaisesRegex(ValueError, "finished ISO script differs"):
            route_audit._require_exact_payload(
                altered, original, "finished ISO script differs from exact official output"
            )

    def test_corrupt_choice_map_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_inputs(Path(directory))
            path = root / "DG/EN/DG00_00.KSFDC.json"
            path.write_bytes(path.read_bytes() + b" ")
            with patch.object(route_audit, "PS4_ADV_ROOT", root):
                with self.assertRaisesRegex(ValueError, "official localization map.*mismatch"):
                    route_audit.audit(FINISHED_ISO)

    def test_missing_official_map_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self._copy_inputs(Path(directory))
            (root / "DG/EN/DG00_00DC.json").unlink()
            with patch.object(route_audit, "PS4_ADV_ROOT", root):
                with self.assertRaisesRegex(ValueError, "missing official localization map"):
                    route_audit.audit(FINISHED_ISO)


if __name__ == "__main__":
    unittest.main()
