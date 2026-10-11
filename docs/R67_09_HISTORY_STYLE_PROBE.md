# r67 — START-history font-style diagnostic (2026-10-10)

**Scope:** START dialogue-history only. **Status:** diagnostic, not a fix or release; visual acceptance pending.

## Evidence and renderer routing

- Pablo's paired screenshots show normal old-man dialogue horizontally while the START history shows one English character per row in two vertical columns.
- The native `y_AdvLog.c` / `ADV LOG PROC` registration at `0x255D90` calls history update callback `0x253840`. Its log-entry object is created through `0x255E10` (invoked from `0x253CF8`).
- `0x255E10` supplies font-style IDs `5`, `3`, and `4` at original ELF offsets `0x155ED4`, `0x155EE8`, and `0x155EFC`, respectively. These are history-specific code instructions, not shared dialogue text.
- The common factory `0x190A50` routes styles `0` and `1` to native `0x192400`, and styles `2` and higher to native `0x18F6F0`. Those two glyph-processing paths are structurally similar but have different glyph-positioning routines. **Font-style selection is a stronger candidate than the unsuccessful `0x259CD4` constructor shim; horizontal glyph advance is not yet proven.**
- The font-style data table at runtime `0x5D77D0` contains different glyph resource/size descriptors for styles `0/1` versus `2–5`. Switching style IDs may therefore alter font size and colors as well as glyph advance. A diagnostic result is necessary before adopting any production strategy.

## Bounded A/B diagnostic

- Original baseline: `local/r67-candidates/67.07-containment.iso`, SHA-256 `d5925fcf14959d041b0af45b38170f03e375eaefd43ccc9d089253a093acadfb`.
- Separate **diagnostic only**: `local/r67-candidates/67.08-history-style1-diagnostic.iso`, SHA-256 `f1e9af0e94808a9f7ad592e37bf02aed9faa4f62094a8bcd04c1447860517d70`.
- This experiment changes exactly **three bytes** inside installed `SLPM_665.11`: `0x155ED4:05→01`, `0x155EE8:03→01`, and `0x155EFC:04→01` (all `addiu a1,zero,style`). ISO image size and all other bytes are identical. No H.A.N.T., normal dialogue, graphics, controller art, save namespace, or companion text bytes changed.
- The installed baseline ELF is **not byte-identical** to the separately staged `local/r67-07-containment.elf` (2,563 differences in unrelated existing assets), so the diagnostic correctly patches the **verified installed ELF extracted from the baseline ISO**, rather than accidentally replacing the installed executable with the staged file.
- The current `tools.startup_acceptance` verifier reports `153/155` for **both** the baseline and diagnostic, with the same two startup-graphics failures: `graphics_BLBRD/B_GP020.BIN` and `startup_graphics_count` (`31/32`). Those failures are not introduced by the three-byte experiment; the earlier documented `155/155` requires reconciling the graphics acceptance fixture. Do not weaken acceptance rules.
- The diagnostic boots and displays the ordinary old-man dialogue in English horizontally. **A reliable screenshot of START history under the diagnostic has not yet been captured**. Therefore there is no claim that changing styles fixes vertical history.

## Isolated PCSX2 input lessons and safeguards

- The user objected to automated keystrokes affecting the YouTube tab in Edge. **Never send the previous global `M`/mute-capable keyboard sequence again.** Leave Edge's tabs, media and mute state untouched.
- PCSX2 was upgraded from v2.9.115 to v2.9.116. The latter resolves `-datapath <isolated path>` to **`<isolated path>/PCSX2/`**, including config at `PCSX2/inis/PCSX2.ini`. Earlier temporary keyboard edits under `<isolated path>/inis/PCSX2.ini` were therefore not loaded by v2.9.116. Both paths are inside the private worktree-local isolated profile; neither is the user's real PCSX2 profile.
- Temporary bindings in the actual nested profile use `V` (move forward), `Z` (START), `X` (Circle) and are designed not to trigger YouTube's `M` mute shortcut. Even with the nested config fixed, keyboard-only scripted tests have not yet produced a trustworthy START-history diagnostic frame; do not claim successful A/B validation.
- GUI tests were stopped, private PCSX2 process shut down, and Edge restored as foreground app. The copied slot-2 save still matches the original SHA-256: `15896a89c0cd2cb54af42cc15a5621fa9517217610a6ea22e05c8e34a73edfb4`.
- No ISO diagnostic, savestate, copyrighted asset, screenshot, or BIOS belongs in Git. Never merge PR #42 or tag a release based on this result.

## Only next step

Obtain one clear screenshot of the **START history under the style-1 diagnostic** using the user's physical 8BitDo controller or a verified isolated controller input path. Determine whether the rows become horizontal **without changing glyph content or damaging normal dialogue**. If the diagnostic changes orientation, develop a *history-only* production implementation with correct font metrics, X/Y and wrapping; if it fails, discard the three-byte hypothesis and continue tracing native `0x18F6F0` glyph advance. Keep the approved H.A.N.T. Basic Attack page immutable.
