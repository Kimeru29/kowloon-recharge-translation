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
3. Turn-Based Combat separators: section-aware reflow removes separator dashes joining sentences; runtime recheck required.
4. Basic Attack step layout: explicit 22-row icon-safe instructions; runtime recheck required.
5. START-key dialogue history: a separate MIPS constructor draws two native speaker/body font canvases vertically. Candidate shim switches to orientation 0 at X=20, Y=276/300. Requires PCSX2 screenshot before approval.
6. Chamber speech/inscription centering: 3 formerly lengthy native inspection strings have compact meanings fitting the PS2 box. Precise centering still unverified.
7. Stone tablet text overflows green box: compact English preserves Ancient Egyptian identification, four fierce beasts, and opening the eastern door. Bounded text avoids inventing pagination behavior. Runtime recheck required.
8. Treasure Vase Japanese description: added PS4 English name/phonetic/description/open-state owners; runtime recheck required.
9. Lion Statue pickup Japanese: patched two separate 24-byte fixed-width acquisition rows, verified against Japanese bytes; separate phonetic name uses official PS4 blank value. Runtime centering check still required.
10. Combat-triggered companion text below bubble: screenshot matches companion AFK record 480 ('Come now, this way.'). Accepted r66 normal AFK already anchors this text to the green border. In the combat-transition screenshot the relative anchor appears different. Do not change accepted generic AFK geometry without proving the battle-transition owner; this issue remains OPEN and requires still/animated-frame evidence.

## Implementation and regression guarantees

tools/r67_playtest_inspections.py: 14 independently fingerprinted source owners, 37 literal aliases plus 3 compact already-English owners, 43 redirected pointers total and 2 fixed pickup rows. Correspondences are verified at runtime against user-owned official PS4 English.bytes. Proprietary corpus bytes are never committed.

tools/r67_playtest_help.py: preserve all 50 native Help page row counts and EOF; exactly 32 Help pages reflowed; 529 changed rows. Original icon descriptors and controller-hole positions are frozen. The Entering Battle and Basic Attack pages are separately structured.

tools/r67_playtest_history.py: one verified MIPS JAL at original file offset 0x159d54, 72-byte appended shim, original ADV, accepted AFK/L1, and save identifiers untouched. The history patch is STATIC ONLY until user tests.

tests/test_r67_playtest_fixes.py covers owner hashes, exact PS4 correspondences, fixed pickup bytes, Help icon holes, row cardinalities, all 50 Help pages, history trampoline opcode, and frozen accepted renderer regions.

tools/r67_playtest_iso_delta.py validates the entire 2 GB game image against original r67. History candidate has zero unclassified changes: 129 changed inspection-pointer bytes, 121 Help-descriptor bytes, 32 fixed-item bytes, 3 history-JAL bytes, 35,012 appended bytes, 3 ELF segment-size bytes and 6 ISO9660 file-length bytes. The original 155/155 finished-ISO checks pass; 266 tests pass with 16 expected dependency skips.

Artifacts: local/r67-playtest-with-history-build.json; local/r67-playtest-with-history-delta.json; local/r67-playtest-with-history-acceptance.json; local/r67-playtest-history-v2-report.json; local/r67-playtest-inspections-v2-report.json; local/r67-playtest-help-v2-report.json.

### Runtime gate before any merge
Pablo should boot the latest ISO and revisit all ten evidence cases. Ensure the START-modal contents are horizontal without trapping dialogue. Verify the first fight transition bubble after its entry animation finishes. Any Japanese, clipping, missing glyph, wrong positioning or save regression keeps the branch out of main. Do not create the first permanent save until the New Game to Soul Well experience is approved.
