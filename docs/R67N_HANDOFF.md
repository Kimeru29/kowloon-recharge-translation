# r67.15n official-script cumulative diagnostic

## Candidate and acceptance boundary

This diagnostic continues the exact r67.15m cumulative disc. It retains the gameplay-approved r67.15k native/UI behavior and byte-identical r67.15l wheel artwork. It adds only source-proven official translations, repairs prior literal name macros, and restores eleven unsafe KSF fields to Japanese. No Phase 2 translation, emulator session, card/state/configuration mutation, merge or gameplay approval occurred.

| Identity | Value |
|---|---|
| Repository worktree | `/Users/juan.pena/.codex/worktrees/r67m-cumulative-script/kowloon-recharge-translation` |
| Branch | `feat/67.15n-official-script-transfer` |
| Candidate | `local/r67n-release/67.15n-official-script-diagnostic.iso` |
| ISO SHA-256 | `c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0` |
| Bytes | 2,095,382,528 |
| Exact comparison baseline | r67.15m cumulative script + wheel, `3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f` |
| Installed ELF SHA-256 | `0d5ace47c618c8c9af92f76aecad72dd0da2c4f7588410d2f9d866458a8f38bb` |
| Wheel payload SHA-256 | `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee` |
| Protected Group 4 SHA-256 | `9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a` |

`translations/r67n_script_transfer.json` pins all 323 delta resources, before/after hashes, PS2/PS4/DC fingerprints and full producer report hashes. `translations/r67n_release_lock.json` pins this candidate. The historical source images remain unchanged. The inherited 27 dirty/untracked source files were fingerprinted and preserved byte-for-byte, then committed as checkpoint `346cbb8`; no incomplete edits were silently transferred from other worktrees. The other pre-existing worktrees were not edited.

## Installed content

| Population | Prior m | Newly transferred | Final n |
|---|---:|---:|---:|
| MTX files with official imports | 997 | 3 | 1,000 |
| MTX official DC entries represented | 92,727 | 5,275 | 98,002 |
| Additional KSF files | — | 15 | — |
| Additional KSF official choice entries | — | 116 | — |

These are resource and localization-map entry counts, not dialogue-line counts or a translation percentage. The 98,002 MTX entries include nine inherited semantic-cluster entries explicitly flagged for correspondence review. The new transfers use no fuzzy text similarity or numeric operand normalization.

The partial importer transfers 2,539 entries in `MS/MS01_00.MTX`, 1,729 in `MS/MS06_03.MTX`, and 1,007 in `MS/MS13_02.MTX`. Original unmatched Japanese and all event controls/pointer slots remain intact. See [partial mapping and layout evidence](R67N_PARTIAL.md).

The additional 116 KSF choices require byte-identical complete native records at the same scenario ordinal and choice index, and fit the native 29-byte text plus NUL limit. See [KSF format, consumer and renderer proof](R67N_KSF_COMPATIBILITY.md). The eight-file safety correction restores eleven unterminated historical labels and fifteen altered structural bytes; it changes 345 bytes. Two historically approved compact DG00 choices are preserved and remain explicitly distinguished from verbatim official English.

Retroactive repairs replace 1,288 literal name macros across 297 files, including three prior structural imports. Twenty-seven other macro-bearing files were already native. The final ISO has zero literal ASCII/fullwidth parenthesized p-prefixed macro spellings in all 1,516 MTX bodies. The full-name and speaker-selected semantics were traced in both executables; custom-name rendering is still unobserved. See [native lookup ownership](R67N_DYNAMIC_LOOKUP.md) and [repair provenance](R67N_NAME_SUBSTITUTIONS.md).

## Exhaustive ADV inventory

`local/r67n-inventory-final/` contains:

| File | Scope |
|---|---|
| `files.json` | All 3,032 PS2 MTX/KSF files, counterparts, source/map/installed hashes and ISO coordinates |
| `entries.json` | All 101,487 official DC array entries, preserving duplicate-key array identity, offsets and source/installed evidence |
| `japanese.json` | All 26,064 conservative installed Japanese lexical/active-choice findings and classifications |
| `ksf-labels.json` | All 1,136 native active KSF labels with payload hashes and bounded terminators |
| `ps4-payload-index.json` | Alternate whole-file source hash index |
| `summary.json` | Counts, evidence fingerprints and explicit scanner limits |

Every serialized file hash, 99,048 claimed installed ranges, Japanese occurrence range and native KSF label was reread directly from the completed ISO. All 101,487 `(file, official_array_index)` identities are unique. The 488 PS2 MTX assets without same-path maps have no byte-identical complete counterpart among 1,028 mapped PS4 MTX assets. This does not establish platform exclusivity or rule out partial/contextual alternate correspondences.

| Official map entry classification | Count |
|---|---:|
| Official English installed, strict/replayed evidence | 98,966 |
| Inherited English installed; semantic-cluster correspondence needs review | 9 |
| Official U+3000 no-op, already source-identical | 4 |
| Inherited approved constrained choice | 2 |
| Official English available, exceeds proven safe capacity | 56 |
| Deliberate technical-safety Japanese fallback | 11 |
| Correspondence unresolved | 2,439 |
| **Total** | **101,487** |

Of the 26,064 Japanese findings, 25,997 have unresolved correspondence, 56 have available official English blocked by capacity, and eleven are explicit safety fallbacks. MTX scans exclude pointer headers and respect CP932 boundaries. KSF scans inspect active labels only, excluding packed binary. These are conservative text candidates, not proven rendered dialogue or a reachability census. ELF, artwork, fonts, audio and saves are outside this ADV inventory. No absent same-path resource or failed importer is classified as PS2-exclusive.

## Remaining blockers

- **MTX source-map entries: 2,396 unresolved.** This comprises 373 entries in the five requested MS scripts, 729 in 25 FD00 templates, and the 1,294-array-entry FN02_31 map. The complete per-entry source locations and rejection reasons are in the reports; synthetic entries are not miscounted as independent Japanese sentences.
- **FN02_31:** the two 604-byte source templates are identical, but 961 array entries address outside the file and the dictionary has duplicate keys. The actual PS4 deserializer calls `Dictionary.Add`, not first/last assignment. Identical templates have eleven different English profiles. There is no defensible ordinary-offset or arbitrary alternate-map import. Gameplay use of this map remains unobserved.
- **FD00:** every one of the 729 same-path groups was examined. Exact source/control/pointer identity is unproven; alternate scene, voice and character ownership remains needed. Do not select Minakami template text for another character merely by filename or text resemblance.
- **MS00_01 / MS01_03:** no eligible exact spans; the latter also has phonetic-name macros whose PS4 and PS2 semantics differ. **MS01_00:** two unresolved groups. **MS06_03:** five. **MS13_02:** 97. Details are in the partial report and source-offset inventory.
- **KSF:** 56 otherwise available full official labels exceed capacity, eleven prior unsafe labels now retain Japanese for safety, and 43 nonidentical-record entries lack correspondence. A storage side lookup alone is insufficient: the separate choice renderer has a fixed handle-array boundary. Both storage and a narrowly owned renderer solution require further proof and gameplay testing. Two previously approved DG00 compactions remain historical exceptions.
- **Nine historical semantic-cluster entries:** retained as installed baseline English, not reclassified as proven by similarity. Their exact file/key/source ranges and installed hashes are separately listed in `entries.json`.
- **Other source occurrences:** all remaining Japanese candidates remain unresolved until contextual or alternate-asset ownership is demonstrated. Phase 2 has not started.

## Binary and regression evidence

The independent whole-disc auditor derives exact expected writes from m and the fingerprinted overlay without trusting the builder's write report. It compares all 2,095,382,528 bytes, including relocation padding, tail files, ELF allocation and metadata.

- 323 resource deltas, 108 additional DATA.CVM sectors.
- 7,941,626 changed bytes; **zero unexplained**.
- Every native ELF byte preserved except exact resource ROFS size/extent metadata.
- 10,656 runtime ROFS records; zero mismatches or unmatched records.
- Raw startup 154/155, scoped 155/155 with only the pre-existing bounded `memory_card_8` exception.
- Four history lock regions and fifteen save descriptors preserved, serial `SLPM-66511`, namespace `BISLPM-66511Save`.
- All 52 approved producer files and immutable historical k report verified unchanged.
- Final suite: **894 run; 887 passed, seven historical skips, zero failures/errors** (224.454 seconds). New installed-ISO checks ran; history guards used the final n ELF/ISO. Two complete builds produced the identical candidate hash. Results are recorded in `local/r67n-session/final-validation.json` and the delivered validation logs.

The initial resumed suite failed because temporary owned-source aliases had disappeared; those failures and logs were retained. Once aliases were restored, the prebuild full suite passed 876 tests with seven historical skips. A separate final run requires the installed n ISO and passes its ELF/ISO to the existing history checks. Static checks do not establish cross-release save compatibility or gameplay approval.

## Runtime acceptance required

Use this exact ISO hash. Retain r67.15k as the approved fallback.

1. Cold boot; check accepted startup/name entry, horizontal ADV, HANT, AFK/L1, Item Details, Isis inspection and early progression.
2. Exercise the exact wheel art in ordinary/forced modes, every position, fades, timeout and repeated opens. r67.15l/r67.15m gameplay approval remains pending.
3. Use distinct full-length family/given names. Exercise `px`, reordered `pn`/`pm`, repeated name references, all relevant speaker contexts, and new partial-import pages. The partial report flags 121 rows with runtime name expansion.
4. Inspect the **48-cell title-like row in MS06_03**: source offset 19769, pointer slot 96, output 32873–32969, native delimiters `w60{` / `}w`. It exceeds the static 39-cell triage threshold; no text was shortened. Also check the eight inherited long scene-title cards in the r67m layout report.
5. Traverse the newly translated MS chapters and all 116 new KSF choices, including branch outcomes, choice IDs, line reveals, pages, pauses, special punctuation and full-text display. Confirm the eleven documented safety choices show intact Japanese and retain their gameplay behavior.
6. Save and load ordinary memory-card saves with progress checks across old/new releases, using protected clones rather than overwriting existing saves. The static descriptor lock is not a runtime save/load test.

Do not merge or promote this diagnostic until the user explicitly approves gameplay from this hash. Reproduction uses the existing Python 3.14.7 environment and `DEVELOPER_DIR=/Library/Developer/CommandLineTools`; see `R67N_REPRODUCTION.md` and the delivered script/report archive. No further investigation is needed to locate each outstanding entry.
