# r67.14z — Storeroom name and inscription diagnostic

**Status:** Built and statically checked; new room presentation still requires gameplay screenshots and user approval before merge.

### Requested symptoms and native ownership

The new area displays `資材庫（しざいこ）`, with the exact PS4 English name **Storeroom** (English.bytes record `0xC30FA`). Two original native room-map name pointer owners (`0x5CD6B4`, `0x5CD84C`) both reference Japanese `0x6CC6E0`. Both now point to one identical appended English string.

The Stone tablet at record `0x591090` already has approved English title and descriptor. Its three inscription rows (`0x591098`, `0x59109C`, `0x5910A0`) were still native Japanese. Official PS4 English text at `0xCC573/0xCC5D5/0xCC612` is about **two waters becoming one, and their power making the golden lock disappear**. The original Japanese says `《黄金の鎖》` — the golden **lock/chain**, not a golden door.

To fit the native 21-glyph row limit while preserving the original quote markers and indentation:

> When 2 waters join,
> their power dispels
> the golden lock.

Rendered full-width CP932 row cell counts, **including original indent/quotation glyphs**, are **21, 21, 19**. This is semantic compaction of the official PS4 three-row translation; the original text and script/story flags are untouched. The original r67.14t/14y 58-tablet registry and 160 populated inscription rows still pass the game-wide width gate.

### Approval preservation

This diagnostic starts from exact user-accepted **r67.14y** staged ELF, with the frozen hash and acceptance manifest at `translations/r67_14y_approved_lock.json`. `tools/r67_14y_approved_lock.py` requires an exact source SHA and verifies **every pre-existing byte** of the new ELF except the five requested pointer owners and ELF filesize. No previously accepted companion bubbles, save prompts, graphics, object inspections, Stone tablets, history or native serialization/code were modified. q/t strict immutable UI locks pass with **no exceptions**.

The whole-disc audit compares every byte against the approved y disc and classifies only the five text pointers, the appended 148 bytes (including alignment), the changed embedded ELF filesize and ISO9660 directory filesize. Source: `tools/r67_14z_storeroom_tablet.py`, builder/auditor `tools/r67_14z_iso_release.py`, mutation and approval-gate tests `tests/test_r67_14z_storeroom_tablet.py`.

- Staged ELF `local/r67-14z-storeroom-tablet.elf`
- Diagnostic ISO `local/r67-candidates/67.14z-storeroom-inscription.iso`
- ISO SHA-256 `18b390bcb230a9a69ccff284eeea39a0d00dfc6502b2526ee9895f5f38c423a6`
- Whole ISO: **157 modified bytes, 0 unexplained**, old approved y SHA `079b4d0ed73fb010b0d0020f5a3e84357b44804a9b2a2425fa3328fd497aee8f` unchanged.
- Exact ELF byte-ownership report: `local/r67-14z-storeroom-report.json`.
- ISO build and full byte audit: `local/r67-14z-build.json`, `local/r67-14z-iso-audit.json`.
- Startup/history/save checks: `local/r67-14z-startup-raw.json`, `local/r67-14z-startup.json`, `local/r67-14z-history.json`, `local/r67-14z-save-static.json`.

The raw inherited legacy startup gate is **154/155**, because it expects the rejected overflowing save-warning wording from earlier releases. The existing explicit y bounded-reflow replacement passes **155/155** on z, without any other exemptions. History remains **4/4**. Game serial `SLPM-66511`, memory-card namespace `BISLPM-66511Save`, save serialization and all original card/savestate files are unchanged. Golden save cross-release runtime compatibility remains unverified.

### Release gate

The user has **approved r67.14y**, not yet the new r67.14z Storeroom translation. This diagnostic must be cold-booted and screenshotted showing (1) Storeroom name, (2) inscription wholly enclosed, centered and readable, and ideally (3) the already approved companion comment/save interface. Do not switch PCSX2 automatically or use old executable-bearing savestates across versions.

Until those screenshots are accepted, do not merge this new diagnostic. See `docs/R67_APPROVED_UI_CHANGE_CONTROL.md`: any future changes to already approved owners require an explicit user decision and a separate technical review of the exact native byte scope.
