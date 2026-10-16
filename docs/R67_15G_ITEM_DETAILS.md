# r67.15g item-menu SELECT Details

Status: implemented as a proven official subset; release status is **PARTIAL_NOT_FULL_SCOPE**. This component does not claim all item descriptions are translated. No emulator/runtime approval, final ISO, or commit is part of this component.

## Scope and interface

`tools/r67_15g_item_details.py` exposes `apply(source: bytes, *, corpus_path=CORPUS_PATH) -> (bytes, report)` and `PERMITTED_EXISTING_RANGES`. It reads the official PS4 corpus at build time; no extracted asset or corpus is copied into the repository. It validates its own native/table preimages against `local/r67-15f-item-panel-layout.elf`, so another approved transform may append its payload or modify its own hook first. This is not a whole-input hash check.

Example integration:

```python
from tools.r67_15g_item_details import apply

image, details_report = apply(previous_transform_image)
```

The only original-code range owned here is the JAL at file offset `0x1520C` through `0x15210`; the ELF `p_filesz` word at `0x64..0x68` is updated as append metadata and separately audited by the parent integrator. All strings, a sparse 756-entry full-item-ID pointer table, and the helper are appended in the reserved load segment. A zero pointer slot keeps the exact pointer returned by the original getter.

## Native owner and layout proof

This patches the SELECT Details paragraph consumer, not the card-name renderer. The getter at EE VA `0x134B80` masks the ID to 16 bits, uses the sentinel pointer for `0xFFFF`, indexes the primary description table at `0x49BEF4` for IDs below 500, and indexes the alternate table at `0x49CB00` using the full ID otherwise. The getter has one JAL caller, at `0x115148`; that call is in the paragraph-construction path. The getter result is passed to text constructor `0x189E40` by the call at `0x11518C` (file offset `0x1520C`), and the returned handle is stored at instance `s2+0x190`.

That caller creates the group-4/type-`0x0B` frame, whose native sprite is `256x112` pixels. Paragraph origin is frame `(x+26,y+16)` and its right bound is `x+256-10`, so the text rectangle is `220x96`. The existing font has `16x18` metric cells. The component calls the existing per-instance metric setter `0x18B120` after native construction, at scale `0.5`: effective cells are `8x9` pixels, allowing 27 cells per row and 10 rows. English is wrapped at whole-word boundaries, preserving every official word. Source rows without an exact official key stay Japanese and retain their explicit source row separation. The measured worst case is 5 rows in the full 431-record catalogue; all generated rows are checked against the 10-row/27-cell rectangle before patch emission. No global font, item name, stat, ID, or gameplay logic changes.

## Catalogue and official-source evidence

The pinned native name and description table preimages are:

| Owner | VA | Length | SHA-256 |
| --- | ---: | ---: | --- |
| Primary Details pointers | `0x49BEF4` | 500 x 4 | `4550051ea3a1948f06ec9b594c6616a3abe2e9368d3e414d38e60e4c34af8f01` |
| Alternate Details pointers, IDs 500–536 | `0x49CB00 + 500*4` | 37 x 4 | `dfb51bf0054523ef71feb404d6d950c39c020758a742603fb4b82e4027609e38` |
| Primary item-name pointers | `0x491234` | 500 x 4 | `5280ead4ca65b89c495970984e650fbec52f51cf0ceac1d8a376995361423057` |
| Alternate item-name pointers, IDs 500–536 | `0x4913A0 + 500*4` | 37 x 4 | `fba0631cf1b0b74c2e0027e3250120863f766adba9f13a19374e5e93ebde86fa` |

Binary-derived valid catalogue counts are 446 primary names and 37 alternate names. Of those, 394 primary and all 37 alternate IDs have mapped Details paragraphs: 431 total. A further 52 primary name records have no valid mapped Details text and are not fabricated into the Details catalogue. Pointer aliases are `(0,536)`, `(89,90)`, and `(137,209,238,327)`; each ID is still independently represented in the report/table. Four valid records resolve to an all-break empty paragraph and contain no prose.

The official source is `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`, SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`. It parses to 11,711 records. Keys are matched exactly, including the native `＠改行` marker when present; ambiguous keys, missing source markers, malformed native pointers, changed owner tables/callsites, and a corpus hash mismatch fail closed. ID 112's final row has no terminal marker and is mapped using its exact source key, not a synthesized key.

Current exact coverage: 391 nonempty descriptions fully mapped from official English rows, plus four valid empty/no-prose records. The native catalogue contains 1,452 source rows; 1,346 have exact official mappings. Five alternate records (IDs `500, 501, 504, 515, 534`) have at least one exact official row and remain partially Japanese. The other 31 alternate records—`502, 503, 505–514, 516–533, 535`—have no exact official row. Across IDs 500–535, 106 unmatched source rows are retained in Japanese, without authored or guessed English. The generated report identifies all 36 unresolved IDs and the five mixed entries individually.

## Search for alternate official source text and remaining blocker

Before marking the catalogue gap, the full recovered PS4 `StreamingAssets` tree was searched at:

`/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/Media/StreamingAssets`

The read-only search inspected 6,975 candidate files (63,450,113 bytes) across `.bytes`, `.ksf`, `.kes`, `.esf`, `.json`, `.txt`, `.tmx`, `.mtx`, `.map`, `.wrd`, `.itm`, `.eve`, `.enm`, and `AssetFileDic` files. It found no full raw alternate-description paragraph. Parsing translation `.bytes` files and comparing exact framed keys found the five English rows listed above in `English.bytes`; the same Japanese keys occur in `SimplifiedChinese.bytes` and `TraditionalChinese.bytes`, which do not establish official English translations. No exact keys for the remaining rows were found in `Japanese.bytes` or `Rockford.bytes`. Some raw substring hits in those files occur inside larger keys and were not treated as translations. The official English corpus and all searched candidate assets therefore leave 31 descriptions without any exact English row and five with only partial exact coverage.

The reusable, import-safe search utility is `tools/r67_15g_details_source_search.py`. Run it from the repository root using the recorded recovered-source defaults:

```sh
PYTHONPATH=. /opt/homebrew/bin/python3.14 -m tools.r67_15g_details_source_search
```

Override any recovered input location with `--asset-root PATH`, `--elf PATH`, or `--corpus PATH`; `--help` lists these options without opening the inputs. The reusable functions `scan_raw_assets()` and `find_exact_keys()` operate on supplied bytes/keys, allowing focused tests without extracted game assets. The search tool contains code only and does not bundle or write recovered corpora/assets.

The actionable blocker is an authoritative English source for the unresolved Japanese rows (or explicit user-authored translations, which are not authorized here). Until then, the component deliberately preserves them and reports `release_eligibility: PARTIAL_NOT_FULL_SCOPE`; the parent release must not describe this item-details scope as fully translated.

## Verification

Targeted regression command:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m unittest tests.test_r67_15g_item_details -q
```

The focused suite covers the actual unique getter consumer and constructor geometry, full catalogue cardinality and pointer aliases, corpus identity, exact and ambiguous row matching, preservation of unmapped Japanese, all official words, bounds for every catalogue record, malformed owner mutation guards, sparse fallback pointer behavior, append-after-independent-transform compatibility, and the partial release flag. Latest run: **9 tests passed**. The repository-wide suite is owned by the parent integrator; its supplied baseline was 560 passed, 14 skipped, zero failures before component integration. Static binary/layout evidence is not emulator or gameplay acceptance.

Search utility regression command (synthetic in-memory fixtures; does not need the recovered corpus):

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 python -m unittest tests.test_r67_15g_details_source_search -q
```

The focused search tests cover raw paragraph/line byte detection, exact-key matching without substring promotion, empty-pattern rejection, and a side-effect-free CLI help path.
