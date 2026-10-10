# 67.05 — 67.04 playtest feedback and scope

Pablo's 67.04 screenshots (2026-10-09) reveal five remaining visual defects:

1. START dialogue log still renders vertical English. **Not fixed.** The experimental 67.02 native MIPS constructor hook remains present yet ineffective. Cannot safely patch a different render path without execution evidence.
2. Chamber entry old-man text and blue background still overflow the green speech bubble; prior reported blue enclosure regressed visually. **Not fixed.** The entire 67.03->67.04 ISO difference was confined to text pointers, one target label and appended Help strings, not the comment renderer's geometry. Do not alter approved AFK/L1 graphics or assume those are the comment owners.
3. H.A.N.T. Basic Attack has orphaned SELECT and (!) icons at the end. **67.05 static candidate:** add icon-aligned captions to native row 16 (SELECT) and row 19 (!) and adjacent rows 17/20; retain all six original icon metadata records, page descriptor, and original EOF. This reopens four formerly blank native Help rows. Previous runtime freezes with full-page rewrites mean gameplay validation is essential. No claim of runtime approval.
4. Lion Statue L1/R1 Change target extends offscreen. **67.05 static candidate:** shorten the already semantically and officially validated label to Target, so the screen shows complete context L1/R1 Target. The same 32-byte fixed string slot is used; no button/sprite changes. Runtime approval pending.
5. New-item Lion Statue title overflows the yellow pickup box. **Not fixed.** Its full official item-catalog string is used elsewhere and checked by 155/155 ISO acceptance. Shortening this owner would corrupt the item-name acceptance contract; fix requires proven popup-specific renderer layout/scale/wrapping owner.

### Frozen

- **Stone Pedestal Push/Use Item action: now visible and accepted.** No changes to its 0x594FA0 pointer, translated data, or UI renderer. Freeze.
- H.A.N.T. Turn-Based Combat, Entering Battle, Stone Tablet, Lion Statue (physical inspection, distinct from the item), Large Container, Stone Pedestal inspection, Treasure Vase, Door, and accepted companion AFK/L1 remain frozen.
- Original SLPM-66511 and BISLPM-66511Save identity, inventory official names, all sprite resources and all mapped MIPS graphics code remain unchanged.

### Validation

67.05 partial testing candidate; no automatic PCSX2 run or main merge. The user must visually approve the target caption and Basic Attack page. To resolve the remaining three display path issues, instrument runtime callsites/render state (with explicit permission to launch/debug PCSX2) or capture equivalent execution evidence. Avoid unrelated geometry guesses.
