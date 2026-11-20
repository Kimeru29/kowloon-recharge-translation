# r67.15l Emotion Wheel Implementation Plan

> **For agentic workers:** Execute with Luna implementation and verification. The user's explicit routing overrides independent review gates. Continue autonomously; publish a draft PR and do not merge.

**Goal:** Localize every identified shared Emotion Input wheel label using verified official PS4 English resources while preserving approved PS2 behavior.

**Architecture:** Trace native resource consumers and event dispatch before selecting the smallest shared resource patch. Prefer fixed-size label pixel replacement with the complete approved executable unchanged. Enumerate distinct resources explicitly; never infer that one scene proves every route.

**Tech Stack:** Existing Python unittest, ISO9660/CVM/TMX tools, UnityPy, Pillow, Capstone and Unicorn where applicable.

**Spec:** User's r67.15l request in this chat; preservation authority is `docs/R67_15K_APPROVED_LOCK.json` and the existing q/t/y/f/history approval contracts.

## Global constraints

- Base: `main` at `6a0f1f4c97ad3e8e253f523a8c196bee69e47706`, branch `feat/67.15l-emotion-wheel` in the requested existing worktree.
- Approved k ISO SHA-256: `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`; confirmed locally at task start.
- Approved k ELF SHA-256: `fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d`.
- Preserve historical ISO/report/source locks and all accepted UI, dialogue, saves, mappings, event logic, geometry, animation and transparency.
- Label pixels may change; ornaments and non-label pixels must retain their original PS2 representation.
- Preserve all prior artifacts; fail on output collisions. No PCSX2, card or savestate changes.
- Official source provenance is mandatory. No labels inferred from absent reference screenshots.
- Deliver `67.15l-emotion-wheel.iso`, SHA-256, source/tests/docs/handoff, and draft PR. No full game assets committed or uploaded to GitHub.
- Static/native proof does not establish complete-game runtime acceptance. User PCSX2 approval remains pending.

## Failure modes to cover

- Rotated/selected states use a separate label crop: enumerate every descriptor and selected/unselected variant.
- Indirect event dispatch bypasses a direct-call census: distinguish proven shared routes from unresolved dynamic references.
- Palette edits alter ornament alpha or colors: verify non-label pixels and palette consumers, not only rectangles.
- Output audit permits arbitrary bytes within a large container: compare against independently derived exact replacement bytes and mutation-test outside ownership.
- Missing fixtures silently bypass current-release checks: require source/candidate/provenance artifacts for release validation and disclose historical skips.

## Task 1: Establish ownership and official correspondence

**Files:** investigation scripts/art under ignored `local/r67-15l-investigation/`; final evidence in `docs/R67_15L_EMOTION_WHEEL.md` and `translations/r67_15l_emotion_wheel.json`.

- [x] Locate every identified PS2 label resource and Japanese label; identify initializer, draw/update consumers, selection tables and resource variants.
- [x] Locate corresponding official PS4 English textures/text and record source file, texture identity, dimensions and hashes.
- [x] Census known direct and indirect callsites/event routes. Record limitations explicitly.
- [x] Establish label-only transfer regions and native selection-to-emotion mapping. Refine implementation interfaces from this evidence before patching.

## Task 2: Implement and verify shared resource localization

**Files:** `tools/r67_15l_emotion_wheel.py`, `tests/test_r67_15l_emotion_wheel.py`, native/coverage test module if needed, provenance manifest from Task 1.

**Interface:** source container bytes plus verified official assets produce same-length localized container bytes and an ownership/provenance report. Exact function signatures follow discovered resource count and existing helper conventions.

- [x] Write regression tests for complete label/variant/position inventory and source hashes; show rejection of unlocalized or mutated resources.
- [x] Implement bounded label replacement, preserving container metadata, PS2 non-label art, palette behavior and native program bytes.
- [x] Exercise all selection IDs/positions and transform states with actual descriptors/native execution where feasible; test mapping preservation and wrong-owner rejection.
- [x] Run targeted tests and produce inspectable atlas/state previews. Record what simulation can and cannot prove.

## Task 3: Build and verify diagnostic release

**Files:** `tools/r67_15l_iso_release.py`, `tests/test_r67_15l_iso_release.py`, `tests/test_r67_15l_release_lock.py`; ignored candidate and reports under `local/`.

- [x] Verify approved k ISO/ELF/art/source locks before generating a new artifact.
- [x] Clone k to a new candidate; replace only exact owned resource bytes, with no prior output overwrite.
- [x] Audit every disc byte against k, requiring zero unexplained modifications and unchanged file extents/lengths unless evidence explicitly requires otherwise.
- [x] Validate candidate executable, approved art, startup, history and native save descriptors; retain documented raw startup `memory_card_8` exception.
- [x] Run complete suite with new-candidate history environment variables and pinned dependency environment; record totals/skips/errors.
- [x] Recheck original k ISO hash and approved source contracts after build.

## Task 4: Document and publish

**Files:** `docs/R67_15L_EMOTION_WHEEL.md`, `docs/R67_15L_HANDOFF.md`, `docs/LOCALIZATION_STATUS.md`.

- [x] Document exact owners, all known callsites/variants, official label mappings, patch scope and static/native coverage limits.
- [x] Add screenshot checklist for representative early/later Emotion Input scenes, every selection position, rotation, selection/confirmation, fades and outcome regression.
- [x] Record diagnostic path/hash, reproduction commands, full-suite/audit results and continuation steps.
- [ ] Commit source/tests/docs, push feature branch and create draft PR targeting main. Attach PR to chat.
- [ ] Provide local ISO deliverable and concise verification report; leave merge pending explicit user approval.

## Progress

- Initial repository clean; remote main matches local main. Created feature branch from main.
- Read k/q/t/y/f/history approval contracts and current localization ledger. k is gameplay approved; ledger's older pending paragraph is stale and will be corrected with attribution.
- PS4 provenance and PS2 native ownership investigations delegated independently to Luna. No implementation review agent will be used per user instruction.
- Resumed 2026-10-21 on the existing feature branch; remote main remains `6a0f1f4`. Prior agents were unavailable, so new Luna workers received the saved findings and disjoint write scopes. Existing builder work was retained.
- Fresh baseline: 18 builder/approved-k tests passed. CLI composition extension subsequently passed 11 builder tests; final installed-artifact tests deliberately require a real candidate and remain pending.
- Agreed interfaces: artwork `apply(old: bytes) -> (bytes, report)`; native coverage `verify(elf: bytes) -> report`; release `prepare()` composes both into the exact `BLBRD/B_GP001.BIN` replacement and evidence.
- Shared resource binding: loader `0x105fe0` resolves group 1 through filename table `0x43a030`, pointer `0x43a034 -> 0x4391f0`, string `BLBRD/B_GP001.BIN`. Installed file offset `0x2ed7a800`, size 603,520. The executable remains unchanged by design.
- Read-only corpus census: 116 grouped graphics containers, 709 TMX names. General parser handles 694 textures in 114 containers; two use unsupported palette forms. A separate raw payload search across all 116 finds each of the four exact wheel palette/pixel signatures only in group 1. This does not exclude transformed or independently authored artwork and is not runtime reachability proof.
- Official wheel artwork uses `HOT` and `COLD`; corpus prose uses `Zeal` and `Apathy`. Ruling: preserve the verified graphic lettering requested by the user, not substitute prose terminology.
- Ruling: accept Luna targeted verification and do not dispatch an implementation reviewer, following the user's explicit routing. Full integrated tests and disc audit still required before publication.
- Toolchain diagnosis: historical preflight ran 756 tests with 13 expected skips and six errors, all from the old kernel's Clang pin. System-selected Xcode now has `2100.3.34.2`; the required `2100.1.1.101` remains in `/Library/Developer/CommandLineTools`. Command-local `DEVELOPER_DIR=/Library/Developer/CommandLineTools` selects it without modifying system settings. All 20 tests in the six affected native/layout modules then passed (`local/r67-15l-toolchain-recheck.log`). No source/approval lock was changed. Final integrated suite still pending.
- Provisional first l build existed after worker integration (ISO SHA `38319eb2ab1dca658377eb7cf226f16760763832fd58c49b630375dc5c8ebc04`, 38,083 changed bytes). Its byte audit passed, but its native report was stale. All four artifacts are preserved unchanged in `local/r67-15l-precoverage-20261021/`, with hashes in that directory's README. Canonical output paths are available for final rebuilding after proof stabilization.
- Further native evidence: scenario constructor `0x25a940` has 15 direct JAL callsites and registers scenario draw `0x25a480` via split immediate reference `0x25aa3c/0x25aa40` and task registration `0x25aa50`. That callback creates emotion task `0x258700` at `0x25a58c`, connecting ordinary scenario owners to the shared wheel.
- Default selector branch `0x153bf4..0x153f74` maps highwords `0x100..0x800` to glow sprites `[88,89,94,95,92,93,90,91]`, hence labels `[JOY,LOVE,SOMBER,GRIEF,COLD,ANGER,AMITY,HOT]`. Default event IDs are `[8,1,2,3,7,5,6,4]`; event branches `0x2581e8,0x258250,0x258400,0x258438,0x258470,0x2584a8,0x2584e0,0x258518` read scenario offsets `+0xa..+0x11`. Labels are mapped through actual texture-8 UVs, not inferred from enumeration order.
- Forced modes: callback `0x1533a4..0x1533d8` selects four plaque resources with `109 + 4*(mode-1) + side`; modes 1..8 cover resource IDs109..140. Completion glow uses `87 + mode` at `0x153fec..0x153ff0`. Nonzero scenario modes retain their own event-slot values; default mode-0 event mappings must not be generalized to them.
- Final artwork acceptance: Japanese-only alpha support is included in paired-plaque mattes; all 16 single-glyph tiles are cleared before English compositing. All 56 drawings are checked. Art suite9/9, combined art/composition21/21, expanded native coverage18/18 pass. Code/proofs frozen for final build. First candidate is superseded by this pixel-support correction as well as expanded evidence.
- Final CLI build passed: ISO `c70dd6e70c9be85c05732bfc3f4fa60ff1c9e7c280470d7ebe9c76c7a7290f94`; complete 2,095,382,528-byte audit, exactly 60,028 changes in group1, zero unexplained. Installed ELF/group4 remain byte-identical to approved k. Independent post-build SHA checks reconfirmed both final l and unchanged k. Full candidate-pinned suite running.
- Corrected atlas previews were regenerated and inspected by the art implementer. These show the expected English plaque/gold/glow regions; they are asset previews, not PCSX2 screenshots or gameplay approval.
- Final verification: focused40/40 pass in24.794s; complete candidate-pinned suite804 tests in234.789s, 791 passed/13 expected historical-fixture skips, zero failures/errors. All l checks ran. Approved52 source/test files and the historical k report remain unchanged. Logs: `local/r67-15l-final-focused.log`, `local/r67-15l-final-suite.log`.
