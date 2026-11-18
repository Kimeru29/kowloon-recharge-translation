# r67.15m cumulative script + emotion-wheel diagnostic

## Candidate and acceptance boundary

This integration starts from the gameplay-approved **r67.15k** image, retains its
accepted native/UI changes, installs **28 additional MTX files / 33,801 official
English entries**, and includes the exact **r67.15l emotion-wheel artwork**.
It supersedes the v9-based r67m diagnostic as the cumulative test candidate.
Historical images and reports are preserved. This is **not gameplay approved**.

- Candidate: `local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso`
- SHA-256: `3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f`
- Size: 2,095,382,528 bytes.
- Base k ISO: `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`.
- Installed ELF: `089fcd47143d37d70ad7f809e7e70f13fa49587777baa8b845398c77946d487c`.
  Its only logical changes from approved k are the exact script ROFS size/extent
  fields. Native code, translated native text, and all other ELF bytes are kept.
- Installed wheel payload: `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee`.
- Group 4: `9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a`.

## What changed

### Localization groups and substitutions

Synthetic DC keys must enumerate consecutive English-line indices. A CP932
boundary alone does not establish a continuation. The parser rejects duplicate
keys, control delimiters consumed as continuations, and independent pointer
entry points consumed by grouping. The actual two-byte-source patterns contain
anchor+1 and anchor+2; the copied Opus regression that skipped anchor+1 was
corrected in this isolated checkout, with the original v9 edits preserved.

The new scripts contain 682 `(px)`, 55 `(pn1)`, and 89 `(pm1)` placeholders.
The old encoder would have rendered their full-width literal spellings. These
now emit the corresponding native `px`, `pn`, and `pm` source controls, in the
English order, with ordinary text still restricted to the two-byte glyph bank.
Each control must exist on a CP932 boundary in the matched source asset.
Unproven macros fail closed. The field/control correspondence is static;
custom-name rendering remains a runtime acceptance checkpoint.

### Structural correspondence

The blanket digit-stripping fallback has been removed. Six newly recovered
short labels use unique exact context: an exact matching block containing the
entire span must occur exactly once in each source, extend at least 64 bytes
beyond the span in total, and contain at least 32 high-bit source bytes. No
numeric command operands are rewritten. The historical inserted-prefix
exception is restricted to the source's first text span.

Per-file source/DC/output hashes, synthetic groups and all structural span
coordinates are recorded in `translations/r67m_script_transfer.json`.

### Cumulative composition and executable placement

Only the 28 newly supported scripts are installed. Each must still equal the
pristine PS2 bytes in k before replacement. Existing translated scripts,
accepted overrides, KSF files, and all unrelated resources are retained.

A regression exposed an old builder assumption: k already stores its enlarged
ELF after DATA.CVM. Growing the container could overwrite appended script data
with that executable. The builder now retains the ELF's shifted tail allocation;
its exact patched bytes are verified separately from untouched tail payloads.

The wheel transform is reused without alterations and installed byte-for-byte,
covering GP001_02, GP001_03, GP001_08, GP001_10 and all 56 label drawings.

## Coverage

| MTX class | Installed files | Official DC entries |
|---|---:|---:|
| Existing exact + new exact | 984 | 77,020 |
| Existing structural + new structural | 13 | 15,707 |
| Total | 997 | 92,727 |
| New files in this candidate | 28 | 33,801 |

These are asset/DC-entry counts, not visible dialogue-line counts or a whole-game
translation percentage. The existing 868 fitting KSF entries are inherited;
no KSF capacity or relocation policy changes in this integration. Existing translated
MTX resources are also retained byte-for-byte. The new placeholder handling is
installed in the 28 new files; it does not retroactively repair literal name
placeholders in older translations. Those require a separate installed-content
inventory before claiming complete substitution coverage.

Unresolved: FN02_31's 1,294 dynamic entries; five structural files / 5,648 entries;
25 remaining FD00 templates; 48 KSF overflow and 4 ambiguous fields; unmatched
PS2-only content. The five structural files are MS00_01, MS01_00, MS01_03,
MS06_03, and MS13_02. MS01_03 also contains unproven name macros. Near-complete
files remain rejected as whole files; no partial-emission policy was introduced.

The 449 PS2-only-file count does **not** establish that 449 files require new
translation. A historical lexical proxy found 419 novel runs / 3,672 Japanese
characters. Reused text and actual untranslated occurrences still need matching;
this integration makes no claim to have completed that inventory.

## Validation

The independent whole-image auditor derives exact writes from k's inventory and
the overlay, without trusting the build report or broad container allowances.
It checks every byte, including relocation padding, metadata and native ELF
bytes. Mutation tests reject changes inside translated payloads, outside all
owned writes, and inside ELF allocation outside exact ROFS fields.

- Whole image: 2,095,382,528 bytes compared; 8,289,562 changed; **0 unexplained**.
- 29 resource overlays: 28 MTX + one wheel container; no overlay collisions.
- DATA.CVM grows by 654 sectors; the outer tail/ELF move accordingly.
- All 10,656 runtime ROFS records match installed data.
- Startup: raw 154/155; scoped 155/155 with the existing bounded `memory_card_8`
  exception checked against k, not a new exception.
- Four history lock regions and all 15 save descriptors preserved.
- Source hashes and the 52-file k producer lock verified.
- Repeated builds produce the same ISO SHA-256.

Final suite: **842 tests run in 237.037 seconds; 835 passed, 7 historical skips,
zero failures/errors**. All new installed-candidate/source checks ran. The seven
skips cover one old graphics-port report and historical q/t/u/z/a/r67.12 ISO
fixtures. Exact skip names and source checks are recorded in
`local/r67m-integration/validation-summary.json`.
The initial Python 3.12 run had missing-fixture errors and could not decompress
archived zstd savestates. The documented Python 3.14.7 dependency environment
was restored in an isolated venv, with owned fixture/source aliases supplied;
that initial failed run is retained for diagnosis, not counted as acceptance.

## Reproduction

Use the isolated integration checkout and its Python 3.14.7 venv. Pin dependencies
from `local/r67m-integration/runtime314-packages.txt`. `DEVELOPER_DIR` must select
`/Library/Developer/CommandLineTools` for native compilation.

Regenerate with `tools.import_exact_mtx` and `tools.import_structural_mtx` using
the owned PS2/PS4 ADV roots. Use a fresh output directory for each run. The
structural importer requires `--allow-template-path FD/FD00_31.MTX`. The release
entry point takes paths to the generated outputs and their reports; the exact
reproduction command is retained in `local/r67m-integration/reproduce.sh`.

```bash
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
PYTHONDONTWRITEBYTECODE=1 \
local/r67m-integration/venv314/bin/python -m tools.r67m_cumulative \
  --output-dir local/r67m-integration/another-unique-build \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --baseline-reports /Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/startup-flow-v10/local \
  --regenerated local/r67m-integration
```

The release expects the fresh reports `exact-report-v2.json` and
`structural-report-v2.json`, and their `exact-mtx-v2`/`structural-mtx-v2` outputs.
Sources under `/private/tmp` can disappear; recover them from the owned ISO/PKG
and verify hashes. Existing outputs must not be overwritten.

## Runtime checklist

No emulator was launched. No card, savestate, emulator setting, commit, push,
publication, or merge was performed.

- Cold-boot this exact candidate and confirm accepted startup, horizontal ADV,
  HANT, AFK/L1, Item Details wrapping and Isis inspection behavior.
- Exercise ordinary and forced emotion-wheel modes, all positions, selection,
  confirmation, fade, timeout and repeated opens in early and later scenes.
- Use custom player names and verify `px`/`pn`/`pm` substitutions and punctuation.
- Exercise the new MS/FN/FD scripts across chapters and relevant choices/branches.
- Inspect long messages, page transitions, speaker associations and choice outcomes.
- Inspect eight long scene-title cards in MS02_02 and MS11_03, listed by source
  anchor in `local/r67m-integration/layout-preflight.json`. They have 41–42
  estimated cells; their actual renderer must be observed before calling them
  clipped or applying reflow. All new DC groups have at most three English rows.
- Save/load ordinary memory-card saves and check progression; static identity
  checks do not prove complete cross-release save compatibility.

Retain r67.15k as the gameplay-approved fallback. Obtain explicit user acceptance
of screenshots/gameplay from the new hash before promoting this candidate.
