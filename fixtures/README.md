# Local integration fixtures

This directory may contain small files extracted from Pablo's legally owned PS2/PS4 copies for local reverse-engineering and integration tests. They are intentionally ignored by Git.

The repository test suite must not require these files merely to import its test modules; tests that need them use `tests.local_fixtures.require_local_fixture()` and skip when absent.

Never force-add files from this directory.
