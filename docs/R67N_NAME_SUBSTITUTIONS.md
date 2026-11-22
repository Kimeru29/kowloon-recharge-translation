# Installed ADV name repair

Baseline is the r67.15m cumulative image, SHA-256 3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f. These are overlays on that image. No native patches, game state or emulator session were used.

| Relationship and installed status | Files | (px) | (pm1) | (pn1) |
|---|---:|---:|---:|---:|
| Exact scripts repaired | 294 | 1,047 | 87 | 81 |
| Historical structural scripts repaired | 3 | 53 | 10 | 10 |
| Exact scripts already native | 21 | 437 | 49 | 31 |
| Structural scripts already native | 6 | 245 | 40 | 24 |
| Structural scripts still original in m | 4 | 112 | 22 | 9 |

The four still-original files also contain one occurrence each of (pmyh) and (pnyh). Other script-transfer work can independently change those four. Original status applies to the inspected m baseline.

**297 repaired MTX payloads, 1,288 native name substitutions restored.** The three structural repairs are DG/DG13_02 (11), FN/FN13_16 (5) and MS/MS05_03 (57). Prior source/target ranges from the archived structural report and r67m manifest were pinned by SHA-256. For structural files a complete historical output hash and byte-identical replay of that output were both required. No Japanese text was realigned for this repair. Localized English references are emitted in their official position. The native semantic evidence and the checks for cross-line movement are in dynamic.md.

The encoder computes legacy literal and modern native variants and their exact per-entry positions, then checks both descriptions of the edit. It applies only the identified literal byte ranges to the legacy installed payload and verifies each resulting pointer region against the canonical native build. The two may differ in NUL padding after the terminal underscore when a historic file had already acquired alignment bytes. The canonical result keeps the source-replay padding. All other bytes of each region and all pointer slots and aliases must match. An unrecognized installed preimage aborts. The report records the PS2/PS4/DC, installed and output hashes for replayed assets.

**Artifacts:** `local/r67n-names-final/overlay/ADV/` and `local/r67n-names-final/report.json` (SHA-256 78fdd32978298c5e69838781aa6d370e4ca5b8c1541bf471da5f5c795789cf56). A second fresh run produced identical overlay and report files. The earlier exact-only run is superseded. Direct occurrence reads confirmed all 1,288 controls in the emitted resources. The JSON contains offsets for 70,092 groups in 324 replayed assets. For every represented official DC entry, `groups[].lines[]` gives its original key and final byte offset. `source_start/end` refer to the PS4 text group. `legacy_start` and `output_start/end` refer to their respective rebuilt resources. Every macro occurrence identifies the original group, key, legacy/installed/output offsets, source spelling and native control. No corpus text appears in the source code or generated JSON.

The command, from the r67m integration worktree, requires a new output directory.

```bash
local/r67m-integration/venv314/bin/python -m tools.r67n_names \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --baseline-iso local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso \
  --historical-report /Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/startup-flow-v10/local/structural-import-report.json \
  --output-dir local/r67n-names-reproduction

local/r67m-integration/venv314/bin/python -m unittest \
  tests.test_r67n_names tests.test_localization tests.test_exact_import tests.test_structural_import
```

26 tests passed, including five focused name tests covering full-name order, line movement, external speaker selection control in a source without any such opcode, duplicate pointer aliases, structural clusters, missing ownership, installed/source drift, unsupported macros and binary replay. Actual custom-name display, fit and all possible speaker selections remain unobserved in this session.
