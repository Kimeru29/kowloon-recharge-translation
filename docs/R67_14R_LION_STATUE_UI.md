# r67.14r — Lion Statue acquisition / PUSH item-name fit (DIAGNOSTIC)

**Status: pending Pablo's cold-boot gameplay screenshots and explicit visual approval.**
Neither compatibility nor final release is approved. Nothing has been
committed/pushed; no PR has been created or merged for this branch.

## Provenance and Git

- Repository: `~/repos/kowloon-recharge-translation`
- Worktree: `~/repos/kowloon-recharge-translation/.worktrees/first-save-r67`
- Branch: `fix/67.14r-lion-statue-ui`, created directly from
  `origin/main` = `1655eaf9756993457bca04b9bae004b38f771958`,
  which includes merged PRs #36–#42 and the locked r67.14q baseline.
- Older `fix/67.06-renderer-corrections` branch was not rewritten.
- Permanently preserved approved r67.14q ELF:
  `local/r67-14q-opening-final-line-fit.elf`,
  SHA-256 `c3babe784c07f83312273ac789040b74ea46d492eea48eee0f1ae17ce5c781ba`.
- Permanently preserved approved r67.14q ISO:
  `local/r67-candidates/67.14q-opening-final-line-fit.iso`,
  SHA-256 `3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96`.

## Two independent verified native text owners

1. **Vase item acquisition** — `M_ObjGetDraw` at VA `0x2A23E0`:
   item catalog getter `jal 0x134AB0` at VA `0x2A2A5C`,
   then `jal 0x18A080` at VA **`0x2A2A6C`** with its
   acquisition-popup text object in `$a0` and item name in `$a1`.
2. **Dungeon item-use / Stone Pillar PUSH selection** —
   item catalog getter `jal 0x134AB0` at VA `0x2A6050`,
   then a **separate** `jal 0x18A080` at VA **`0x2A6060`**
   with the item-selection text object in `$a0`.
   Not the unrelated L1/R1 Change target call at `0x2A6AF8`.
3. The shared native item-name lookup at `0x134AB0` reads the original
   catalog table VA `0x491234`; entry ID 413 at ELF offset
   `0x391928` points to translated **`Lion Statue`** at VA
   `0x92CBCA`. Neither this pointer nor the text is edited.
4. The native text-object pair-scale method `0x18B120` writes
   `$f12` to object X scale at `0x48` and `$f13` to Y scale
   at `0x4C`, and updates layout. The two callsites are patched to
   one private helper which first invokes the original native name setter
   `0x18A080` unchanged, then **only if the original input pointer
   equals exactly `0x92CBCA`** invokes `0x18B120` with
   `X=0.78` and `Y=1.0`.
   The 0.78 horizontal fit is a testable layout hypothesis, not a claim
   of confirmed on-screen rendering. Other item names remain unchanged.

## Implementation and candidate

- Patch source: `tools/r67_lion_statue_ui.py`
- ISO patch: `tools/r67_lion_statue_iso_patch.py`
- Whole-ISO audit: `tools/r67_lion_statue_iso_delta.py`
- Regression tests: `tests/test_r67_lion_statue_ui.py`
- Diagnostic staged ELF: `local/r67-14r-lion-statue-ui.elf`;
  SHA-256 `55c7a2041909d22f1fb109d280c75b6e29cdad6cf3531626401409242245091c`.
- Diagnostic finished ISO:
  `local/r67-candidates/67.14r-lion-statue-ui.iso`;
  SHA-256 `80722883fc688a482a68821b34a75d2e97d95c1ef7940535e31f4ffdc265a7ed`.
- Candidate embedded ELF SHA-256:
  `81c3c229c828bf5067749c4e6f0836cd2c8861f022fdf6c0b5b3a4003527eaa0`.
- ELF stage report: `local/r67-14r-lion-statue-ui-report.json`
- ISO report: `local/r67-14r-iso-patch-report.json`
- ISO build manifest: `local/r67-14r-build.json`
- Byte audit: `local/r67-14r-whole-iso-audit.json`
- Startup: `local/r67-14r-startup-final.json`
- Baseline native instruction bytes and original SHA are fail-closed checks.
  The original approved ISO is never edited or overwritten. The new
  translated ELF is size-compatible within the same ISO sector allocation,
  so the original ROFS records are retained exactly.

## Current static validation evidence

- `r67_14q_approved_lock --elf`: PASS.
- `r67_14q_approved_lock --iso --build-report`: PASS.
- `r67_history_layout_lock --elf`: PASS (4/4).
- `r67_history_layout_lock --iso`: PASS (4/4).
- Startup acceptance: **155/155** from finished ISO.
- Full Python regression suite: **380 tests successful, 18 expected skips**;
  retained transcript: `local/r67-14r-full-regression.log`.
- Save compatibility unit tests: **6/6 passed**, but runtime transfer remains unverified.
  Immutable-source read-only card hashes and outstanding runtime gates are
  recorded at `local/save-compat/r67-14r-lion-statue-diagnostic/compatibility-status.json`.
- Exhaustive whole-ISO comparison against approved q: **0 unexpected bytes**.
  Exact changed-byte classification:
  - ELF PT_LOAD size: 2 bytes.
  - ISO9660 ELF file size (LE/BE): 2 bytes.
  - Acquisition name setter JAL: 3 bytes.
  - PUSH selection name setter JAL: 3 bytes.
  - New appended alignment/private helper: 75 nonzero changed bytes
    among 115 newly occupied bytes.
  All `DATA.CVM` contents and the non-target executable remain unchanged.

**Graphics fixture nuance:** The older `local/r67-acceptance-graphics`
folder's symlink to `B_GP020.BIN` no longer matched q's approved rendered
asset, causing an initial 153/155 false failure. For the final
155/155 check a unique `local/r67-14r-acceptance-graphics` directory was
made: same 31 existing reference paths with `B_GP020.BIN` extracted
**read-only from approved r67.14q ISO**, checked against the original
build-report SHA-256
`d18a05bc7d3952a100c3c4f5efc499f076b9c92716a5c2942a3aab0f80ccebc7`.
The original symlink, graphics assets and ISO are unchanged.

## Mandatory outstanding gameplay and compatibility gates

Pablo must cold-boot the r67.14r ISO and provide screenshots demonstrating:
(1) full `Lion Statue` visibly inside its original acquisition-title box
after breaking the vase, and (2) full `Lion Statue` text next to `PUSH`
without clipping at the Stone Pillar. The original green/blue companion
dialogue and AFK must remain correct; the Stone Pedestal interaction must
still work. Static checks are not a substitute.

Preserve `SLPM-66511` and `BISLPM-66511Save`; no save serialization,
story flags or inventory IDs are changed. Never substitute PCSX2 `*.p2s`
savestates as cross-release proofs. No real Soul Well golden save has yet
been identified. The current original memory cards were inspected read-only,
not snapshotted/replaced. A future offline golden checkpoint must use
`tools.save_compatibility snapshot/verify` only when PCSX2 is closed,
with disposable copies under unique `local/save-compat/` directories.
Runtime compatibility requires load comparison in q versus r, meaningful
transition, normal save, cold restart/reload and user signoff. **Status:
NOT RUNTIME VERIFIED.**

No commit, push, PR or merge until user gameplay approval. After that,
record screenshot evidence and promote via PR targeting main, merging
only with explicit approval.
