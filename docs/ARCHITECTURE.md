# Architecture

## Principle

Every output is derived from pristine user-owned sources plus deterministic tooling/metadata. Never use a previously patched ISO as build input. Automatic localization is fail-closed: uncertainty produces a report/rejection, not a guessed translation.

## Layers

1. **Source identity** — hashes and game IDs prove the PS2/PS4 inputs.
2. **Corpus inventory** — PS2/PS4 ADV relationships and English-map availability are classified independently.
3. **Format parsers/compilers** — MTX, KSF, TMX, ELF/ROFS, CVM and ISO9660 logic are isolated and structurally validated.
4. **Localization importers** — exact, structural and explicit-reviewed imports emit only proven outputs.
5. **Startup/UI backport** — executable-resident UI and localized PS4 graphics are ported through renderer-specific encodings and PS2 indexed textures.
6. **Regression/identity gate** — accepted translations, serial and save namespace cannot silently drift.
7. **Build/repack** — overlays are applied to the nested CVM ISO, executable ROFS metadata is updated atomically, and the finished image is re-read and verified.

## MTX

The first little-endian u16 is the pointer-header size in 4-byte units. Pointer targets are quarter-offsets and rebuilt regions stay 4-byte aligned. Because MTX also uses ordinary ASCII as a command language, localized dialogue uses the PS2 two-byte CP932/full-width glyph path rather than injecting ambiguous ASCII opcode bytes.

## KSF

PS4 KSF DC maps identify official strings, but English can exceed PS2 inline field capacity. The current importer accepts only proven fixed fields whose English fits. Overflow fields stay Japanese unless there is a reviewed constrained override. A relocatable general KSF compiler is still unproven.

## Executable UI

Renderer encoding is not assumed globally. The title renderer was runtime-proven to consume two-byte glyph units. The exact official labels are now stored in a verified 40-byte title arena: `New Game` remains at the first source slot and `Load Game` is moved within the arena with its pointer updated. Name-entry keyboard cells also remain two-byte glyphs and preserve the original 20-key logical geometry.

Name/profile startup prompts are a separate two-byte-glyph class. Six official English prompts fit a verified module-local arena; the two reading prompts overflow that arena and are relocated by v7 into the shared executable translation PT_LOAD. Protagonist/default names are redirected to wide strings. Default/runtime kana-reading values can remain blank, but the active reading-input prompts must not be blank. All source preimages, staged/final pointer preimages, arena bounds, and emitted wide strings are fail-closed tests. Static tracing also shows the PS2 name editor has two structural 3-glyph permanent-name buffers; this is tracked as an unresolved renderer/input-structure issue rather than patched as data.

## PS2 indexed graphics

`tools/tmx.py` handles both named TMX chunks inside `B_GPxxx.BIN` containers and standalone `TMX0` files. `tools/graphics_port.py` downsizes official PS4 RGBA artwork, quantizes it to the PS2 palette size, preserves 4/8-bit indexed layout and CLUT ordering, and rewrites only palette/pixel payloads. File/container sizes remain fixed.

The first accepted graphics scope is startup-specific:

- `BLBRD/B_GP019.BIN` — name-entry controls;
- `BLBRD/INIT_MES/TR000.TMX` through `TR028.TMX` — the 29 random opening quotation images.

Generated graphics remain local-only; repository code stores no copyrighted artwork.

## Runtime CVM / ROFS lookup

ISO9660 is not the only runtime source of truth. `SLPM_665.11` contains a ROFS file table: for the proven records, byte size is 14 bytes before the NUL-terminated basename and sector extent is 6 bytes before it. The failed v1 runtime build proved that updating only ISO9660 leaves the game loading stale Japanese sectors.

`tools/build_translation_iso.py` therefore treats embedded ISO metadata and executable ROFS metadata as one atomic update. Every overlay asset must have a unique pristine size+extent match in the ELF; the final record must resolve to the same output size/extent and payload as ISO9660. Missing, duplicate or mismatched records are hard failures.

## Save compatibility

The executable uses `BISLPM-66511Save`. Ordinary memory-card saves are the cross-build compatibility target. Savestates are considered build-specific. The serial `SLPM-66511` and save namespace are build invariants.
