from __future__ import annotations

import unittest

from tools.ksf_import import KsfFieldAnalysis, summarize_ksf_analyses


class KsfReportTests(unittest.TestCase):
    def test_summarizes_statuses_and_entry_counts(self) -> None:
        analyses = (
            KsfFieldAnalysis(10, "A", "fit", capacity=8),
            KsfFieldAnalysis(20, "Too long", "overflow", capacity=3, reason="overflow"),
            KsfFieldAnalysis(30, "?", "ambiguous", reason="marker"),
        )

        summary = summarize_ksf_analyses(analyses)

        self.assertEqual(
            {"entries": 3, "fit": 1, "overflow": 1, "ambiguous": 1},
            summary,
        )


if __name__ == "__main__":
    unittest.main()
