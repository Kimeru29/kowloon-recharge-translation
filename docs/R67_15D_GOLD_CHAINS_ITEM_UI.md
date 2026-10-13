# r67.15d — Golden Chains and Items UI follow-up

**Status: diagnostic built and statically validated; NOT gameplay approved.**

## Regressions from r67.15c gameplay screenshots

1. **Choose storage:** The prior handcrafted typography and broad image inpainting badly damaged the parchment background. The official PS4 English source texture GP004_18 already provides the exact "Choose storage" lettering inside the original 128-pixel PS2 tile. r67.15d keeps those original PS4 pixels and restores only the overflowing "location" artwork in neighboring tile region x130–204, y7–24 using clean source parchment columns x205–212. All other GP004_18 pixels, including Vest and Room, exactly match the PS4 source. No substitute font is used.
2. **"COMPOL" in Items bar:** The previous GP004_19 bitmap drew full COMPOUND over a presumed 76px atlas area, but the live UI samples a 48px tile. Keep the official word "COMPOUND" and redraw with condensed four-column glyphs and 1px spacing. Full text width is 39px within the tested 48px region x48–95; sibling labels Details, Swap, Discard and Recycle are unchanged.
3. **Japanese floating synthesis action:** The prior release translated the synthesis result messages but not their separate UI action owner at executable offset **0x38632C** (original pointer 0x793678 to Japanese 調合). This owner now points to official PS4 **Compound**, at English.bytes offset **0x46208**, encoded with the game's two-byte CP932 font glyphs (8 cells). No other action label was patched.
4. **Japanese Golden Lock inspection:** Native six-pointer record starts at **0x58A9F0**. Official PS4 terms: **Gold Chains** (corpus 0xC58DD), **Very strong chains of pure gold.** (0xC58FC), **Affixed to the door.** (0xC594B). Preserving all meaning within 21-cell body bounds uses three lines: **Very strong chains** / **made of pure gold.** / **Affixed to the door.**. Original body fields 1 and 2 are redirected, empty body field 3 is populated, body field 4 stays empty and Japanese-only phonetic reading field 5 is suppressed through the existing native empty sentinel. Title 11 cells and description rows 18/18/20 cells. No behavioral/story code changes.

All PS4 source mappings are checked against SHA-256 b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b. The baseline r67.15c installed ELF is SHA-256 c9328e04282e652035119ab331adaa9adeac232507b86632ea67ecab39356ffa. New exact approved native pointer owners are **0x58A9F0, 0x58A9F4, 0x58A9F8, 0x58A9FC, 0x58AA04 and 0x38632C**. Apart from these six pointer words, executable size metadata and appended English strings, all existing ELF bytes must be unchanged.

## ISO, artifacts and audit

- Parent: local/r67-candidates/67.15c-synthesis-items-ui.iso — SHA-256 d140cca2ce4c9603d5f89a4b0413c4dc5ddce0e1385301e9a11f376fa17368aa.
- Diagnostic: **local/r67-candidates/67.15d-gold-chains-item-ui.iso** — SHA-256 **5d5850b660e92d9fd0dcb11456519d99b060cbaae131ebf48f6d0f80262a446d**.
- Full-disc report: local/r67-15d-whole-iso-audit.json. **2,095,382,528 bytes compared, 3,355 changes, zero unexplained.** Classes: 2,837 storage art, 344 condensed footer art, 18 pointer bytes, 150 appended text bytes, 2 ELF size bytes, 4 ISO9660 size bytes.
- Source and validations: tools/r67_15d_visible_art.py, tools/r67_15d_gold_chains_compound.py, tools/r67_15d_iso_release.py, tests/test_r67_15d_gold_chains_item_ui.py.
- All previous ISO artifacts retained, including approved q/t/y/z; no executable binaries or PS4 asset content committed.

## Static validation

- Focused regression/mutation/finished ISO checks **13/13 PASS**.
- Raw startup gate **154/155**; only failing check is the inherited obsolete memory_card_8 expectation for old, overflowing save-warning text.
- Scoped startup acceptance with the single established save-warning exception **155/155 PASS**.
- Protected history **4/4 PASS**.
- Native save serial **SLPM-66511**, namespace **BISLPM-66511Save**, and **15/15 save-descriptor regions unchanged**; genuine runtime cross-release save compatibility remains *unverified*.
- Existing q/t/Y approvals preserved. The previous approved Lion Statue helper JALs are reconstructed in memory only from SHA-pinned z baseline for the original strict t lock, because the explicit 15a generic item-width helper replaced those two known call sites. No old manifests are modified.
- Repository-wide suite: **511 tests, 9 expected skips, 0 failures/errors**, exit code **0**, completed in 128.891 seconds. Full logs: local/r67-15d-full-suite.log and local/r67-15d-full-suite.exit.

## Required gameplay screenshots

Cold-boot this ISO; do not modify or reuse original PCSX2 savestates, cards, settings or active session automatically. Verify all of the following: the storage choice heading retains PS4 lettering and clean parchment with intact Vest / Room; the Items footer shows the entire **Compound** within its own segment with unchanged Details/Swap; Square opens the English **Compound** action and translated result text; Golden Lock inspection title **Gold Chains** and three English description lines all fit in the bubble. Reconfirm previous approved Storeroom, Lion Statue, tablets, AFK/event dialogue, Soul Well and history do not regress.

**No commit or PR may be merged for this unapproved candidate until the user sends screenshots and explicitly approves it.**
