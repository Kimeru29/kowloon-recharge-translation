# r67.15g — H.A.N.T. Help layout

## Diagnosis

The 15f pages preserve the English text but retain Japanese row breaks and icon
coordinates. `tools/first_save_help.py` reserves five text cells on one rounded
row for every icon. That does not cover the full frame or its pivot, and it
does not bind a moved icon to the instruction that explains it. The three
provided captures show row collisions on Item Synthesis and Save & Load and
overlapping Jumping maps. The Wire Gun capture is absent; its page and icon
owners were inspected directly in the ELF, not inferred from the duplicate
Save & Load image.

H.A.N.T. mode 4 uses the existing page-local 12-pixel glyph advance and
16-pixel row pitch. Its native list renderer keeps a 16-row viewport and
updates the page scroll offset through the row count; therefore longer page
tables can be reached without changing global renderer code. The old pages
were 19, 17, 27, and 38 content rows. The new tables use 34, 18, 55, and 70
rows respectively, with maximum scroll offsets 18, 2, 39, and 54. At maximum
scroll the final page row is still inside the visible 16-row window.

## Native rectangle evidence

The glyph grid is the accepted H.A.N.T. style-1 profile: 12×12 glyph cells,
12-pixel horizontal advance, and 16-pixel row pitch. Icon records retain their
original first/second short identities. The second short resolves to the
native sprite-group table at VA `0x480A70`; each group entry points to its first
`0x30`-byte frame record. Width, height, and pivot X/Y are the four floats at
frame offset `+4`. The module pins the hash of each group entry plus frame
record before using it:

| Group | Frame W×H | Pivot X/Y | Help use |
| ---: | ---: | ---: | --- |
| 1 | 16×16 | −11/−15 | D-pad mark |
| 3, 5, 10, 11 | 24×24 | −6/−12 | face/SELECT, caution, and wire-gun marks |
| 16 | 64×64 | 32/32 | wire-gun tutorial map |
| 17 | 80×64 | 40/25 | wire-gun tutorial map |
| 18 | 48×32 | 24/48 | jumping radar map |
| 19 | 120×96 | 60/−25 | jumping destination map |
| 28 | 144×104 | 2/0 | jumping landing map |

For overlap checks, the sprite rectangle uses the exact frame W/H and a
conservative pivot envelope extending by `abs(pivot)` on each side. This
contains either signed anchor interpretation while preserving the native
dimensions; the text never shares those reserved rows. Icons are relocated
with their original identities and are stacked immediately before the
instruction paragraph selected by a page-specific text anchor. Test coverage
checks both identity and that the corresponding instruction still contains its
anchor phrase. Scrolling translates all rectangles uniformly, and the geometry
check examines every legal scroll offset.

The screenshots are spacing evidence only; controller meanings come from the
existing PS2 metadata and official English text. No controls or sprite IDs are
substituted.

## Owners and interface

`tools/r67_15g_help_layout.py` exposes:

```python
apply(source: bytes, official_english_bytes: bytes) -> tuple[bytes, dict]
```

It accepts a sequentially extended 15f ELF. It independently pins its four
page descriptor pointers, each source table and icon-metadata table, the
per-row official-English text stream, translation `PT_LOAD` geometry, the
official corpus SHA-256
`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`, and the
native sprite frame records it consumes. It does not pin the whole ELF, so a
disjoint component can append first. A drift in one of these owned preimages
fails closed.

Only the following existing bytes may change:

| Owner | File range |
| --- | --- |
| Item Synthesis descriptors | `0x5CBADC–0x5CBADF`, `0x5CBA8C–0x5CBA8F` |
| Save & Load descriptors | `0x5CBAE8–0x5CBAEB`, `0x5CBA98–0x5CBA9B` |
| Wire Gun descriptors | `0x5C8A90–0x5C8A93`, `0x5C8A40–0x5C8A43` |
| Jumping descriptors | `0x5C8A8C–0x5C8A8F`, `0x5C8A3C–0x5C8A3F` |
| Translation `PT_LOAD.p_filesz` | `0x64–0x67` |

New row strings, page tables, and icon metadata are appended to the existing
translation segment. All other Help pages, renderer code, sprite resources,
game logic, and accepted layouts remain byte-identical. The audit report lists
those ranges, append extent, per-page rows/icons, frame geometry, corpus hash,
and any runtime assumptions.

## Verification

`tests/test_r67_15g_help_layout.py` covers the four legacy collision witnesses,
full glyph/frame rectangles at every scroll offset, complete word/punctuation
preservation, 28-cell row bounds, icon identity/instruction pairing, scroll
end reachability, unaffected owners, the exact preimage allowlist, malformed
page and sprite-frame rejection, and sequential-append compatibility.

Targeted run (Python 3.14 with Pillow, NumPy, Unicorn, Capstone, OpenCV, and
UnityPy):

```text
Ran 11 tests in 0.351s
OK
```

Static geometry report: old collisions on all four target pages; zero
intersections after reflow. This worker did not run the integrated full suite,
launch an emulator, build an ISO, or claim runtime visual acceptance. The
parent integration run and user-provided runtime screenshots remain the final
acceptance gates.
