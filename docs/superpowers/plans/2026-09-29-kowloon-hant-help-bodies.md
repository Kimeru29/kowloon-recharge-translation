# H.A.N.T. Help Body Expansion Plan

## Goal
Translate the first newly proven selected H.A.N.T. Help body without regressing v11-r11 accepted presentation. Runtime labels and selected body pages are separate owners.

## Current evidence
- Help selection at VA `0x28D210..0x28D24C` calls the generic page constructor with `(mode=4, category, topic)`.
- Text resolver VA `0x2A9FE0` indexes the hierarchy rooted at VA `0x006CBAC0`.
- `(4,2,0)` resolves through descriptor file `0x5CBAB0` to body table file `0x5C8C70`; this is the already-translated H.A.N.T Functions/tutorial body.
- `(4,2,1)` resolves through `0x5CBAB4` to `0x5C9180` (`Command Thumbnails`), which remains Japanese and has two metadata records.
- `(4,2,5)` resolves through `0x5CBAC4` to `0x5C9B80` (`About the Shop`), seven pre-EOF rows and no metadata records. This is the minimal safe expansion target.
- The extracted PS4 tree still lacks `English.bytes`; new body wording must therefore be tagged `semantic`, not `official`.

## Tasks
1. Add failing tests that pin the `(4,2,5)` descriptor/table preimage, source rows, no-metadata property, semantic provenance, and post-patch descriptor relocation while preserving the pristine source table.
2. Implement a dedicated H.A.N.T. Help-body owner for `About the Shop`, using the existing shared translation PT_LOAD and EOF-terminated table model. Keep source strings/table byte-identical.
3. Add final-image/startup acceptance coverage for the translated body owner and fail-closed descriptor preimage.
4. Update current-status documentation with the manual r11 runtime truth and the new body ownership model; do not rewrite historical r5-r10 observations.
5. Run focused tests, full dependency-free tests, Pillow-enabled tests, build from the pristine ISO, final-image acceptance, and a repeat deterministic build. Produce a precise PCSX2 checklist; do not claim runtime acceptance until Pablo tests it.

## Constraints
- Preserve accepted r11 title/backing, memory-card tablet, quotes, profile/name screens, ADV dialogue, H.A.N.T. labels/navigation, and H.A.N.T Functions body.
- No speculative global renderer changes.
- Evidence before mutation; exact preimages; fail closed.
- `About the Shop` wording provenance is `semantic` unless official local corpus evidence appears.
