# r67.13 — Chamber of Lions automatic old-man comment: isolated geometry diagnostic

**State: BUILT / STATICALLY VALIDATED / NOT VISUALLY APPROVED. Do not merge PR #42 or tag a release.**

## User-reported defect and test scene

Upon entering **Chamber of Lions** an **automatic** old-man comment displays in a green HUD speech bubble and disappears without input. User screenshot: bubble is correctly drawn, but the English comment begins at/below its bottom edge and extends past the right border. This text does **not** use the normal ADV dialogue renderer or START dialogue-history owner. Preserve full English dialogue, font atlas, green bubble graphics, approved H.A.N.T. Basic Attack and r67.12 dialogue history.

Slot-3 save is **already during** the automatic comment. The untouched original save has been copied to `local/pcsx2-67.06-isolated/slot3-chamber-oldman-20261010.p2s`, SHA-256 `9372b86d139b90e0b2a3ae8215c3db8d1f3d870581d7b06a4be60bbf49e07d6a`. EE RAM inside the save shows three active font objects at `0x014E2540`, `0x014E4480` and `0x014E7DC0`, each with style 0, original `x=117.0`, `y=313.0`, `xScale=1.0`. Their glyph output was prepared **before** that state was captured; changing those fields in a disposable savestate afterward did not prove an on-screen correction. Do not mistake reloading already-constructed slot 3 as a valid test of this constructor-level fix.

## 67.13 native constructor experiment

`tools/r67_chamber_comment_geometry_probe.py` generates an ELF from the fixed approved r67.12 baseline checksum `d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179`.

- The existing native font constructor at `0x188AD0` stores font object's style at offset `+0x0C`, coordinates at `+0x14/+0x18`, horizontal scale at `+0x48` and vertical scale at `+0x4C`.
- Redirect **only** the original `sw v0,0x48(s0)` at VA `0x188CEC` to an append-only 108-byte MIPS helper in the executable's already-reserved translation segment. The original instruction executes in the helper; `sw v0,0x4C(s0)` stays unchanged as the MIPS branch-delay-slot instruction.
- The helper checks **all three** conditions: font style 0, original float X exactly 117.0, original float Y exactly 313.0. Only matching objects receive `Y=285.0` (up 28 native pixels) and horizontal scale `0.68` (narrow enough to fit English glyphs inside bubble).
- Nonmatching objects immediately return with the original X, Y and scale; temporary GPR registers are saved/restored. The helper jumps back to the original native constructor at `0x188CF4`; it does not change fonts, dialogue content or unrelated paths.
- **These are diagnostic values, not user-approved centering coordinates.** A fresh entry into Chamber of Lions must show the text comfortably centered and **fully enclosed** in its original green bubble; otherwise correct only this owner and retest. Verify multiline and another automatic comment when possible.

## ISO build and guardrails

`tools/r67_chamber_iso_probe.py` copy-on-write clones **only** the user-approved r67.12 ISO (SHA-256 `87cfa6f445eba36687e1d5badc621d9efd3157560a3be8da0c5eda4309a54e63`). It verifies the installed executable checksum, retains the installation's relocated file pointers, applies exactly the constructor hook/header bytes and append-only tail, and updates the ISO9660 record size in place. All other files, including the unchanged original green bubble graphics and text content, are preserved. Generated ISO/ELF/savestates remain untracked.

- Candidate: `local/r67-candidates/67.13-chamber-comment-geometry-diagnostic.iso`.
- Whole ISO SHA-256 `2ffaa2a29873725232818c7014be998887f4cc4b25b8e76ce0bf99234db7d99b`.
- Staged ELF SHA-256 `dd0ddad9642b9f81d47399943236c75590ff8494501d88a89bc5d5e7173a64cd`.
- Installed ELF SHA-256 `95c50ffe78262a5694b1c704f98edf5dce535ae76a0393fbe1a96941f8168c6a`.
- Startup ISO acceptance: **155/155**. Full Python suite: **309 tests, 17 expected skips, zero failures**.
- Independent audit of all **2,095,382,528 ISO bytes** against approved r67.12: **81 changed bytes**, strictly **2** ELF PT_LOAD metadata, **4** native constructor jump bytes, **73** nonzero helper-tail bytes, and **2** ISO9660 size-record bytes. **Every unrelated ISO byte is identical.** Details at `local/r67-13-chamber-complete-iso-byte-audit.json`.
- **4/4** approved r67.12 START history byte regions match in the staged ELF **and** final ISO. H.A.N.T. Basic Attack lock regression tests also pass. The new regression suite in `tests/test_r67_chamber_comment_geometry_probe.py` checks exact native instruction preimages, helper branch targets, touched-byte bounds, and fail-closed input hash.
- No change to source original disc, user original saves, global PCSX2 profile, Edge/YouTube or fonts. No release, approval, or PR merge implied.

## Visual-test caveat and remaining work

- Isolated PCSX2 uses a separate profile `local/pcsx2-67.06-isolated`, with copied state files. Replaying the older slot-2 state reached Heracleion, the earlier `[Old man's voice] Hey; over here.` story dialogue, and the H.A.N.T. tutorial; **not yet** the Chamber of Lions automatic comment. Do **not** treat this runtime work as acceptance of bubble geometry.
- The user slot 3 screenshot already has its text objects constructed, so reloading it under r67.13 is **not** an adequate renderer test. Re-enter the room from a state **before the automatic comment was instantiated** and capture a screenshot at its first appearance.
- If it remains outside the bubble, compare a fresh native constructor trace with the original slot-3 EE memory sample to confirm whether object style and X/Y are exactly as expected at construction time; this will determine if the hook fires.
- The r67.12 history presentation is visually approved only for the earlier single dialogue. Its multi-turn pagination and scrolling still require separate runtime verification and are not reopened by this fix.

**Do not request alterations to user's original slot 3 or merge until visual approval.**
