# r67.14 — Chamber of Lions automatic story-comment text-only diagnostic

STATUS: STATICALLY VALIDATED; NOT VERIFIED ON-SCREEN; NOT APPROVED FOR RELEASE.

## User rejection and rollback

User rejected r67.13: its global font-constructor hook moved text above the bubble and enlarged the bluish backing beyond the green border. The rejected code was reverted by commit 808f8f4. The approved comparison baseline remains r67.12. Do not restore the rejected constructor hook.

## Native owner and constrained correction

The original H_TalkBuddyTask makes green/blue resource calls at 0x1660C8 and 0x16612C, before its separate story-comment text calls to native 0x189E40 at VAs 0x1661BC and 0x16628C. The two callsites are outside the AFK/free-talk path and are distinct from normal dialogue and history. Both background resources and their construction paths remain completely unchanged.

tools/r67_chamber_story_text_only.py patches only those two story-comment JALs with isolated helpers. Each checks one of three official comment source pointers (0x92D0C8, 0x92D104, 0x92D140; offsets 0x3D3438, 0x3D343C, 0x3D3448). Other texts use the original 0x189E40 call and arguments. Matching text is placed at native Y=280/300 before rendering and its font-only horizontal scale is set to 0.55 after specialized text construction. The short 'any time.' segment is horizontally centered at X=205. The caller's t1/temporary registers and RA are restored. No shared font constructor, green frame, blue fill, other comments, approved history, H.A.N.T., AFK, L1 or save identifier is changed.

Geometry assumption: 29 characters * 16 native units * 0.55 = 255.2, within the 264-pixel native text body. This arithmetic DOES NOT prove visual enclosure or centering; that must be tested with a genuinely fresh chamber-entry render.

## Artifacts and validation

Staged ELF: local/r67-14b-chamber-story-only.elf
Staged ELF SHA-256: 97c35aed8617d89a911d42b1335e7739272696e3eb9206abb778da2cddbc147b
Diagnostic ISO: local/r67-candidates/67.14b-chamber-comment-text-only.iso
ISO SHA-256: 6d7eeab329dacf85389e58d2289ef3d7af3e4e19dab22d4f9a52a3dac42d594e
Relocated installed ELF SHA-256: 370ab80ca812b62f80e4a8fa899f0d1b1f000e4e060b8c9ae29b809187080cd6
Startup acceptance 155/155; approved START history byte guard 4/4 on both staged ELF and finished ISO.
Full Python suite 308 tests, 17 expected skips, zero failures.
Whole 2,095,382,528-byte ISO binary audit versus accepted r67.12: 266 changed bytes, exclusively 6 size-metadata bytes, 6 story-comment callsite bytes and 254 appended nonzero helper bytes. Every other disc byte is unchanged. Audit report: local/r67-14b-chamber-full-iso-byte-audit.json.

## What was not proven

The user's slot-3 state already has native text objects constructed. Attempts to alter only a disposable copy of H_TalkBuddyTask state near EE 0xE11C80 and replay did not reproduce the target comment: the game advanced into H.A.N.T. or a blank state. Thus there is NO visual proof that the new renderer places the entire text correctly inside the green bubble; mark as diagnostic, do not tell the user it is fixed, and do not merge PR #42.

Original slot3 copy SHA-256: 9372b86d139b90e0b2a3ae8215c3db8d1f3d870581d7b06a4be60bbf49e07d6a. Original user saves were never modified. Synthetic states are isolated scratch only; isolated PCSX2 was stopped and its StartPaused setting restored. Real user PCSX2 and Edge must not be touched.
