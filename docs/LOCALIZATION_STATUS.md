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
| Name fields / permanent name storage | **Known limitation / intentionally frozen** | The PS2/Re:charge editor retains its original structural 3+3 behavior (`Hab` / `Kur`). The attempted 8+8 expansion was reverted after breaking runtime; r47 makes no name-editor changes and keeps the accepted 3+3 behavior unchanged. |
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
| H.A.N.T. Help category/topic labels + navigation | **Working / runtime-proven / frozen** | Pablo accepts r28 as complete for the current H.A.N.T. scope. Freeze `ADV`/`Ruins`/`Other` text positions/style and their centered selector geometry: ADV = 48px at x=204, Ruins = 72px at x=257, Other = 64px at x=338. The 268px topic selector and all accepted Help owners remain unchanged; r29 adds an end-to-end regression over every `HANT_RUNTIME_LAYOUT_PATCHES` owner. |
| H.A.N.T. selected Help topic bodies | **Working / frozen for current scope** | The reviewed H.A.N.T Functions, ADV Controls, Exploration Controls and Moving in Ruins presentation is accepted for now. Do not change those promoted bodies/metadata while work moves to the dungeon HUD; independent unpromoted Help bodies remain deferred rather than implicitly translated. |
| H.A.N.T. Config labels / values | **Working / runtime-proven** | r15 runtime reports Config looks fully translated and visually correct. r16 does not modify this path. |
| H.A.N.T. Mail empty state | **Working / runtime-proven** | r19 runtime accepts the empty-state presentation. Freeze the shared Mail-row x=120 owner and `No mail received.` payload. |
| H.A.N.T. Enemy category tabs | **Working / runtime-proven / frozen** | Pablo accepts the current Enemy header as perfect. Freeze labels 220/282/344, selector 218+62*i at 64px, L1 x=190, R1 x=407, y=93 and style 1. r27 adds a dedicated regression that pins both shoulders, all category bases, selector width/cadence and text style. |
| H.A.N.T. Dictionary tabs + term lists | **Working / runtime-proven / frozen** | Pablo accepts the r26 Dictionary header as perfect. Freeze L1 x=266, tabs x=294+12*i, the 16px selector at x=292+12*i, R1 x=412, cadence/UVs, detail geometry, generated definitions and `0x588C84 = 12`. r27 adds a dedicated regression that pins the complete accepted Dictionary geometry. |
| H.A.N.T. Dictionary selected definitions | **Working / runtime-proven** | r18 runtime accepts Cairo, H.A.N.T and Heracleion detail pages. Freeze the 3,827-row official definition reflow, mode-1 offset `0x588C84 = 12`, and pristine `0x190A40`. |
| Dungeon HUD exploration action text | **Working / runtime-proven / frozen** | Pablo accepts r29's moving action HUD as completely translated and visually correct. Freeze the proven `H_CmdIconDraw` owners for `Examine` / `Items` / `Jump`; r30 changes no r29 action-menu geometry or text. |
| Dungeon HUD battle/L1 item text | **Working / runtime-proven / frozen** | Pablo accepts the r29 action/L1 HUD pass. Freeze the 446 exact PS4 item-name relocations and their 500-entry table ownership; r30 keeps these owners unchanged and regression-covered. |
| SELECT command/menu labels | **Working / runtime-proven / frozen** | Pablo accepts r29's SELECT/start menu as completely translated and visually correct. Freeze all 18 proven wide-text command aliases; unresolved `メディア` remains pristine rather than guessed. |
| Companion HUD action/skill label | **r53 candidate: synchronized L1 blue sprite, runtime pending** | r52 runtime showed tint below the green bubble. r53 creates blue at the exact green X/Y, initially transparent, follows the three native green alpha-transition owners, and tears down through both correct sprite-destructor paths. Runtime must prove blue behind text and full disappearance with the L1 bubble. |
| Companion HUD transient comments | **r53 AFK live-register correction and 3px inset, runtime pending** | r51/r52 clobbered specialized constructor argument t1. r53 preserves t0..t3 while supplying Y through f13/stack using t4..t6. AFK blue width becomes 282px with X+3px within unchanged 288px green, preserving frozen translations and multiline height growth. Runtime must prove text visibility and all sizes contained. |

## Known executable/UI text not yet solved

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| `メディア` | **Still Japanese / unresolved** | No exact official dictionary mapping has been proven for this PS2-only label. |
| Remaining H.A.N.T. content | **Still Japanese / unresolved** | r16 covers all 208 selectable Dictionary definition pages in addition to the previously translated Config/ringtones, empty-Mail state/chrome, Enemy categories, Dictionary tabs/terms and promoted Help bodies. Independent unobserved content remains fail-closed, especially non-empty Mail subjects/bodies and unpromoted Help bodies. |
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


### v11-r14 — runtime-tested H.A.N.T. layout checkpoint; contains critical H.A.N.T Functions regression

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
- PCSX2 status: **manually runtime-tested by Pablo; review stopped after the critical H.A.N.T Functions blank/trapped-state regression**.

r14 preserves all pre-H.A.N.T. accepted surfaces and the r13 H.A.N.T. translations. Runtime confirms the main H.A.N.T. menu remains good, `Exploration Controls` is much improved except for the warning-icon overlap, and `Moving in Ruins` is acceptable. However, r14 also changed `0x190A40` under a false Dictionary-detail style attribution; `H.A.N.T Functions` becomes blank and can leave H.A.N.T. blank/trapped afterward. The definition text-table relocations remain separately owned, but their font-style owner is not proven.

r14 runtime result: pre-H.A.N.T. and the main H.A.N.T. menu remain accepted. Exploration ordinary icons/text are improved, but the `(!)` warning overlaps its bottom text. Moving in Ruins appears acceptable. `H.A.N.T Functions` is a release blocker: the body is blank, and leaving it can leave the H.A.N.T. screen blank/trapped while audio/input feedback continues. The review stopped there.

### v11-r15 — runtime-tested H.A.N.T Functions recovery checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r15.iso`
- ISO SHA-256: `e4cf331c90470e99c2c0db1728673a7ddcdab358182f8d1ba7927b6dbbf387f6`
- translated ELF SHA-256 before ROFS rewrite: `dcdd2f0c4a22bb74f280ec285fc43a061dd475c07ce10a00e31498849a274f86`
- final post-ROFS ELF SHA-256: `306cfa21e720328c269c505995c5041b0d4b77496329ecbf22bdf14b5eef1a68`
- translated/final ELF size: 8,416,238 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r15.json`)
- dependency-free suite: **215 tests OK** (10 expected skips)
- Pillow-enabled suite: **215 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r15-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **runtime-tested by Pablo**; H.A.N.T Functions/ADV/Moving/Config are good, with remaining Mail/Dictionary/Enemy/Exploration issues carried to r16.

r15 restores `0x190A40` to its pristine style-0 singleton-constructor word and fail-closes on that preservation invariant. `0x190968` remains the proven style-1 body-row owner. This explicitly retracts r14's unsupported claim that both words are Dictionary-definition font owners. r15 also keeps the corrected Exploration icon metadata and adds a two-cell text gutter to the three night-vision warning rows so the `(!)` icon has reserved space. Moving in Ruins and all pre-H.A.N.T. accepted owners are untouched.

Manual r15 gate: `H.A.N.T Functions` must show its English body again and exit cleanly back to H.A.N.T.; entering/exiting it must never blank or trap the H.A.N.T. state. In Exploration Controls the `(!)` icon must no longer overlap the bottom three warning lines. Moving in Ruins and every pre-H.A.N.T./main-H.A.N.T. accepted surface must remain visually unchanged.


### v11-r16 — current H.A.N.T. completion/presentation candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r16.iso`
- ISO SHA-256: `7669e50ddd81778e48e15c1f85f8ac4ff56a7d9e4e6c330c58ab9ae3b7bd8b9b`
- translated ELF SHA-256 before ROFS rewrite: `f8c90885dfd9050570fd5b70db6fbf5b890915e6469128996ab89cfa7ac86106`
- final post-ROFS ELF SHA-256: `bb4bcb3640616cb33de351b3735cfacb25376e7e4e56601113956e8dc85df752`
- translated/final ELF size: 8,563,534 bytes
- overlays: 1,145 total; 892 in place / 253 relocated
- executable ROFS records: 1,145 patched/re-resolved
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r16.json`)
- dependency-free suite: **217 tests OK** (10 expected skips)
- Pillow-enabled suite: **217 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r16-repeat.iso` has the same SHA-256 and is byte-for-byte identical.
- PCSX2 status: **runtime proof pending**.

r16 keeps the r15-good surfaces frozen. It nudges only Exploration's final warning icon by 6px; repairs Mail count-slot semantics and empty-state centering; compresses/repositions Dictionary top tabs and centers its empty state; moves Enemy categories below L1/R1; and promotes all 208 Dictionary definition pages from the recovered official remaster `English.bytes`. The generated definition corpus proves 2,073 unique exact source-row matches, 208 fail-closed source fingerprints, 4,177 deterministic output rows, and a conservative 21-cell page width without touching the runtime-critical `0x190A40` singleton.

Manual r16 gate: continue from the r15 review. Check Exploration's final `(!)` gap, Mail alignment/centering, Dictionary tabs/empty state plus several opened definitions including Cairo, and Enemy category/L1/R1 separation. Reconfirm Moving in Ruins, H.A.N.T Functions, ADV Controls and Config are unchanged.


### v11-r17 — runtime-tested Dictionary/Enemy presentation checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r17.iso`
- ISO SHA-256: `728f9eae1d7dd2f69009732ff8c880585db1c6cde41d120358e04362428276dc`
- translated ELF SHA-256 before ROFS rewrite: `68ab06d3b2b51dbcdc8853944c04eadd0c165009afed488dfe158a167e0ca6f2`
- final post-ROFS ELF SHA-256: `ee24bb03984c7be760f398f01128faa65c02925552283c0ac9a6bc48dfd125a0`
- translated/final ELF size: 8,562,126 bytes
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r17.json`)
- dependency-free suite: **218 tests OK** (10 expected skips)
- Pillow-enabled suite: **218 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r17-repeat.iso` is byte-for-byte identical.
- PCSX2 status: **runtime-tested by Pablo; Dictionary body reflow is live, but Mail/Dictionary empty-state centering and Dictionary top/detail chrome remain incorrect**.

r17 is bounded to the final r16 Dictionary/Enemy review. Dictionary index tabs are centered at x=232 with their accepted 14px cadence; the Dictionary-only mode offset at file `0x588C84` moves selected title/icon chrome +32px away from `【Dictionary】`; official 208-page definition generation removes Japanese paragraph separators from English body prose while retaining one title/body break; Enemy keeps y=110/style 1 but corrects its actual visible starts to 210/290/370. All other r16-good surfaces are frozen.


### v11-r18 — runtime-tested Dictionary-detail checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r18.iso`
- ISO SHA-256: `136a528030ab5ce611efd67fd06cf637f9015e1ba3473f760f9a6e72d7754c9a`
- translated ELF SHA-256 before ROFS rewrite: `64c220490e64da7e6d50d8d76ebd0f9e60cc94c42cbc6414605ba258bd71fad1`
- final post-ROFS ELF SHA-256: `a61b72b35d95112f68e79f1d1f1f1c36a77a1ab454ff714514694e540799f74a`
- translated/final ELF size: 8,562,114 bytes
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r18.json`)
- dependency-free suite: **218 tests OK** (10 expected skips)
- Pillow-enabled suite: **218 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r18-repeat.iso` is byte-for-byte identical.
- PCSX2 status: **runtime-tested by Pablo; Cairo/H.A.N.T/Heracleion detail pages are accepted, but Mail centering and Dictionary/Enemy root navigation remain incorrect**.

r18 preserves r17's official Dictionary definition body reflow and Enemy placement. It removes Mail's leading empty-state padding, reduces Dictionary empty-state padding to five cells, starts the ten Dictionary index tabs at x=268 with the accepted 14px cadence, and changes only the Dictionary mode-1 title/icon offset from 6 to 12. All previously accepted surfaces and `0x190A40` remain frozen.


### v11-r19 — runtime-tested root-layout checkpoint

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r19.iso`
- ISO SHA-256: `4dbce7f49d537e6cc6aa156ff6d4723596de31b3a8657caa83a4b0a40db81928`
- translated ELF SHA-256 before ROFS rewrite: `c8795405f9746db2ba260c4fe644ee45218d200232112496f4ad6f1f58ba50b3`
- final post-ROFS ELF SHA-256: `d34d53d62b6236d1c1b87577704bbd2eb8d84945564216750df74347e82a7cef`
- translated/final ELF size: 8,562,114 bytes
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r19.json`)
- dependency-free suite: **218 tests OK** (10 expected skips)
- Pillow-enabled suite: **218 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r19-repeat.iso` is byte-for-byte identical.
- PCSX2 status: **runtime-tested by Pablo; Mail and all other reviewed surfaces are accepted, while Dictionary/Enemy red selectors remain misaligned and Enemy R1 is clipped**.

r19 freezes the now-accepted Dictionary detail path. It changes only three reviewed presentation classes: shared Mail-row X 143→120 so the 272px English empty state centers in the 512px viewport; Dictionary root navigation becomes L1=274, tabs=302..422 at 12px cadence, R1=428; Enemy root navigation returns to y=93 with L1=194, Small/Large/Human=226/292/358 and R1=428.


### v11-r20 — current Dictionary/Enemy selector-alignment candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r20.iso`
- ISO SHA-256: `374a8813fcf10d148c35b9e0e47be6d1d943ebf447752ed461f4a0fb17884ebd`
- translated ELF SHA-256 before ROFS rewrite: `30333e4d488714d2639b67c07da4ea76a4afd4b70e92ecc02f446421dd6850f9`
- final post-ROFS ELF SHA-256: `e4aa7717fe11111a7a82c07595a3d6e5088c2fc3b93dd4af2cb23610666bca83`
- translated/final ELF size: 8,562,114 bytes
- final-image startup acceptance: **150/150** (`local/startup-acceptance-v11-r20.json`)
- dependency-free suite: **220 tests OK** (10 expected skips)
- Pillow-enabled suite: **220 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r20-repeat.iso` is byte-for-byte identical.
- PCSX2 status: **runtime proof pending**.

r20 changes no translated content and no accepted detail/list geometry. It changes only Dictionary's moving selector from `223+18*i` to `300+12*i`, Enemy's moving selector from `288+40*i` to `222+66*i`, and restores Enemy R1 from the clipped r19 x=428 to pristine x=407.


### v11-r23 — final H.A.N.T. header-clearance candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v11-r23.iso`
- ISO SHA-256: `4465f4322fc252d1fa0cf734fc4c63697c38adbda155a90eadcaca37698a55c5`
- translated ELF SHA-256 before ROFS rewrite: `564c4268faf7f7224bc5a4dc1d67c758a2af003f2c5487a4056af8d537a2041f`
- final post-ROFS ELF SHA-256: `4b59521acbfc96b68a6a934a7eb2442b8e426288714065f96f1980aeff3516f8`
- translated/final ELF size: 8,562,114 bytes
- final-image startup acceptance: **150/150**
- dependency-free suite: **224 tests OK** (10 expected skips)
- Pillow-enabled suite: **224 tests OK** (1 owned-corpus skip)
- deterministic repeat: `/private/tmp/kowloon-recharge-startup-en-v11-r23-repeat.iso` is byte-for-byte identical.
- PCSX2 status: **runtime proof pending only for Dictionary R1 clearance and Enemy L1/selector clearance**.

r23 changes no translated content and no accepted selector/text geometry. It moves only Dictionary R1 x=428→424 and Enemy L1 x=194→190. Final-image regression coverage now tamper-checks every owned H.A.N.T. runtime-layout patch so later rounds cannot silently alter already-complete Config/Dictionary/Enemy geometry.


## v11-r27 runtime-owner correction checkpoint

The r26 runtime review accepts Enemy and Dictionary as final/frozen and proves the last Help category-owner attribution was reversed. r27 restores `Ruins` at `0x18C768` and applies the intended -8px nudge only to `ADV` at `0x18C778`; Help selector geometry and `Other` are unchanged. Dedicated regressions pin the accepted Enemy and Dictionary geometry. Candidate `/private/tmp/kowloon-recharge-startup-en-v11-r27.iso` hashes to `5210dde53302c6340cc27550f0f170a31ca317907759dbc29a92839c4781fb9e`; final-image acceptance is **150/150**; both suites execute **228 tests**; repeat ISO is byte-identical.


## v11-r28 Help selector-box checkpoint

The r27 runtime review accepts all three Help category labels as final, so r28 freezes their exact X/style owners and changes no text. Static tracing shows ADV/Ruins/Other share one 64px group-20/index-0x32 selector resource; the live selector sprite exposes X at `+0x3c` and X scale at `+0x60`. r28 redirects only the selector-update sequence through a bounded helper in existing inter-function padding and selects `(x, scale)` from a three-entry table: `(204, .75)`, `(257, 1.125)`, `(338, 1.0)`. That yields centered 48/72/64px boxes while preserving Other exactly. Candidate `/private/tmp/kowloon-recharge-startup-en-v11-r28.iso` hashes to `e7517dfafd98766733324d3b8f62dcccf29b69928e8242cf469114830e197a83`; final-image acceptance is **150/150**; both suites execute **229 tests**; repeat ISO is byte-identical.


## v11-r29 dungeon HUD / SELECT checkpoint

r29 is the first post-H.A.N.T. candidate and preserves every accepted H.A.N.T. runtime-layout owner. It corrects the SELECT renderer by replacing compact ASCII substitutions with wide PS2 text for all 18 proven command labels, promotes the three exploration action-palette owners to `Examine` / `Items` / `Jump`, and relocates all 446 exact item-name table matches used by the battle/L1 HUD path. Japanese source bytes remain unchanged and every promoted pointer/code owner is fail-closed; unresolved `メディア` is still pristine.

Candidate `/private/tmp/kowloon-recharge-startup-en-v11-r29.iso` hashes to `1692b234b810bf966b94d0d3959abab07ad0c611bca469a5e022727eaac3de0e`; pre/post-ROFS ELF hashes are `8caddb81607bd1afe7d30344d2b4bc0e87e979e7df9bd8714bd2e18d27f41062` / `923bc218585f0b9d1ee1edb12ea73d5c04ca6447c653b6aff3b2b43fd30e754f`; final ELF size is 8,573,437 bytes; final-image acceptance is **151/151**; dependency-free and Pillow-enabled suites both execute **234 tests** (10 / 1 skips); repeat ISO is byte-identical. Runtime proof is pending only for the newly promoted SELECT and dungeon-HUD text paths.

## v11-r30 companion HUD checkpoint

The r29 runtime review promotes both dungeon action-menu sections and the SELECT/start menu to accepted/frozen. r30 traces the remaining companion HUD independently: 1,650 unique live `h_buddy.c` comment strings / 1,784 aliases all have unique exact PS4 `English.bytes` matches, while the 31-entry companion action table has 26 exact PS4 labels, one pristine placeholder, and four explicitly provenance-tagged Re:charge-only semantic labels. The generated manifest pins the pristine PS2 ELF and owned `English.bytes` hashes; regression tests fail closed on both source and pointer drift while preserving all r29 and H.A.N.T. owners. Candidate `/private/tmp/kowloon-recharge-startup-en-v11-r30.iso` hashes to `7bed876be95e19fd7c2fe1ade882eaf9fb0518db1165510861fa69d89db63c5f`; final-image acceptance is **153/153**; both suites execute **239 tests**; repeat ISO is byte-identical.
