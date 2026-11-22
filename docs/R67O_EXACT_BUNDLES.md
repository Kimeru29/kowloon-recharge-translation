# Exact MTX bundle delta on r67.15n

The delta transfers 51 additional official PS4 DC entry IDs onto the fingerprinted r67.15n diagnostic. It changes two MTX files. The three large MS files in this sweep account for 5,275 previously transferred IDs, 51 new IDs and 53 unresolved IDs.

| MTX | Prior IDs | New IDs | Unresolved IDs |
| --- | ---: | ---: | ---: |
| `MS/MS01_00.MTX` | 2,539 | 1 | 1 |
| `MS/MS06_03.MTX` | 1,729 | 0 | 5 |
| `MS/MS13_02.MTX` | 1,007 | 50 | 47 |

The remaining groups have 47 cases with no exact bundle, three with repeated exact context, two that conflict with a prior anchor and one whose unique windows imply different targets. The sweep covers these three MTX files. Alternate assets and smaller source-only scripts require their own correspondence evidence.

## Evidence required for a transfer

- The producer enumerates every window of 2–12 adjacent DC groups containing a previously unresolved group. The Japanese text and intervening native bytes must occur exactly once within the corresponding pointer region of each pristine source. All participating group boundaries must be CP932 boundaries. The files must agree on the pointer-slot tuple, left native boundary under the r67.15n rule and right native delimiter.
- Every accepted window preserves the ordering of the independently proven r67.15n anchors in the same region. An enclosed anchor must map to the exact same target offsets. The report includes all surviving windows, their hashes, and the nearest and enclosed prior anchors. Every surviving window must imply the same target span. Overlapping or inverted new claims invalidate both groups.
- The whole baseline disc, prior report, pristine sources, raw DC and installed MTX have pinned fingerprints. An audit walks the baseline's installed regions and checks the proven replacement hashes, untouched runs and terminal padding before mapping each new original PS2 range into the installed disc.
- The delta compiler replaces only those installed ranges, preserving the native bytes between groups. A separate audit walks the result and verifies each replacement, skipped run, terminal suffix, pointer slot and alias. Alignment can add up to three NUL bytes after a region's terminal `_`. Any untouched unaligned final region is carried through byte-for-byte.

Each accepted span has half-open PS4, original PS2, installed r67.15n and output ranges. Its nested entries carry the official DC IDs and exact output byte ranges and hashes for each line. All offsets are MTX file offsets.

## MS01_00 name omission

The one approved absence of a source name control is DC key `33444` in `MS/MS01_00.MTX`. The matched Japanese span is PS4 `33444..33481` and PS2 `33564..33601` in pointer slot `119`. The full speaker-and-text scope is PS4 `33433..33481` and PS2 `33553..33601`, with the independently proven speaker anchor `33433`. The Japanese includes `px`, and the official DC value omits the marker.

The owned PS4 build retrieves the DC dictionary value and stores it at RVA `0x142b5e1`. RVA `0x142b92b..0x142b941` passes that exact string to `Y_AdvOriginalNameChangeProc`. The search at `0x142d772..0x142d78e` uses the localized character marker. Its negative-result branch runs from `0x142d7a6` to `0x142dd5a`, bypassing the current-speaker resolver and `St_GetCallPcName` at `0x142da75` and `0x142daa6`. The importer preserves this official omission in the exact pinned page. Other transfers conserve native name tokens within proven presentation runs and emit them in official order.

| PS4 evidence | SHA-256 |
| --- | --- |
| `Il2CppUserAssemblies.prx` | `fa6f474834155a111996395e48695f4d706bab94c9b682671c160a23ebadf4d3` |
| `global-metadata.dat` | `c16ac1a8084e74c42843dc6ce15e14f277be02bbb5499a95084e2be2cac00ea0` |
| Dictionary and call bytes at RVA `0x142b52c..0x142b961` | `2b521feb6989b41a0acc9fc39413e6d407debc1f1e8e62c4cc3a2ac2f8df5dc5` |
| Name-processing bytes at RVA `0x142cc30..0x142e620` | `6d479f22d459e6d7fd8398317048fc3553464e960b9b15a2ff1f8f700ee950af` |

The PRX file offsets for these two code ranges are the listed RVAs plus `0x1f610`.

## Reproduce the static overlay

Run from the repository root. Select a fresh output directory for each run.

```sh
PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m tools.r67o_bundles \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --baseline-iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --baseline-report local/r67n-partial/report.json \
  --output-dir local/r67o-bundles-reproduction

PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python \
  -m unittest discover -s tests -p 'test_r67o_bundles.py'
```

| Artifact under `local/r67o-bundles` | SHA-256 |
| --- | --- |
| `report.json` | `879ab842981954c52f1b0df60c466f0dcba5161b7379818b694609ac22395938` |
| `overlay/MS/MS01_00.MTX` | `7eeda6825e1bea31c31d2b77a4c23cf02a83075fda1d52e1402e9d06c04a5df0` |
| `overlay/MS/MS13_02.MTX` | `88ca109d59aa7693f26e47e50d8ffd005be01c673e3ad7146324ad1f641bd1a3` |

A fresh run reproduced the report and both MTX payloads byte-for-byte. The independent output walk checked all 51 source-to-target spans, 1,355 exact-window observations and four added terminal NULs. The new single-line entries use at most 30 static cells under the existing layout triage.

These artifacts establish static source and payload correspondence. Rendering and gameplay acceptance require cold-boot evidence from the integrated diagnostic.
