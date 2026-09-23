# Localization status

This file is the authoritative runtime/localization ledger. Update a row only when new static or runtime evidence changes its state. Static verification never upgrades a surface to runtime-proven by itself.

Status meanings:

- **Working / runtime-proven** — observed in PCSX2 and accepted for the tested surface.
- **Translated but buggy** — English exists, but the runtime surface has a proven defect or unresolved transition.
- **Still Japanese / unresolved** — no safe accepted English implementation exists yet.
- **Not runtime-tested** — statically translated/verified but not yet observed successfully in PCSX2.

## Startup / first-play flow

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| 29 opening quotations (`TR000`-`TR028`) | **Working / runtime-proven** | English quotation artwork renders correctly. v7 repeatedly showed the same quotation, but the 29 generated TMXs have 29 distinct hashes and the executable explicitly selects `PRNG % 29` before formatting `TR%03d.TMX`. Repetition is therefore a runtime seed/PRNG behavior to investigate, not duplicated translation assets. |
| Pre-title memory-card status text | **Not runtime-tested** | v7 showed the Japanese stone-panel message. v8 maps the proven executable pointer-table entries to official English; the observed startup entry is `Checking memory card slot 1`. Re:charge-only clear-data entries without proven official correspondence remain Japanese/fail-closed. |
| GP088 startup/title artwork — direct `GP088_03` counterpart | **Not runtime-tested** | v8 ports the same-name official English `b_gp088_en/GP088_03` into PS2 `B_GP088.BIN`. |
| GP088 PS2 packed title atlas (`GP088_12`/`GP088_13`) | **Still Japanese / unresolved** | The screenshot's large Japanese title is represented by PS2-specific packed artwork. PS4 `GP088_10/11` are the corresponding JP/EN title variants, but their atlas transformation into PS2 `GP088_12/13` is not yet proven enough to automate. |
| Title `New Game` / `Load Game` | **Working / runtime-proven** | Runtime showed both exact English labels correctly. |
| Name-entry English button graphics (`B_GP019.BIN`) | **Working / runtime-proven** | Back/Edit/Finish/Delete/Confirm controls render correctly. |
| `Enter last name.` | **Working / runtime-proven** | Wide English prompt renders correctly. |
| Lowercase Latin keyboard | **Working / runtime-proven** | Runtime accepts lowercase Latin input. |
| Uppercase Latin keyboard | **Working / runtime-proven** | v7 runtime proved the PS2-adapted reachable rows expose uppercase alongside lowercase. |
| Name fields / permanent name storage | **Translated but buggy** | PS2 editor is structurally two 3-glyph permanent fields: two 6-byte buffers, six-position cursor, and split/layout/delete logic at position 3. `Habaki`/`Kuro` visibly truncate to `Hab`/`Kur`. No unsafe limit-only patch is applied. |
| `Enter first name.` | **Not runtime-tested** | Official wide English is statically present; the current runtime path has not produced a clean accepted observation of this prompt. |
| `Enter reading for last name.` | **Translated but buggy** | v7 relocated the full official string, but runtime displayed only `Enter`. Static tracing found the translation PT_LOAD was being overwritten by libkernel's stale `sbrk` heap break at `0x00902F00`. v8 moves that allocator break to `0x00A02F00`; runtime proof pending. |
| `Enter reading for first name.` | **Not runtime-tested** | v8 contains the full relocated official prompt in the now-protected translation segment; runtime has not reached/accepted it cleanly. |
| Reading-input states | **Translated but buggy** | States are active in the PS2 state machine. v7 showed corruption/truncation from the heap collision; v8 allocator fix is statically verified but not runtime-proven. |
| Finish/advance after name-reading input | **Translated but buggy** | v7 freezes when finishing the reading input. Static root cause is a translation-segment/heap collision: startup/ELF heap metadata moved to `0x00A02F00`, but libkernel's live heap-break word at file `0x650014` still pointed to `0x00902F00`. v8 patches all heap ownership sites; runtime must prove the freeze is gone. |
| `Is this fine?` / `Yes / No` | **Not runtime-tested** | Official English is statically present; currently blocked by the v7 freeze. |
| License-ID messages | **Not runtime-tested** | `Verifying license ID...` and `ID verification complete.` are statically present. |
| `Heracleion Shrine` | **Not runtime-tested** | Statically translated as wide executable text. |
| H.A.N.T. tutorial | **Not runtime-tested** | Official English is relocated into the executable translation PT_LOAD; v8 additionally protects that segment from the runtime allocator. |
| ADV horizontal dialogue renderer | **Not runtime-tested** | Four-instruction fail-closed renderer transform is present; v5 proved the pre-fix vertical failure. |
| First old-man DG00 English dialogue | **Not runtime-tested** | English MTX data is present and statically accepted; runtime has not reached it after the current startup blockers. |
| DG00 English choices | **Not runtime-tested** | Reviewed KSF overrides/imports are present; runtime has not reached them. |

## Known executable/UI text not yet solved

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| `Return above ground` | **Still Japanese / unresolved** | Exact official English is known, but the current compact executable slot cannot hold it safely. |
| `Report card` | **Still Japanese / unresolved** | Exact official English is known, but it does not fit the proven fixed slot. |
| `メディア` | **Still Japanese / unresolved** | No exact official dictionary mapping has been proven for this PS2-only label. |
| Re:charge-only memory-card clear-data messages | **Still Japanese / unresolved** | Eight pointer-table entries have no proven official remaster counterpart and remain untouched. |

## Corpus-level translation coverage

| Class | Status | Current evidence |
| --- | --- | --- |
| Exact mapped MTX | **Partially translated** | 962 files / 56,642 official English entries imported. 23 exact mapped files / 21,672 entries remain rejected because their localization semantics are indirect/dynamic. |
| Changed/template MTX | **Partially translated** | 7 files / 2,284 entries proven and imported. Consolidated FD00 remains the largest special class; only `FD00_31` is currently proven among the 26-file FD00 family. |
| KSF | **Partially translated** | 868 fitting official entries imported; 48 overflow entries and 4 ambiguous entries remain unresolved. |
| PS2-only text | **Still Japanese / unresolved** | Lexical proxy estimates 419 novel runs / 3,672 Japanese characters beyond reused mapped content. This is an estimator, not a dialogue-line percentage. |
| Broad graphics beyond startup | **Still Japanese / unresolved** | Indexed PS2 graphics porting is proven for normal same-layout classes. Structurally changed atlases, including the PS2 packed GP088 title atlas, require explicit transformation proof. |

## Candidate history

### v6 — runtime failed in name entry

Static verifier: 96/96. Runtime proved the quotation, title, name-entry graphics, `Enter last name.`, and lowercase keyboard. It then exposed the 3+3 name structure, inaccessible uppercase rows, a blank active reading prompt caused by our suppression, and a freeze after the hidden reading flow.

### v7 — runtime failed after improving name entry

- ISO SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`
- static acceptance: **98/98**

Runtime proved uppercase is now reachable and the last-name UI is substantially correct except for the intentional 3+3 structural limit. The next reading-input screen rendered only `Enter` even though the final ELF contained the complete relocated prompt, and finishing the state froze again. The startup memory-card/title screen also still showed Japanese. This run led to the libkernel heap-break discovery and the executable memory-card message classification.

### v8 — current static candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v8.iso`
- ISO SHA-256: `7431f7f44eb9ed14927f2181491b02217efe8675c64c4c07789d13ad934aa550`
- translated ELF size: 8,403,943 bytes
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`
- overlays: 1,144 total; 891 in place / 253 relocated
- executable itself relocated by the tested builder from outer extent 288 to 1,013,782 because it crossed the old sector allocation
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,144 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- dependency-free suite: **126 tests OK** (6 expected skips)
- Pillow suite: **126 tests OK** (1 owned-corpus skip)
- final-image startup acceptance: **120/120** (`local/startup-acceptance-v8.json`)

v8 adds three statically proven classes/fixes: the live libkernel heap break is moved out of the translation PT_LOAD, the proven memory-card pointer-table subset is relocated to official English, and the direct same-name GP088_03 English texture is ported. It deliberately does not guess the PS2-specific GP088_12/13 packed-title transformation or change the structural 3+3 name buffers.

## Runtime gate for v8

Do not launch PCSX2 automatically. Before launch, state the exact expected visual sequence and wait for Pablo's explicit approval.

The minimum v8 regression scope is:

1. an English opening quotation appears; the same quotation may repeat because seed behavior is not yet classified, but any Japanese quote is a failure;
2. the memory-card stone-panel message observed in v7 should now read `Checking memory card slot 1` rather than Japanese;
3. GP088_03 should use official English art where that texture is visible; the known PS2-specific GP088_12/13 title atlas may still display Japanese and must be captured rather than treated as solved;
4. `New Game` / `Load Game` remain correct;
5. `Enter last name.` remains correct, and both lowercase and uppercase Latin letters remain selectable; the 3+3 name-field limit is still expected;
6. the corrupted `Enter` screen must now show the full `Enter reading for last name.` prompt;
7. the next active reading prompt must show full `Enter reading for first name.`;
8. finishing the reading flow must advance to `Is this fine?` / `Yes / No` instead of freezing;
9. if it advances, continue through license verification, `Heracleion Shrine`, H.A.N.T., choices, and the first old-man dialogue; any Japanese, corrupted/truncated text, or vertical English dialogue is a failed checkpoint.
