# Description Word-Wrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bound all Item Details and dungeon inspection descriptions using
metric-aware whole-word wrapping without removing text.

**Architecture:** Keep the shared font renderer and accepted screens unchanged.
Build a shared layout contract and validate it against native converted text,
then install only owner-scoped layout hooks after resolving grouped inspection
height and lifecycle behaviour.

**Tech Stack:** Python unittest, existing MIPS Assembly emitter, Unicorn,
Capstone, pinned PS2 executable and official PS4 corpus.

**Spec:** `docs/R67_15K_WORD_WRAP_DESIGN.md`

## Global Constraints

- Reuse `.worktrees/first-save-r67`; work on `fix/67.15k-description-word-wrap`.
- Preserve complete text and all accepted j behaviour outside the two bodies.
- Never overwrite old artifacts or change PCSX2 sessions/settings/saves.
- Do not claim a runtime cause, visual fix, or passing release without evidence.
- Delegate implementation and focused verification to Luna per user routing.

## Review Focus

- Native controls and glyph lists differ from the synthetic test fixtures.
- Later alpha, position, and scale updates can rebuild glyph geometry.
- Four inspection lines must not overlap after wrapping.
- Large words or font growth can exceed the available height as well as width.
- Native callback lifetime, registers, and allocation sizes must remain valid.

### Task 1: Reproduce the native input pipeline

Files: `tests/r67_native_text_pipeline.py`, `tests/test_r67_15k_pipeline.py`.

- [x] Run the existing j focused baseline: 41 tests pass.
- [x] Execute native conversion on actual grenade and ammunition strings.
- [x] Execute native node construction and identify the exact j divergence,
  or document the remaining evidence gap without inventing a cause.
- [x] Test the actual owner update/draw sequence, not only manufactured nodes.

### Task 2: Define and test the complete layout policy

Files: `tools/r67_15k_word_wrap.py`, `tests/test_r67_15k_word_wrap.py`.

- [x] Write failing tests for the three supplied examples and all catalogues.
- [x] Implement word measurement using live font metrics and owner rectangles.
- [x] Test repeated layout, changing font metrics, hard/soft line boundaries,
  Japanese runs, empty text, long words, and grouped inspection rows.
- [x] Resolve vertical over-capacity before native integration; never silently
  clip, drop text, or present an unsupported case as passing.

### Task 3: Install and execute owner-local native layout

Files: `tools/r67_15k_description_layout.py`,
`tests/test_r67_15k_description_layout.py`.

- [x] Trace and pin callback ownership, metadata allocation, and destruction.
- [x] Implement only the two description-family hooks from the verified policy.
- [x] Execute native input, layout, subsequent updates, and final draw vertices.
- [x] Add mutation tests and byte-preservation locks for all accepted regions.

### Task 4: Build, audit, document, and integrate

Files: `tools/r67_15k_iso_release.py`, `tests/test_r67_15k_iso_release.py`,
`tests/test_r67_15k_release_lock.py`, `docs/R67_15K_HANDOFF.md`,
`docs/LOCALIZATION_STATUS.md`.

- [ ] Build a separate versioned diagnostic and audit every changed ISO byte.
- [ ] Run all standing startup/history/save/resource locks and full suite.
- [ ] Document native owners, hashes, limitations, and screenshot checklist.
- [ ] Commit, push, and integrate only after verification under the user's
  existing authorization; do not conflate integration with visual approval.
