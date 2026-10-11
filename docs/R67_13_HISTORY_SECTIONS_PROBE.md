# r67.11 — Chronological dialogue-history sections (diagnostic, 2026-10-10)

## Request and established evidence

Pablo confirmed that `67.10-history-rows-diagnostic.iso` now renders START dialogue history **horizontally**. He requested **speaker on the first line and speech on the second**, and future conversations displayed **chronologically**, one separate speaker/dialogue section after another. Current focus is START history only. Normal ADV dialogue and the approved H.A.N.T. Basic Attack screen are locked.

## Proven history storage and presentation owners

- The native START history callback `0x253840` initializes `s3 = (historyCount - 1) % 255` at `0x253A70–0x253A88` and then **decrements** `s3` after each visible entry at `0x253D74–0x253D80`. This was suited to the former right-to-left Japanese vertical columns; after horizontal X/Y swapping, newest speech appeared ahead of its older speaker label.
- The visible-window size at `s1+0x7A` is capped at 12 records. The native ring has 255 slots. Every entry occupies an individual 40-byte record in the ring at `global+0x924+(recordSlot*40)`; one record is either a speaker-type label or spoken text (record tag zero follows text-formatting branch `0x253B0C`).
- At `0x253D38–0x253D64`, the old layout adds an extra 39px spacer after **nonzero tag** records and some flags, i.e. primarily labels in the old right-to-left column ordering. For English sections, the gap should follow the spoken-text record, not separate the speaker from their dialogue.
- `67.10` already horizontally positions records with a history-only font-constructor clone plus the two history-only X/Y loads. That approved experiment is retained unchanged.

## Bounded new experiment

`tools/r67_history_sections_probe.py` only patches START-history-local code in the `67.10` generated ELF:

1. At history record lookup `0x253AE8–0x253AEC`, replace the two native `s3*5` instructions with a `jal` to an append-only 48-byte helper. It calculates the chronological visible slot, `(count - visibleCount + ordinal) % 255`, returns `5*slot` in `v0`, and resumes the original `sll v1,v0,3` (the original 40-byte record stride). It does **not** change global history storage, `s3`, unrelated history consumers, or saved progress.
2. At history-local `0x253D3C`, change the branch to add the extra spacer **after tag-zero spoken text**. At `0x253D48`, unconditionally skip the extra spacer for nonzero-tag label records. The original 39px row stride, 39px section gap, and text styles are otherwise unchanged.
3. Update the translated ELF segment size metadata to include the append-only 48-byte helper. Original existing ELF changes are restricted to the index callsite (two words), two history-specific spacer branches (two words), and PT_LOAD filesz metadata.

The helper is deliberately **generic**: unit tests cover counts 1, 2, 4, 12, 19, 255, 262 and full 255-slot rollover, rather than special-casing the first two lines. It handles the **latest visible 12 records**, displaying them in chronological story order. It does not claim support for every older page through scrolling yet.

## Build and correctness gates

- Input `local/r67-10-history-rows.elf` SHA-256: `572022168275e32b3fba3ba2373eb7a6f6521631574ba27106f870929b01ca3a`.
- Output `local/r67-11-history-sections.elf` SHA-256: `35ccde0a6d363c8b8f767d131dda46a543458f46cf8c6371975d7c0ea7651048`.
- Local diagnostic `local/r67-candidates/67.11-history-chronological-diagnostic.iso`, SHA-256 `eaed0747900a0f62d87d1896c2cab16437a19e6619c1be3c1d25dbddaf5b9519`.
- The accepted translation overlay pipeline rebuilt the ISO from the pristine locally extracted Japanese source and approved owners. Installed ELF SHA-256 after ROFS reconciliation: `59965a328c836c34c71b88430a751dd65bb0768961a96bc11fff143eec7cc626`.
- ISO static startup acceptance: **155/155**.
- **294 tests passed** in the full Python suite (17 expected skips; zero failures). Focused tests cover source checksum, exact modified original ELF offsets, unchanged renderer and Basic Attack, chronological multi-entry scenarios, MIPS helper instructions, circular-buffer wraparound, and a fail-closed path.
- ISO and original saves are local/untracked. No release, merge, emulator automation or editing of Edge/YouTube is authorized.

## Remaining runtime gate (do not call complete)

Ask Pablo to load `67.11-history-chronological-diagnostic.iso` in his existing PCSX2 and 8BitDo, enter the slot-2 story scene, open START history and send a screenshot. Confirm:

- Speaker appears **above** its associated line of dialogue.
- Speaker and dialogue share a section; gap follows spoken content.
- With multiple consecutive conversations, **sections follow their original chronological story order**, labels paired with correct bodies, without collisions or clipping.
- Check opening history after >12 records, scrolling older/newer pages, and variable-length lines separately; native scrolling and dynamic wrapping **have not been validated**. Do not approve until these scenarios work; further adjustments must remain history-only.

Preserve all unrelated user-reported defects for later, and do not merge [PR #42](https://github.com/Kimeru29/kowloon-recharge-translation/pull/42) before visual acceptance.
