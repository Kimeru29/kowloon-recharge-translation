# r67.15h diagnostic integration

The integration accepts only the pinned r67.15g partial diagnostic ELF and ISO.
Before preparing the new components, it independently regenerates r67.15g from
the approved 15f ISO and official corpus and requires byte equality with the
pinned 15g ELF. It composes the supplied components in this order:

1. `item_layout`
2. `hant_pool`

Both components must be passed explicitly as `(name, apply, allowed_source_ranges)`
tuples. Their owner ranges are half-open ELF offsets. Each stage is audited
against those ranges, its append extent and `PT_LOAD.p_filesz`; the complete
ordered preparation runs twice and must be byte/report deterministic. A
component that makes no change, reports inaccurate changed offsets, or changes
an unowned byte is rejected.

`build(components, ...)` is an explicit operation. It refuses existing
outputs and writes only the separately named
`local/r67-candidates/67.15h-details-transition-diagnostic.iso`, with a
recoverable `.incomplete` clone retained if finished-image checks fail. Growth
is checked against available executable space before the clone is made. The
finished image is audited byte-for-byte from the approved 15f ISO, including
the regenerated 15g changes, both endian executable directory sizes and
byte-identical `DATA.CVM`.

The report carries the existing 36 unresolved official Details records, so
this remains a partial diagnostic and not a full translation. It also records
the parent-provided resource lookup comparison: 10,656 embedded ROFS records,
969 relocated or resized records, zero mismatches and zero unmatched records.
That prior observation remains labeled parent evidence. The build additionally
runs `tools/r67_15h_rofs_audit.py` against the **finished diagnostic** and pristine
PS2 image before publication. It requires all 10,656 unique file lookups to
match the installed DATA.CVM directory, with unchanged filename bytes. Missing,
added, duplicated, ambiguous, stale or out-of-container records fail closed.
The fresh result is recorded separately as `finished_resource_lookup`.
The existing 15g route/provenance report is retained after its pinned
input hashes and read-only/static status are checked. No `DATA.CVM` mutation is
planned.

The reported observation that 4–5 HANT pages were opened/scrolled before a
door-loading hang is context only. The cause is unconfirmed; loading
confirmation, runtime verification and gameplay approval remain pending/false.
The integration does not invoke the builder automatically. The subsequent
explicit build succeeded; actual results and hashes are in
[R67_15H_HANDOFF.md](R67_15H_HANDOFF.md).

## Repeatable resource lookup check

This read-only command also reproduced the earlier 15g result: 10,656 matching
records, 969 resized/relocated files, zero mismatches. Mutation tests reject stale
sizes, stale extents, changed filenames, truncated executables, duplicate or
missing inventory entries and ambiguous original lookups. This is metadata
consistency evidence, not proof of an executed area transition.

```sh
python -m tools.r67_15h_rofs_audit \
  '/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  local/r67-candidates/67.15h-details-transition-diagnostic.iso
```

## Build entry point

Run only after the component and full regression suites pass. This refuses to
overwrite any existing 15h output; keep prior artifacts and investigate a failed
build's `.incomplete` file rather than deleting or silently reusing it.

```python
from tools import r67_15h_item_layout as item_layout
from tools import r67_15h_hant_pool as hant_pool
from tools.r67_15h_iso_release import build

report = build((
    ("item_layout", item_layout.build, item_layout.ALLOWED_SOURCE_RANGES),
    ("hant_pool", hant_pool.build, hant_pool.ALLOWED_SOURCE_RANGES),
))
```

The final handoff records the actual build outcome, hashes, suite counts and
draft PR. This integration contract alone is not evidence that a build ran.
