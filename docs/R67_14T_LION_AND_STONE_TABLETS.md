# r67.14t — Lion Statue final fit + game-wide Stone tablet inscription-width gate

**Status: diagnostic only; Pablo's gameplay screenshots and explicit approval are required.**
No PR, commit, push, merge, PCSX2-session modification, savestate rewrite, or
memory-card modification has been performed for this candidate.

## Workflow and provenance

- Worktree: `~/repos/kowloon-recharge-translation/.worktrees/first-save-r67`
- Working branch: `fix/67.14r-lion-statue-ui` from merged `origin/main`
  `1655eaf9756993457bca04b9bae004b38f771958`.
- Permanent approved **r67.14q** baseline:
  `local/r67-candidates/67.14q-opening-final-line-fit.iso`
  SHA-256 `3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96`.
- Prior diagnostics **r67.14r** and **r67.14s** were not overwritten.
- Combined diagnostic **r67.14t**:
  `local/r67-candidates/67.14t-lion-statue-and-tablets.iso`
  SHA-256 `03526a1779822ad1ec15136c26ff8c3b50d6997bb395a601db228b3fc2fe321f`.
- Staged candidate ELF:
  `local/r67-14t-lion-and-tablets.elf`
  SHA-256 `062689efed67a83f24f7524cedb50a21505ce6431f456fc196961d98cd434a3d`.
- Embedded finished ELF:
  SHA-256 `f29cb00fa819bdcc82b91d62f889c09f547ad4811f734295c7843a8cb080518a`.

### 1. Lion Statue popup title / PUSH item caption

The r67.14r native item ID 413 string-pointer guard, two private callsite
wrappers and their original native text setter are preserved. The only final
adjustment in r67.14s is **horizontal scale 0.78 → 0.72**, targeting the
pixel-overlap Pablo showed at the right edge of the acquisition rectangle.
The screenshot of r67.14r showed a substantially improved but not yet fully
enclosed last letter. The 0.72 candidate awaits a new screenshot; no visual
success is inferred from numeric fit. The physical Lion inspection,
shared catalogue spelling **Lion Statue**, AFK/automatic comments, approved
green/blue dialogue geometry, original popup sprite, history and save logic
remain untouched.

- Source `tools/r67_14s_lion_final_fit.py`.
- Only 3 original native ELF bytes altered relative to r67.14r, at
  `0x86425c`, `0x864260`, `0x864261`.
- The r67.14s intermediate ISO was preserved separately.

### 2. Game-wide Stone tablet policy (not a global font-renderer hack)

Static inspection of the executable proved that all 58 native Stone tablet
object records use the exact translated title VA `0x962C7A`, with original
record schema containing title, description, up to three inscription text rows,
and fixed end marker `0x962C94`.

There are **58 game-wide records / 160 populated inscription rows** in the
currently shipped executable. The longest surviving original PS2 Japanese row
is 21 full-width glyphs. The earlier, visually accepted Chamber inscription
also uses short lines. To prevent remaster English rows from overflowing
this narrower PS2 interface, the translation-side invariant now:

1. Discovers all 58 native Stone tablet records by exact shared title pointer.
   The count and record schema are fail-closed: missing/reclassified tablet
   records invalidate the candidate.
2. Decodes and validates **every populated inscription row**, not only the
   one visible after the first fight.
3. Rejects any inscription row containing more than **21 CP932 full-width
   glyph cells**, and checks row count remains 160.
4. Retains all original native record row slots, headers, string source
   pointers outside the changed six rows, quotation markers and story flags.
5. Provides a reusable `--check-elf` / `--check-iso --build-report` gate.
   Future translations of any of these 58 tablets MUST pass this gate.

The two early Door-of-Anubis tablets contained exactly six violating lines
(29–33 visible CP932 characters, except one 24-cell line). Those six
inscription-row pointers alone were redirected to shorter equivalent puzzle
instructions, preserving original leading spaces and PS2 0xEEFC quote markers:

- Alignment clue: **Nether gods face / south at sunrise; / heaven's isle rises**.
  Original meaning: face the row of nether gods south from the sunrise to
  make an island leading to heaven emerge.
- Western clue: **The bowed one / walks west, finds / the mercy of God.**
  Original meaning: the one with the lowered head who walks west receives
  God's mercy.

The original `Stone tablet` title, `Egyptian writing.` descriptor, two
existing scripts' row cardinality, 56 unrelated tablet records and all other
object text owners are byte-identical. No generic game-dialogue glyph renderer
was modified. There is no claim that the game can automatically wrap or
scale *unknown future tablet types*: this is a tested, data-class-wide
width gate for all 58 existing native Stone tablet records, applied whenever
new translations are released.

- Patch: `tools/r67_14t_stone_tablet_fit.py`.
- Reusable guards:
  `python3 -m tools.r67_14t_stone_tablet_fit --check-elf local/<candidate>.elf`;
  `python3 -m tools.r67_14t_stone_tablet_fit --check-iso local/r67-candidates/<candidate>.iso --build-report local/<candidate>-build.json`.
- Tests `tests/test_r67_14t_stone_tablet_fit.py` include whole-class coverage,
  missing owner rejection, an overwide translation mutation, source
  fail-closed input and six exact owner offsets.

## Release gates / evidence

- Full source approval lock on candidate staged ELF: **PASS**;
  on installed ISO ELF: **PASS**. All four protected r67.14q code regions,
  16 native words, and two approved dialogue lines were preserved.
- History locks: **4/4** on staged ELF and installed ISO.
- Startup final ISO acceptance: **155/155**.
- Explicit Stone tablet fit gate: **58/58 records, 160/160 rows**, zero overwide
  rows. Runs independently on staged ELF and finished ISO.
- Complete 2GB finished-ISO audit against SHA-pinned r67.14q:
  **zero unclassified modified bytes**, only the two Lion code callsites,
  the six inscription pointer owners, appended private helper/English
  strings, PT_LOAD size and ISO9660 ELF-record size changed. No DATA.CVM,
  unrelated ELF regions, scripts, inventories or save structures changed.
- Full Python regression suite: **389 tests passed, 18 expected skips**;
  log: `local/r67-14t-full-regression-final.log`.
- ISO release reports:
  `local/r67-14t-tablet-fit-report.json`,
  `local/r67-14t-iso-report.json`,
  `local/r67-14t-build.json`,
  `local/r67-14t-whole-iso-audit.json`,
  `local/r67-14t-startup.json`,
  `local/r67-14t-tablet-elf-gate.json`,
  `local/r67-14t-tablet-iso-gate.json`.

### Baseline-preservation incident (do not conceal)

During the audit at approximately 2026-10-11 17:27–17:29 local, the previously
present r67.14q ISO and various older archived candidate ISO files were found
absent from `local/r67-candidates/`. The current tool workflow had not issued
a deletion or cleanup command. The reason for the disappearance **has not been
established**, and missing unrelated historical archives were NOT silently
considered recovered.

To honor the approved immutable baseline, the missing r67.14q ISO was rebuilt
in a NEW temporary copy, by reversing exactly the recorded and SHA-pinned
r67.14q→r67.14r delta from the still-present r67.14r candidate. The
temporary clone's **entire 2GB SHA-256 matched the original approved q
SHA exactly**, including its post-ROFS executable and all resources, before
it was placed back into the absent original q pathname. No existing q file was
overwritten. The next complete q→t ISO audit ran successfully against the
verified restored q. The older unrelated missing release files are an
outstanding artifact-preservation issue, not evidence of a valid cleanup.

## Runtime gameplay approval still needed

Pablo should cold-boot **r67.14t**, capture (1) the Lion Statue acquisition
popup with the final `e` safely inside its original border, (2) the
Stone Pillar `PUSH Lion Statue` line without clipping, (3) the first
Door of Anubis / two-statue Stone tablet inscription, and (4) if practical
the neighboring Stone tablet for the western clue. The previously approved
Chamber of Lions stone text and physical Lion inspection must remain correct.

Memory-card cross-release runtime validation **not established** because a
true first Soul Well golden checkpoint is unavailable. Keep original PCSX2
cards/savestates intact; do not rename or inject savestates, change PCSX2
configuration, or claim compatibility from static save identifiers. A
verified in-game checkpoint, disposable card clone, normal save and cold
reload are still required under `docs/SAVE_COMPATIBILITY.md`.

**No commit, push, pull request or merge until screenshot approval.**
