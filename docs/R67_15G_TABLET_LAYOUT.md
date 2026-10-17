# r67.15g — western Stone tablet punctuation and centering

Static component note only. This change has no emulator or gameplay approval.

## Scope and native owners

The supplied screenshot shows the western Door-of-Anubis inscription with a
colon-like ornament before the first row, an unevenly indented row block, and
a matching ornament after the last row. The row strings are owned by the
western tablet record at file offset `0x590FB0`; its inscription pointer words
are `0x590FB8`, `0x590FBC`, and `0x590FC0`. The two other Anubis clue rows at
`0x590F38`, `0x590F3C`, and `0x590F40`, the accepted Chamber record, the
Storeroom tablet, and the other 56 records are outside this change.

The old strings contain byte sequence `EE FC`, which Python's CP932 decoder
identifies as U+FF02 FULLWIDTH QUOTATION MARK. The existing tablet patcher
deliberately preserved it as a quote marker. In the user-provided native
render, that glyph appears as the colon-like ornament; the source byte is not
a literal colon. This component removes only the western clue's opening and
closing `EE FC` glyphs. It keeps the accepted words, comma, and final period.

The wording remains the historically accepted semantic compaction. Its source
is the owned PS4 `English.bytes` corpus, SHA-256
`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`:

| Corpus record | Official English source |
| --- | --- |
| `0xCC448` | “The one with a lowered head” |
| `0xCC48A` | “that walks to the west” |
| `0xCC4D2` | “will receive the mercy of god.” |

The native row width is the established 21 full-width CP932 cell bound from
the 58-record tablet class gate. Each accepted English row is CP932 full-width
text; leading full-width spaces are calculated so the left and right blank
cells within that 21-cell bound are equal. No font metrics, renderer, title,
descriptor, script flag, record cardinality, or other tablet is changed.

## Patch contract and locks

`tools/r67_15g_tablet_layout.py` exposes
`apply(source: bytes, official_corpus: Path = CORPUS) -> (bytes, report)` and
`PERMITTED_EXISTING_RANGES`. It accepts a sequentially extended ELF, validates
only its format and owned 15f row pointer/string preimages, appends the three
new strings, updates those three pointer words and PT_LOAD file size, and
reports the exact old-file changes and appended extent. It does not pin an
entire ELF hash.

The immutable q/t locks are run after reconstructing the previous owner words
in memory. The reconstruction restores the two 14t Lion callsite words that
15f already changed and the three former western-tablet pointers. The prior
strings remain in the candidate ELF and are reached by those original
pointers. No lock manifest or historical patcher is edited. This is a scoped
exception for the requested western-tablet presentation only.

Tests: `tests/test_r67_15g_tablet_layout.py`. They cover the old artifact's
visible quote/centering defect, bounded centering and punctuation, fail-closed
owned preimages, precise writable ranges, sequential ELF composition,
unrelated tablet preservation, official corpus provenance, and in-memory
q/t lock preservation.

## Evidence limits

Targeted tests establish static encoding, pointer ownership, append bounds,
and preservation. They do not establish the exact font rasterization beyond
the supplied screenshot, screenshot parity after this patch, gameplay
readability, or runtime alignment. No emulator was launched and no gameplay
approval is inferred. A cold-boot screenshot remains required for visual
acceptance.
