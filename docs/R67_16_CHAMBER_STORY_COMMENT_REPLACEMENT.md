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

## r67.14c — X-overflow refinement after positive user runtime feedback (2026-10-10)

Pablo confirmed the r67.14b old-man automatic comment is now centered vertically, with the bluish background fully enclosed by the original green speech bubble. The only remaining regression is that the text extends past the **right-hand (X+) border**. Do not reopen the accepted vertical text placement, green graphics, blue fill or name/history layouts.

The new **r67.14c** candidate changes `HORIZONTAL_SCALE` from **0.55 to 0.40** at the exact same two already-isolated story-comment text helper constants. It preserves both text Y coordinates (280/300), all X origins including the short third-line alignment, original English source pointers, line spacing and vertical character scale. It does not touch a single backing-layer pixel, resource, callsite or font-constructor instruction.

- New candidate ISO: `local/r67-candidates/67.14c-chamber-comment-x-fit.iso`, SHA-256 `4d2030145c5d970b8affbcd39697fb8d99aae7990d82989e90d549221719eb4d`.
- ELF: `local/r67-14c-chamber-story-only.elf`, SHA-256 `b179b9deeb37b7bcad019841f29b28acbff49850f1d1fafc077c7e49c86e0b8d`.
- ISO 155/155 checks pass. Locked r67.12 history four-region checks pass on ELF and ISO; H.A.N.T. and AFK tests remain under the full regression suite.
- **Exact 2,095,382,528-byte ISO audit against r67.14b:** precisely **four bytes changed**: `0x7c46efb8`, `0x7c46efb9`, `0x7c46f084`, `0x7c46f085`. Each is the high immediate halfword of one of two horizontal font-scale float literals. Every other ISO byte—including all green-bubble graphics, bluish background, text origins, pointer records, full script content, save IDs and unrelated UI—is identical. Audit `local/r67-14c-strict-only-scale-delta.json`.
- User's qualitative previous screenshot feedback guides the amount of reduction. A true fresh chamber-entry screenshot from r67.14c has not been captured within the isolated test environment, so the final visual enclosure is **pending user playtest**, not already proven. Do not merge PR #42 without that approval.

## r67.14d rollback — user rejected (2026-10-11)

User's live screenshot showed corrupt automatic-comment glyphs (`(mTkK)`), a bluish backing layer extending outside the green speech bubble, and a much shorter comment lifetime. **r67.14d is a rejected regression**; do not reintroduce its private 576-byte cloned renderer or constructor shim. It was reverted cleanly and pushed as `d12193e`, restoring the user-accepted r67.14c code as the latest safe baseline: intact green/blue bubble and intelligible dialogue, but horizontal glyph spacing still overflows at X+.

## r67.14e — before-glyph horizontal spacing correction (DIAGNOSTIC)

**Root cause:** r67.14b/c performed `font->horizontalScale = 0.40` after `0x189E40` returned. By that point, glyph layout was already constructed; shrinking the final object did not reduce per-character horizontal advance. r67.14d tried cloning the entire routine to change constructor timing, but regressed other rendering and timing.

**Targeted architecture:** `tools/r67_chamber_pre_glyph_marker.py` starts from the locked r67.12 executable with the exact unchanged green/blue sprite bytecode. It retains r67.14c's two story-text callsite wrappers at `0x1661BC` and `0x16628C`, including the user-approved Y=280/300 anchors, short-sentence X=205, and official complete text pointers `0x92D0C8/0x92D104/0x92D140`. Only for those pointers, the wrapper saves the caller's MIPS callee-saved `s7`, sets a private `LION` marker in `s7` while invoking the unmodified native `0x189E40`, and restores the original `s7` on return. All other story comments retain their original renderer and register values.

Inside the existing native renderer, only its callsite `0x189ED8` (`jal 0x188940`, followed by NOP) now invokes a tiny shim that calls **the exact original `0x188940` glyph-clear routine first**. If and only if `s7` contains the transient comment marker and native `s2` is non-null, the shim sets `*(float*)(s2+0x48)=0.40` immediately **after glyph-clear and before glyph creation/advance**. It preserves/restores RA, t0, t1 and has no user-visible side effects outside the active matched comment. The native story renderer and constructor are not cloned or changed; the actual drawable backing-layer resources and game timer counters remain bit-identical to r67.14c. The existing r67.14c post-render scale setter remains unchanged.

**Artifacts and verification:**
- Staged ELF `local/r67-14e-chamber-pre-glyph.elf` SHA-256 `41ee0f936b9422da3c2297e72abf6e4570dd572e2bd7690d58244dc14501491f`.
- Candidate ISO `local/r67-candidates/67.14e-chamber-pre-glyph-marker.iso` SHA-256 `9a0626c5849a66d2bc66ac7913caf4635a52af8dcd54de58070f15f2fe1026a4`.
- Stage + ISO **four approved history regions match**. ISO startup acceptance **155/155**. Full suite **314 tests, 18 expected skips, zero failures**. New targeted test `tests/test_r67_chamber_pre_glyph_marker.py` validates the 3 exact string guards, marker save/restore, original-call ABI, early font scale setter, intact original sprites/constructor/renderer, and all changed original-byte boundaries.
- Full disk `local/r67-14e-chamber-whole-iso-audit.json` checks the full **2,095,382,528 bytes** against the user-reviewed r67.14c ISO. Exactly **402 changed bytes**: 1 ELF size-header byte; 2 changed bytes in existing story-JALs; 3 in the native glyph-clear call; 392 nonzero private append bytes; 4 directory-size bytes. Every unrelated ISO byte, including green/blue sprite graphics and normal/H.A.N.T. dialogue code, is **bit-identical** to r67.14c.
- User's source savestates and actual running emulator/Edge session were not modified; no PR merge.

**Critical acceptance limitation:** There is no trustworthy savestate from before the Chamber of Lions automatic text construction; the old slot3 has text objects already laid out. Thus the actual on-screen horizontal enclosure, exact blue-background fit and display duration **still require the user's fresh PCSX2 scene test**. Do not describe the patch as visually approved or the regression as conclusively fixed until that screenshot verifies it. The current patch is technically constrained and statically validated, but not yet runtime-accepted.

## r67.14f — original glyph X-position compression, not font/shader alterations (2026-10-11)

**User screenshot of r67.14e** confirmed that all green/blue bubble geometry, text legibility and vertical placement were back to the near-perfect baseline, but the old man's text still exceeded the bubble's **right X+ border**. The user explicitly prohibited modifying either bubble layer.

**New independent evidence:** Decode the user's untouched slot-3 PS2 EE RAM from `local/pcsx2-67.06-isolated/slot3-chamber-oldman-20261010.p2s` (SHA-256 `9372b86d139b90e0b2a3ae8215c3db8d1f3d870581d7b06a4be60bbf49e07d6a`). At font object `0x014E4480`, `font+0x04` is a linked list of 30 drawable glyph and sentinel nodes, each with `node+0x120` pointing to the next node. The drawable atlas nodes have type `0x00EAxxxx`, x coordinate `node+0x10`, and **16.0 native pixels of advance per character**: `117,133,149,...,565`. Spaces (`0xFFFFFF0B`) and the terminator (`0xFFFFFF0F`) have separate sentinel nodes and must NOT have their payload rewritten. A shorter nine-character phrase at `0x014E7DC0` exhibits the identical 16-pixel spacing. This proves why reducing only font glyph-size property `+0x48` did not make the complete line fit.

**Single-owner solution:** `tools/r67_chamber_glyph_x_positions.py` rebuilds from the immutable accepted `r67.12` ELF, keeping **exact r67.14c source text owner logic**: the same two `H_TalkBuddyTask` story-comment hooks, same three exact official string pointer guards (`0x92D0C8/0x92D104/0x92D140`), unchanged text Y coordinates (280/300), short phrase X=205, and glyph-size scale=0.40. Immediately after the original native text constructor returns and the accepted glyph size is applied, a private helper walks only its font object's own glyph list. For validated `0x00EAxxxx` glyph nodes, computes `newX = fontOriginX + (oldX-fontOriginX)*0.55` and writes **only** the existing glyph node's X float (`+0x10`). It deliberately leaves Y, glyph width/height, text corpus, timers, the font constructor, the shared renderer and all background graphics completely unchanged. Spaces and sentinel nodes are never modified. It saves/restores RA, t1–t5, FPU f0/f2/f4, preserves the renderer's v0 return value, guards EE pointer bounds (8–32 MB), and caps traversal at 64 nodes.

**Geometry:** for the 29-character longest line, native glyph origins span 28×16 = 448 px before correction; after X compression, 28×8.8 = 246.4 px. Adding approved 0.40 glyph scale yields a rightmost visible glyph edge of ~252.8 px beyond the original text origin, inside the ~264 native-pixel safe text span used by the existing background. Third-line X origin remains 205, and Y spacing is unchanged.

**Artifacts and checks:**
- Staged ELF `local/r67-14f-chamber-glyph-x.elf`, SHA-256 `6eef21ee4da9897f0506690aabbedee8627a233677f5100f929a94c4d57f9fad`.
- New diagnostic ISO `local/r67-candidates/67.14f-chamber-glyph-x-fit.iso`, SHA-256 `4f7c403984e26fd712a0d97a933c9c94e7be0af068c6b7e1aada940e020a0e53`.
- 155/155 startup checks; approved history lock 4/4 on ELF **and** ISO; full 323-test Python suite with 18 expected skips and no failures; targeted tests assert actual PS2 RAM coordinates, MIPS COP1 sub/mul/add encodings, exact glyph X-only write, pointer/bounds guards, and preserved caller registers/FPRs.
- The full 2,095,382,528-byte ISO audit compared directly to approved r67.14c. Exactly 462 bytes changed: 2 executable size-header bytes; 2 story-hook JAL bytes; 454 private helper bytes; 4 ISO directory-size bytes. **All unrelated ISO bytes are identical**, including the complete green border, blue backing, normal story dialogue, approved H.A.N.T. Basic Attack, AFK and START-history code. Audit: `local/r67-14f-glyph-x-iso-byte-audit.json`.

**Runtime limitation:** The user's slot-3 save was captured after glyph nodes were generated, not immediately before the automatic event. Static analysis and the saved geometry demonstrate why this should fit, but it is **not proof that every glyph node is available exactly when the one-time story text helper executes**. The user should load this diagnostic ISO and check the complete message and timing in the actual Chamber of Lions. Do not claim visual approval, merge draft PR #42, or replace the visually near-perfect r67.14c until that fresh screenshot confirms success. Original savestates and user's running PCSX2/Edge session remain untouched.

**Additional r67.14f call-order verification:** Static native callsite analysis confirms the untouched story renderer at `0x189E40` invokes `jal 0x192400` (glyph-list builder) at `0x18A028`, followed by its completion calls at `0x18A04C` (`0x190C90`) and `0x18A058` (`0x18CB50`), and only then returns at `0x18A078`. The new post-return X-position helper therefore executes after this renderer's glyph construction. The new dedicated unit test asserts that instruction sequence against the actual approved binary; targeted suite is 9/9. Live display still requires a fresh screenshot for user approval.
