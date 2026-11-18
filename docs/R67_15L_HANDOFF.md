# r67.15l release and runtime handoff

## State at handoff

The artwork transform, manifest, native proof, tests, and snapshots are
frozen. Native coverage passes **18 tests**. Fresh art-plus-composition checks
pass **21 tests in 15.871 seconds**. The final CLI build completed with exit
code 0. The separate focused release suite passed **40/40** in 24.794 s
(exit 0), including the installed release-lock test; log:
`local/r67-15l-final-focused.log`. The integrated full suite ran **804
tests in 234.789 seconds** (exit 0): 791 passed, 13 expected skips,
and zero failures/errors. The 13 skips are five CVM/KSF/MTX module skips, one
old graphics-port skip, six historical finished-ISO skips (q, t, u, z, a,
and r67.12 history), and one DG13 structural-corpus skip. All new/current
installed-candidate and history-environment checks ran without skips. Log:
`local/r67-15l-final-suite.log`. The frozen-source verification passed: 52
protected k-source files and the historical report are unchanged, and an
independent check confirms the k ISO SHA-256 remains
`ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`.

The existing precoverage artifact set is preserved under
`local/r67-15l-precoverage-20261021/`. Its associated earlier ISO hash,
`38319eb2ab1dca658377eb7cf226f16760763832fd58c49b630375dc5c8ebc04`, is
historical only and is not the final acceptance hash. The final candidate is
`local/r67-candidates/67.15l-emotion-wheel.iso` with SHA-256
`c70dd6e70c9be85c05732bfc3f4fa60ff1c9e7c280470d7ebe9c76c7a7290f94`.
Retain both artifact histories distinctly.

| Final integration field | Value |
|---|---|
| Final ISO path | `local/r67-candidates/67.15l-emotion-wheel.iso` |
| Final ISO SHA-256 | `c70dd6e70c9be85c05732bfc3f4fa60ff1c9e7c280470d7ebe9c76c7a7290f94` |
| Disc size audited | 2,095,382,528 bytes |
| Changed bytes | 60,028, confined to `BLBRD/B_GP001.BIN` (603,520-byte resource) |
| Unexplained changed bytes | 0 |
| Installed ELF | SHA-256 `fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d`; byte-identical to approved k |
| Protected Group 4 | SHA-256 `9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a`; unchanged |
| Startup | 154/155 raw; 155/155 scoped with only `memory_card_8` exception |
| History / saves | 4 history regions; 15 save descriptors; namespace `BISLPM-66511Save`, serial `SLPM-66511` |
| ROFS | 10,656 records; 0 mismatches |
| Art payload SHA-256 | `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee` |
| Main build report / audit / log | `local/r67-15l-emotion-wheel.json` / `local/r67-15l-whole-iso-audit.json` / `local/r67-15l-final-build.log` |
| Full suite | **804 tests PASS** in 234.789 s (exit 0): 791 passed, 13 expected skips, 0 failures/errors; `local/r67-15l-final-suite.log` |
| Separate final focused run | **40/40 PASS** in 24.794 s (exit 0), including installed release-lock test; `local/r67-15l-final-focused.log` |
| Approved k-source lock | 52 protected files and historical report unchanged; independent k ISO SHA-256 check unchanged |
| Final runtime screenshots | **PENDING user review** |

The approved source remains r67.15k, ISO SHA-256
`ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`, with
approved ELF SHA-256
`fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d`. The
r67.15l change is texture-only: retain the installed ELF byte-for-byte and
make no changes to previously locked native code or unrelated artwork.

## Static native and art map

The independent [native coverage record](R67_15L_NATIVE_COVERAGE.md) is the
authority for the ELF anchors, resource descriptors, bounded execution
results, and remaining reachability limits. Its current proof has 18 passing
tests. Key findings for runtime observation:

- The scenario constructor at `0x25a940` has 15 direct call sites. The
  registered callback path reaches `0x25a480`, creates the task at `0x258700`,
  installs callback `0x258040`, and reaches the wheel constructor at `0x154980`
  using shared Group 1 resources. The complete pinned call-site list is
  `scenario_constructor_direct_callers` in
  [`translations/r67_15l_native_coverage.json`](../translations/r67_15l_native_coverage.json).
- Group 1 contains 146 descriptors and 820 frames. The art transform covers
  the paired, gold, and glow wheel resources only; see the [art record](R67_15L_EMOTION_WHEEL.md)
  for source hashes, pixel ownership, and Japanese-pixel clearing rules.
- Default selection slots map in native order to `JOY`, `LOVE`, `SOMBER`,
  `GRIEF`, `COLD`, `ANGER`, `AMITY`, `HOT`, with event IDs
  `8, 1, 2, 3, 7, 5, 6, 4`. The eight native wheel positions are:

  | Position | Coordinates | Default label | Event ID |
  |---:|---:|---|---:|
  | 1 | `(257, 311)` | JOY | 8 |
  | 2 | `(257, 281)` | LOVE | 1 |
  | 3 | `(227, 341)` | SOMBER | 2 |
  | 4 | `(197, 341)` | GRIEF | 3 |
  | 5 | `(257, 371)` | COLD | 7 |
  | 6 | `(257, 401)` | ANGER | 5 |
  | 7 | `(287, 341)` | AMITY | 6 |
  | 8 | `(317, 341)` | HOT | 4 |

- Forced scenario modes `1..8` select paired-plaque resource IDs
  `109 + 4 * (mode - 1) + side` and glow resource ID `87 + mode`. Preserve
  caller-provided scenario slots in forced modes; do not apply the default
  label/event crosswalk to them.
- Static call-site and callback evidence does not close every indirect event
  route. There is no complete game-runtime claim. Do not infer additional
  reachable scenes or scenarios from the static census.

## Runtime acceptance checklist

Use only the final ISO whose exact SHA-256 is recorded above. Capture and
retain screenshots with the ISO hash and scene/context recorded. If the final
hash is not available, runtime acceptance has not started.

- [ ] In normal mode, inspect all eight positions and confirm the expected
  default label order, legibility, placement, and selection response.
- [ ] Wherever reachable, exercise forced modes `1..8`; verify the mode's
  paired-plaque and glow variants and confirm custom scenario slots are kept.
- [ ] Check no-command and timeout states, including transitions into and out
  of the wheel.
- [ ] Check gold and glow single-label art, paired plaques, selection fades,
  close/reopen behavior, and repeated opens.
- [ ] Capture coverage in multiple early and later gameplay scenes. Record
  the actual scene names observed; do not invent scenario names to fill gaps.
- [ ] Regression-check prior accepted surfaces: Item Details for ammo,
  grenade, weapon, and longest-name cases; Isis inscription reveal, settle,
  and reopen; HANT scrolling; and the Aqua Regia next-area transition.
- [ ] Review the screenshots against the final ISO hash and record the user's
  explicit acceptance or remaining defects.

Static verification and native coverage do not satisfy this checklist. No
PCSX2 runtime approval is claimed until the user reviews screenshots from the
hash-pinned final ISO.

## Reproduction environment and integration gate

The pinned runner uses `DEVELOPER_DIR=/Library/Developer/CommandLineTools`,
Python 3.14.7 at `/opt/homebrew/bin/python3.14`, Pillow 13.0.0, NumPy 2.5.4,
Unicorn 2.1.4, Capstone 5.0.9, opencv-python-headless 5.0.0.93, UnityPy
1.25.4, llvmlite 0.50.0, and pyelftools 0.33. Use the exact runner recorded
by the main integration report for reproducibility; do not substitute a
different environment when recording final metrics.

The release CLI completed exact-size ISO composition and whole-disc audit.
`tests/test_r67_15l_release_lock.py` pins the final candidate hash. The
integrated suite passed with the final ISO/ELF fixtures: **804 tests in
234.789 s**, 791 executed passing, 13 expected skips, and zero
failures/errors. The focused release suite passed **40/40** in 24.794 s
(exit 0), including the installed release-lock test. Runtime screenshots and
visual/gameplay approval remain pending.

The main agent is preparing the draft PR and will handle adding its URL to the
handoff. Do not merge or claim gameplay approval until the user explicitly
signs off after reviewing screenshots captured from the exact-hash ISO.
Preserve the earlier precoverage artifacts and all approved k baselines.
