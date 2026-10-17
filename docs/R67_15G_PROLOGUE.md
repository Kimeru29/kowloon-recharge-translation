# r67.15g — remaining native prologue labels

Status: diagnostic static ELF component. No emulator or final ISO was run or
built, and no new gameplay approval is implied.

## Scope and result

This component appends the two exact PS4 English labels still found in the
15f executable on the requested route through the military ambush:

| Label | Japanese source | Source file offset | Literal pointer owner | Official English.bytes record | Text | Cells |
|---|---|---:|---:|---:|---|---:|
| Altar room name | `アヌビスの祭壇（アヌビスのさいだん）` | `0x5CCDC0` | `0x5CD794` | `0xC3CB8` | `Altar of Anubis` | 15 |
| Anubis enemy/boss name | `アヌビス` | `0x594B08` | `0x594E78` | `0x660B3` | `Anubis` | 6 |

Both source strings and their one-pointer alias sets are independently
preimage-pinned against the 15f owners. The English bytes are read from the
local corpus at build time; the corpus is not copied into the module. Only the
two pointer words and the translation PT_LOAD `p_filesz` word change in the
existing ELF. Text is appended after the input ELF, including any earlier
component payload.

## Route inventory and ownership boundaries

The bounded route evidence available for this component is:

| Route surface | Existing owner/evidence | This component |
|---|---|---|
| Opening, exploration, and Chamber/Door of Anubis room names | Existing first-save owner manifest covers 29 source records and 148 pointer aliases, including `Heracleion Shrine`, `Chamber of Lions`, `Door of Anubis`, and 13 `Soul Well` aliases. | Preserved. The remaining Altar room label is added above. |
| Lion and Anubis puzzle inscriptions; treasure vase, Snake Staff, doors, and fixed-base/interaction descriptions | Existing first-save pointer-owner manifest; storeroom label/tablet has its separate r67.14z component. | Preserved; no shared owner or tablet record is modified. |
| Anubis statue inspection/actions and save UI | Existing r67.14y bounded interaction/save owners. | Preserved. The new `Anubis` owner is the enemy-name string at `0x594B08`, not the statue inspection record. |
| ADV/DG event text through the military ambush | Parent's read-only overlay check found `ADV/DG/DG00_00.MTX`, `DG00_01.MTX`, and `MS/MS00_02.MTX` identical to the English overlay. `MS00_02.MTX` contains the ambush followed by the hospital scene. | No MTX edits. The hospital portion is already English and is outside this component's new scope. |
| Optional Anubis H.A.N.T. Enemy entry | The complete record has 17 nonblank text fields in the terminated table at `0x5C2410`–`0x5C2460`, plus three blank slots. All 17 have exact official corpus matches. | Translated by repointing the same 17 nonblank pointer words. The eight description/remarks/treasure source rows are joined and whole-word wrapped into those same slots at indices 10–17; dynamic indices and sentinels remain fixed. |

This is a bounded static inventory from the identified executable owners and
the cited existing route modules. It is not a claim that every optional or
conditional screen reachable before the ambush has been observed. Other
reachability and runtime-only text remain unknown. The complete 17-row Anubis
H.A.N.T. text/heading inventory, record-field offsets, source hashes, and exact
PS4 matches and rendered packed rows are emitted in
`report["optional_hant_anubis_page"]`; exact frame geometry and optional route
reachability remain unverified.

### Optional Anubis Enemy record trace

| Field | Japanese source | Record field | Official corpus | Exact English |
|---|---|---:|---:|---|
| Name heading | `【化人名】` | `0x5C2410` | `0xA9E2E` | `[Kehito Profiles]` |
| Name | `　アヌビス` | `0x5C2414` | `0xACC8B` | `　Anubis` |
| Type heading | `【分類】` | `0x5C2418` | `0xA9E89` | `[Type]` |
| Type | `　死人（しびと）` | `0x5C241C` | `0xACCAB` | `　Undead` |
| HP heading | `【ＨＰ／弱点ＨＰ】` | `0x5C2420` | `0xA9ECD` | `[HP/Weakness HP]` |
| Weak spot heading | `【急所】` | `0x5C2428` | `0xA9F00` | `[Weak Spot]` |
| Weak spot | `　眉間` | `0x5C242C` | `0xAA55E` | `　Between brows` |
| Attack heading | `【攻撃方法】` | `0x5C2430` | `0xA9F37` | `[Method of Attack]` |
| Attack | `　【射撃】口から腫瘍を吐く。` | `0x5C2434` | `0xACCD4` | `　[Shoot] Spits neoplasms.` |
| Description heading | `【解説】` | `0x5C2438` | `0xA9FBC` | `[Description]` |
| Description | `　死を告げる冥府の王。` | `0x5C243C` | `0xACD21` | `　King of the underworld who announces` |
| Description | `　犬またはジャッカルの姿で表され、墓所に` | `0x5C2440` | `0xACD71` | `　death. Appears as a dog or jackal.` |
| Description | `　侵入した盗掘者たちは、アヌビスが描かれ` | `0x5C2444` | `0xACDDA` | `　Tomb robbers can see murals or carvings` |
| Description | `　た壁画や彫刻を見る事ができる。` | `0x5C2448` | `0xACE48` | `　of Anubis.` |
| Remarks heading | `【特記事項】` | `0x5C244C` | `0xAA180` | `[Remarks]` |
| Remarks | `　【火炎】【破邪】に弱い。` | `0x5C2450` | `0xACE8D` | `　Weak against Fire, Cleanse.` |
| Treasure heading | `【宝物】` | `0x5C2454` | `0xAA204` | `[Treasure]` |

The three remaining fields (`0x5C2424`, `0x5C2458`, `0x5C245C`) are the
native blank sentinel; `0x5C2460` is the EOF sentinel. The hierarchy is
mode 2 → category 1 → record 0: root VA `0x6CBAC0` selects the mode table at
file `0x5C2A30`; its category-1 table at `0x5C29B0` points to the record at
`0x5C2410`. Native getter `0x2A9FE0`, called at `0x291EC0`, receives
`(s4 mode, s3 category, s2 record index)`. Parallel metadata getter
`0x2AA020` reads the matching page metadata field at `+0x2C`.

This proves data ownership and selection indexing. All 17 nonblank fields
match exact official English records. The component repoints only those 17
nonblank field words; it preserves the three blank sentinels, EOF sentinel,
record/table hierarchy, and all row indices.

### Native selected-page capacity and index constraints

The mode-2 selected-page renderer is not the mode-4 Help renderer covered by
`tools/hant_layout.py`. Its relevant native path is:

| Evidence | Native location | Consequence |
|---|---:|---|
| Selected Anubis field table | EE `0x291E84`–`0x291EC8` calls `0x2A9FE0` at `0x291EC0`; returned pointer is stored at object `+0x1808` | Confirms this page consumes the record table traced above. |
| Row selection and dynamic cases | EE `0x290304`–`0x290330`; mode 2 dispatch at `0x290318`; source-row comparisons at `0x290358`, `0x290440`, and `0x290520` | Source indices 5, 7, and 18 are special: HP emits up to three dynamic rows, weak-spot resolves a live value, and treasure emits up to five dynamic rows. |
| Native row storage | Page object allocation at EE `0x291DDC` requests `0x1A94` bytes. Row addressing multiplies the output-row count by `0x48`, then uses fields `+0x120`, `+0x124`, and text at `+0x128` (for example EE `0x290398`–`0x290410`) | Row records have a 72-byte stride, with a 64-byte text region. The mode-2 ordinary copy explicitly passes `a2=0x40` to `0x39FCC0` at EE `0x290694`–`0x290698`; the special-row paths use the same bound. |
| Display / scroll | EE `0x290880`–`0x290890` clamps draw objects to 16. The constructor extent is passed as 512 at `0x2908D0`; rows use 20px font size and native 21px row placement. Scroll height uses the row count at `0x2909F0` onward. | The 512 value is a constructor clipping extent, not proof of usable text width from row X=85 to the frame/scrollbar edge. |

The known conservative style-1 span is 336 logical pixels (28 cells at the
12px glyph advance), as documented by the separate tutorial runtime work in
`tools/hant_layout.py`. This conservative bound is applied; the exact usable
frame edge for this Enemy page is not runtime-measured. The longest original
official row is 40 cells / 480 logical pixels and needs 80 encoded bytes plus
a NUL (81 bytes), exceeding the native 64-byte row copy.

The component concatenates exact official rows at record indices 10–17
(Description heading, four description body rows, Remarks heading, remark,
Treasure heading), removes source-row indentation, joins at word boundaries,
then wraps at 28 cells. The resulting eight rows are:

1. `[Description] King of the`
2. `underworld who announces`
3. `death. Appears as a dog or`
4. `jackal. Tomb robbers can see`
5. `murals or carvings of`
6. `Anubis. [Remarks] Weak`
7. `against Fire, Cleanse.`
8. `[Treasure]`

All words and punctuation remain in official order. `[Description]` and
`[Remarks]` remain as inline section markers where packing joins source rows.
The output reuses the exact eight pointer slots at indices 10–17; it adds or
removes no table entries. This preserves fixed source indices 5, 7, and 18 for
dynamic HP, weak-spot and treasure behavior and leaves every blank/EOF sentinel
untouched. Each rendered row is bounded to 28 glyph cells and at most 57 bytes
including NUL, within the existing 64-byte copy. The report retains both each
source row's exact official match and its rendered packed line. Runtime route
reachability and the exact frame edge remain unverified; no gameplay or
screenshot approval is claimed.

## Native ownership and fit evidence

The Altar label is in the same room-name pointer family as `Chamber of Lions`
(17 cells) and `Door of Anubis` (14 cells); its exact official wording uses 15
full-width PS2 glyph cells. `Anubis` uses six cells in the enemy-name field.
The component does not change render code, coordinates, identifiers, flags,
events, save state, or original string bytes. This establishes pointer-class
and text-cell bounds only; there is no cold-boot screenshot proving pixel fit.

The optional H.A.N.T. Enemy page is not treated as a H.A.N.T. Help page or
absorbed into another worker's four-page component. Its exact official rows
are packed data-only into the existing indices 10–17 under the conservative
336px bound. Exact frame geometry, route reachability, and cold-boot visual
fit remain unverified.

## Reproduction interface and verification

`tools/r67_15g_prologue.py` exports:

```python
apply(source: bytes, official_corpus: Path = CORPUS) -> tuple[bytes, dict]
```

It accepts a sequentially extended 15f ELF, pins its owned source strings and
literal aliases, verifies the official corpus SHA-256, appends encoded text,
and reports exact changed offsets and append extent. Its
`PERMITTED_EXISTING_RANGES` are half-open original-file ranges for the two
prologue pointers and 17 Anubis record fields; the ELF segment-size word at
`0x64..0x68` is reported separately.
The full 15f SHA-256 is recorded for traceability, while the apply path pins
only this component's preimages so other sequential appends remain valid.

Inputs:

- Approved 15f working ELF: `local/r67-15f-item-panel-layout.elf`, SHA-256
  `418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1`.
- Pristine comparison source: `../startup-flow-v10/fixtures/elf/SLPM_665.11`.
- Official PS4 corpus:
  `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`,
  SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`.
- Original PS2 ISO: `/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`.
- Recovered PS4 ADV data root:
  `/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/Media/StreamingAssets/data/ADV`.
  These original/extracted sources are read-only inputs and are not modified.

Focused tests:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m unittest tests.test_r67_15g_prologue -q
```

The seven tests cover exact official wording, permitted original-byte changes,
the 17-field optional H.A.N.T. owner inventory and getter trace, exact
word-preserving eight-slot packing with dynamic/sentinel preservation,
fail-closed pointer preimages, and sequential append preservation. Parent owns
the integrated full-suite run.
Static checks do not establish runtime reachability, text clipping, or gameplay
approval.
