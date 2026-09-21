from __future__ import annotations

import unittest

from tools.accepted_overrides import apply_ksf_override_manifest


class AcceptedKsfOverrideTests(unittest.TestCase):
    def test_applies_committed_fixed_field_overrides_on_top_of_existing_import(self) -> None:
        base = b"HEAD" + b"JAPANESE" + b"TAIL" + b"X" * 20
        manifest = {
            "ksf": [
                {
                    "offset": 4,
                    "capacity": 8,
                    "official": "Long official",
                    "text": "Short",
                    "constrained": True,
                }
            ]
        }

        result = apply_ksf_override_manifest(base, manifest)

        self.assertEqual(len(base), len(result))
        self.assertEqual(b"Short\x00\x00\x00", result[4:12])
        self.assertEqual(base[:4], result[:4])
        self.assertEqual(base[12:], result[12:])

    def test_rejects_manifest_text_that_does_not_fit_committed_capacity(self) -> None:
        with self.assertRaisesRegex(ValueError, "only a 3-byte"):
            apply_ksf_override_manifest(
                b"12345678",
                {"ksf": [{"offset": 1, "capacity": 3, "text": "TOO LONG"}]},
            )


if __name__ == "__main__":
    unittest.main()
