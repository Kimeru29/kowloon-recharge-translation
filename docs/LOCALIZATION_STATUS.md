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
| 29 opening quotations (`TR000`-`TR028`) | **Working / runtime-proven** | v10 runtime confirmed English quotation artwork and observed different quotations across restarts. The 29 generated TMXs remain distinct and the executable selects `PRNG % 29` before formatting `TR%03d.TMX`. |
| Pre-title memory-card status text | **Translated but buggy** | v11 runtime showed the official `Checking memory card slot 1` text reaching the stone panel but clipping horizontally. v11-r4 intentionally does **not** change this surface: the accepted single-line official payload and both boot-handler aliases (`0x4077F0`, `0x4078D0`) remain as before. The clipping defect is still pending outside the r4 four-defect scope. |
| GP088 startup/title artwork — direct `GP088_03` counterpart | **Not runtime-tested** | v9 retains the v8 same-name official English `b_gp088_en/GP088_03` port into PS2 `B_GP088.BIN`. |
| GP088 PS2 packed title atlas (`GP088_12`) | **Not runtime-tested** | v9 proves that the two GP088_12 Japanese title variants are repacked GP088_03 regions (Dice 0.8758 / 0.8765 after excluding the known flattened banner band), then rebuilds GP088_12 from the official English GP088_03 regions. The official English remaster omits the flattened gold `re:charge` banner, so v9 removes it rather than synthesizing missing artwork. `GP088_13` is a separate already-English blue `re:charge` badge and remains unchanged. |
| Title `New Game` / `Load Game` | **Not runtime-tested** | v10 runtime proved the exact strings but exposed the undersized purple backing. v11 statically ties the backing to the paired GP088_12 title objects and widens only their animation target to `17/9`; `title_english_backing_geometry` passes in the final ISO. The resized presentation still needs PCSX2 observation. |
| Name-entry English button graphics (`B_GP019.BIN`) | **Working / runtime-proven** | Back/Edit/Finish/Delete/Confirm controls render correctly. |
| `Enter last name.` | **Working / runtime-proven** | Wide English prompt renders correctly. |
| Lowercase Latin keyboard | **Working / runtime-proven** | Runtime accepts lowercase Latin input. |
| Uppercase Latin keyboard | **Working / runtime-proven** | v7 runtime proved the PS2-adapted reachable rows expose uppercase alongside lowercase. |
| Name fields / permanent name storage | **Translated but buggy** | v10 still shows the structural two-3-glyph permanent-name behavior. The editor uses two 6-byte buffers, a six-position cursor, and split/layout/delete logic at position 3; `Habaki`/`Kuro` truncate to `Hab`/`Kur`. This remains explicitly out of scope for v11. |
| `Enter first name.` | **Not runtime-tested** | Official wide English is statically present; the current runtime path has not produced a clean accepted observation of this prompt. |
| `Enter reading for last name.` | **Translated but buggy** | The log-confirmed v8 run proved the allocator fix: the full official string survived, but the PS2 two-byte-cell renderer clipped it at the right edge (`Enter reading for las...`). v10 no longer enters this PS2-only kana-reading editor during the English flow, so this prompt should be unreachable rather than cosmetically shortened. |
| `Enter reading for first name.` | **Not runtime-tested** | The exact official prompt remains present in the protected translation segment for provenance, but v10 should bypass the kana-reading pass before this screen is reached. |
| Reading-input states | **Translated but buggy** | The log-confirmed v8 run reached the PS2 reading editor and showed that its prompt now survives but clips. Reverse engineering proved this is a kana-specific second pass backed by `name/namedic.bin`; v10 reuses the existing post-reading transition and skips the pass entirely for English. |
| Finish/advance after name-reading input | **Translated but buggy** | The log-confirmed v8 run still remained stuck after Finish, so the old heap collision was not the only flow defect. State 9 passes flag `0` to the shared `M_Name` transition and deliberately enters the kana-reading editor; state 11 passes flag `1` to the same routine and commits/finalizes. v10 changes only the state-9 flag to `1`, with exact instruction preimage checks, so English should skip the problematic reading phase. Runtime proof pending. |
| `Is this fine?` / `Yes / No` | **Not runtime-tested** | Official English is statically present. v10 preserves the normal-name confirmation; an affirmative result now routes directly through the existing post-reading/finalization path instead of opening the kana-reading editor. |
| License-ID messages | **Not runtime-tested** | `Verifying license ID...` is the runtime-good 23-glyph reference at X=140. v11-r4 keeps both official strings and moves only the 25-glyph `ID verification complete.` X owner from 156 to 108 so both lines end at the same 508-pixel right edge in the traced 16-pixel renderer. The instruction preimage and final image are fail-closed; runtime proof of the unclipped completion line is pending. |
| `Heracleion Shrine` | **Not runtime-tested** | Statically translated as wide executable text. |
| H.A.N.T. tutorial | **Translated but buggy** | Original v11 runtime disproved the 16px presentation: the live page exposed only about 336 usable horizontal pixels and the 16-row reflow clipped vertically. v11-r4 switches only this mode-4 tutorial row constructor from existing font style 0 (16px) to existing style 1 (12px), giving a 28-cell budget across the same proven pixel span. The accepted wording now reflows to 14 rows with controller holes on rows 6/9/12; row spacing remains 21px and original sources stay pristine. Final-image checks pass; target-screen proof is pending. |
| ADV horizontal dialogue renderer | **Translated but buggy** | Original v11 runtime proved the coordinate-origin swap was insufficient. Follow-up tracing showed the DG object constructs four font canvases and propagates one wrapper orientation argument to all four; r3 changed only a downstream canvas and therefore could leave speaker/body canvases vertical. v11-r4 keeps the proven coordinate transpose and changes the unique wrapper callsite at file `0x14E96C` from `a2=1` to `a2=0`, so all four DG canvases inherit horizontal advance. Final-image acceptance passes; corrected dialogue still needs runtime target-screen proof. |
| First old-man DG00 English dialogue | **Translated but buggy** | The DG00 English content itself is runtime-proven, but original v11 still rendered it vertically. v11-r4 contains the upstream all-canvas orientation correction described above. The r4 ISO has **not** been launched in PCSX2; the old-man target screen still requires supervised runtime observation. |
| DG00 English choices | **Not runtime-tested** | Reviewed KSF overrides/imports remain present; the accepted v10 observation did not explicitly promote this row. |
| H.A.N.T. chrome labels | **Not runtime-tested** | v11-r4 proves the independent seven-entry live H.A.N.T. chrome owner table at file `0x586D20` and relocates `【Main Menu】`, `【Mail】`, `【Dictionary】`, `【Enemy】`, `【Memo】`, `【Help】`, and `【Config】` through those pointers. The owned remaster extraction does not expose the localized TextAsset, so these seven are explicitly **semantic translations**, not claimed official-remaster wording. Runtime proof is pending. |
| Command/menu labels | **Not runtime-tested** | v11 replaces fit-driven patches with the 19-label semantic manifest and 21-entry pointer ownership table. Fixed labels use accepted English; `Return above ground` and `Report card` relocate through their proven aliases; unresolved `メディア` remains intentionally Japanese. All three menu acceptance classes pass, but runtime semantics/layout still need observation. |

## Known executable/UI text not yet solved

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| `メディア` | **Still Japanese / unresolved** | No exact official dictionary mapping has been proven for this PS2-only label. |
| Additional pointer-backed H.A.N.T. candidates outside the tutorial | **Still Japanese / unresolved** | Ownership candidates are inventoried, but the expected local `English.bytes` extraction was unavailable during the proof pass; no mapping is guessed. |
| Re:charge-only memory-card clear-data messages | **Still Japanese / unresolved** | Eight pointer-table entries have no proven official remaster counterpart and remain untouched. |

## Corpus-level translation coverage

| Class | Status | Current evidence |
| --- | --- | --- |
| Exact mapped MTX | **Partially translated** | 962 files / 56,642 official English entries imported. 23 exact mapped files / 21,672 entries remain rejected because their localization semantics are indirect/dynamic. |
| Changed/template MTX | **Partially translated** | 7 files / 2,284 entries proven and imported. Consolidated FD00 remains the largest special class; only `FD00_31` is currently proven among the 26-file FD00 family. |
| KSF | **Partially translated** | 868 fitting official entries imported; 48 overflow entries and 4 ambiguous entries remain unresolved. |
| PS2-only text | **Still Japanese / unresolved** | Lexical proxy estimates 419 novel runs / 3,672 Japanese characters beyond reused mapped content. This is an estimator, not a dialogue-line percentage. |
| Broad graphics beyond startup | **Still Japanese / unresolved** | Indexed same-layout ports and a generalized fail-closed atlas-repack class are now proven. Other structurally changed atlases still require their own correspondence/layout proof before import. |

## Candidate history

### v6 — runtime failed in name entry

Static verifier: 96/96. Runtime proved the quotation, title, name-entry graphics, `Enter last name.`, and lowercase keyboard. It then exposed the 3+3 name structure, inaccessible uppercase rows, a blank active reading prompt caused by our suppression, and a freeze after the hidden reading flow.

### v7 — runtime failed after improving name entry

- ISO SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`
- static acceptance: **98/98**

Runtime proved uppercase is now reachable and the last-name UI is substantially correct except for the intentional 3+3 structural limit. The next reading-input screen rendered only `Enter` even though the final ELF contained the complete relocated prompt, and finishing the state froze again. The startup memory-card/title screen also still showed Japanese. This run led to the libkernel heap-break discovery and the executable memory-card message classification.

### v8 — historical candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v8.iso`
- ISO SHA-256: `7431f7f44eb9ed14927f2181491b02217efe8675c64c4c07789d13ad934aa550`
- translated ELF size: 8,403,943 bytes
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`
- overlays: 1,144 total; 891 in place / 253 relocated
- executable ROFS records: 1,144 patched/re-resolved
- dependency-free suite: **126 tests OK** (6 expected skips)
- Pillow suite: **126 tests OK** (1 owned-corpus skip)
- final-image startup acceptance: **120/120** (`local/startup-acceptance-v8.json`)

v8 fixed the live libkernel heap break, relocated the proven memory-card pointer-table subset, and ported direct GP088_03 English art. It was initially superseded by v9 as the static candidate; a later emulator log identified the supervised runtime session as v8, documented below.

### v9 — historical static candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v9.iso`
- ISO SHA-256: `6770862cbde8edf301afdef7778d440c0d2eab99806d732724afc6ef5a279d76`
- translated ELF size: 8,403,943 bytes
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`
- overlays: 1,144 total; 891 in place / 253 relocated
- executable relocated from outer extent 288 to 1,013,782
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,144 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- dependency-free suite: **130 tests OK** (8 expected skips)
- Pillow suite: **130 tests OK** (1 owned-corpus skip)
- final-image startup acceptance: **121/121** (`local/startup-acceptance-v9.json`)

v9 adds the generalized `RegionTransfer` atlas-repack renderer class and applies it to GP088_12. The pristine GP088_03→GP088_12 relationship is fail-closed at Dice ≥0.82; the actual source scores are 0.8758 and 0.8765 with the flattened banner band excluded. The generated PS2 GP088_12 contains only the two official-English vertical title variants, `Kowloon High School Chronicle` and `Huanglong High School Chronicle`; no Japanese title pixels or reconstructed banner art are retained. The later PCSX2 log proved the latest runtime session actually booted v8, not v9, so this v9-only GP088_12 change remains untested at runtime.

### v8 — log-confirmed runtime follow-up

The latest supervised PCSX2 session was identified from the emulator log as `/private/tmp/kowloon-recharge-startup-en-v8.iso`. Opening quotation rotation was runtime-proven, existing title/name-entry/Latin-keyboard behavior remained good, but the memory-card stone panel was still Japanese. The protected reading prompt now rendered its full payload but clipped at the right edge, and the flow remained stuck after finishing that screen. Because v8 and v9 share the same final executable SHA-256 (`5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`), those executable defects also apply to v9; only v9's GP088_12 graphics differ.

### v10 — runtime-tested checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v10.iso`
- ISO SHA-256: `24d425433af97b1617e820cac05aa2a4d9389aa9fa19c1767a57eb763812da8e`
- translated ELF size: 8,403,943 bytes
- final post-ROFS ELF SHA-256: `e276442dc435034c59d471f6aad4b1eab7c0a4679f68717d4a3a5a3808b345a0`
- overlays: 1,144 total; 891 in place / 253 relocated
- executable relocated from outer extent 288 to 1,013,782
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,144 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- dependency-free suite: **134 tests OK** (8 expected skips)
- Pillow suite: **134 tests OK** (1 owned-corpus skip)
- final-image startup acceptance: **123/123** (`local/startup-acceptance-v10.json`)
- deterministic rebuild: second pristine build has the same SHA-256 and is byte-for-byte identical (`cmp`)

v10 adds two fail-closed runtime-path fixes. Memory-card entry 1 repoints the proven `H_BootMcardChk`/`H_EmptyMcardChk` aliases as well as the main table. The English name flow changes only the state-9 flag word from `0` to `1`, reusing the game's existing post-reading transition so the PS2 kana-reading editor is skipped; all four dispatcher words are validated before patching.

The supervised v10 run advanced through the startup/name flow into the first old-man scene. It established the v11 baseline: opening quote rotation is working; `New Game` / `Load Game` text is correct but its backing geometry is buggy; first-old-man DG00 English content is runtime-proven content, vertical-layout bug; H.A.N.T. is partially translated and clips; menus are mixed translated/awkward/unresolved; and the 3+3 name-storage behavior remains buggy and out of scope.

## v10 runtime result

The supervised v10 launch has now occurred. Do not launch PCSX2 again automatically; future emulator launches still require an exact expected-visual checklist and Pablo's explicit approval.

The pre-launch v10 checklist remains useful as a historical regression reference. v10 passed the startup/name progression needed to reach gameplay, but failed presentation checkpoints for title backing, H.A.N.T. clipping/completeness, menu semantics, and horizontal DG dialogue:

The minimum v10 regression scope was:

1. an English opening quotation appears; restarts may show different English quotations, and any Japanese quotation is a failure;
2. the pre-title stone-panel message must read `Checking memory card slot 1`; Japanese here means the boot-handler alias fix failed;
3. the red-sky/title sequence must no longer show the large Japanese Kowloon title: GP088_12 should show the vertical English `Kowloon High School Chronicle` / `Huanglong High School Chronicle` variants. The old flattened gold `re:charge` banner is intentionally absent; the separate blue `re:charge` badge may appear;
4. `New Game` / `Load Game` remain correct;
5. the normal name editor shows `Enter last name.` / `Enter first name.` as the cursor crosses the original 3+3 fields, with both lowercase and uppercase Latin selectable. The 3+3 limit (`Hab` / `Kur`) remains expected;
6. after accepting the normal-name confirmation, **no `Enter reading ...` screen should appear**. The game must bypass the PS2 kana-reading editor without clipping or freezing;
7. the flow should continue through `Verifying license ID...`, `ID verification complete.`, and `Heracleion Shrine`;
8. the H.A.N.T. tutorial must be English;
9. DG00 choices must be English;
10. the first old-man dialogue must be horizontal English, including `Old man's voice`, `Hey, over here.`, `Old merchant Salah`, `This is the Heracleion temple.`, `First, it would be a good idea to`, and `check H.A.N.T.`.

Any Japanese in the tested startup slice, corrupted/clipped text, appearance of the reading editor, freeze, wrong name state, or vertical English dialogue is a failed checkpoint.


### v11 — runtime failed presentation acceptance

- path: `/private/tmp/kowloon-recharge-startup-en-v11.iso`
- ISO SHA-256: `4150414b817fe54cf90ac28887568a37c6910995d7f8bc46e6887a6c4f6ef516`
- final-image startup acceptance: **130/130** (`local/startup-acceptance-v11.json`)
- deterministic rebuild: byte-for-byte identical

The supervised v11 screenshots disproved two static renderer assumptions despite the clean verifier. ADV fragments had their origins transposed, but their font objects still carried orientation `a2=1`, so characters continued advancing vertically. H.A.N.T. was wrapped for a theoretical 26-cell canvas, while the live page exposed only about 21 cells; English clipped and one page was effectively blank. The pre-title memory-card wording was English but also clipped as a single line. Japanese H.A.N.T./Help chrome remained visible; those broader owners stay unresolved because the required official `English.bytes` corpus is absent.

### v11-r3 — superseded correction candidate, target-screen proof pending

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r3.iso`
- ISO SHA-256: `bbc7fa247288769679b1d41d83d5aba001ff194c9070825c7534b6af56097245`
- translated ELF SHA-256 before ROFS rewrite: `5f7cbe627cdffbc52c55ce6ab2908732590c4d62f1200f81026db82396ffc711`
- final post-ROFS ELF SHA-256: `17c3858f45ac26ac864cfe2e6434a05f7ee934d18d1ac2e74f0b59ac225b24f0`
- translated/final ELF size: 8,403,932 bytes
- overlays: 1,144 total; 891 in place / 253 relocated
- executable relocated from outer extent 288 to 1,013,782
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,144 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- full suites: **178 tests OK** in both measured environments (8 expected local-dependency skips in each)
- final-image startup acceptance: **130/130** (`local/startup-acceptance-v11-r3.json`)
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r3-repeat.iso` has the same SHA-256 and is byte-for-byte identical (`cmp`)
- PCSX2 boot identity: log-confirmed exact `v11-r3` ISO, game CRC `6AF4B773`; boot reached the normal startup sequence.
- runtime status: **target screens not yet re-observed**; no ADV/H.A.N.T./memory-card presentation fix is promoted to runtime-proven yet.

v11-r3 corrects the runtime-disproven mechanics rather than adding another cosmetic approximation. The ADV dialogue-fragment constructor now clears the vertical-advance orientation only for the proven DG fragment object while preserving the existing coordinate formulas/progress callback. H.A.N.T. uses the runtime-observed 21-cell viewport and 16-row budget, omitting only redundant presentation rows while preserving accepted body/instruction wording and controller holes at rows 8/11/14. The memory-card entry keeps the exact official wording but uses the already-supported line-break token as `Checking memory card` / `slot 1`.

The r3 target screens were never re-observed, so its presentation changes remain historical static hypotheses rather than runtime proof.

### v11-r4 — historical deterministic correction candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r4.iso`
- ISO SHA-256: `3566b2395165cf4ba4b34ebed874ba405f17c0d452753786cfc116ed80c494bb`
- translated ELF SHA-256 before ROFS rewrite: `4501cee41d3941d40c687f9806b51aa0196f6c206132fd6614f3bbe8ee461a43`
- final post-ROFS ELF SHA-256: `54690aed73a68d19e8b1fcd787e346086fbd3bb30dd9dea9b39b99acf93d3d9f`
- translated/final ELF size: 8,404,046 bytes
- overlays: 1,144 total; 891 in place / 253 relocated
- executable relocated from outer extent 288 to 1,013,782
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,144 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- dependency-free suite: **182 tests OK** (8 expected local/optional-dependency skips)
- Pillow-enabled suite: **182 tests OK** (1 owned-corpus skip)
- final-image startup acceptance: **132/132** (`local/startup-acceptance-v11-r4.json`)
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r4-repeat.iso` has the same builder SHA-256 and is byte-for-byte identical (`cmp`)
- PCSX2 status: **not launched** for r4; no r4 target screen is runtime-proven yet.

v11-r4 was intentionally limited to its four runtime defects while preserving the already-improved title/tablet geometry. It moves the license-completion X owner from 156 to 108, changes the unique DG wrapper orientation argument from vertical to horizontal for all four font canvases, changes only the mode-4 H.A.N.T. tutorial rows to the existing 12px font style and 28-cell/14-row reflow, and relocates the seven proven H.A.N.T. chrome labels with explicitly semantic English wording. The r3 memory-card wrapping experiment is **not** included; the known memory-card clipping remains a separate issue.

The next supervised r4 runtime acceptance should verify exactly these targets plus regression safety: `ID verification complete.` is fully visible; the H.A.N.T. tutorial is compact/readable with no bottom clipping and its seven chrome labels are English; the first old-man dialogue is horizontal; and the previously accepted title/tablet centering remains unchanged. Memory-card clipping is not an r4 acceptance criterion.


### v11-r5 — current deterministic correction candidate; Pablo runtime test pending

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r5.iso`
- ISO SHA-256: `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`
- translated ELF SHA-256 before ROFS rewrite: `6e385c38fd012d8d11a5e3f0f20220412506ed6aa43b75b8bd712035365a28fa`
- final post-ROFS ELF SHA-256: `c3b228c946df9bae9d8aec81058a04801de1483191c28d5077087e1d9c2d3eee`
- translated/final ELF size: 8,404,478 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **137/137** (`local/startup-acceptance-v11-r5.json`)
- dependency-free suite: **191 tests OK** (8 expected skips)
- Pillow-enabled suite: **191 tests OK** (1 owned-corpus skip)
- deterministic repeat ISO: byte-for-byte identical by `cmp`
- PCSX2 status: **not launched**; Pablo will perform the runtime checks manually.

r5 preserves the r4 title/tablet geometry and adds only the remaining screenshot-driven fixes. The separate speaker-name canvas now receives horizontal orientation independently of the body canvas. The H.A.N.T. tutorial retains the 12px/28-cell reflow but uses an 18px row stride; the 15 Help index aliases relocate to semantic English; and `GRP020/GP020_03.TMX` repaints nine baked caption regions to semantic English while preserving all non-caption pixels. The pre-title memory-card text now uses two visible lines: `Checking memory card` and `slot 1`.

Manual acceptance targets: speaker label and dialogue body horizontal; full H.A.N.T. page visible vertically; Help/topic list and H.A.N.T. tile captions English; stone-panel text not clipped; title/tablet centering unchanged.
