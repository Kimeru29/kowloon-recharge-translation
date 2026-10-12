# r67.14x — Generic companion event-bubble normalization

**Diagnostic only. Await visual approval; no commit, push, PR or merge.**

## User requirements

All automatic companion event dialogues, not just opening or Chamber-specific lines, must stay inside the green bubble. Existing correct dialogue, including “Eerie place.”, approved Lion Statue and Stone tablets, must not regress. The separate H.A.N.T. Jumping visual issue is tracked as [GitHub #43](https://github.com/Kimeru29/kowloon-recharge-translation/issues/43) and intentionally not modified by this release.

## Native ownership

The original 601 normal event records (`s0+4 < 0x259`) share the bubble constructor at EE `0x166070–0x166134`. The separately approved 600 Re:charge AFK/free-talk records (`>= 0x259`) use other specialized wrapping and resource-geometry hooks.

The native green sprite shape is 288×80, pivot Y=77, native anchor Y=346; text Y=280/300 produces insets 11/31 relative to the frame top. The earlier 58-unit offset is **companion X**, not Y. r67.14u/v's Y shift was incorrect. Action/AFK rendering mutates shared sprite metadata, so the normal event constructor may read stale dimensions.

## r67.14x implementation

Starting from exact SHA-pinned, accepted r67.14t rather than rejected u/v or record-specific w, substitute only the original native event constructor store instruction at EE `0x16606C` with a JAL into one append-only 188-byte MIPS helper. It performs the original store, checks the **generic event-family boundary** and valid companion slot, then restores the selected green 0x68/0x69 and all blue 0x6A animation frames to native width, height and pivots immediately before sprite construction. The existing delay slot `lh v1,0x2F8(s0)`, original English Y 280/300, per-record text, source pointers, font, timer, event segmentation, story/save data, AFK and action UI are unchanged. No room, string, subrow or record-specific cases remain.

Source: `tools/r67_14x_generic_event_bubble.py`. Scoped unchanged-q/t preservation: `tools/r67_14x_scoped_approval_lock.py`. Tests: `tests/test_r67_14x_generic_event_bubble.py`.

Tests **execute the actual compiled MIPS helper** for all **601 original event IDs × both slots × both row indices** and for **600 AFK IDs × both slots**; validate original native geometry in the former and absolutely no geometry mutations in the latter. Tests include invalid slots, source SHA pinning, original Y identity and old approved q/t UI locks.

Original q's strict code-region lock correctly rejects the one intentionally modified constructor word. The scoped lock restores that word **in memory only**, then runs the original unchanged q and t manifests, preserving four q regions, approved Lion Statue scale 0.72 and 58 tablets / 160 bounded inscription rows. The old manifests were not changed or regenerated.

## Validation

- Full suite: **433 tests run; 18 expected skips; no failures** (`local/r67-14x-full-regression.log`).
- Startup acceptance: **155/155** (`local/r67-14x-startup.json`).
- History locks: **4/4**, both staged ELF and finished ISO.
- Full **2,095,382,528-byte** finished ISO comparison versus r67.14t: **0 unexplained bytes**. Only one original native JAL (4 changed bytes), appended helper (139 nonzero new bytes), ELF size (1 changed byte) and ISO9660 ELF size metadata (4 changed bytes). Report `local/r67-14x-whole-iso-audit.json`.
- Stage ELF SHA-256: `20dde0425125af1b4729b6ecd0dacbb77e63d9f70c33bcf3558f2d9a46e7bd44`.
- Candidate: `local/r67-candidates/67.14x-generic-companion-bubble.iso`.
- ISO SHA-256: `5ea1fa67d972b00ab499f0ac27bbc4308f51cd11a929b3fdd6741f9f9ee79a13`.
- Build reports: `local/r67-14x-iso-report.json`, `local/r67-14x-build.json`, `local/r67-14x-generic-event-bubble-report.json`.

**Still unverified:** Real PCSX2 rendering of the specific **post-Chamber** message, all opening/short original events and other companions. Static instruction simulation cannot prove that no later frame mutates live sprite metadata. Use a cold-boot r67.14x and check the opening two-line bubble, “Eerie place.”, the post-Chamber failed comment, another companion and AFK where possible. No active PCSX2 session/settings or original cards/savestates were touched; no true cross-release golden save runtime verification exists yet.
