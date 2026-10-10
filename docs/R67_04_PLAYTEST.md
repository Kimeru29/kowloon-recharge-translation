# 67.04 — playtest findings and frozen approval gates

Input: seven 67.03 gameplay screenshots received 2026-10-09.
This records observed results; it does not claim an untested renderer fix.

## Newly approved — lock unless explicitly requested

- H.A.N.T. **Turn-Based Combat**: current formatting good enough. Entire text table, descriptors and controller sprite metadata frozen.
- **Chamber Stone Tablet**: perfect.
- **Physical Lion Statue inspection**: name, description and layout perfect (distinct from the item pickup screen). Freeze it.
- **Large Container inspection**: perfect.
- **Stone Pedestal inspection**: perfect. The translated circle-button Use Item prompt is slightly clipped and must be adjusted independently.
- **Treasure Vase inspection**: perfect.
- Previously frozen Door inspection, Entering Battle Help, main story dialogue and normal AFK/L1 companion presentation remain unchanged.

## Still open in screenshot feedback

1. **START dialogue history**: English still rendered vertically, letter per row (screenshot 1). The old 67.02 MIPS shim remains in 67.03 and had no observed effect. Trace actual active rendering owner.
2. **Chamber entry old-man speech**: oversized empty green bubble and text below it; blue fill is correctly enclosed (screenshot 2). Related story-comment source 0x3C1A70, pointer 0x3D3438, corresponds to official Make sure you're always ready. Do not disturb the enclosed blue backing.
3. **Basic Attack Help**: awkward spacing and icons (screenshots 3–4). 67.04 reflows ONLY first 15 nonblank rows. Native icons and last seven blank rows are frozen because earlier attempts to rewrite every row froze Help. Gameplay approval pending.
4. **Physical Lion Statue L1/R1 prompt**: Japanese target-change label (screenshot 5). Distinct native 32-byte slot 0x596CD0, source Japanese ターゲットの変更, verified PS4 Change target. 67.04 changes only that slot.
5. **Lion Statue item-pickup title**: overflows popup (screenshot 6). Inventory item-name pointer 0x391928 must retain exact official Lion Statue. An attempted abbreviation failed the official-item acceptance gate and was fully reverted. Fix pickup-specific renderer geometry, not shared item names.
6. **Lion placement old-man line**: same enlarged bubble and caption below the box (screenshot 7). Local Door's ready. originates in story-comment source 0x3C1F38 with pointer 0x3D3B28, distinct from normal AFK/L1.
7. **Use Item** label: translated but slightly clipped on right. Keep original English; trace text placement owner before adjusting.

## 67.04 partial testing build

Changed: officially matched Change target in a verified native fixed slot, and Basic Attack copy in exactly 15 existing Help rows with unchanged icon holes.

Immutable: all accepted inspection pointers/strings, Turn-Based Combat text and metadata, Entering Battle Help, underlying approved AFK/L1 and ADV rendering, save namespace, and globally correct Lion Statue item name.

Unresolved: history orientation, both old-man bubble/text mismatches, Lion Statue pickup clipping, slight Use Item clipping. The ISO is **NOT** fully visually approved and the first Soul Well milestone is NOT complete.

Static acceptance target: 278 automated tests (16 expected skips), 155/155 startup ISO checks, reproducible builds, 0 unexplained whole-image changes, and unchanged SLPM-66511 / BISLPM-66511Save identities.

Do not launch PCSX2 automatically or merge to main.
