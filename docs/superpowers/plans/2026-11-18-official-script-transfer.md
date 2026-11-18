# Official Script Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Recover every defensible official PS4 correspondence and deliver a cumulative diagnostic with installed-content evidence.
**Architecture:** Preserve historical producers; add strict per-group transfer and ISO verification modules. Native investigations gate format-specific changes.
**Tech Stack:** Existing Python 3.14.7 unittest tooling, CP932 MTX/KSF, PS2 ELF/ISO9660/CVM.
**Spec:** docs/superpowers/specs/2026-11-18-official-script-transfer-design.md and supplied request.

## Global Constraints

- Preserve r67.15k approved baseline, exact wheel artwork and all historical ISOs.
- No Phase 2 translation; no fuzzy similarity or numeric normalization proof.
- Every new transfer includes source/DC/output hashes, entry identifiers, source/target offsets and control/pointer evidence.
- No merge without explicit gameplay approval; no review of delegated implementation per user routing instructions.

## Review Focus

Ambiguous repeated contexts; pointer-region crossings; unproven macros; untouched Japanese fallback relocation; stale source/report hashes. Each importer test must exercise these boundaries.

### Task 1: Reproducible checkpoint and source recovery
- [ ] Snapshot/hash inherited dirty files and branch existing worktree.
- [ ] Restore sources into fresh local paths, verify pristine and cumulative ISO hashes.
- [ ] Run established baseline tests, record environment failures separately.
- [ ] Commit inherited validated cumulative source with provenance.

### Task 2: Strict partial structural transfer
**Files:** tools/r67n_partial.py, tests/test_r67n_partial.py.
**Interface:** import_partial_mtx(ps2_raw, ps4_raw, dc) returns data, proven spans/entry IDs, unresolved records and source hashes; reject overlap/ambiguity and unsafe compilation.
- [ ] Write focused positive/negative regression tests and observe failure.
- [ ] Implement exact-content/context proof per group, native relocation and untouched fallback evidence. No semantic-similarity fallback.
- [ ] Test five requested structural files; save per-group evidence and hashes.
- [ ] Run targeted suites and commit.

### Task 3: Dynamic/KSF/native research
**Files:** docs/R67N_NATIVE_RESEARCH.md and hash/offset evidence.
- [ ] Trace FN02_31 runtime selection, FD00 identity, KSF record/consumer semantics, and px/pn/pm native ownership.
- [ ] Implement/test only proven safe mechanisms; retain exact blockers otherwise.

### Task 4: Source and installed-content inventory / name repairs
**Files:** tools/r67n_inventory.py, tests/test_r67n_inventory.py, tools/r67n_names.py, tests/test_r67n_names.py.
- [ ] Test deterministic coverage and offset-level findings, control-aware CP932 scan, missing counterparts remaining unresolved, installed hash drift rejection.
- [ ] Inventory every MTX/KSF and every official DC entry; classify installed/proven/unresolved/technical fallback without completion percentage.
- [ ] Audit older installed literal placeholders against source and repair only proven native substitutions.
- [ ] Verify installed candidate from ISO resources; report residual Japanese eligible/non-rendered/unknown occurrences with source evidence.

### Task 5: Cumulative release and handoff
**Files:** tools/r67n_release.py, tests/test_r67n_release.py, docs/R67N_HANDOFF.md, translations/r67n_script_transfer.json.
- [ ] Add only source-verified new/repaired payloads onto exact m hash; use existing build/audit modules.
- [ ] Verify deterministic generation, full-disc exact byte audit, ROFS, startup, history/save descriptors, approved source/native/art locks.
- [ ] Run full established suite and record skips/limitations accurately.
- [ ] Export next diagnostic ISO, machine-readable reports and handoff into user outputs; hash historical releases again.
- [ ] Commit scoped changes, push feature branch, prepare draft PR; do not merge.
