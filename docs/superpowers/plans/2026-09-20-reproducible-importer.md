# Reproducible Importer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Kowloon translation workspace reproducible, corpus-aware, regression-protected, and capable of fail-closed exact PS4-English-to-PS2 MTX imports.

**Architecture:** Add small Python modules for source/corpus metadata, exact importing, and regression validation while keeping existing binary parsers focused. Local copyrighted inputs remain external and ignored. Every automatic import is classified and reported rather than guessed.

**Tech Stack:** Python 3 standard library, `unittest`, Git/GitHub CLI.

**Spec:** `docs/superpowers/specs/2026-09-20-reproducible-importer-design.md`

## Global Constraints

- Never modify pristine PS2/PS4 sources.
- Never commit game binaries, extracted game assets, fonts, textures, ISO/PKG/CVM files, or copied game scripts.
- No emulator launch in this phase.
- Automatic localization is fail-closed.
- `SLPM-66511` and `BISLPM-66511Save` remain invariants.
- Preserve existing working behavior and keep the full local test suite green.

## Review Focus

- A clean clone without local copyrighted fixtures must skip fixture-dependent integration tests instead of crashing at import time.
- Duplicate/indirect DC keys must be rejected from the direct MTX tier instead of being treated as literal byte anchors.
- Corpus classification must distinguish source relationship from English-map availability.
- Regression comparison must fail on removed accepted entries and identity drift while allowing additive entries.
- Repository audit must catch forbidden generated/game binary files before push.

---

### Task 1: Repository hygiene and handoff foundation

**Files:**
- Modify: `.gitignore`
- Create: `README.md`, `fixtures/README.md`, `config/sources.example.json`
- Create: `docs/HANDOFF.md`, `docs/ARCHITECTURE.md`, `docs/DISCOVERY.md`, `docs/BUILD.md`, `docs/REGRESSION.md`
- Create: `tests/local_fixtures.py`
- Modify: fixture-dependent tests to use `require_local_fixture()`

**Interfaces:**
- Produces `require_local_fixture(path: Path) -> Path`, which raises `unittest.SkipTest` if a local-only fixture is missing.
- Produces safe repository documentation/configuration consumed by future sessions and later tasks.

- [ ] **Step 1: Write a failing clean-clone fixture test**

Create `tests/test_local_fixtures.py` that calls `require_local_fixture()` on a guaranteed-missing path and asserts `SkipTest`.

- [ ] **Step 2: Run it and verify RED**

Run: `python3 -m unittest tests.test_local_fixtures -v`
Expected: import failure because `tests.local_fixtures` does not exist.

- [ ] **Step 3: Implement fixture helper and repository hygiene**

Implement `require_local_fixture`, update fixture-dependent tests to call it before reading local files, expand `.gitignore`, and create the documentation/configuration files from the design spec.

- [ ] **Step 4: Verify GREEN and full suite**

Run: `python3 -m unittest tests.test_local_fixtures -v`
Expected: PASS.

Run: `python3 -m unittest discover -s tests -v`
Expected: all current local tests PASS with zero failures.

- [ ] **Step 5: Audit staged-safe files**

Run a `find`/Git status audit proving forbidden extensions and local extracted trees are ignored.

### Task 2: Deterministic corpus manifest

**Files:**
- Create: `tools/corpus.py`
- Create: `tools/build_corpus_manifest.py`
- Create: `tests/test_corpus.py`

**Interfaces:**
- Produces `scan_corpus(ps2_adv: Path, ps4_adv: Path) -> dict`.
- Manifest records per-asset hashes, sizes, `relation`, `english_map`, entry counts, direct-import eligibility, and aggregate summaries.

- [ ] **Step 1: Write failing synthetic classification tests**

Use temporary PS2/PS4 trees to assert: identical mapped => `exact`; missing counterpart => `ps2-only`; changed unique counterpart => `structural`; changed PS4 binary reused by multiple paths => `template`; exact source without EN DC => `unmapped` localization status.

- [ ] **Step 2: Verify RED**

Run: `python3 -m unittest tests.test_corpus -v`
Expected: import failure for `tools.corpus`.

- [ ] **Step 3: Implement scanner and CLI**

Use SHA-256, relative paths, EN filename conventions (`NAME` + `DC.json` for MTX, `NAME.KSFDC.json` for KSF), and deterministic sorted JSON output.

- [ ] **Step 4: Verify GREEN and real corpus invariants**

Run unit tests, then scan the local corpus and assert/report PS2 MTX=1516, PS2 KSF=1516, PS4 MTX=1067, PS4 KSF=1067, common MTX=1067, exact MTX=1022, PS2-only MTX=449.

### Task 3: Generalized MTX English encoding and exact importer

**Files:**
- Modify: `tools/localization.py`
- Create: `tools/exact_import.py`
- Create: `tools/import_exact_mtx.py`
- Modify/Create: `tests/test_localization.py`, `tests/test_exact_import.py`

**Interfaces:**
- `encode_ps2_english(text: str) -> bytes` supports the full observed official corpus repertoire while guaranteeing two-byte CP932 glyphs.
- `import_exact_mtx(ps2_raw: bytes, ps4_raw: bytes, dc: dict) -> bytes` rejects non-identical sources, unresolved/overlapping/indirect keys, or invalid output.
- CLI writes translated files into a separate output tree and emits an import/rejection report.

- [ ] **Step 1: Write failing encoder tests**

Add official-character cases covering `"()*,-./;=`, em/horizontal bars, `♪`, `【】`, and right apostrophe; assert all encoded glyphs are two-byte CP932 and no ordinary ASCII opcode bytes are emitted.

- [ ] **Step 2: Verify RED**

Run localization tests and confirm unsupported punctuation fails.

- [ ] **Step 3: Implement generalized encoding**

Map printable ASCII U+0021..U+007E to full-width U+FF01..U+FF5E, ASCII space to U+3000, normalize straight apostrophe to U+2019, and explicitly map official non-ASCII dash variants to CP932-compatible two-byte forms where necessary. Reject anything not exactly two bytes in CP932.

- [ ] **Step 4: Write failing exact-import tests**

Synthetic MTX tests must cover: identical/direct succeeds; PS2/PS4 mismatch rejects; duplicate/indirect dense keys reject; overlapping spans reject.

- [ ] **Step 5: Implement exact importer fail-closed**

Reuse `MtxFile` and `DcLocalization`. Improve DC grouping only where evidence is unambiguous; keys that cannot be proven as direct text anchors remain rejections rather than guessed mappings.

- [ ] **Step 6: Verify on real exact corpus**

Run the importer in dry/report mode across all exact mapped MTX files. Record success and rejection counts and reasons. Every successful file must reparse as MTX; source files remain unchanged.

### Task 4: Regression gate and conservative KSF inventory/import

**Files:**
- Create: `tools/regression.py`, `tools/check_regression.py`
- Create: `tools/ksf_import.py`
- Create: `tests/test_regression.py`, `tests/test_ksf_import.py`
- Create: `translations/accepted.json`

**Interfaces:**
- `compare_manifests(baseline: dict, current: dict) -> RegressionResult` exposes added/changed/removed and fails when accepted entries disappear or invariants drift.
- `analyze_ksf_exact(raw: bytes, dc: dict) -> report` identifies provable fields and fit/overflow/ambiguous status; patches only fitting proven fields, never truncating.

- [ ] **Step 1: Write failing regression tests**

Assert additive entries pass, removed entries fail, changed source preimage fails, and wrong serial/save identity fails.

- [ ] **Step 2: Verify RED, then implement regression module**

Run targeted tests, implement minimal comparison/validation, rerun to GREEN.

- [ ] **Step 3: Write failing KSF safety tests**

Synthetic fixed-field cases assert a fitting official string patches exactly, an overflow is reported without mutation, and ambiguous anchor/capacity is rejected.

- [ ] **Step 4: Implement conservative KSF analyzer/importer**

No relocation in this phase. A field must have a provable bounded writable region and exact source identity. Normalize PS4 double spaces to single ASCII spaces only for the PS2 inline representation.

- [ ] **Step 5: Seed accepted baseline**

Represent the current title/H.A.N.T. UI patches and DG00 vertical-slice accepted translations as provenance-bearing entries without copying source game text blobs beyond the hand-authored localization metadata already present.

### Task 5: Real corpus reports, documentation refresh, GitHub publication

**Files:**
- Generate ignored: `local/source-manifest.json`, `local/corpus-manifest.json`, `local/exact-import-report.json`, `local/ksf-report.json`
- Update: `README.md`, `docs/HANDOFF.md`, `docs/DISCOVERY.md`, `docs/BUILD.md`, `docs/REGRESSION.md`

**Interfaces:**
- Future AI sessions can resume from `docs/HANDOFF.md` plus repository state.

- [ ] **Step 1: Generate and inspect real reports**

Run source hashing/identity verification, corpus scanning, exact MTX dry/import report, KSF report, and regression check. Capture measured counts in docs.

- [ ] **Step 2: Run repository safety audit**

Confirm no staged/trackable file is an ISO, PKG, CVM, 7z, ELF/game executable, FNT, TMX, copied extracted game tree, or generated translated binary.

- [ ] **Step 3: Run full verification**

Run: `python3 -m unittest discover -s tests -v`
Expected: zero failures/errors.

Run the corpus/regression CLIs against local sources and ensure exit code 0.

- [ ] **Step 4: Commit**

Create English commits with no AI mention.

- [ ] **Step 5: Publish privately**

Create `Kimeru29/kowloon-recharge-translation` as a private GitHub repository if it does not exist, add `origin`, and push `main`. Verify remote visibility is private and `git status` is clean except ignored local artifacts.
