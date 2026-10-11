# r67.12 — Compact spacing inside chronological dialogue-history sections

**Status update (2026-10-10): User has approved the single-dialogue visual layout in r67.12. The layout is now frozen by `docs/R67_15_APPROVED_HISTORY_LAYOUT_LOCK.md`, `translations/r67_history_layout_lock.json`, and `tests/test_r67_history_layout_lock.py`. Multi-dialogue/scroll runtime validation remains pending. Do not merge PR #42 or tag r67.**

## User feedback

After testing r67.11, Pablo confirms speaker-first chronological English dialogue history is nearly correct, but the vertical gap between each speaker name and dialogue is **much too large**. Preserve the already verified order and grouping. The explicit future requirement remains: each speaker/dialogue turn must be its own section, and multiple sections must remain in story order.

## Diagnosis

The START history callback at `0x253840` retains the **39.0 logical-pixel** Japanese column step, which became vertical row spacing after r67.10 swapped the two history-only X/Y position loads. The r67.11 chronological correction moves the extra spacer after spoken dialogue but leaves both spacing instructions at 39.0, producing:

- Before: speaker → dialogue = 39 logical px; dialogue → next speaker = 78 logical px.
- Proposed: speaker → dialogue = **25 logical px**; dialogue → next speaker = **37 logical px**, comprising the next 25px baseline step plus a 12px after-dialogue paragraph gap.

These values are **static text-object positions**, not changes to font glyph metrics or global story dialogue. The separate spacing after each spoken line keeps consecutive turns distinct. They operate on all up-to-12 visible history records; no first-conversation special case.

## Precisely scoped patch

Source: `tools/r67_history_compact_spacing_probe.py`; fixed checksum input from r67.11 `local/r67-11-history-sections.elf`.

Only these **two START-history-local MIPS instructions** are modified:

- VA `0x253D24`, file offset `0x153DA4`: `lui v0,0x421C` (39.0f) → `lui v0,0x41C8` (25.0f). This is the common row advance executed after each history record.
- VA `0x253D54`, file offset `0x153DD4`: `lui v0,0x421C` (39.0f) → `lui v0,0x4140` (12.0f). This is the **extra** spacer for a spoken-line type (after r67.11).

Existing horizontal-only constructor clone, chronological ring-index helper, type branch, text styles, normal dialogue, H.A.N.T. Basic Attack and save IDs remain byte-identical. No changes to input handler, PCSX2 configuration, global Edge, YouTube, real saves, or BIOS.

## Model-based regression

`tests/test_r67_history_compact_spacing_probe.py` checks a single turn and up to **six chronological speaker/dialogue sections (12 records)**, spacing `+25` after a speaker and `+37` after dialogue. It rejects unexpected record kinds/counts and drifted executable instructions; byte-diff assertion ensures no other code changes. This tests the computed static row positions but **not actual glyph height/wrapping, rich formatting, display clipping, or native scrolling for older records**. Keep those runtime gates open.

## Build and verification

- Input ELF SHA-256: `35ccde0a6d363c8b8f767d131dda46a543458f46cf8c6371975d7c0ea7651048`.
- Candidate ELF SHA-256: `d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179`.
- Only four original ELF bytes changed (`0x153DA4`, `0x153DA5`, `0x153DD4`, `0x153DD5`). ELF size unchanged.
- New diagnostic ISO: `local/r67-candidates/67.12-history-compact-diagnostic.iso`; SHA-256 `87cfa6f445eba36687e1d5badc621d9efd3157560a3be8da0c5eda4309a54e63`. Installed ELF SHA-256 `669b997d767d39c1ca5e29dc6458eaedc71bfe78e2fe74ca7f1dd9312858988c`. Built from the existing original-Japanese-disc copy using the same approved r67 overlays.
- ISO startup acceptance: **155/155**. Full Python suite: **299 tests, 17 expected skips, zero failures**. Focused regression suites: **17 tests, zero failures** (including the previous Basic Attack lock tests).
- Independent 2 GB ISO byte-diff audit against `67.11-history-chronological-diagnostic.iso`: **exactly four changed bytes** at image offsets `0x7BD5EDA4`, `0x7BD5EDA5`, `0x7BD5EDD4`, `0x7BD5EDD5`, all inside the two history spacing instructions. Every other image byte—including translated text, the approved H.A.N.T. page, normal dialogue, and save metadata—remains bit-identical.
- Do not call this release-ready before user visual acceptance.

## Runtime checklist

Request Pablo to test 67.12 with his existing 8BitDo controller and slot-2 save, inspect START dialogue history, and send a screenshot showing a speaker above their dialogue with compact separation. Later test multiple consecutive turns, different speaker label lengths, longer dialogue wrapping, history scrolling beyond twelve records, and story ordering. The 39px scrolling animation stride elsewhere in the ADV history state machine remains unchanged; **its interaction with 25px rows is not yet validated**, so no claim that history navigation is fully correct.

Do not proceed to the other renderer bugs; do not merge PR #42.
