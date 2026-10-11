# r67.10 — Horizontal dialogue-history rows (DIAGNOSTIC ONLY)

## Latest user-provided runtime evidence

Pablo tested the r67.09 history-only direction ISO. **Glyphs now advance horizontally**, confirming that the cloned horizontal constructor works. However, the START-history screenshot shows `[Old man's voice]` and `Hey; over here.` interleaved on a **single horizontal band**, so the text is unreadable. The speaker/body strings are not corrupted: two independent log-entry canvases are still arranged by the old Japanese vertical-column layout.

## Exact history-only positioning owner

- Each history log entry is created in callback `0x253840`, especially the entry constructor at `0x253CF8`.
- The history callback increments the position accumulator at `$s1+0x80` by **39.0f** per entry (sometimes twice). It places successive vertical Japanese text columns at different X positions, with an approximately fixed Y at `$s1+0x84`.
- Text-object creation passes `f12 = *(float*)(s1+0x80)` and `f13 = *(float*)(s1+0x84)`, via loads at `0x253CE8` and `0x253CEC` respectively. With horizontal glyph advances, these produce overlapping rows.
- **r67.10 diagnostic swaps only those two argument loads**, so the original row spacing runs along Y instead of X:
  - VA `0x253CE8` / ELF offset `0x153D68`: `lwc1 f12,0x80(s1)` (`0xC62C0080`) → `lwc1 f12,0x84(s1)` (`0xC62C0084`)
  - VA `0x253CEC` / ELF offset `0x153D6C`: `lwc1 f13,0x84(s1)` (`0xC62D0084`) → `lwc1 f13,0x80(s1)` (`0xC62D0080`)
- This preserves the r67.09 cloned horizontal constructor and its dedicated history call. **Original font styles 5/3/4, shared constructor, ordinary dialogue, H.A.N.T. Basic Attack, save identities, and unrelated UI remain unchanged.**
- The 39px row spacing, longer-entry wrapping and START-history scrolling have **not** been visually validated. If those need correction, they must be adjusted only within the same history subsystem. Do not declare the issue complete yet.

## Build and validation

- Read-only input ELF: `local/r67-08-history-direction.elf`, SHA-256 `76f71fc7eb62fea52ff347b8e1464a7f217066af288eba17802c8a6eb5e4cd02`.
- Diagnostic generator: `tools/r67_history_rows_probe.py`; fails closed on unexpected input fingerprint or instruction preimages and refuses to overwrite existing output.
- Output ELF: `local/r67-10-history-rows.elf`, SHA-256 `572022168275e32b3fba3ba2373eb7a6f6521631574ba27106f870929b01ca3a`. **Exactly two existing bytes changed** (offsets `0x153D68`, `0x153D6C`), and ELF length is identical to r67.09.
- Diagnostic ISO: **`local/r67-candidates/67.10-history-rows-diagnostic.iso`**, SHA-256 `032a9c543175cbf211d0a31daf838d9dd9a259a7e61679a40844889a629a0a87`. Built via the repository's original-disc overlay pipeline (exact MTX, KSF, structural MTX, accepted overrides, startup graphics) using the r67.10 ELF.
- Startup acceptance: **155/155**. Full suite: **289 tests, 17 skips, 0 failures**. Focused tests: **7/7 passed**, including prior r67.07 Basic Attack freeze tests and r67.09 isolated constructor checks. New `tests/test_r67_history_rows_probe.py` verifies exactly the intended two instructions change and rejects tampered input.
- Do not merge [PR #42](https://github.com/Kimeru29/kowloon-recharge-translation/pull/42), tag a release or mark r67 completed without visual confirmation. No ISO/BIOS/savestate/copyrighted image is tracked in Git.

## Immediate next step (history only)

Have Pablo test `67.10-history-rows-diagnostic.iso` in his **existing PCSX2/8BitDo** with copied slot-2 save. Request a screenshot of the START history screen. The two English entries should appear as independent horizontal **rows** in the correct order. Check wrapping, clipping and UI navigation/scrolling. Do not run synthetic keyboard input that could mute Edge/YouTube; never alter the original emulator state or settings without permission.
