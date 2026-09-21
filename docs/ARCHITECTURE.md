# Architecture

## Principle

Every build is derived from pristine sources plus deterministic repository metadata. The project never patches the previously patched ISO as input.

## Layers

1. **Source identity** — hashes and game IDs prove the inputs.
2. **Corpus inventory** — compares PS2 and PS4 ADV assets and classifies source relationships independently from localization-map availability.
3. **Format parsers/compilers** — MTX, KSF, ELF, CVM and ISO logic remain isolated modules with structural validation.
4. **Localization importers** — official PS4 English is imported only when the correspondence can be proven. Ambiguity becomes a report item, not guessed output.
5. **Translation manifest/regression gate** — stable accepted entries prevent later builds from silently losing translations.
6. **Build/repack** — generated files go to ignored output trees; pristine sources stay untouched.

## Import confidence tiers

- **Exact/direct**: byte-identical source plus a DC map whose anchors resolve unambiguously to PS2 text spans. Automatic.
- **Structural**: source changed but semantic/control alignment is strong enough to prove correspondence. Future phase.
- **Template/semantic**: remaster collapsed several PS2 scripts into shared templates (notably FD00). Future phase.
- **PS2-only**: no PS4 counterpart; manual translation queue using official terminology as context.

## MTX

The first little-endian u16 encodes the pointer-header size in 4-byte units. Pointer targets are quarter-offsets and regions remain 4-byte aligned. Text and the ASCII-like command language coexist in the data area, so imported English currently uses the game's two-byte CP932/full-width glyph path to avoid creating opcode bytes.

## KSF

PS4 KSF DC maps provide useful official string anchors, but the PS4 runtime externalizes localization. A byte-identical KSF does not prove the PS2 inline field can hold longer English. This phase therefore patches only provably bounded, fitting fields; relocation waits for a fuller KSF compiler.

## Save compatibility

The PS2 executable uses `BISLPM-66511Save`. Ordinary memory-card saves are treated as cross-build compatibility targets. Savestates are build-specific and disposable.

## Runtime CVM / ROFS lookup

ISO9660 directory metadata is **not** the only runtime source of truth. `SLPM_665.11` contains a ROFS file table for CVM assets. Each proven record stores the file byte size 14 bytes before the NUL-terminated basename and the sector extent 6 bytes before it. The failed v1 whole-game runtime build proved that relocating a file while updating only ISO9660 leaves the game loading stale Japanese data.

`tools/build_translation_iso.py` therefore treats the executable table and embedded ISO directory as one atomic metadata update. Every overlay asset must have exactly one ELF record matching its pristine size+extent; the final record must resolve to the same output size+extent and payload hash as ISO9660. Missing, duplicate, or mismatched records are hard failures.

## ELF UI encodings

Do not assume all PS2 UI renderers accept single-byte ASCII simply because the executable contains ASCII elsewhere. The title renderer was runtime-proven to consume its menu labels as two-byte glyph units: replacing four Japanese CP932 glyphs with 8/9 ASCII bytes produced roughly 4/5 meaningless glyphs. Title test labels now use the two-byte CP932/full-width path. Other fixed UI fields remain renderer-specific and should not be promoted from static evidence to runtime-proven status without a visual test.
