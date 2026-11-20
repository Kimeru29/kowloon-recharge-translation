# r67.15o cumulative official script handoff

Status: **statically verified diagnostic; gameplay verification and approval belong to Pablo.** The user explicitly reserved actual gaming verification for their own playthrough on November 19, 2026. The o candidate has not been launched for agent gameplay testing. No merge is authorized. Phase 2 has not started.

## Candidate identity

| Item | Value |
| --- | --- |
| Candidate | `local/r67o-release/67.15o-cumulative-official-diagnostic.iso` |
| ISO SHA-256 | `049b68c70c74f99b195975000c90e064b5106cbe18cf0dc89f87b44526081b13` |
| Physical bytes | 2,095,382,528 |
| Exact comparison baseline | r67.15n, `c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0` |
| Installed ELF SHA-256 | `fd4760a3c96260ef0fde8cf113a9cc49d46fe732a7f7b0087357f612f1182787` |
| Source branch / draft PR | `feat/67.15n-official-script-transfer`, draft PR #57 |

The k, l, m and n historical images were freshly rehashed and retain their original identities. The gameplay-approved baseline remains k. The n checkpoint and its original in-progress source checkpoint remain preserved. The general ISO builder changes intentionally in o to support a bounded final-ELF extension; none of the 52 protected k producer files change.

## Installed content

| Official DC array population | Final o |
| --- | ---: |
| Installed official English MTX entries | 98,201 |
| Installed official English choice entries in guarded ELF table | 1,079 |
| Source-identical U+3000 no-ops | 4 |
| Correspondence unresolved | 2,203 |
| **All original array identities** | **101,487** |

Compared with n, 199 additional MTX entries are installed: 51 from exact context bundles and 148 from the proven alternate KWLNSCR owner. Another 106 choice entries gain complete official wording: 56 capacity holds, eleven safety fallbacks, two historically compacted labels restored to full official wording, and 37 newly proven correspondences. Nine inherited English MTX entries gain explicit reviewed source correspondence; they are not new payload translations. Thus 305 official entries gain full English installation, while the strict verified-English census grows by 314 after the nine inherited proofs.

Official DC imports now occupy 1,001 MTX files, including the newly added KWLNSCR owner; the 199 new entries affect three files. The speaker stage adds 7,402 exact fixed official headers to 478 MTXs, using 31 identities from 214 verified bidirectional label pairs. These occurrences are counted separately from DC entries. Another 474 assets have these fixed-header imports without a proven body mapping: 448 FI files, 25 FD00 files and FN02_31. They are not counted as fully translated scripts. All 478 final MTX payloads have verified source/preimage chains; all 1,516 KSF payloads remain byte-identical to n. The native table covers 441 complete choice records in 163 KSF files. Unknown records retain their original behavior.

The installed inventory replays source producers and projects inherited ranges through both MTX splice stages. It rereads every final payload, all 99,284 claimed installed ranges, all 1,136 native active choice slots, and all 18,411 Japanese findings from the finished ISO. The findings comprise 18,254 unresolved MTX lexical candidates, 53 unresolved physical Japanese choice labels, and 104 physical Japanese choice fallbacks with a verified guarded English owner. Lexical findings are not rendered-line counts or a translation percentage.

## Mechanisms and native ownership

- [Exact context bundles](R67O_EXACT_BUNDLES.md): whole Japanese/control scopes, matching pointer slots, unique consistent windows and monotonic prior anchors. No fuzzy matching or numeric operand normalization.
- [KWLNSCR correspondence](R67O_KWLNSCR.md): three exact whole-scene blocks establish the native root MTX as the owner of 148 remaster MS01_03 entries. The numbered PS2 MS01_03 control program is retained.
- [Reviewed inherited correspondence](R67O_REVIEWED_CORRESPONDENCE.md): nine explicit spelling, typo and ruby differences, bounded to original source spans and exact native boundaries.
- [Choice correspondence](R67O_CHOICE_CORRESPONDENCE.md) and [renderer](R67O_CHOICES.md): guarded filename/ordinal/header/flag/sibling-preimage ownership; complete source glyph streams; bounded names; two-line layout; 56-handle animation; instance-local stock-art selection indicator.
- [Speaker labels](R67O_SPEAKERS.md): only proven dispatch boundaries are replaced. Two native bridges preserve the original Japanese actor and alias-column identity for exact English headers, including the original speaker-selected player-name path.
- [ELF extension](R67O_TAIL_ELF.md): only a last, nonoverlapping executable can extend into remaining outer slack. Other allocations retain the old relocation policy. Existing output destinations are rejected by the release entry point.

## Binary and regression evidence

The independent full-disc auditor derives its own exact expected writes from n and the fingerprinted final payloads. It compares every byte, including CVM/ISO metadata, outer-tail movement, ELF resource metadata and padding.

- 2,095,382,528 bytes compared; 7,285,685 changed; **zero unexplained**.
- 478 MTXs, thirteen resource relocations and 53 appended DATA.CVM sectors.
- Ten exact original JAL words, the translation PT_LOAD file-size word, derived ROFS fields and 182,360 appended native bytes. All other existing native bytes remain preserved; the original heap reserve is unchanged.
- All 10,656 ROFS records match; zero unmatched records.
- Startup 154/155 raw and 155/155 scoped, with only the existing bounded `memory_card_8` wording exception.
- All 52 protected producers, the historical k report, q/t UI locks, four history regions, fifteen save descriptors, wheel and Group 4 artwork pass.
- Final suite: **1,008 run, 1,001 passed, seven historical skips, zero failures/errors**, in 333.250 seconds with the pinned Python/compiler environment. Two full builds produced byte-identical ISOs and ELFs; repeated inventory generation reproduced all seven JSON files exactly.
- The final validation record and full test log accompany the exported diagnostic. Native execution covers real parser/lookup equivalence, custom-name behavior, font/cursor draw submission, animation counts, cancellation/reopen and malformed-input boundaries. These checks establish offline behavior within the harness; they do not establish gameplay approval.

See [release reproduction](R67O_RELEASE.md) and [final inventory reproduction](R67O_INVENTORY.md). Each producer also has its own command and focused tests. Use Python 3.14.7 and `DEVELOPER_DIR=/Library/Developer/CommandLineTools` for the pinned Apple Clang build. The evidence bundle contains the local research contracts and reports needed alongside the owned source assets. Use fresh output directories throughout.

## Remaining official correspondence blockers

| Official array entries held | Count | Missing evidence |
| --- | ---: | --- |
| FN/FN02_31.MTX | 1,294 | Duplicate DC keys, 961 entries beyond the 604-byte template, and eleven competing English profiles; no valid runtime profile selection proven |
| 25 FD00 MTXs | 729 | Character/scene ownership for template dialogue; fixed speaker identity alone does not establish a body translation |
| MS/MS00_01.MTX | 43 | No corresponding dialogue body in the numbered PS2 command program |
| MS/MS01_03.MTX | 78 | 74 unmatched root-owner entries and four held mapped entries involving phonetics, name movement or title prefix |
| MS/MS01_00.MTX | 1 | No consistent exact bundle proof |
| MS/MS06_03.MTX | 5 | No consistent exact bundle proof |
| MS/MS13_02.MTX | 47 | Exact-context ambiguity, absence or anchor conflict |
| MS/MS01_03.KSF | 6 | No source-proven active PS2 choice owner at the required context |
| **Total** | **2,203** | |

The exported `remaining-official-entries.json` lists every held original `(file, official_array_index)` identity and its source evidence. The complete inventory also records Japanese occurrences with no same-path official map. Failed correspondence is not evidence that a line is PS2-exclusive.

Six Japanese speaker variants are excluded because three English reverse labels are ambiguous: Madame Butterfly, Masked male student and Students. Fifty-five otherwise known-header occurrences lack a proven dispatch boundary and stay unchanged. These speaker holds are separate from the table above.

## Gameplay handoff

Pablo will verify actual gameplay and save compatibility. Boot the hash above and identify that exact artifact in any issue report. Keep historical images and original cards/states intact; use copies for compatibility experiments. Older RAM-bearing savestates do not prove execution of a newly booted ISO.

Priorities during play are complete English choices and their branch outcomes, multi-line text and selection movement, fade/reveal/cancel/reopen behavior, speaker identity, and default/custom player names. Name-bearing choice owners include FN06_01, ID00_04, ID00_26 and MS06_01. KWLNSCR mode-6 presentation needs its own observed activation.

Header fit remains unapproved: the longest newly projected label is 25 cells (`Dignified woman's voice`); the complete accepted corpus also includes a 34-cell label. Native identity verification does not prove their visual fit. No official label is shortened to conceal a possible layout issue. Scene playback, later routes, the Emotion wheel, original fallback behavior and cross-release save/load also remain subject to the user's gameplay approval.
