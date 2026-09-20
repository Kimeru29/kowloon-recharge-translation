# Verified discoveries

## Source identity

- PS2 archive SHA-256: `e5ff46e62846758cda33bd5a4ef98d12d6bdfe2f76cdd6ac73145a76f68a3fec`.
- Pristine extracted PS2 ISO SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`.
- PS4 PKG SHA-256: `054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`, title `CUSA27034`.
- PS2 boot executable: `SLPM_665.11`; serial invariant: `SLPM-66511`; save directory invariant: `BISLPM-66511Save`.
- `local/source-manifest.json` records the current absolute paths, sizes and hashes and is intentionally ignored by Git.

## ADV corpus — live generated manifest

`local/corpus-manifest.json` is generated from the current extracted PS2/PS4 sources.

### MTX

- PS2 total: 1,516.
- PS4 counterparts: 1,067.
- Byte-identical: 1,022.
- Structurally changed, unique PS4 binary: 19.
- Changed and detected as shared/template PS4 binary: 26.
- PS2-only: 449.
- English-mapped PS2 files: 1,028, totaling 100,398 official English DC entries.
- Common but English-unmapped: 39.
- 985 files are both byte-identical and English-mapped, totaling 78,314 official English entries.
- 43 English-mapped files differ structurally, totaling 22,084 entries; two additional changed MTX files are not English-mapped.

### KSF

- PS2 total: 1,516.
- PS4 counterparts: 1,067.
- Byte-identical: **1,010**.
- Structurally changed, unique PS4 binary: 29.
- Changed and detected as shared/template PS4 binary: 28.
- PS2-only: 449.
- English-mapped PS2 files: 164, totaling 1,089 official entries.
- Exact + English-mapped: 144 files.

This corrects an earlier exploratory count of 1,019 exact KSF files. The deterministic live scanner and an independent direct byte comparison both report 1,010 exact / 57 changed common KSF files.

## Exact MTX importer

`local/exact-import-report.json` records every exact+mapped MTX attempt.

- Eligible: 985 files / 78,314 English entries.
- Imported with proven direct anchors/control boundaries: **962 files / 56,642 entries**.
- Rejected fail-closed: **23 files / 21,672 entries**.

The rejected set is dominated by MS scripts whose DC keys hit still-unresolved continuation/control semantics. `FN/FN02_31.MTX` is especially important evidence: its source is only 604 bytes but its English DC map has 1,294 entries and duplicate/dense keys, so it is clearly an indirect/dynamic map despite byte-identical PS2/PS4 source. The importer correctly refuses to treat those keys as literal offsets.

Conservative localized-span terminators currently proven are `r` at the end of a segment, `wc`, `}w`, and boundary-aligned fallbacks `}`, `rds`, `ds`, or a trailing `c`. Marker matches must begin on decoded CP932 boundaries.

## Exact KSF conservative importer

`local/ksf-report.json` covers the 144 exact+mapped KSF files.

- Provably fitting fixed-field entries: **868**.
- Overflows: **48** — never truncated and left untouched.
- Ambiguous: **4**, all four being non-ASCII ideographic-space-only values in `MS/MS09_03.KSF`.
- All 144 exact-mapped files contain at least one provably fitting entry.

A KSF field is currently accepted only when the DC key is immediately preceded by the observed `0x01` string-record marker, the source text is valid CP932 and NUL terminated, the padding remains zero until a following nonzero structural byte, and normalized English fits that proven capacity. This is intentionally narrower than a relocatable KSF compiler.

## PS2-only text-size estimate

File count badly overstates the exclusive translation burden. A deterministic lexical scan of MTX CP932 literals (minimum two characters, ASCII command bytes treated as separators) reports:

- Unique runs across all PS2 MTX: **41,337**.
- Unique runs in English-mapped common files: **40,824**.
- Unique runs appearing in PS2-only files: **568**.
- Of those PS2-only runs, 149 also occur in mapped common content.
- **Novel PS2-only runs: 419**, totaling **3,672 Japanese characters**.
- Common-but-English-unmapped novel runs: 94.

Thus mapped common content contains roughly 98.8% of this lexical-run universe, while novel PS2-only material is roughly 1.0%. This is an estimator, not a dialogue-line or word count: MTX ASCII controls split Japanese source text, and a run being present in an English-mapped file does not prove that every occurrence is individually localized by a DC entry.

An exact-key lookup of the 419 novel PS2-only runs against `English.bytes` found zero exact matches. Earlier substring experiments did find a small amount of reusable translation memory, so `English.bytes` remains useful for terminology/context but not blind replacement.

## FD00 family

Many remaster `FD00_*` scripts were consolidated into a shared 604-byte MTX template while PS2 files are larger and distinct. Raw offset alignment is the wrong algorithm for this family; it requires semantic/template matching.

## MTX encoding

The official English MTX corpus uses printable ASCII plus `—`, `―`, `’`, `♪`, ideographic space, `【` and `】`. The generalized encoder maps printable ASCII to full-width/JIS equivalents, straight apostrophe to `’`, em dash to the CP932-compatible horizontal bar `―`, preserves supported non-ASCII localization glyphs, and requires every emitted glyph to occupy exactly two CP932 bytes. This avoids injecting ordinary ASCII opcode bytes into MTX dialogue.

## Fonts

PS2 `SYSFONTALL.FNT` and `ADVFONTALL.FNT` contain Latin uppercase/lowercase/digits. No new glyph drawing is required merely to display Latin. Ordinary ASCII is safe in proven system UI fields but is not yet safe as literal MTX dialogue because MTX uses ASCII commands/opcodes.

## Save system

The executable contains `BISLPM-66511Save` and normal `mc0:`/`mc%d:` save paths. Treat normal memory-card saves as the compatibility contract across patched builds; do not rely on savestates across builds. A real cross-build create-save/load-save runtime test is still required once the next emulator launch is approved.
