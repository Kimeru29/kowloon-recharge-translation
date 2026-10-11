# r67 first gameplay defects — isolated candidate

Status: static ISO tests passed; runtime approval pending. Do not merge to main or create a permanent PS2 save. Preserve serial SLPM-66511 and save namespace BISLPM-66511Save.

Branch: fix/r67-first-playtest-findings (from feat/first-save-r67, commit 70feac2). Draft PR #36 remains unchanged.

ISO (includes experimental START-modal orientation):
/private/tmp/kowloon-r67-first-playtest-fixes-with-history.iso
SHA-256 1db9a36ad76af07956b63b9564c4f0c9746866fc8f6a97f0c8190f8aa85237c8

Conservative fallback (without START-modal patch):
/private/tmp/kowloon-r67-playtest-round1-v2.iso
SHA-256 e49265ff5026737e90c031f5d572882cbe8d7639b75e1fc851cbb02407dcb789

## User screenshot findings

1. First door Japanese description: added exact PS4 English for strong door, lock states, and generic Open label; runtime recheck required.
2. Entering Battle H.A.N.T. Help layout: explicit 18-row icon-safe instruction layout; runtime recheck required.
3. Turn-Based Combat separators: special 29-row layout places AP, Recovering AP, and Ending Your Turn headings and dotted leaders on the SAME row; the SELECT icon hole is preserved. Runtime recheck required.
4. Basic Attack froze during the previous playtest: its 22-row text table and pointer are now restored BYTE-FOR-BYTE to the previously accessible r67 version. This safety rollback takes priority over cosmetic formatting. The user MUST test that the page opens before polishing it again.
5. START-key dialogue history: a separate MIPS constructor draws two native speaker/body font canvases vertically. Candidate shim switches to orientation 0 at X=20, Y=276/300. Requires PCSX2 screenshot before approval.
6. Chamber speech/inscription centering: 3 formerly lengthy native inspection strings have compact meanings fitting the PS2 box. Precise centering still unverified.
7. Stone tablet text overflows green box: compact English preserves Ancient Egyptian identification, four fierce beasts, and opening the eastern door. Bounded text avoids inventing pagination behavior. Runtime recheck required.
8. Treasure Vase Japanese description: added PS4 English name/phonetic/description/open-state owners; runtime recheck required.
9. Lion Statue pickup Japanese: patched two separate 24-byte fixed-width acquisition rows, verified against Japanese bytes; separate phonetic name uses official PS4 blank value. Runtime centering check still required.
10. Combat-triggered companion text below bubble: screenshot matches companion AFK record 480 ('Come now, this way.'). Accepted r66 normal AFK already anchors this text to the green border. In the combat-transition screenshot the relative anchor appears different. Do not change accepted generic AFK geometry without proving the battle-transition owner; this issue remains OPEN and requires still/animated-frame evidence.

## Implementation and regression guarantees

tools/r67_playtest_inspections.py: 14 independently fingerprinted source owners, 37 literal aliases plus 3 compact already-English owners, 43 redirected pointers total and 2 fixed pickup rows. Correspondences are verified at runtime against user-owned official PS4 English.bytes. Proprietary corpus bytes are never committed.

tools/r67_playtest_help.py: preserve all 50 native Help page row counts and EOF; v4 reflows exactly 31 pages and 509 rows. Basic Attack is intentionally reverted to its EXACT earlier translated r67 table and descriptor due to reported freeze. The Entering Battle and Turn-Based Combat pages have explicit readable, icon-safe layouts. Original icon descriptors and controller-hole positions are frozen.

tools/r67_playtest_history.py: one verified MIPS JAL at original file offset 0x159d54, 72-byte appended shim, original ADV, accepted AFK/L1, and save identifiers untouched. The history patch is STATIC ONLY until user tests.

tests/test_r67_playtest_fixes.py covers owner hashes, exact PS4 correspondences, fixed pickup bytes, Help icon holes, row cardinalities, all 50 Help pages, history trampoline opcode, and frozen accepted renderer regions.

tools/r67_playtest_iso_delta.py validates the entire 2 GB game image against original r67. History candidate has zero unclassified changes: 129 changed inspection-pointer bytes, 121 Help-descriptor bytes, 32 fixed-item bytes, 3 history-JAL bytes, 35,012 appended bytes, 3 ELF segment-size bytes and 6 ISO9660 file-length bytes. The original 155/155 finished-ISO checks pass; 266 tests pass with 16 expected dependency skips.

Artifacts: local/r67-playtest-with-history-build.json; local/r67-playtest-with-history-delta.json; local/r67-playtest-with-history-acceptance.json; local/r67-playtest-history-v2-report.json; local/r67-playtest-inspections-v2-report.json; local/r67-playtest-help-v2-report.json.

### Runtime gate before any merge
Pablo should boot the latest ISO and revisit all ten evidence cases. Ensure the START-modal contents are horizontal without trapping dialogue. Verify the first fight transition bubble after its entry animation finishes. Any Japanese, clipping, missing glyph, wrong positioning or save regression keeps the branch out of main. Do not create the first permanent save until the New Game to Soul Well experience is approved.


## v4: freeze-safe follow-up (2026-10-09)

**Use this candidate instead of the previous history candidate.** All unapproved
r66 AFK/L1 code/data and original memory-card serialization remain unchanged.

Stable Mac path:
`local/r67-candidates/r67-playtest-freeze-safe-v4.iso`

SHA-256: `bff7786abd7dc21c85e4a8e75502442a0ad63ed776c9ca14ce0a72277110755f`

- 267 automated tests, 16 expected skips; 155/155 final ISO acceptance.
- Whole-ISO byte audit: **0 unclassified changes**.
- Basic Attack H.A.N.T. Help table pointer and all 22 table rows are **bitwise
  identical** to the previously working translated r67 table; this is a
  rollback of an unapproved formatting experiment, *not yet a runtime-proven
  freeze resolution*. Revisit after Pablo confirms page loads.
- Entering Battle gets a separate Combat Mode Controls heading. Turn-Based
  Combat has heading and dots on a SINGLE text row, preserving its SELECT icon.
- Independent story comment offset `0x3c1a50` is compacted from the unique
  PS4 English “What an eerie place...” to “An eerie place...” (17 full-width
  cells), maintaining the meaning while fitting its separate native bubble.
  The native, approved AFK/L1 renderer and the other 1,649 comment owners
  remain byte-for-byte unchanged. The final-ELF verifier allows only that
  identified compact phrase **or** the original phrase, preserving
  backward acceptance of r66 and prior r67.
- No Start-key history shim is included. Its previously attempted separate
  font-constructor hook remains unapproved after Pablo reported vertical text.
- The previous door/vase/object/inscription text owners are carried forward.
  UI screenshots still need runtime verification. The first supplied recent
  screenshot of “What an eerie place...” is a **companion story comment**, not
  the door's inspection panel itself.
- Combat-transition AFK text alignment and independent blue rectangle overflow
  remain unconfirmed. Do not adjust accepted r66 background geometry blindly.
- Both r67 and main remain unmerged/unchanged. No ISO or source assets committed.
