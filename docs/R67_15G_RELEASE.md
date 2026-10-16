# r67.15g release integration contract

Status: a partial diagnostic has been built and audited; see
[the handoff](R67_15G_HANDOFF.md#built-partial-diagnostic) for artifact hashes
and finished-image evidence. Final full suite: 621 tests, 14 expected skips,
zero failures/errors on 2026-10-16. This does not imply gameplay/runtime approval.
Details reports `PARTIAL_OFFICIAL_SUBSET` with 36 unresolved records.
The default full-scope build still rejects it. An explicit partial
diagnostic path is available; parent route/provenance evidence is required
before either path can build.

## Inputs and sequence

The only accepted base is the approved r67.15f image:

| Artifact | Required SHA-256 |
| --- | --- |
| `local/r67-candidates/67.15f-item-panel-layout.iso` | `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0` |
| `local/r67-15f-item-panel-layout.elf` and the installed `SLPM_665.11` | `418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1` |
| Official `English.bytes` corpus | `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b` |

Components apply in this fixed order: tablet, Help, prologue, then Details.
The integration calls each component's existing interface explicitly:

| Component | Corpus argument | Existing-range convention |
| --- | --- | --- |
| Tablet | `official_corpus: Path` | half-open `(start, end)` |
| Help | `official_english_bytes: bytes` | half-open `(start, end)` |
| Prologue | `official_corpus: Path` | half-open `(start, end)` |
| Details | keyword-only `corpus_path: Path` | named half-open owner ranges |

The adapter converts ranges to named half-open spans, strips only the exact
four-byte ELF `PT_LOAD.p_filesz` field `[0x64,0x68)` for separate metadata
accounting, and rejects malformed, broad, overlapping, or out-of-source
permissions. Per-component checks compare every existing-byte delta against
that component's declared native owners, verify the segment metadata and
append extent, and reject unresolved mappings. Details must report
`PATCHED_ALL_OFFICIAL_DESCRIPTIONS` with zero unresolved records. Whole-file
15f hash equality is used only for the source; the candidate instead preserves
the accepted 15f hooks, item-name pointer catalogue and strings, Lion name,
and locked Group-4 art by their exact owners.

## Build and finished-image audit

The default `build(route_evidence=..., allow_partial_diagnostic=False)` path
remains fail-closed for incomplete Details coverage. The separate opt-in
`allow_partial_diagnostic=True` accepts only the exact
`PARTIAL_OFFICIAL_SUBSET` / `PARTIAL_NOT_FULL_SCOPE` report when its unresolved
count, IDs, preserved native IDs, source-row inventory, row count, and blocker
all agree. Only when the Details result is actually partial, it writes a
distinct artifact set headed by
`local/r67-candidates/67.15g-partial-diagnostic.iso`, and its manifest says
`PARTIAL_DIAGNOSTIC_NOT_GAMEPLAY_APPROVED`, `scope_complete: false`, and records
every unresolved item and preserved native Japanese source row. Invalid flags
or malformed/inconsistent gap reports fail closed. This exception changes
only the completeness gate and output labeling/path; the static and byte-level
audits below are identical.

Both paths require a read-only finished-image route report whose MTX records match
official source/map regeneration, all ten `MS00_02.KSF` choices fit and match
the importer, and `DG00_00.KSF` retains its three exact rows plus the two
historically approved compactions. It performs component preparation twice
and requires byte-identical results. The new destination is
`local/r67-candidates/67.15g-prologue-details-help.iso`; every output path is
checked against overwrite, then the ISO is APFS-cloned before mutation.

The 2,095,382,528-byte finished image is compared byte-for-byte with the
approved 15f ISO. Only component-owned executable deltas/appends and the
executable directory-record length in both endian encodings are allowed, with
each expected new byte checked. The executable must retain its ISO extent;
any growth is checked by the existing 14y overlap/volume guard and its zero
sector-slack guard. `DATA.CVM` must remain byte-identical, covering artwork,
ADV, and all other resources. A byte flip, wrong value, absent expected byte,
unexpected growth, malformed ELF, or changed record/resource fails the audit.

The approved 15f source lock is verified before composition, not claimed for a
changed candidate. Q/T/history/save validators run on the candidate. For the
historical T lock only, the verifier reconstructs the two 14t Lion callsite
words and three western-tablet pointer words in memory; it does not modify
either approved manifest. Startup is reported as raw 154/155 and scoped
155/155 only when the sole raw failure is the preserved bounded
`memory_card_8` wording; this is an explicit legacy expectation exception,
not a changed owner or gameplay claim. Static save identity is not cross-release
runtime compatibility.

## Evidence boundary

The release report must retain `gameplay_approved: false` and
`runtime_verified: false`. No emulator is launched. Even a successful
ISO audit proves only static owned-byte and payload provenance; cold-boot
screenshots, route reachability, visual fit, and save/load compatibility remain
separate acceptance evidence. Runtime endpoint captures are still pending.

Focused tests live in `tests/test_r67_15g_iso_release.py`. The finished-image
run passed; the handoff records its exact artifact and verification results.
A partial diagnostic is explicitly not full-scope translation and is not a
gameplay-approved release. The initial component task did not build an ISO;
the subsequent integrated build produced the separately named partial artifact.
