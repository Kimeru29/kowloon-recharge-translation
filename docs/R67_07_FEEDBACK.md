# r67.07 feedback — approved surface protection, NOT A COMPLETED FIX

Pablo's 2026-10-09 screenshot after 67.06 proves that the L1/R1 caption was translated left into the statue while the icons stayed near the original position. In contrast, the Basic Attack page is now perfect and **must not change**.

## Containment candidate, not final release

- Derived strictly from 67.06 experimental ISO; reverted the four native float constants introduced by its incorrect controller-overlay assumption to their 67.05 values, and restored the previous non-overflowing, but **incomplete** short caption "Target". This is a nonfinal regression rollback; the required full "Change target" still needs a tested, control-specific layout fix.
- Kept 67.06 Basic Attack 22-row pointer table, glyph strings, controller icon atlas, and icon metadata byte-identical. Regression test explicitly rejects modifying any.
- Did not touch previously approved Turn-Based Combat, physical Lion Statue inspection, Stone Tablet, Stone Pedestal, Large Container, Treasure Vase/Base, save identity, or other UI controls.
- 67.07 containment ISO: `local/r67-candidates/67.07-containment.iso`. 28 changed installed ELF bytes, zero unexplained. SHA-256: `d5925fcf14959d041b0af45b38170f03e375eaefd43ccc9d089253a093acadfb`.
- 155/155 startup acceptance. No visual acceptance; do **not** release, merge, or describe this as fixing the user-reported items.

## Still open — user-reported defects

1. **Dialogue log/history**: START modal still advances English letters vertically. ELF contains debug module marker `y_AdvLog.c` at file 0x5780D0 and `ADV LOG PROC` at file 0x5780E0. This is a stronger lexical owner clue than the two font-constructor breakpoints, but no executing callsite or corrected renderer has been established. Do not reuse the failing 0x259CD4 shim speculatively.
2. **Old-man entry comment**: long original official English horizontal line exceeds green bubble width; blue background and typography are separate from approved AFK/L1 story. Do not shorten official text or mutate approved AFK/L1 surfaces. Need pinpoint comment glyph canvas/rectangle and implement true wrapping/scale.
3. **Lion Statue L1/R1**: required complete `Change target`. Existing native `M_DngItemUseDraw2` literal owner (0x596CD0, 32 bytes), callsite VA 0x2A6AF8. Moving 0x1A67FC/1A6820/1A6880/1A6AD4 by -100 did **not** move L1/R1 icon group in gameplay, and failed. Need exact independent icon-caption pairing and fit test.
4. **Lion Statue item-acquisition popup**: official item name must remain `Lion Statue`; yellow popup clips end of `Statue`. Item pickup / object-get draw has independent native path (M_ObjGetDraw 0x2A2344). Need title-specific font measurement, scale or card width, not a global catalog change.

## Isolated experiment

Copied memory cards and BIOS to private `local/pcsx2-67.06-isolated`; booted explicit pre-existing savestates with temporary keyboard mapping and SDL off. Confirmed separate emulator/gameplay, including corridor movement. Both states were already past the first old-man cutscene; no credible reproduction of story-log history, bubble or yellow pickup yet. Shut down private PCSX2 instance. User's original 8BitDo settings, saves and source files remain untouched.

**Release gate**: full `Change target` visible, two old-man comments fully contained, correct English horizontal dialogue history, pickup card fully contains `Lion Statue`, Basic Attack and all previously locked UI unchanged. Static 155/155 is necessary but insufficient.
