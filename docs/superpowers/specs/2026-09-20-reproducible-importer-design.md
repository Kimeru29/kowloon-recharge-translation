# Reproducible Importer Phase Design

## Goal

Turn the current Kowloon Youma Gakuenki re-charge reverse-engineering workspace into a reproducible, handoff-safe project that can automatically import every PS4 English localization item whose PS2 correspondence is proven, while failing closed for ambiguous content and preventing previously accepted translations from silently disappearing.

## Project invariants

- The pristine PS2 and PS4 sources are never modified.
- The repository never contains an ISO, PKG, CVM, extracted copyrighted game tree, font dump, texture dump, executable, or copied game script fixture.
- Generated translated binaries stay local and ignored by Git.
- Every automatic import is provenance-bearing and deterministic from pristine sources plus repository code/manifests.
- Ambiguous mappings are reported, never guessed.
- `SLPM-66511` and save directory `BISLPM-66511Save` are permanent compatibility invariants.
- PCSX2 must not be launched until Pablo has been told exactly what the next build should display and explicitly approves that launch.

## Verified source identity

Local source locations are configuration, not repository requirements. The currently verified sources are:

- PS2 archive: `Kowloon Youma Gakuenki re-charge (Japan).7z`, SHA-256 `e5ff46e62846758cda33bd5a4ef98d12d6bdfe2f76cdd6ac73145a76f68a3fec`.
- Extracted pristine PS2 ISO: SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`.
- PS4 package: `khc.pkg`, title `CUSA27034`, SHA-256 `054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`.
- PS2 executable identity: `SLPM_665.11` / serial `SLPM-66511`.

A checked-in example source configuration documents expected inputs. A generated local manifest records absolute paths, sizes, and hashes and remains ignored.

## Repository layout

- `tools/`: parsers, classifiers, importers, validators, builders.
- `tests/`: synthetic unit tests plus optional local integration tests that skip cleanly when copyrighted fixtures are absent.
- `translations/`: hand-authored translation metadata only; no copied source game content.
- `docs/`: architecture, discovery, build instructions, regression policy, and AI handoff.
- `config/`: safe example configuration and expected source identities.
- `local/`: generated machine-specific manifests/reports; ignored.
- `artifacts/`: generated binaries/images/build outputs; ignored.
- `fixtures/`: local copyrighted fixtures may exist for integration testing but are ignored except for a README explaining how they are obtained from owned sources.

## Corpus model

A corpus scanner compares PS2 `ADV` files with the PS4 remaster `ADV` tree. For each MTX and KSF it records:

- relative path and kind;
- SHA-256 and size for each available source;
- source relationship: `exact`, `structural`, `template`, or `ps2-only`;
- English DC map presence and entry count;
- localization status: `mapped`, `unmapped`, or `not-applicable`;
- direct-import status and a reason when automatic import is rejected.

`template` is reserved for a changed PS4 source whose binary is shared across several distinct script paths, such as the consolidated FD00 family. `structural` means a PS4 counterpart exists but differs and is not a detected shared template. `unmapped` is localization metadata, not a claim that the source file has no counterpart.

The manifest also emits aggregate counts and coverage metrics. Metrics distinguish file overlap from localization-entry coverage so file count is not misreported as translation percentage.

## MTX direct importer

Exact source identity is necessary but not sufficient for direct import. Some remaster DC maps use indirect/dynamic keys even when the MTX binary is byte-identical. Therefore direct import requires all of the following:

1. PS2 and PS4 MTX bytes are identical.
2. An English `*DC.json` map exists.
3. Every mapped group can be resolved to a non-overlapping PS2 text span with a supported control terminator.
4. Every output character can be represented through the PS2 two-byte CP932/full-width glyph path.
5. Rebuilding pointer regions preserves MTX structural assertions.

The importer writes translated MTX files only for files that pass all checks. Rejected files remain unchanged and receive a machine-readable reason. No fuzzy correspondence is used in the exact tier.

The English encoder supports the complete character repertoire observed in the official English MTX corpus by mapping printable ASCII to full-width Unicode equivalents, space to U+3000, and preserving CP932-compatible non-ASCII localization glyphs such as `【】`, `♪`, `―`, `—`, and `’` through verified two-byte representations.

## KSF policy for this phase

Byte-identical PS2/PS4 KSF files give reliable DC anchor provenance, but the PS4 runtime applies localization externally and does not prove that the PS2 binary has enough inline storage for the English string. The current PS2 implementation has demonstrated fixed-capacity fields.

Therefore this phase does not pretend that every exact KSF map is directly writable. The scanner classifies exact KSF maps, and a conservative importer may patch only fields whose capacity can be proven and whose official normalized ASCII text fits without relocating unknown structures. Overflow or ambiguous fields are reported for the future relocatable-KSF compiler. Truncation is forbidden.

## Regression manifest

Accepted generated translations are represented by stable entries containing:

- stable ID;
- asset relative path and format;
- source SHA-256/preimage identity;
- provenance (`official-ps4`, `manual`, or `ui-patch`);
- localization anchor or patch identity;
- normalized translated text or generated output SHA-256.

A regression comparison emits `added`, `changed`, and `removed`. Unless explicitly acknowledged in the baseline update, any removed accepted entry fails validation. Source hash changes also fail closed.

The regression validator additionally enforces the save/serial invariants `SLPM-66511` and `BISLPM-66511Save`.

## Documentation and handoff

`docs/HANDOFF.md` is the one-file entry point for a future AI session. It contains the verified facts, paths, current phase, commands, unresolved reverse-engineering questions, corpus statistics, safety rules, and the emulator approval gate. Other docs provide deeper architecture, discovery evidence, build instructions, and regression policy.

## GitHub

The canonical remote will be a private repository owned by the authenticated GitHub account. Only safe source code, tests, documentation, schemas, hashes, and hand-authored metadata are pushed. A pre-push repository audit checks for forbidden binary extensions and known local game-source paths.

## Success criteria

This phase is complete when:

1. A clean clone without copyrighted fixtures can run the non-integration test suite successfully, with local-fixture tests skipped rather than failing.
2. The corpus scanner reproduces the known high-level PS2/PS4 counts and writes a deterministic JSON report.
3. The generalized English encoder covers the observed official MTX character repertoire.
4. The exact MTX importer processes every confidently direct exact file and explicitly reports every rejected exact file; no ambiguity is silently imported.
5. KSF exact mappings are inventoried and only provably safe fitting fields are patched.
6. Regression validation detects removed accepted translations and source/save identity drift.
7. Project documentation is sufficient to resume from another chat without reconstructing discoveries from conversation history.
8. The private GitHub repository is created and the verified project state is pushed.
9. No emulator is launched during this phase.
