# 67.06 renderer corrections — 2026-10-09 (NOT RELEASED)

Based on Pablo's 67.05 screenshots and the authorized PCSX2 debugger session.

## Experimentally built — runtime screenshot still required

1. **Full L1/R1 "Change target"** is restored at native fixed label slot 0x596CD0, without changing the official PS4 English string. A static call-path trace identifies the ONLY literal owner via native file 0x1A6B78, VA 0x2A6AF8: `lui a2,0x69; addiu a2,a2,0x6c50; jal 0x29A520`. Font, button backgrounds and rendered text positions originate in the same M_DngItemUseDraw2 controller region, so 67.06 moves the four matching X-offset float constants from 120->20 (and 121->21) together: file offsets 0x1A67FC, 0x1A6820, 0x1A6880, 0x1A6AD4. This is a position *candidate*, not a visual success claim.
2. **Basic Attack page** keeps all six native sprite anchor metadata entries intact, preserves icon slots, and indents only native row 17 and row 20 so the SELECT and warning captions align with the line above. The approved Turn-Based Combat/Entering Battle tables and all other text rows remain frozen.

### Tested and preserved

- Complete ISO stage is 67.05 plus 104 bytes of appended text; **135 changed ISO bytes, 0 unclassified**.
- Final startup acceptance **155/155**; full Python suite **282 tests, 16 expected skips**.
- Two independent ISO builds identical SHA-256 `192e772163e58450c3f628aa9de9a5fdc83ee175ef8a146c4e3660c316b75f23`.
- Executable and ISO save namespace unchanged (SLPM-66511 and BISLPM-66511Save).
- Stone Pedestal Push/Use Item, physical Lion Statue inspection, Stone Tablet, Large Container, Treasure Vase, Door, approved normal DG and AFK/L1 dialogue, and Turn-Based Combat untouched.
- The test ISO is local-only at `local/r67-candidates/67.06-experimental.iso`. **Do not publish 67.06 or merge to main without visual approval.**

## Specifically NOT fixed / evidence from live debugging

- **START history**: Vertical English persists. The previously patched JAL at 0x259CD4 and alternative constructor at 0x251594 both remained at 0 breakpoint hits during one attempted reopen; not proof that the code is never executed. They may be one-time canvas initializers. The displayed first lines originate in ADV/DG/DG00_00.MTX; tracing its distinct history glyph layout owner remains required.
- **Old-man hall speech**: Text/blueish backing mismatch remains. One experiment compacted the independent source 0x3C1A70 from the official 'Make sure you're always ready' to 'Stay ready.' but failed `companion_hud_comments` startup acceptance (**154/155**) and was discarded. 67.06 retains the entire approved sentence and pointer unchanged. Solve its background/text geometry instead.
- **Lion Statue item pickup**: The official `Lion Statue` catalog name at pointer 0x391928 is preserved. Visual title overflow is in an independent yellow acquisition popup. Disassembly shows native M_ObjGetDraw registration at 0x2A2344 with draw controller 0x2A23E0 and related M_EvItemDraw paths. Text/sprite handles are rendered through 0x18AD30. Need identify which title font or border width belongs to this card; do not shorten the shared catalog text or edit approved physical Lion Statue inspection.

## PCSX2 isolation

- User's running instance PID 71367 was left with its controller mapping, existing saves and original profile unchanged.
- Its memory cards and savestates were copied to `local/debugger-backups/2026-10-09-67.05` before experiments.
- A separate PCSX2 data directory was created under `local/pcsx2-67.06-isolated` with copied PS2 BIOS and copied memory cards, SDL controller support disabled, and an independent debugger-at-entry session. User's original application and settings are not shared. Remove or shut down this temporary instance after diagnostics.
- No prohibited game assets or BIOS should be committed, uploaded, or attached to GitHub.

## Next

Identify the historical-font glyph advance code and the acquisition popup's title width via the separate test emulator; visually validate the coordinated M_DngItemUseDraw2 position constants. **Do not treat passing static checks as gameplay acceptance.**
