# r67.15l Emotion Input wheel art

## Scope and evidence

r67.15l ports the official PS4 English Emotion Input wheel lettering into the
approved r67.15k PS2 image. The art transform and manifest are frozen. The
focused art suite passes **9/9** tests. Fresh art-plus-composition checks pass
**21 tests in 15.871 seconds**. The final CLI build completed with exit code 0.
The final integrated suite ran **804 tests in 234.789 seconds** (exit 0):
791 executed tests passed, 13 expected skips, and zero failures/errors. The
skip categories are five CVM/KSF/MTX module skips, one old graphics-port skip,
six historical finished-ISO skips (q, t, u, z, a, and r67.12 history), and
one DG13 structural-corpus skip. All new/current installed-candidate and
history-environment checks ran without skips.
Static checks and atlas previews do not establish in-game appearance or
gameplay approval.

The historical precoverage artifact set remains at
`local/r67-15l-precoverage-20261021/`. The earlier ISO digest
`38319eb2ab1dca658377eb7cf226f16760763832fd58c49b630375dc5c8ebc04` is
historical evidence only, not the final r67.15l acceptance image. Preserve it
unchanged. The approved input remains the r67.15k ISO at SHA-256
`ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`; the
installed ELF is byte-identical to the approved k ELF.

## Official art sources

The bundle and every consumed texture are hash-pinned in
`tools/r67_15l_emotion_wheel.py` and recorded in
`translations/r67_15l_emotion_wheel.json`.

| Source | SHA-256 |
|---|---|
| Official `b_gp001_en` bundle | `78ac1bcdbe7e6838be3c0d3ae49d76c290bfd3205ad55e97bc647697b3d6260b` |
| `GP001_02` | `490072a4f90b21ae3137f9eaa8a003eb3d7a7c8ee73377402d118d6a44125fb6` |
| `GP001_03` | `3b13dadf29209f3d64ffc1fd1da5c97e154b1cd90a08d0825ed613d3182fb190` |
| `GP001_08` | `42494369fbe7fc0686ebef4dd4782392a4f3c3881dd625c99836f1527c26eb98` |
| `GP001_10` | `e00101e7b784db568f47f65f2123d4c2cd97e60be4c52abcc73d35d033ec3615` |

The Japanese comparison textures used by the paired-label matte are also
hash-pinned in the transform: `GP001_02`
`0ee399cf25917db5669dabe7af1bbd90484dd3114eb797afd5b800005d78c263`,
`GP001_03` `99f753f350a9a3c3e04b9bd273607aec863e2204061b9d9dca677baadbd22683`,
`GP001_08` `ee33eb96e057cdaa3e085b07ab1b29c402cb67c7b8fed29c800f56d4c7f5451d`,
and `GP001_10`
`b520345691a18f7a92a808bc9df73eace249fcdad80d085ced16d72ae592dfce`.

The source container is `BLBRD/B_GP001.BIN`, 603,520 bytes at ISO offset
`0x2ed7a800`, SHA-256
`895f3d1864a653b3eb76a06eae8b8ea65b9f31cfe156fe922eb72d9eeb967942`.
The four patched textures are `GP001_02`, `GP001_03`, `GP001_08`, and
`GP001_10`. Their approved UV ownership is listed in the translation manifest.

## Art coverage and removal rules

The official wheel labels are `JOY`, `LOVE`, `AMITY`, `HOT`, `COLD`, `ANGER`,
`SOMBER`, and `GRIEF`. The transform covers **56 label drawings** across four
art variants: 20 paired plaques (40 drawings), 8 gold single labels, and 8
glowing single labels. The no-command state is a native selection state and
has no label texture; its behavior is unchanged.

Paired plaque ownership is restricted to the native UV rectangles in
`GP001_02` and `GP001_10`. The matte combines the thresholded official English
versus Japanese texture difference with Japanese-only alpha support, applies
a 5-pixel maximum-filter dilation, downsamples to the PS2 atlas, and includes
the downsampled Japanese-only support. Only nonzero matte texels are eligible.
This includes old-only strokes while leaving texels outside the matte and
owned rectangles unchanged.

Each of the 8 gold tiles in `GP001_03` and 8 glow tiles in `GP001_08` is first
cleared to an existing transparent palette entry, then composited from the
official English RGBA source. This removes Japanese pixels even where the
English artwork is transparent. Writes remain inside those 16 native single-
label rectangles.

All four textures retain their original palettes. Conversion blends the
official source against the original indexed pixel using matte coverage, then
maps to the nearest entry in the existing palette. The container, TMX
geometry, palette bytes, native code, and all bytes outside the owned texture
payloads remain unchanged. Regression coverage checks Japanese-only support,
single-tile clearing, UV containment, untouched plaque/background texels,
palette preservation, and all 56 drawings.

## Corrected atlas preview QA

Four previews were regenerated from the frozen `apply()` output with payload
SHA-256 `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee`.
They are nearest-neighbor 3x views of the decoded indexed PS2 atlases:

| Preview | Visual inspection |
|---|---|
| [`corrected_preview_02.png`](../local/r67-15l-investigation/corrected_preview_02.png) | Paired English labels sit within the expected plaque bounds; surrounding atlas icons and ring art remain visible. |
| [`corrected_preview_10.png`](../local/r67-15l-investigation/corrected_preview_10.png) | Default and alternate paired plaques show English lettering in the owned UVs; no Japanese glyphs were apparent at this preview scale. |
| [`corrected_preview_03.png`](../local/r67-15l-investigation/corrected_preview_03.png) | Gold single-label lettering is visible in the 8 tiles; the adjacent wheel rim and decorative pieces remain present. |
| [`corrected_preview_08.png`](../local/r67-15l-investigation/corrected_preview_08.png) | All 8 English single labels appear over the green glow artwork; unused atlas area is transparent. |

These are source-atlas previews for pixel-art QA, not PCSX2 screenshots. They
do not show native compositing, animation, scene reachability, or gameplay.

## Release record

| Evidence | State |
|---|---|
| Frozen art transform and manifest | Accepted; no further art edits authorized |
| Focused art tests | **9/9 PASS** |
| Fresh art-plus-composition tests | **21 PASS in 15.871 s** |
| Native coverage proof | **18 tests PASS**; see [native coverage](R67_15L_NATIVE_COVERAGE.md) |
| Final CLI build | **PASS**, exit 0 |
| Final integrated ISO SHA-256 | `c70dd6e70c9be85c05732bfc3f4fa60ff1c9e7c280470d7ebe9c76c7a7290f94` |
| Full-disc audit | 2,095,382,528 bytes; 60,028 changed bytes only in `BLBRD/B_GP001.BIN`; zero unexplained bytes |
| Art payload SHA-256 | `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee` |
| Full regression suite | **804 tests PASS** in 234.789 s (exit 0): 791 passed, 13 expected skips, 0 failures/errors; `local/r67-15l-final-suite.log` |
| Separate final focused run | **40/40 PASS** in 24.794 s (exit 0); includes the installed release-lock test; log `local/r67-15l-final-focused.log` |
| Approved k-source verification | 52 protected files and historical report unchanged; independently verified k ISO SHA-256 `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53` unchanged |
| PCSX2 screenshots and gameplay acceptance | **PENDING** user review |

Do not treat the earlier `38319…` ISO as final, change the frozen art
transform, or claim runtime approval from static evidence. Final approval
requires the exact final ISO hash and user-reviewed screenshots from that same
image.
