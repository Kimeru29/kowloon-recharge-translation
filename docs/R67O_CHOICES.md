# r67.15o KSF choice renderer

The renderer adds 1,079 complete official-English choices to 441 type-2 records across 163 KSF files. Four U+3000-only labels keep their stock presentation. The six held remaster keys have no source-proven PS2 choice owner. The installed KSF files remain byte-identical to r67.15n, including the two approved DG translations and all branch data.

The side table uses the exact loader request and native ordinal. Activation checks the loaded record displacement, type and branch header, all four packed flags, and the complete 30-byte preimages of all active siblings. The source verifier pins both executables and the installed, pristine, remaster and dictionary hashes. The 37 supplemental labels also require the independently verified MTX region and native branch proof. [Choice correspondence](R67O_CHOICE_CORRESPONDENCE.md)

## Rendering and fallback

- The style-0 16×18 font preserves capitalization, punctuation, double quotes, repeated ASCII spaces and source ordering. The first-line origin is X=24 and Y=22+39×slot. The setter may insert one display-only line break without removing the adjacent separator. Both lines fit within 448 pixels.
- The four name templates use the complete native family and given names. Both 32-byte fields are checked for termination, assigned CP932 pairs and converter/font admission before substitution. An invalid name makes the entire guarded record use pristine Japanese payloads, including any original bare name tokens. A valid name outside style-0 coverage uses the pristine record and bounded substitution if style 2 accepts both names. This handling is confined to guarded records. Unknown records retain the original executable's behavior.
- The choice animator retains the original header and states. Its two 56-handle blocks and physical index map occupy a private 0x218-byte allocation. The linked-list proof checks both directions, source-derived tokens, the native terminator and the font descriptor before children are created. Its first pass skips the display break and counts original spaces.
- The original horizontal selector exceeded the viewport in native draw capture at 17 cells. The native 0x8d/0x90 caps submitted Y=−13 and a strip reached X=552. On the choice-owned instance alone, the wrapper calls the stock update then adjusts the five stock sprites' position and scale before the independent native sprite draw. The resulting margin indicator occupies X=4–20 and Y=first-line top through top+17. The stock task creation, timing, interpolation, art and teardown remain the same.

## Executable ownership

| Native JAL | Choice owner |
| --- | --- |
| 0x22c388 | Initial guarded slot copy |
| 0x22c394 | Initial choice name preprocessing |
| 0x251594 | Font constructor |
| 0x251668 | Choice name preprocessing before display |
| 0x2516a8 | Choice setter |
| 0x2516f8 | Choice animator constructor |
| 0x251a24 | Choice selector constructor |
| 0x251be0 | Choice selector movement |

The existing PT_LOAD file-size word at file offset 0x64 grows within the existing reserve. The output report lists the exact old/new JAL words, byte offsets, appended extent and hashes. No KSF is rewritten by this builder.

## Offline verification

Run from the repository root with the pinned Python and Apple Clang toolchain.

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
  local/r67m-integration/venv314/bin/python -m unittest \
  tests.test_r67o_choices tests.test_r67o_choices_native tests.test_r67o_choices_pipeline -v
```

The native harness executes the pinned executable's converter, node builders, quad builders, font draw callback, sprite draw callback, sprite transforms, animator states, child factories, destructors and controller slices. The harness provides allocator/task scheduling boundaries, initialized font cache slots, loaded texture handles and draw submission capture. It models the few EE instructions Unicorn lacks in its private image. The geometry checks cover the original sprite frames, settled and interpolated cursor positions, alpha rebuild, UVs and per-vertex ordering. PCSX2 gameplay and visual approval require a separate cold boot.

Create the diagnostic choice-only ELF from a fresh output directory.

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. \
  local/r67m-integration/venv314/bin/python -m tools.r67o_choices \
  --elf local/r67n-release/67.15n-official-script-diagnostic.elf \
  --pristine-elf local/r67n-sources/SLPM_665.11 \
  --iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --research local/r67o-research/ksf-design-evidence.json \
  --inventory local/r67n-inventory-final/files.json \
  --supplement local/r67o-choice-correspondence/report.json \
  --output local/r67o-choices
```
