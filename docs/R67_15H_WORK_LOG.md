# r67.15h — reported overflow and area-transition investigation

## Scope and constraints

User reports r67.15g SELECT Details overflow (grenade and Aqua Regia), recipe
ingredient/result names colliding with capacity columns, and indefinite animated
loading after opening Gold Chains with Aqua Regia. Preserve accepted right-card
names, Compound/Can't bubbles, official wording, all previous releases and saves.
Reuse `first-save-r67`. No emulator launch/input/configuration/card/state changes.
New gameplay acceptance requires the user's screenshots; no merge is authorized.

Base: `c2033b1`, branch `fix/67.15h-details-area-transition`.
Input ELF SHA-256: `74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee`.
Input ISO: `local/r67-candidates/67.15g-partial-diagnostic.iso`.
Baseline suite: 621 tests, 14 skipped, zero failures (129.011 seconds).

## Execution record

- Astra diagnosed Details/native space and newline metrics and the three separate
  recipe constructors. Full handoff: ignored `local/r67-15h-ui-diagnosis.md`.
- Luna owns new item-layout module, tests and component documentation. Worker
  resumed after a usage-limit interruption; its initial stub is not a fix.
- Parent owns loading diagnosis and release integration. A separate Astra probe
  checks the discovered HANT row-pool mismatch, not the item-layout implementation.
- User screenshots and original emulator log copied without overwriting into
  ignored `local/r67-15h-evidence/`. No proprietary evidence is to be committed.
- PCSX2 ran the exact 15g image. Log at 276.04 seconds records invalid text handles
  (e.g. `0x18AAB0`, address `0x41`). It subsequently closed independently; no
  emulator operation was performed by this task.
- Native HANT draw path `0x28FD60` has 16 handles at private `+0x17A0`; eligible
  row origins satisfy `89 < Y < 383`. Help rows have 16-pixel pitch. A scrolled
  page can select 18–19 rows. Slot 16 aliases state `+0x17E0`, whose active value
  is 5; passing this as a text handle produces the observed `5+0x3C=0x41` access.
  This is a proven unsafe path, not yet proof of the later door-loading cause.
- Independently compared all 10,656 original DATA.CVM file records with their
  embedded executable ROFS size/extent records and the installed 15g nested
  directory. All matched; 969 assets have changed size or extent since pristine,
  zero stale executable lookup records and zero missing matches. This rules out
  that specific loading-metadata fault, not every area-transition failure.
- User confirmed opening/scrolling at least four or five HANT Help pages in the
  same run before the stall. This establishes exposure to the unsafe viewport
  path, but does not independently prove the later transition's failure cause.
- Astra confirmed the row-pool diagnosis: the purported assertion is a no-op;
  the seventeenth eligible row reads state 5 as its handle. Luna implements the
  scoped pool relocation to owner tail `+0x1A94`, 19 handles, allocation `0x1AE0`,
  with actual bounds enforcement and unchanged native layout/scroll behavior.
  Detailed reasoning is in ignored `local/r67-15h-hant-pool-diagnosis.md`.
- Continued from saved files after the prior workers were no longer available.
  The two replacement Luna workers retain disjoint ownership: item layout and
  HANT pool. Parent owns integration, the repeatable read-only ROFS audit, and
  publication documentation. No intermediate native patch is a release.
- Added a repeatable finished-image ROFS audit with six mutation tests. Fresh
  execution against 15g independently reproduced 10,656 matches / 969 changes /
  zero mismatches. The 15h builder now requires the same check on its finished
  image, rather than relying solely on the earlier investigation's report.

## Remaining gates

- [x] Native item metric and recipe-bound regressions, including saved registers.
- [x] Reproduce and correct HANT row-pool safety with native execution tests.
- [x] Check installed 15g resource lookup metadata against actual disc directories.
- [x] Deterministic component composition and exact complete-disc audit.
- [x] q/t/latest locks, history 4/4, save identity 15/15, startup raw154/scoped155
  with only the documented memory_card_8 exception, fresh full suite.
- [x] New diagnostic ISO and comprehensive handoff; commit, push, draft stacked PR.
- [ ] User cold-boot gameplay screenshots: overflow cases, HANT scroll, and door.

Fresh integrated suite: **664 tests, 14 skipped, zero failures**, 142.018 seconds.
All 43 new 15h tests executed; the skip count remains the baseline count.
The full-dependency command is recorded in the handoff/component notes.

The separate 15h diagnostic build passed all static gates and the fresh
finished-image ROFS audit. Complete-disc comparison: 2,095,382,528 bytes,
67,452 changed versus 15f (including inherited 15g), zero unexplained. Final
ISO SHA-256: `3c4a2a57079070fed5c205aa338e45d88371164dc4ccc0db36fc402f88c5ace8`.
See [handoff](R67_15H_HANDOFF.md) for artifact paths, hashes and runtime limits.

Published implementation checkpoint `905d4b1` on
`fix/67.15h-details-area-transition`, with
[draft PR #52](https://github.com/Kimeru29/kowloon-recharge-translation/pull/52)
targeting `feat/67.15g-prologue-details-help`. No merge; the existing worktree,
all prior releases and original saves remain in place. Only new gameplay
acceptance and the loading-causality question remain open for this diagnostic.

Ruling: follow the user's explicit autonomous-work and Astra/Luna routing
instructions rather than adding routine approval or redundant review cycles.
No unproven workaround (timeouts, arbitrary pointer thresholds, skipped area
loads, or guessed resource edits) will be presented as a root-cause correction.
