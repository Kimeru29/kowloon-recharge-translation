# r67m AI continuation handoff

## What was done

This session implemented two improvements to the Kowloon re-charge PS2 English
translation script-transfer tooling, recovering significant additional content
from the official PS4 remaster.

### 1. CP932-boundary DC key merge (`tools/localization.py`)

**Problem:** The DC localization maps from the PS4 remaster sometimes place
consecutive keys where the first byte is a single-byte MTX control token
(`l`, `p`, `N`) or a two-byte CP932 character, and the next key is at the
immediately following CP932 boundary. Both keys fall on valid boundaries, so
the grouping logic incorrectly split them into separate groups — creating a
tiny 1–2 byte group that could never find a terminator marker.

**Fix:** In `DcLocalization.from_json`, when building the grouped list, if
a boundary-aligned key is exactly at the next CP932 boundary after the
previous anchor, treat it as a synthetic continuation rather than a new
group. The check uses the first byte at the previous anchor to determine
whether it's a 1-byte or 2-byte CP932 character.

**Impact:** +22 exact MTX files (+20,378 entries), +3 additional structural
MTX files enabled by the same fix.

**Tests:** Three new tests in `tests/test_exact_import.py`:
- `test_merges_single_byte_control_prefix_with_following_key`
- `test_merges_two_byte_cp932_prefix_with_following_key`
- `test_rejects_when_merge_causes_wrong_terminator_position`

### 2. Relaxed numeric context for structural imports (`tools/structural_import.py`)

**Problem:** Structurally changed scripts have speaker-name tags (e.g.,
`【Yachiho】`) that are byte-identical between PS2 and PS4, but the
surrounding control command parameters contain different scene/chapter
numbers (e.g., `cf99escf97afew95` vs `cf97escf99afew95`). The strict
boundary-context comparison rejected these mappings.

**Fix:** Added `_strip_digits` and `_boundary_context_matches_relaxed`
functions. For direct-mapped groups where the text content is byte-identical,
a relaxed context check normalizes numeric parameters in control sequences.
This is only applied when `allow_relaxed_context=True` AND the text span
content is verified byte-identical — never for semantic/approximate matches.

**Impact:** +3 structural MTX files (MS/MS08_01, MS/MS11_01, MS/MS12_01)
totaling +7,362 entries.

## Current state

| Metric | v9 baseline | r67m diagnostic | Delta |
|---|---:|---:|---:|
| Exact MTX files | 962 | 984 | +22 |
| Exact MTX entries | 56,642 | 77,020 | +20,378 |
| Structural MTX files | 7 | 13 | +6 |
| Structural MTX entries | 2,284 | 15,707 | +13,423 |
| KSF fit entries | 868 | 868 | 0 |
| Total overlay files | 1,144 | 1,173 | +29 |
| Total script entries | 58,926 | 92,727 | +33,801 |
| Startup acceptance | 121/121 | 121/121 | 0 |
| Test suite | 130 | 133 | +3 |

## Source paths

- Pristine PS2 ISO: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
  (SHA-256: `29e305e3...`, extracted from 7z on external drive)
- PS2 ADV: `/private/tmp/khc-ps2-assets/ADV` (1,516 MTX + 1,516 KSF)
- PS4 recovery: `.worktrees/first-save-r67/local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/`
  (symlinked to `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/`)
- CVM payload: `/private/tmp/kowloon-recharge-inspect/DATA_payload.iso`
- Diagnostic ISO: `/private/tmp/kowloon-recharge-r67m-diagnostic.iso`

All `/private/tmp` paths may be cleaned by macOS. Re-extract from the
archive and ISO using the documented extraction commands in `docs/BUILD.md`.

## Worktree preservation

- Main tree (`fix/startup-title-atlas-v9`): Modified `tools/localization.py`,
  `tools/structural_import.py`, `tests/test_exact_import.py`. Clean working
  state except these three changed files.
- `first-save-r67` worktree (`feat/67.15l-emotion-wheel`): Staged but
  uncommitted r67.15l work preserved. Not touched by this session.
- r67.15k approved baseline: ISO SHA-256 `ad706667...` verified intact at
  `.worktrees/first-save-r67/local/r67-candidates/67.15k-description-word-wrap.iso`.

## What remains unresolved

### Near-complete files (high potential for recovery)

1. **MS/MS01_00.MTX** (2,541 entries): 2,505/2,506 groups proven. One group
   at anchor 19092 genuinely differs between PS2 and PS4. A safe partial-
   emission policy or manual override for this single group would recover
   the entire file. Total potential: 2,541 entries.

2. **MS/MS06_03.MTX** (1,734 entries): 1,664/1,693 groups proven (98.3%).
   The 29 unresolved groups need per-anchor investigation.

3. **MS/MS13_02.MTX** (1,104 entries): 1,070/1,101 groups proven (97.2%).
   The 31 unresolved groups need per-anchor investigation.

### Fundamentally different structures

4. **MS/MS00_01.MTX** (43 entries): All groups fail. Different structure.
5. **MS/MS01_03.MTX** (226 entries): All groups fail. Different structure.
6. **FN/FN02_31.MTX** (1,294 entries): Indirect/dynamic localization table.

### Template families

7. **FD00 templates** (25 files, ~725 entries): PS4 uses shared templates
   that don't match PS2's per-character scripts.

### KSF

8. **48 overflow entries**: Official text 1–11 bytes too long for fixed KSF
   fields. Format relocation semantics unproven.
9. **4 ambiguous entries**: Fullwidth-space placeholders, not real text.

### PS2-only content

10. **449 PS2-only files**: No PS4 counterpart. 419 novel Japanese lexical
    runs / 3,672 characters by deduplication proxy.

## Recommended next steps

1. **Partial structural emission**: For files with 95%+ proven groups,
   investigate whether leaving the unproven groups in Japanese is safe.
   MS01_00 (99.96% proven) is the strongest candidate.

2. **Per-anchor investigation for MS06_03 and MS13_02**: Check if the
   unresolved groups share a common pattern that can be addressed.

3. **KSF overflow research**: For the 48 entries with small overflows
   (1–6 bytes), investigate whether field capacity bounds are too
   conservative or whether safe truncation/abbreviation exists.

4. **Runtime testing**: The r67m diagnostic ISO should be tested with
   PCSX2 to verify all translated content renders correctly, especially
   the newly imported MS-series files.

5. **Integration with r67.15k/15l**: After runtime validation, merge
   these tooling improvements into the release pipeline.

## Files changed (relative to `fix/startup-title-atlas-v9`)

```
M tools/localization.py          # CP932-boundary DC key merge
M tools/structural_import.py     # Relaxed numeric context + strip_digits
M tests/test_exact_import.py     # Three new merge tests
A docs/R67M_DIAGNOSTIC_REPORT.md # Coverage report
A docs/R67M_HANDOFF.md           # This file
```

## Generated local artifacts

```
local/exact-mtx/                 # 984 translated MTX files
local/exact-ksf/                 # 144 translated KSF files
local/structural-mtx/            # 13 translated structural MTX files
local/exact-import-report.json   # Exact import report
local/ksf-report.json            # KSF import report
local/structural-import-report.json  # Structural import report
local/r67m-build-report.json     # ISO build report
local/r67m-acceptance-report.json    # Startup acceptance report
local/r67m-coverage-inventory.json   # Machine-readable coverage inventory
```
