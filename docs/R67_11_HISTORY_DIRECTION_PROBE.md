# r67.09 — History-only horizontal constructor diagnostic (2026-10-10)

**State: built, byte-audited, static checks passed, NOT visually accepted.** Do not merge PR #42, publish a release, or proceed to other renderer defects until Pablo verifies the history screen.

## User feedback / hypothesis revision

- First diagnostic (`67.08-history-style1-diagnostic.iso`): visibly changed presentation, but glyphs remained vertical and lost correct formatting. Rejected.
- Second diagnostic (`67.08-history-parser-diagnostic.iso`): Pablo's START history screenshot again shows the original vertical single-character columns. Rejected.
- **Proven root owner:** In approved r67 executable, native `0x190AB0` is `sltu a2,zero,s0` (word `0x0010302B`), where `s0` contains the requested font style. This makes the direction argument passed to native font-object constructor `0x188AD0` equal to `1` for history styles `3/4/5`; constructor stores the direction at object offset `+0x24` (`0x188CD0`). Style 0 uses direction 0 and renders normal DG text horizontally.
- Pristine 2006 executable instead had `0x24060001` (`addiu a2,zero,1`); the approved r67 style-dependent selector is intentionally retained for **all other callers**. Simply changing style IDs or parser-dispatch routines cannot reliably resolve a direction argument that remains 1.

## History-only implementation

- Added `tools/r67_history_direction_probe.py`. It checks source SHA-256 and PT_LOAD geometry, verifies the native constructor matches pristine **except the approved direction selector**, checks that all internal copied relative branches remain valid, and fails closed on any mismatched preimage.
- It appends a **576-byte clone** of constructor `0x190A50..0x190C90` into the existing executable translation PT_LOAD. In the clone **only**, instruction corresponding to `0x190AB0` becomes `0x24060000` (`addiu a2,zero,0`). This forces horizontal advance without changing font style IDs, font descriptors, glyph content, or scaling.
- It changes **only the ADV history-specific callsite** at VA `0x255E88`, ELF offset `0x155F08`, from `jal 0x190A50` to `jal 0x963A50` (the appended clone). Shared `0x190A50`, normal dialogue and all other font constructor callers remain unchanged.
- Fail-closed audit checks: changed **original** ELF byte offsets only `0x64,0x65,0x155F09,0x155F0A` (PT_LOAD filesz and history JAL); no changes to original helper code, approved Basic Attack strings/pointers/atlas, ADV dialogue, save IDs or other game objects. Clone uses identical original constructor logic apart from the one direction instruction.
- History screen coordinates and wrapping have **not yet** been visually approved; further history-local positioning corrections may be necessary. Do not extend scope to other issues.

## Rebuilt verified ISO and checks

- Earlier `r67-candidates` ISO files had been removed; recovered the original ISO from existing `/private/tmp/khc-ps2/` and rebuilt the 67.07 baseline deterministically from preserved translation assets, without changing the user's original disc archive, global PCSX2 profile or saves.
- Reconstructed baseline: `local/r67-candidates/67.07-reconstructed-baseline.iso`, whole-ISO SHA-256 `9ba49ae57a80a65e361f2c89476f7b4f64293d6d18b9293445334d90dc6f67a0`; embedded ELF SHA-256 `1db2b2bfe2dc9df4ab54b71775688062d28bb5922436168051621f8925cdc591` **exactly matches** the previously verified 67.07 installed ELF. All **155/155** startup checks pass. Whole-ISO SHA differs from the earlier deleted 67.07 ISO because the reconstruction used current owned overlays; do not present as bit-identical to deleted earlier ISO.
- New diagnostic ISO: **`local/r67-candidates/67.09-history-horizontal-diagnostic.iso`**, whole-ISO SHA-256 `b1d042952df96ddcbb28b3e4ec47220b22797a55ec84b753e088616475c36ce6`. Installed ELF SHA-256 `aacf88dd4cad60ba37d913fd0eecad1e0af75c3b630ce3afee0175e8192707c1`.
- Finished ISO has **155/155 startup checks**. Independent full-image audit versus reconstructed 67.07 baseline checked all 2,095,382,528 bytes: **387 changed bytes**, all restricted to permitted outer ISO executable-length metadata, original ELF PT_LOAD file size and history callsite, plus the append-only horizontal constructor bytes. Everything else (all non-executable assets, fonts, normal dialogue, 22-row H.A.N.T. Basic Attack, save identifiers, translation source data) remains identical. Audit report is local at `local/r67-09-history-direction-binary-audit.json`.
- Focused regression tests in `tests/test_r67_history_direction_probe.py` cover fails-closed preimages, relocation safety, clone identity, shared code immutability, and non-release status. The old 67.07 Basic Attack regression tests also passed. Full suite: **287 tests, 17 skips, 0 failures**.

## Safety and next test

- **Do not send global keyboard shortcuts.** Earlier synthetic input accidentally affected the user's Edge/YouTube mute state. No GUI keyboard control was attempted during the r67.09 build; user's running PCSX2 and Edge remain untouched.
- Only next step: Have Pablo load **`67.09-history-horizontal-diagnostic.iso`**, using his existing physical 8BitDo and slot-2 savestate, and show the **START history screenshot**. The text should flow horizontally while retaining the original speaker/body style. Check line length, wraps, stacking and history scrolling. Do not declare fixed if words clip, overlap, or are off screen.
- If horizontal direction is confirmed but history columns overlap, adjust **only the ADV-history-local X/Y and wrapping owner**. Do not alter global typeface, approved normal dialogue or the locked H.A.N.T. Basic Attack page.
