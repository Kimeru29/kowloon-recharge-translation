# Whole-game translation build design

## Goal

Produce the first deterministic whole-game PS2 English test candidate from pristine owned sources, without launching PCSX2. The candidate must preserve every accepted early translation, integrate every currently proven exact MTX/KSF import, add structurally changed MTX only when correspondence is proven, and emit machine-readable build evidence.

## Safety contract

- Always derive from the pristine Japanese ISO, never from a previously patched ISO.
- Never modify the pristine ISO, extracted PS2 files, PS4 files, or committed source fixtures.
- Every automatic import is fail-closed. Ambiguous correspondence remains Japanese and is reported.
- Keep `SLPM-66511` and `BISLPM-66511Save` unchanged.
- Do not launch PCSX2 until the exact expected visual scope of the produced candidate is stated to Pablo and he explicitly approves.
- Generated game binaries stay under ignored local/artifact paths and never enter Git.

## Architecture

### 1. Translation overlay

The build consumes one or more overlay roots whose paths are relative to `ADV/`, e.g. `DG/DG00_00.MTX`. Later roots may intentionally override earlier roots, but collisions are recorded with both hashes/provenance.

Initial sources:

1. `local/exact-mtx` — 962 proven exact/direct MTX outputs.
2. `local/exact-ksf` — 144 exact KSF outputs containing only fitting official fields.
3. `local/structural-mtx` — changed-source MTX outputs accepted by structural alignment.
4. `local/accepted-overrides` — accepted hand-tuned exceptions, initially the two constrained DG00 KSF choices so the historical vertical slice does not regress.

The early ELF UI patch remains a separate fixed-size outer-ISO replacement generated from the pristine ELF.

### 2. Generic nested ISO/CVM overlay builder

`DATA.CVM` contains a 0x1800-byte CRI CVM header followed by an ISO9660 payload.

For each translated ADV file:

- If the replacement still fits in the file's existing sector allocation, overwrite it in place and patch only the directory size.
- If it needs more sectors, append the whole replacement at the end of the embedded ISO payload, patch that directory record's extent and size, and leave the original extent unused.

After all relocations:

- grow the embedded ISO volume declaration by the total appended sectors;
- grow the three proven CVM size fields by the same number of bytes;
- shift the small outer-ISO tail (SYSTEM.CNF + IRX files) right by the same number of sectors;
- patch those outer directory extents and the `DATA.CVM` directory size;
- keep the outer ISO volume size/file length unchanged when the original trailing slack is sufficient; fail rather than silently expanding unless a separately tested expansion path is implemented.

The current corpus requires only about 854 appended sectors (~1.75 MiB), while the source outer ISO has over 10,000 free tail sectors, so fixed-size output is feasible.

### 3. Structural MTX importer

Changed PS4/PS2 MTX pairs use byte-level monotonic alignment only as an address-mapping primitive, not as semantic proof.

For each PS4 DC group:

1. Parse the localized text span on the PS4 source with the existing boundary-aware DC parser.
2. Use `difflib.SequenceMatcher(..., autojunk=False)` to build monotonic matching blocks between PS4 and PS2 bytes.
3. Map both the text-span start and end only when they lie on exact matching-block boundaries/interiors.
4. Require the entire PS4 source text span to be byte-identical to the mapped PS2 span.
5. Require CP932 boundaries and non-overlapping monotonic mapped spans on PS2.
6. Compile with `MtxFile.apply_replacements`, reparse the output, and preserve pointer/control invariants.

A file may be automatically emitted only if **every English DC group in that file** is proven. Partial structural files remain rejected for this first whole-game candidate, avoiding mixed unsafe assumptions.

`DG/DG13_02.MTX` is the first acceptance target because prior analysis mapped all 577/577 entries and the files are ~99.7% identical.

### 4. FD00/template family

The remaster collapses many FD00-family scripts into shared 604-byte templates, so raw offset alignment is explicitly forbidden. This phase will investigate and prototype semantic alignment using Japanese dialogue identity, speaker identity, neighboring control tokens, and monotonic sequence position. Only uniquely proven matches may be emitted; otherwise the family remains Japanese in the candidate.

### 5. KSF overflow research

The exact KSF importer keeps 48 overflowing official strings Japanese. This phase will inspect record structure and reference patterns to determine whether KSF text is relocatable or pointer-addressed. No bulk relocation is accepted until references are proven and regression-tested. The two already accepted DG00 shortened choices remain explicit manual exceptions, not evidence that arbitrary truncation is acceptable.

### 6. Graphics research

Continue locating the official localized graphics referenced by `AssetFileDic_en.txt` inside Unity assets/bundles. The test candidate does not depend on graphics unless a deterministic extractor and a proven PS2 format-equivalent conversion path are established.

## Verification

Before asking for a runtime test:

- full Python suite passes;
- exact MTX/KSF reports regenerate deterministically;
- structural importer report proves all emitted files have 100% mapped groups;
- overlay manifest records path, provenance, source hash, output hash, size, and collision history;
- whole-game builder validates every translated output byte-for-byte from the finished ISO;
- outer tail payloads remain byte-identical;
- source ISO remains unchanged;
- boot ELF still contains `SLPM-66511` identity and `BISLPM-66511Save`;
- accepted early DG00 MTX/KSF and ELF UI translations are present in the finished ISO;
- Git contains tooling/docs/tests only, never generated game binaries.

Only after these checks will the exact expected visible scope be stated and emulator approval requested.