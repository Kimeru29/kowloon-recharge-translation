# r67.15e — Compounding bubble and same-item label

**Status: diagnostic built and statically validated, awaiting gameplay screenshots.** The user explicitly accepted all r67.15d UI fixes; 15d is a locked new baseline. Do not adjust its already-accepted storage title, Items footer, Gold Chains inspection, item catalog, Lion Statue, save, history, event or other gameplay owners without a separately justified and approved change.

## User-reported remaining issues

The screenshot shows a small white floating action label when choosing the second component during item synthesis:

1. Selecting a different second item shows the correct **Compound** text but its white background only encloses the beginning of the label. The native action white-bubble sprite must extend horizontally toward X+; do not shrink the correct official English text or change the global font.
2. Selecting the first item again shows **禁止**. The official PS4 English corpus **English.bytes at offset 0x461E4** maps this exact Japanese to **"Can't"**.

## Native provenance and minimal patch

The two actions are part of the separate native H_Item floating action owner at **VA 0x114A20**. Construction first calls the native sprite creator **0x107D60**, with sprite type **0x5E or 0x5F**, saves its handle in **0(s0)**, and then looks up the string indexed by **0x18(s0)** via action table starting at ELF offset **0x386320** (VA 0x4862A0). Previously translated **Compound** has action index **3**, pointer table owner **0x38632C**; same-item **Can't** is action index **1**, owner **0x386324**, original pointer **0x793668**.

The original sprite constructor at **VA 0x107FBC** sets float X scale at **sprite +0x60** to 1.0; it separately initializes Y scale at sprite +0x64. Only the prior branch **VA 0x114AD8** is redirected to an append-only, 44-byte helper. It checks action ID 3 and non-null sprite handle, then assigns **X scale 2.0**, leaving sprite Y scale, position, other actions and their text untouched. The helper tail-jumps to the original **VA 0x114B00** continuation, preserving all caller-owned state and loop counter. Its native delay slot remains a NOP. No global text or object re-layout is performed.

The untranslated same-item action pointer **0x386324** alone is redirected to appended fullwidth-encoded **"Can't"**, preserving PS4's contraction and the native action slot. The original Japanese string and other pointer table entries remain unchanged.

The immutable parent ELF SHA-256 is:

`bff8439a1696272342130808339dd20580c3391538dc5a2c9f1b773f129b23e4`

The parent ISO SHA-256 is:

`5d5850b660e92d9fd0dcb11456519d99b060cbaae131ebf48f6d0f80262a446d`

The new diagnostic ISO is:

`local/r67-candidates/67.15e-compound-bubble.iso`

SHA-256:

`442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014`

The **entire 2,095,382,528-byte ISO** was compared against the SHA-verified 15d baseline. Exactly **42 bytes changed, zero unexplained** (pointer, single native branch, ELF/ISO length fields, appended helper and English glyphs). All prior GP004 assets are **byte identical**. Evidence: `local/r67-15e-whole-iso-audit.json`.

## Lock and validation

- **Approved 15d locked:** tests require the entire original SHA-verified 15d ELF and ISO and fail closed for changes to *any* existing byte beyond the two specifically authorized pointer/branch sites and length field. 15d original object, item catalog, UI, renderers, scripts and stage bytes remain unchanged.
- **Unchanged prior approvals:** strict q and t approval manifests are run; the two accepted r67.15a Lion Statue JALs are reconstructed from the SHA-verified z ELF **in memory only**, without weakening original manifests.
- **Native MIPS execution:** the eleven-instruction helper is run inside disposable Unicorn MIPS32 emulation for **16 action IDs × 2 (null/non-null sprite) = 32 cases**. Only action ID 3 with a valid sprite sets X scale to 2.0; all other action IDs remain 1.0. In every case sprite Y stays 1.0, the original A1 loop register remains zero, and execution resumes at VA 0x114B00.
- **Official localization:** corpus SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`, original 禁止 maps exactly to **"Can't"**, and the emitted CP932 glyph string is `Ｃａｎ’ｔ`.
- **Startup:** original 154/155 raw, with only previously documented old `memory_card_8` overflowing-text fixture; established scoped acceptance passes **155/155**. History 4/4, all 15 native save descriptor windows unchanged, original SLPM-66511 and BISLPM-66511Save identifiers preserved.
- **Cross-release card save/load:** not verified in emulator; no existing active emulator, memory card or savestate modified.
- Focused tests: `tests/test_r67_15e_compound_bubble.py`.
- **Repository-wide suite: 521 tests, 14 skipped, 0 failures/errors**, exit code **0**, completed in 111.406 seconds. Logs: `local/r67-15e-complete-suite.log`, `local/r67-15e-complete-suite.exit`. Optional fixture-dependent skips are reported as skips, not passes.

### Historical artifact restoration

During the regression suite, the earlier 15c ISO was no longer present in its original local path; an existing historical 15d full-disc audit requires it. It was **reconstructed without overwriting any existing file** into `local/r67-candidates/67.15c-synthesis-items-ui.iso` by reversing the known 15d ELF and group4 changes using the preserved, SHA-pinned 15c staged ELF and graphics. Its entire-disc SHA-256 was rechecked as **d140cca2ce4c9603d5f89a4b0413c4dc5ddce0e1385301e9a11f376fa17368aa**, precisely equal to the originally recorded 15c build. The earlier 15b ISO required by the chained 15c regression was also missing, so it was reconstructed from this SHA-verified 15c copy using the preserved 15b ELF and native GP004 sprite. Its complete SHA-256 likewise matches the original recorded 15b build exactly: **8c63c86d64de7cb770bab350a8728fe76db5e6825693b3614d9c559e408f7704**. Both restorations use a new, nonexistent destination and SHA verification before promoting the temporary file. Neither process changed the approved 15d ISO or the 15e candidate.

## Pending gameplay test

Cold boot 15e (do not simply rename/load an old state). Repeat the same Storeroom Items workflow: select one item, select a distinct second item (verify white background fully encloses all eight letters of **Compound**, with its left edge/vertical layout intact), then select the same item twice (verify official **Can't** fits inside white bubble). Inspect the previously accepted Gold Chains, acquisition and Items footer again. **The MIPS scale test proves the X-scale write, not on-screen border geometry**; user screenshots remain essential.

No promotion or merge without explicit user gameplay approval.
