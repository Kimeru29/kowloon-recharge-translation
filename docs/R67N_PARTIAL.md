# r67.15n partial MTX transfer

The strict importer recovered **5,275 official English entries in 5,196 DC groups** across three of the thirty files examined. This is source and payload evidence. In-game rendering, player-name expansion, chapter reachability, and save compatibility require runtime verification.

| MS file | Official entries | Proven groups | Proven entries | Unresolved groups | Unresolved entries |
|---|---:|---:|---:|---:|---:|
| MS00_01 | 43 | 0 | 0 | 42 | 43 |
| MS01_00 | 2,541 | 2,504 | 2,539 | 2 | 2 |
| MS01_03 | 226 | 0 | 0 | 222 | 226 |
| MS06_03 | 1,734 | 1,688 | 1,729 | 5 | 5 |
| MS13_02 | 1,104 | 1,004 | 1,007 | 97 | 97 |
| FD00_00–23 and FD00_29 | 729 | 0 | 0 | 729 | 729 |
| **Total** | **6,377** | **5,196** | **5,275** | **1,097** | **1,102** |

## Source and relocation proof

DC keys, including synthetic continuation keys, establish source geometry through the existing DC parser. The importer validates the original English values per group after geometry is established. This lets a group with an unsupported macro be reported at its own original offsets.

A transfer requires an exact Japanese byte span at CP932 boundaries, with the same pointer-table slots and matching text-boundary controls. It identifies the occurrence by full pointer-region equality or byte-identical context that occurs exactly once inside each corresponding pointer region. Repeated or conflicting candidates, crossed pointer targets, and unrecognized source controls remain unresolved. Numeric command operands are used literally.

The established English encoding emits full-width glyphs and follows the official synthetic row layout. Native display-only ruby and line breaks may be reflowed inside a proven span. Name placeholders use the native spellings documented in [the dynamic lookup trace](R67N_DYNAMIC_LOOKUP.md). If official text moves or reorders an existing name, all groups in the replacement scope must be proven and joined exclusively by original `r` display separators on both platforms within one pointer region. The scope preserves the count of every native name control. Unknown phonetic macros remain unresolved.

The existing MTX compiler relocates native pointer offsets. The audit walks the original and emitted bytes independently of the compiler. It checks each replacement against its encoded source, each suffix and interstitial run against PS2, the alignment NULs after the original underscore terminators, and every pointer slot including aliases and zero words. Every accepted original span, exact context, English replacement, and encoded official entry has offsets and SHA-256 evidence. Candidate offsets in unresolved rows are search evidence and do not assert correspondence.

## Outstanding review

- **MS00_01 and MS01_03** retain their original PS2 script bytes. Their PS4 spans do not occur as eligible PS2 spans. MS01_03 additionally has two unsupported phonetic macro groups.
- **MS01_00** retains an unresolved repeated speaker label at PS4 offset 19081 and a name-token group at 33444. The following group at 19092 has unique, byte-identical 784-byte context in pointer slot 63 and transfers separately.
- **MS06_03** retains five speaker labels whose source contexts do not single out an exact target. Its title-like block at PS2 and PS4 offset 19769 uses native delimiters `w60{` and `}w`. The 48-cell English row at output offsets 32873–32969 exceeds the inherited 39-cell triage threshold, so inspect this transition in the candidate. The entire official row is encoded.
- **MS13_02** retains 97 groups. Conflicting or inverted candidate claims account for 52, incompatible literal contexts 20, absent exact spans 12, different pointer slots 7, and repeated exact contexts 6.
- **FD00** tested each of the 729 same-path official DC groups in the 25 unresolved template files. For 707 groups the literal Japanese span was absent. Eleven have no proven control context, ten lack pointer-slot identity, and one is repeated or ambiguous. Alternate file ownership remains open.
- **Layout and names** have at most two official rows per proven DC group. There are 121 rows with dynamic name expansion. Check these with non-default full-length names and review the marked speaker, title, and branch contexts. Cell counts omit the runtime name expansion, and context tags identify source shapes for triage.

## Reproduction

`tools.r67n_partial.import_partial_mtx(ps2_raw, ps4_raw, dc)` returns the payload, proven and unresolved records, pointer and region evidence, and source, DC, and output hashes. `verify_partial_mtx(ps2_raw, ps4_raw, dc, result)` verifies the report and output using the same owned source files without trusting the compiler's writes. For a serialized DC file, additionally compare its raw SHA-256 with `official_map_sha256`; `dc_sha256` fingerprints the canonical parsed object.

Reproduce the fixed five-MS and twenty-five-FD scope with the owned ADV source roots and a fresh destination.

```sh
python -m tools.r67n_partial_corpus \
  --ps2-adv /path/to/ps2/ADV \
  --ps4-adv /path/to/ps4/ADV \
  --output-dir local/r67n-partial-replay
```

The CLI writes `report.json` and an `overlay` tree. It refuses every existing destination. The local production sweep is `local/r67n-partial/report.json`. It includes raw map SHA-256 values, exact output paths and digests, an offset-level record for every official key, and layout triage. The three verified payloads are under `local/r67n-partial/overlay/MS/`. Reproduce a focused check with the repository's Python 3.14 runtime.

```sh
python -m unittest tests.test_r67n_partial_corpus tests.test_r67n_partial \
  tests.test_mtx tests.test_mtx_compile \
  tests.test_localization tests.test_structural_import tests.test_structural_corpus_import -v
```
