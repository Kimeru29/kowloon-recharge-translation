# r67.15h SELECT Details and synthesis recipe text layout

Status: bounded static patch generator with focused native-metric and helper regressions. Runtime gameplay and ISO release acceptance are not claimed.

## Scope and source contract

`tools/r67_15h_item_layout.py` exposes `build(source: bytes) -> (candidate: bytes, report: dict)`. It accepts only the pinned r67.15g partial-diagnostic ELF (`74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee`), appends two helpers, updates the translation PT_LOAD file size, and redirects the Details and three recipe constructor calls. `ALLOWED_SOURCE_RANGES` lists the four hook words; `[0x64,0x68)` is append metadata. The transform checks the complete existing-byte allowlist and leaves each hook delay slot unchanged.

Official text, the sparse Details table, fallback Japanese strings, numeric formatting, accepted right-card titles, and the Compound bubble remain byte-identical. Details still calls the prior sparse translation helper, and recipe calls still return their original constructor handles to the native owner slots.

## SELECT Details

The native paragraph starts at panel `(x+26,y+16)`. The frame is 256 by 112 pixels. Recipe content begins at `y+76`, leaving 60 vertical pixels from the paragraph origin. Font 0 is 16 by 18 pixels; at 0.5 scale ordinary glyph advances and ink are 8 by 9 pixels.

Native ordinary glyph advance applies X scale, but fullwidth spaces and explicit newline pitch do not. At 0.5 scale an ordinary glyph advances 8px, `FF0B` advances 16px, and `FF0A` advances 8px. Therefore the staged grenade rows occupy 240px and 248px before normalization; the first two Aqua Regia rows each occupy 232px. The scoped helper changes only this instance's `FF0B` nodes to `FF0A` after a successful full stream validation. The rows then occupy 216/216px and 208/208px, within the 220px horizontal inset.

For vertical layout, native text line pitch is `font height + private line spacing`. To obtain 9px pitch, the helper writes `9 - 18 = -9` to private `+0x2C` before calling `0x18B120`. It does this only for Details. The pinned staged pointer table contains one six-row record (ID 40); its rows occupy 54px. At origins 16, 25, 34, 43, 52, and 61, the final ink edge is 69, before the recipe boundary at 76. A seventh row would cross it. The native newline path is exercised at both the old 18px pitch and the corrected 9px pitch.

## Recipe names

Native name origin is panel `x+39` (`0x1153D0`); numeric text origin is `x+177` (`x-1+178`, `0x11592C`). The transform reserves an 8px name-to-icon gap and a full 16px native font-cell width for the numeric icon slot. This places the reserved icon boundary at `x+161` and limits recipe-name advance to 114px. The 16px cell is pinned to the native font descriptor and the name/numeric origins are pinned to the constructor instructions. This is a conservative static layout reserve; final visual acceptance remains outstanding.

After fullwidth-space normalization, the helper measures `G` ordinary glyphs and `S` spaces and selects:

```text
available = 114 - 8*S
scaleX = min(0.5, available/(16*G))  when G > 0
scaleX = 0.5                        when G = 0
advance = 16*scaleX*G + 8*S <= 114
```

Details line spacing is untouched by recipe helpers; native recipe line pitch remains 18px. All 446 supported official item names are checked against the 114px budget without shortening. Original constructor arguments, including the alternate result color, pass through unchanged.

## Validation and limits

The helper validates complete bounded node walks before mutation, normalizes only supported instance spaces, and returns without calling the setter for malformed streams or nonpositive recipe budgets. The setter may clobber `v0`; the constructor handle is saved at stack `+0x2C0`, then restored after the setter and after full GPR restoration. GPR save/load instructions use EE `SQ/LQ`; the regression harness sidecar emulates both 64-bit lanes when Unicorn lowers those instructions for control-flow execution. It verifies saved-state restoration after simulated constructor/setter clobbers.

Unicorn does not execute EE `ADDA.S/MADD.S`. The native regression pins their actual words at `0x18E010/0x18E014`, sidecar-emulates their accumulator semantics, and executes the following native cursor `add.s`. It covers scaled ordinary advances, unscaled space advances, old/new newline pitches, the staged overflow rows, and their measured ink edges.

The 15g catalogue checks reconfirm 431 valid records, 391 fully official nonempty records, four empty records, and 36 records retaining source rows. Mixed Japanese/English IDs 500, 501, 504, 515, and 534 are included. The original sparse pointer table is asserted unchanged by the 15h transform. Passing this suite establishes static patch behavior only; cold-boot screenshots, gameplay, and release approval remain outstanding.

Focused command:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m unittest tests.test_r67_15h_item_layout -q
```
