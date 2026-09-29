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
| Pre-title memory-card status text | **Working / runtime-proven** | r8 runtime accepts the lower/better-balanced tablet presentation. Preserve the exact r8 payload and centered `slot 1`; r11 does not touch this path. |
| GP088 startup/title artwork — direct `GP088_03` counterpart | **Not runtime-tested** | v9 retains the v8 same-name official English `b_gp088_en/GP088_03` port into PS2 `B_GP088.BIN`. |
| GP088 PS2 packed title atlas (`GP088_12`) | **Not runtime-tested** | v9 proves that the two GP088_12 Japanese title variants are repacked GP088_03 regions (Dice 0.8758 / 0.8765 after excluding the known flattened banner band), then rebuilds GP088_12 from the official English GP088_03 regions. The official English remaster omits the flattened gold `re:charge` banner, so v9 removes it rather than synthesizing missing artwork. `GP088_13` is a separate already-English blue `re:charge` badge and remains unchanged. |
| Title `New Game` / `Load Game` | **Working / runtime-proven** | Pablo manually accepted v11-r11: both English labels render correctly and the widened backing rectangles now have the correct width/presentation. Preserve the r11 owner correction: shared backing width 152px, U extent 152/512, backing X=24/336, and accepted text X=36/340. |
| Name-entry English button graphics (`B_GP019.BIN`) | **Working / runtime-proven** | Back/Edit/Finish/Delete/Confirm controls render correctly. |
| `Enter last name.` | **Working / runtime-proven** | Wide English prompt renders correctly. |
| Lowercase Latin keyboard | **Working / runtime-proven** | Runtime accepts lowercase Latin input. |
| Uppercase Latin keyboard | **Working / runtime-proven** | v7 runtime proved the PS2-adapted reachable rows expose uppercase alongside lowercase. |
| Name fields / permanent name storage | **Translated but buggy** | v10 still shows the structural two-3-glyph permanent-name behavior. The editor uses two 6-byte buffers, a six-position cursor, and split/layout/delete logic at position 3; `Habaki`/`Kuro` truncate to `Hab`/`Kur`. This remains explicitly out of scope for v11. |
| `Enter first name.` | **Working / runtime-proven** | r7 runtime confirms the centered English name-entry presentation looks good. Preserve the shared last/first-name geometry; r8 does not modify this path. |
| `Enter reading for last name.` | **Translated but buggy** | The log-confirmed v8 run proved the allocator fix: the full official string survived, but the PS2 two-byte-cell renderer clipped it at the right edge (`Enter reading for las...`). v10 no longer enters this PS2-only kana-reading editor during the English flow, so this prompt should be unreachable rather than cosmetically shortened. |
| `Enter reading for first name.` | **Not runtime-tested** | The exact official prompt remains present in the protected translation segment for provenance, but v10 should bypass the kana-reading pass before this screen is reached. |
| Reading-input states | **Translated but buggy** | The log-confirmed v8 run reached the PS2 reading editor and showed that its prompt now survives but clips. Reverse engineering proved this is a kana-specific second pass backed by `name/namedic.bin`; v10 reuses the existing post-reading transition and skips the pass entirely for English. |
| Finish/advance after name-reading input | **Translated but buggy** | The log-confirmed v8 run still remained stuck after Finish, so the old heap collision was not the only flow defect. State 9 passes flag `0` to the shared `M_Name` transition and deliberately enters the kana-reading editor; state 11 passes flag `1` to the same routine and commits/finalizes. v10 changes only the state-9 flag to `1`, with exact instruction preimage checks, so English should skip the problematic reading phase. Runtime proof pending. |
| `Is this fine?` / `Yes / No` | **Working / runtime-proven** | r10 runtime confirms the focus correction: all of `Yes` is visible and `No` remains correct. Preserve selected-Yes X=192, separator child 3, and accepted No X=272; r11 does not touch this path. |
| License-ID messages | **Working / runtime-proven** | r7 runtime confirms the centered license/name screen looks good. Preserve `Verifying license ID...` at X=72 and `ID verification complete.` at X=56; r8 does not modify either owner. |
| `Heracleion Shrine` | **Not runtime-tested** | Statically translated as wide executable text. |
| H.A.N.T. tutorial | **Working / runtime-proven** | r9 runtime accepts the actual H.A.N.T. page: translated content, 12px font, 16px page-local row spacing and controller presentation all look good. Freeze this path. |
| ADV horizontal dialogue renderer | **Working / runtime-proven** | Pablo manually accepted v11-r11: English dialogue is horizontal and the speaker/body composition and formatting look correct. Preserve speaker X=20/Y=276, primary body X=20/Y=300/316/332, and the proven 12px secondary-fragment spacing. Moving the block slightly lower is optional future polish, not an active defect. |
| First old-man DG00 English dialogue | **Working / runtime-proven** | Pablo manually accepted v11-r11's first dialogue presentation: English body text is horizontal and correctly formatted under the speaker. Preserve the r11 primary body canvases at X=20,Y=300/316/332. |
| DG00 English choices | **Not runtime-tested** | Reviewed KSF overrides/imports remain present; the accepted v10 observation did not explicitly promote this row. |
| H.A.N.T. top-level six tiles (`GP020_03`) | **Working / runtime-proven** | r5 runtime confirms `MAIL`, `DICTIONARY`, `ENEMY`, `MEMO`, `HELP`, and `CONFIG` look good. Preserve the semantic baked-art repaint and do not route these captions back through executable text. |
| H.A.N.T. executable chrome labels | **Working / runtime-proven** | r9 runtime accepts the H.A.N.T. menus/submenus as presented. Preserve the seven-entry translated chrome owner table. |
| H.A.N.T. Help category/topic labels + navigation | **Working / runtime-proven** | v11-r11 manual runtime confirms the Help category/topic menu presentation is substantially English and navigation works. Preserve all **55 topic labels** and the three-tab owner including `Ruins`. This status applies to labels/navigation only, not selected topic body text. |
| H.A.N.T. selected Help topic bodies | **r13 runtime-proven text; r14 layout pending** | r13 proves the promoted bodies render English, but the controller/icon metadata still follows Japanese geometry and can overlap the translated rows. r14 relocates each proven metadata leaf into the measured 12px/16px English geometry while preserving icon identity and sentinels. |
| H.A.N.T. Config labels / values | **r13 runtime-proven text; r14 presentation pending** | r13 proves the labels/values/ringtones are English but still use Japanese style 0 at live constructors. r14 switches the proven Config constructors to existing 12px style 1. |
| H.A.N.T. Mail empty state | **r13 runtime-proven text; r14 positioning pending** | r13 proves the empty state is English but visually off-center. r14 accounts for its fixed fifth-row X owner, uses `   No mail received.`, and retargets the direct count/status materialization to `Mail (New)`. Non-empty mail remains separate. |
| H.A.N.T. Enemy category tabs | **r13 runtime-proven text; r14 spacing pending** | r13 proves `Small / Large / Human` are live but the 40px Japanese cadence overlaps in English. r14 widens the three proven X owners and switches the category renderer to 12px style 1. |
| H.A.N.T. Dictionary tabs + term lists | **r13 runtime-proven text; r14 presentation pending** | r13 proves the Latin tabs and 208 translated/romanized terms are live, but their list/tab constructors still use Japanese style 0. r14 switches the proven constructors to 12px style 1. Selected definition pages are tracked separately. |
| H.A.N.T. Dictionary selected definitions | **r13 runtime-proven Japanese; r14 translation pending** | r13 proves selected terms open a separate detail-leaf class. r14 promotes only the observed `King Akhenaten` and `Heracleion` descriptors/tables and switches their line renderer to 12px style 1; the other 206 leaves remain unresolved. |
| Command/menu labels | **Not runtime-tested** | v11 replaces fit-driven patches with the 19-label semantic manifest and 21-entry pointer ownership table. Fixed labels use accepted English; `Return above ground` and `Report card` relocate through their proven aliases; unresolved `メディア` remains intentionally Japanese. All three menu acceptance classes pass, but runtime semantics/layout still need observation. |

## Known executable/UI text not yet solved

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| `メディア` | **Still Japanese / unresolved** | No exact official dictionary mapping has been proven for this PS2-only label. |
| Remaining H.A.N.T. content | **Still Japanese / unresolved** | r14 covers the runtime-observed Config values/ringtones, empty-Mail state/chrome, Enemy category tabs, Dictionary tabs/208 selectable terms, and the two observed definition leaves. Unobserved/independent content remains fail-closed, including non-empty Mail subjects/bodies and the other 206 Dictionary definition leaves. |
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


### v11-r5 — runtime-tested presentation checkpoint

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
- PCSX2 status: **manually runtime-tested by Pablo**.

r5 established the new runtime ground truth. The GP020 top-level tiles (`MAIL`, `DICTIONARY`, `ENEMY`, `MEMO`, `HELP`, `CONFIG`) look good and the 12px/18px H.A.N.T. tutorial body has good spacing; both are now preservation constraints. The two-line stone-tablet message is noticeably better but still eligible for later measured polish. The title still looks bad. The old-man body can emit horizontal English, but the visible speaker/name layout remains structurally wrong. Deeper H.A.N.T. Help/submenu labels remain Japanese, proving the 15-entry r5 Help table was incomplete.

### v11-r6 — runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r6.iso`
- ISO SHA-256: `dbd25ff8ada4724d6c280a32199dd3ef7fc49442923d904db56359ed02ef32a4`
- translated ELF SHA-256 before ROFS rewrite: `06b76b01e9ef1364f5c67473edaf1b68b367512ba0af7dd1ad533f726b64ecfa`
- final post-ROFS ELF SHA-256: `0fe52d198679c9c2eb4784cab12a554f4569488af018fd9778c3b72ca031b0eb`
- translated/final ELF size: 8,405,736 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **139/139** (`local/startup-acceptance-v11-r6.json`)
- dependency-free suite: **198 tests OK** (8 expected skips)
- Pillow-enabled suite: **198 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r6-repeat.iso` is byte-for-byte identical and has the same SHA-256.
- PCSX2 status: **manually runtime-tested by Pablo**.

Pablo's r6 runtime pass proved several improvements and exposed the remaining presentation defects. `New Game` / `Load Game` are materially better with the recentered anchors, but their black backing still does not cover the full English text. The tablet is translated and improved but still needs centering/padding. Name/license prompts need centering. Deeper H.A.N.T. submenu content is translated, but the submenu title looks awkward and page rows need less spacing. Most importantly, the dialogue still does not match the PS4 horizontal speaker/body composition, disproving the r6 mode-only speaker fix. Those observations are the r7 input contract.

### v11-r7 — runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r7.iso`
- ISO SHA-256: `2b64165f820ec208ff9d721b9fbf30d8ee17bb78b9556e7ebe540c83b27221b4`
- translated ELF SHA-256 before ROFS rewrite: `318f666a1c7cb990ec2cec91be32513c9abd8ddb16f5da4ffe186cb3976cdf7e`
- final post-ROFS ELF SHA-256: `e520a919dd7e2a69c148f4cbe317b8f3ef2d729faa6f36e529a6b536b929b4bc`
- translated/final ELF size: 8,405,744 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **140/140** (`local/startup-acceptance-v11-r7.json`)
- dependency-free suite: **199 tests OK** (8 expected skips)
- Pillow-enabled suite: **199 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r7-repeat.iso` is byte-for-byte identical and has the same SHA-256.
- PCSX2 status: **manually runtime-tested by Pablo**.

r7 addresses only traced r6 presentation defects. Dialogue now fixes the actual generic-font orientation owner, puts the bracket-derived speaker at X=20/Y=80, and changes the transposed body fragment stride from 26px to the proven 12px style-1 advance. The M_Name prompt states and both license lines get fail-closed centered English X geometry. The tablet keeps its proven memory-card owner but adds top padding and centers `slot 1`; H.A.N.T. keeps its 12px font, tightens its page-local stride to 16px, and uses the shorter semantic Help tab `Ruins`. The translated r6 Help/Config content remains intact.

The r6 title-anchor improvement is intentionally preserved unchanged. Static tracing confirms `GP088_08` contains black title chrome, but it is a multi-region atlas and the exact live sampled backing subregion has not been isolated; r7 therefore does not ship another speculative title scale/repaint. That black-backing coverage remains a known issue rather than an r7 regression.

Manual r7 gate: the tablet should have visible top breathing room and a centered second line; name/confirmation/license prompts should be centered; the first old-man speaker should be one horizontal header above a tightly spaced horizontal body block; H.A.N.T. top-level tiles must not regress, deeper Help/Config content must remain English, the Help tab should read `Ruins`, and tutorial rows should be tighter without overlap. Title labels should retain the r6 improvement; incomplete black-backing coverage is a known unchanged issue. Static success is not runtime acceptance.

### v11-r8 — runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r8.iso`
- ISO SHA-256: `c2905f8bf1ebe20defb5479591c0dbf86b2e9bfbf9c6062db37ccf6f8ba6593f`
- translated ELF SHA-256 before ROFS rewrite: `62d68ec47255d37eb372f75d074815159b352367096e488247d699ed54043200`
- final post-ROFS ELF SHA-256: `d19d03a728aba3fff0102b076cc53d045e3329de7b421b4ef4c8ec54a5eb5712`
- final-image startup acceptance: **140/140**
- dependency-free suite: **201 tests OK** (10 expected skips)
- Pillow-enabled suite: **201 tests OK** (1 owned-corpus skip)
- PCSX2 status: **manually runtime-tested**.

r8 improves all three target surfaces, but only the tablet is accepted as-is. The stone text now looks balanced enough and becomes a preservation constraint. The dialogue speaker/name is also now in the correct format and place, but the body begins too far below it. The title backing became wider, proving the `GP088_08` lower strip is live, but it still does not span the complete English label.

### v11-r9 — runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r9.iso`
- ISO SHA-256: `0abe223df878c181da784247fe112553abe030a4f7db240f972285b5aa7696d0`
- translated ELF SHA-256 before ROFS rewrite: `06e364c79be9db69a6b0490d0a2368725ea29d29753aa68e5cd5370a812bf2ca`
- final post-ROFS ELF SHA-256: `61520a390a50de641096514fe219062f7059a382b3e1a6b9cc231ba4069c3ee6`
- translated/final ELF size: 8,405,750 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **140/140** (`local/startup-acceptance-v11-r9.json`)
- dependency-free suite: **201 tests OK** (10 expected skips)
- Pillow-enabled suite: **201 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r9-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **manually runtime-tested**.

r9 was manually runtime-tested. The tablet remains accepted. The name-entry/confirmation layout is correctly translated and aligned, but focused `Yes` loses `Y` and `s` while focused `No` is correct. The dialogue speaker/name is now correctly placed, but the body still appears near the top. The H.A.N.T. menus, submenus and actual page are accepted. The title black backing is still too narrow for the English labels.

### v11-r10 — runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r10.iso`
- ISO SHA-256: `a4f629fb22b2b095fe374eab384d86365ff881038fc37d4fa1e590297d5f928d`
- translated ELF SHA-256 before ROFS rewrite: `711ddca9d7813efaf34fc9788407fd0245a198b3ac8d08e925b851051c7b30c5`
- final post-ROFS ELF SHA-256: `76f335855ce03615f216cff575dfa63ff978b46660b7380d5954825499425a10`
- translated/final ELF size: 8,405,750 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **141/141** (`local/startup-acceptance-v11-r10.json`)
- dependency-free suite: **205 tests OK** (10 expected skips)
- Pillow-enabled suite: **205 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r10-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **manually runtime-tested**.

r10 was manually runtime-tested. The confirmation-focus fix is accepted: focused `Yes` is complete and `No` remains correct. The tablet and H.A.N.T. surfaces remain accepted, and the dialogue speaker/name remains correctly placed at X=20/Y=276. Two r10 hypotheses are disproven: changing generic text-canvas offsets 64→80 does not widen the visible title backing, and changing the later `39 - line*114` fragment formula does not move the visible primary dialogue body. Those two failures define r11.

### v11-r11 — manually runtime-tested presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r11.iso`
- ISO SHA-256: `c99f43b6f4047f63d3b0f4fd228fb893556933d3c1a65cb46e112ba6395325de`
- translated ELF SHA-256 before ROFS rewrite: `2776fe5598074dea7f72faf941130e4fe623d9bc11c79bd6a3bc862df95d6646`
- final post-ROFS ELF SHA-256: `5db2a259210ccb0ad8ca68047b5102c9b52301ba4d99c18af75fa7e7b130382c`
- translated/final ELF size: 8,405,750 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **141/141** (`local/startup-acceptance-v11-r11.json`)
- dependency-free suite: **205 tests OK** (10 expected skips)
- Pillow-enabled suite: **205 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r11-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **manually runtime-tested by Pablo**.

r11 was manually runtime-tested and accepted for the visible presentation surfaces it targeted. `New Game` / `Load Game` and their widened backing are correct; the memory-card tablet and opening quotations remain correct; the visible first/last-name, confirmation, and profile presentation is good; and ADV dialogue is horizontal with the accepted speaker/body composition. The deeper structural 3+3 protagonist-name storage limitation remains unresolved.

The same runtime pass corrected the project's H.A.N.T. interpretation: translated Help category/topic labels and working navigation do **not** imply translated selected-page bodies. Most selected Help topic bodies remain Japanese. `HELP → OTHERS → H.A.N.T Functions` is the confirmed English body exception because tuple `(4,2,0)` resolves to the already-translated tutorial body table.

### v11-r12 — runtime-tested H.A.N.T. content checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r12.iso`
- ISO SHA-256: `ef65129b13b9b49a705a03bc8d83d434a16c76915d5024da597ba1f559f96916`
- translated ELF SHA-256 before ROFS rewrite: `3faa98a1585bc0d55ffb41a5dfbc6cbf8ae3cb0c03742dc7214fcd5f5e21407a`
- final post-ROFS ELF SHA-256: `3844b03e7fc5bc0d9464a3e9d9d256b0c7b6783c1aa90ff09afd32d83e3cf8f0`
- translated/final ELF size: 8,405,990 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **142/142** (`local/startup-acceptance-v11-r12.json`)
- dependency-free suite: **208 tests OK** (10 expected skips)
- Pillow-enabled suite: **208 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r12-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **manually runtime-tested by Pablo**.

r12 adds a bounded inventory of all 55 selected Help-body leaves behind mode 4 and promotes only `HELP → OTHERS → About the Shop` `(4,2,5)`. Its pristine descriptor is file `0x5CBAC4`, text table `0x5C9B80`, metadata descriptor `0x5CBA74`, and metadata leaf `0x698968`; the metadata leaf is an immediate negative sentinel, so this page has no icon records to reposition. The Japanese source table/strings and metadata remain byte-identical; only the proven body descriptor is redirected to a new EOF-terminated English table in the shared translation PT_LOAD. Because the owned local extraction still lacks `English.bytes`, the new wording is explicitly **semantic**, not claimed official.

The r12 runtime pass preserves everything before H.A.N.T. exactly as accepted in r11 and confirms the main H.A.N.T. screen/navigation remain good. It also exposes the next independent content owners: `ADV Controls`, `Exploration Controls`, and `Moving in Ruins` bodies remain Japanese; Mail's empty state is Japanese; Config values are mixed; Enemy L1/R1 category names are Japanese; and Dictionary tabs/term lists are predominantly Japanese. Those observations define r13. `About the Shop` itself was not explicitly reported in this pass, so its runtime status remains unpromoted.


### v11-r13 — runtime-tested H.A.N.T. content expansion; superseded by r14

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r13.iso`
- ISO SHA-256: `53bf85f051ff3f3c8714e41be134dbd5fa9fcd0fd4ba2e3bd58091bf2acc1648`
- translated ELF SHA-256 before ROFS rewrite: `a0b9b3fcb83c6579d5d2f93ab74749636d62fd0cb7aae7f8b0bd5a365d15b2bf`
- final post-ROFS ELF SHA-256: `062d0380ba7f8ee094ac4230799ffee5a4f1029b7230734bca2caafd9d4b6b6f`
- translated/final ELF size: 8,414,614 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **146/146** (`local/startup-acceptance-v11-r13.json`)
- dependency-free suite: **212 tests OK** (10 expected skips)
- Pillow-enabled suite: **212 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r13-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **manually runtime-tested by Pablo; text ownership proven, presentation defects recorded above**.

r13 is scoped to the runtime-observed Japanese H.A.N.T. layers. It translates the selected bodies `(4,0,0)` ADV Controls, `(4,1,0)` Exploration Controls and `(4,1,1)` Moving in Ruins while keeping their pristine row counts and exact metadata/icon records. It additionally translates the empty-Mail message, four Config enum values, all 20 proven ringtone aliases, the three Enemy category tabs, all 10 Dictionary index tabs and all 208 real Dictionary term-list pointers. All Japanese source strings/tables remain byte-identical provenance; only proven aliases/descriptors redirect into the shared translation PT_LOAD. Wording is `semantic` because the owned extraction still lacks the localized `English.bytes` TextAsset.

r13 runtime result: the new English owners are live, but Help icon geometry, Config/Dictionary font style, Enemy tab spacing and Mail centering still need correction. Selecting `King Akhenaten` and `Heracleion` also exposes a separate Japanese Dictionary definition-page class. Those findings define r14.


### v11-r14 — current deterministic H.A.N.T. runtime-layout candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r14.iso`
- ISO SHA-256: `2d543df1367dea4b9b9b31d77cf246d959f2e5c0b23a8726e6b001be611ce795`
- translated ELF SHA-256 before ROFS rewrite: `29be2791d014be9730d5d8107d8d3c4990132bf3fd6d25c227fc6a97b768c08a`
- final post-ROFS ELF SHA-256: `36ac6bfa4e0b995bc94163e728eaa5787110d17f250777c52ccf602830676041`
- translated/final ELF size: 8,416,234 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r14.json`)
- dependency-free suite: **214 tests OK** (10 expected skips)
- Pillow-enabled suite: **214 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r14-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **not launched automatically for r14; manual visual acceptance pending**.

r14 preserves all pre-H.A.N.T. accepted surfaces and the r13 H.A.N.T. translations. It additionally relocates Help icon/controller metadata to the measured English grid, uses existing 12px style 1 for the proven Config/Dictionary/Enemy constructors (including selected Dictionary detail rows), widens Enemy category spacing, fixes Mail empty-state/chrome ownership, adds `No data.` for the observed empty Dictionary/Enemy states, and promotes only the observed `King Akhenaten` and `Heracleion` Dictionary definition leaves.

Manual r14 gate: verify no regression before H.A.N.T.; translated Help bodies have aligned/non-overlapping controller icons; Config values/ringtones and Dictionary lists/tabs are readable at the smaller English font; Enemy shows `Small / Large / Human` without collision; empty Mail is visually centered/readable and shows English chrome; and selecting `King Akhenaten` and `Heracleion` opens English 12px definition pages. `H.A.N.T Functions` must remain unchanged.
