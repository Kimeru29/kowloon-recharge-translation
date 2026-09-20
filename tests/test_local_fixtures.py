from __future__ import annotations

import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture


class LocalFixtureTests(unittest.TestCase):
    def test_missing_fixture_skips_instead_of_crashing(self) -> None:
        with self.assertRaises(unittest.SkipTest):
            require_local_fixture(Path("/definitely/missing/kowloon-fixture.bin"))


if __name__ == "__main__":
    unittest.main()
