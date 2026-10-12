# r67.14y — event lifecycle, inspections and Soul Well save UI

Status: **separate diagnostic built; gameplay approval and cross-release save runtime verification pending**. This is not a claim that the screenshots are fixed in gameplay.

## Release and provenance

- Worktree: `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.
- Branch: `fix/67.14r-lion-statue-ui`; HEAD, fetched origin/main and freshly queried remote main: `1655eaf9756993457bca04b9bae004b38f771958`.
- Existing uncommitted r..x files preserved. Only new y source/tests/docs were added. No commit, push, PR or merge.
- Stage begins from exact accepted t ELF, not the rejected u/v offsets or x's incomplete reset. Finished disc is cloned from exact x and preserves installed ROFS metadata.
- ISO: `local/r67-candidates/67.14y-event-lifecycle-inspection-save.iso`.
- ISO SHA-256: `079b4d0ed73fb010b0d0020f5a3e84357b44804a9b2a2425fa3328fd497aee8f`.
- Staged ELF: `local/r67-14y-event-lifecycle-inspection-save.elf`, SHA-256 `73c27c2728609c7ee38f9c21cfcbc1a26ca980dc8b45b19383d64677c8eba369`.
- Installed ELF: 8,800,303 bytes at unchanged sector 1,013,782; SHA-256 `e11997c7b344cfb811497aa8c3bbaef86059a4e40911585f26442ff7a92ebf8d`.
- Earlier q/t/x hashes rechecked: q `3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96`; t `03526a1779822ad1ec15136c26ff8c3b50d6997bb395a601db228b3fc2fe321f`; x `5ea1fa67d972b00ab499f0ac27bbc4308f51cd11a929b3fdd6741f9f9ee79a13`. No previous ISO overwritten.

The six recovered conversation screenshots were inspected directly: Anubis, island comment, subsequent wire-gun comment, Heaven Door, save footer, and saving warning. They do not include a separate Snake Staff screenshot or the exact quoted “I wonder if ...” frame. Those remain user-reported coverage targets, not images claimed inspected.

## Ordinary companion/event dialogue

### Confirmed static defect in x

The x reset at EE `0x16606C` belongs only to the slot-change reconstruction block. The branch at `0x166048` skips that block for same-slot messages. Initial state-9 construction at `0x165E60` also bypasses it. A constructor-only reset does not enforce geometry after subsequent task callbacks. These are concrete coverage gaps; without a captured failing x runtime state, they do **not** prove the entire causal chain behind each screenshot.

The text callsites are `0x1661BC` and `0x16628C`. Existing q helpers `0x963D20`/`0x963DFC` pass Y=280/300 to native text constructor `0x189E40`; nested font owner is `*(text+0x3C)`, with origin X/Y at `+0x14/+0x18` and horizontal advance/scale at `+0x48`. These bytes, 20-unit spacing, glyph logic, event table/string pointers and 240-frame timer remain unchanged. No guessed Y offset was introduced.

Native sprite constructor `0x107D60` stores packed XY at sprite `+0x3C/+0x40`, group/id at `+0x82/+0x84`, and unit scales at `+0x60/+0x64`; it does not copy the shared width/pivot into those fields. Group-2 table `0x480A70` has eight-byte entries: IDs `0x68/0x69` point to `0x450AC0/0x450AF0`; `0x6A` points to three frames at `0x450B20`. Width/height/pivots begin four bytes into each record. Both green placement records use Y=346; their 58-unit difference is X, not Y.

### Generic lifecycle correction

`tools/r67_14y_event_lifecycle.py` installs two bounded wrappers:

| EE callsite | Appended helper | Behavior |
|---|---|---|
| `0x165E60` | `0x96412C`, 236 bytes | Restore ordinary-event geometry before original `0x107D60`; preserve packed 64-bit XY and other arguments. |
| `0x166820` | `0x964218`, 312 bytes | Call original `0x167980`, then restore geometry at task-frame end. |

The frame guard requires record 0..600, companion slot 0/1, native state 9..13, and the task's live allocated group-2 green sprite with the matching ID. Negative/AFK records, invalid slots, inactive states, absent/freed/foreign sprites do not enter restoration. No room, string or event-subrow exceptions exist.

Restored native geometry: selected green 288×80, pivot X=67/125, Y=77; all three blue frames 288×56, pivot X=67, Y=74/75/76. The nominal native body bounds contain the existing text positions. This is a static geometry relationship, not measured current gameplay pixels. Tests execute actual hook/helper instructions, while native constructor/callback calls are stubbed; an adversarial callback models later metadata mutation. They are not a full PS2 emulator.

## Inspection and action owners

`tools/r67_14y_inspection_save.py` validates pinned pointer/source/context preimages and appends bounded wide-English strings. It covers all eleven discovered state records:

| Object | ELF file record offsets |
|---|---|
| Anubis | `0x58A120`, `0x590FF0` |
| Snake Staff | `0x58A2C0`, `0x58A4B0`, `0x58B1C0`, `0x58B1E0`, `0x5910D0`, `0x591EC0`, `0x592A30` |
| Heaven Door | `0x58FD60`, `0x592CB0` |

Each has title, four description slots, and reading. Reusable validators enforce printable full-width English, explicit rows, no embedded controls/NUL, body ≤21 cells and title ≤14 cells. The title limit is a conservative bounded policy, **not proven pixel containment**. Native font/pitch and inspection geometry are unchanged. Duplicate English/kana readings are suppressed.

Examples: `Anubis Statue`, `Egyptian death god.`, `Mechanism in base.`, `Can be used.`; `Snake-shaped staff.`, distinct moving/fixed/damaged states and `Repair with Wire.`; `Heaven Door`, `Records the soul.`, `Leads to the surface.` No interaction state/ID is changed.

Action pointer owners at file `0x594F84/0x594F88` now use official **Grasp**, and `0x594FB0` uses **Record**. Native action-table reference at file `0x19B320` remains unchanged. Shared labels also affect their other native consumers; this is a deliberate terminology-level change, not a room-specific action hack.

## Soul Well save UI

- Native dialog choice pointers at file `0x338A80–0x338A8C` become **Yes / No / Save / Load**. Their actual native loads at file `0x2D8–0x304` are pinned and unchanged.
- Save-message table: file `0x407440`. Entry 8 owner `0x407460` gets the five-row warning below, preserving the original Japanese warning's five-row topology. Native table consumers are pinned at file `0x7969C`, `0x79A30`, `0x7AE10`.
- Entries 9 (`0x407464`, `Data saved.`) and 18 (`0x407488`, `Save this data?`) were **already correct bounded English** in t/x. They are verified, not falsely reported newly translated. A Japanese prompt persisting after cold boot requires runtime owner tracing; the screenshot set does not establish that alternate path.

```text
[blank row]
Saving...
Do not remove/insert
memory card (PS2) or
turn off the power.
```

Actual row widths: 0, 9, 20, 20, 19 cells. No native line pitch or save/serialization routine changed. Five-row topology and cell bounds do not establish rendered pixel containment.

The footer was baked graphics, not this text table. Native constructor EE `0x178008`, file placement table `0x407520`, group-18 resources 6/7/8 use texture `GRP018/GP018_03.TMX`. `tools/r67_14y_save_atlas.py` repaints only `(0,40)-(48,64)`, `(48,40)-(96,64)`, `(96,40)-(128,64)` with **LOAD / SAVE / BACK**. Palette, bar, Circle/Cross icons, UV/size metadata and all other container bytes remain unchanged. Local bitmap captions follow an existing repo technique; they are not claimed PS4 artwork. The extracted PS4 atlas did not supply usable baked English captions. The resulting atlas was inspected as an image at `local/r67-14y-analysis/save-captions-y.png`; this is not an in-game screenshot.

## Translation provenance

Owned official PS4 corpus: `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`, SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`.

The build report enumerates every source key, official offset/text, output and provenance. Grasp/Record/Yes/No/Save/Load are exact official terminology. Long descriptions, Anubis title and the warning use explicitly labeled semantic compaction; redundant readings are removed. Heaven Door's surface-description variant has no exact audited PS4 key and is authored from the original Japanese. Back is a semantic footer caption corresponding to Return. Corpus provenance tests pass; compact wording is not presented as verbatim official text.

## Verification

- Focused y tests: **32/32**, including source/pointer/context/header mutations, overlong/Japanese/control/extra-row rejection, helper removal/constant mutations, all 601 ordinary records in both slots, all 600 AFK record IDs excluded, and invalid task/sprite guards.
- Complete suite, Python 3.14 + Pillow: **465 tests run, 456 passed, 9 expected fixture skips, zero failures/errors**, 65.894 seconds. `local/r67-14y-all-tests.log`.
- Earlier preintegration Python 3.13 run had nine unsupported-Zstd-fixture errors. Preserved in `local/r67-14y-preintegration-tests.log`; resolved by the fresh 3.14 run, not by changing tests/fixtures.
- Strict immutable q/t locks pass on both staged and installed ELF, **without exceptions or manifest edits**. Lion Statue scale 0.72 and both callsites preserved; 58 tablets / 160 rows / zero overwide rows preserved; opening/Eerie text, renderer and AFK locks pass.
- Raw startup gate **154/155**: only `memory_card_8` expects the deliberately replaced overflowing legacy wording. `local/r67-14y-startup-raw.json` retains that failure.
- Explicit y startup gate **155/155**: only that one wording check is replaced by exact deterministic y payload + row/cell bounds. All other checks are unchanged. Mutation tests reject unexpected failures, changed replacement bytes, and overflow. `local/r67-14y-startup.json`.
- Protected history **4/4** on installed ELF: `local/r67-14y-history.json`.
- Native save code file `[0x77600,0x7DA00)` identical, SHA-256 `06e42787fe30586b8cdaf5092a4869bbb54986c7ea5ec717d0570c1b85a83182`. Entire original instruction range file `[0x80,0x330000)` unchanged except the two event callsites.
- All 15 original save-path descriptor windows retain SHA-256 `27e5830aedec88451070b350897733f043dd11fef38fdab27a1dc9dd5cd5294f`, serial **SLPM-66511**, namespace **BISLPM-66511Save**. `local/r67-14y-save-static.json`.
- No verified golden checkpoint exists under the existing save-compat evidence. **No cross-release runtime save test was performed.** Live PCSX2, settings, original cards and savestates were not modified or loaded. Tests only read pre-existing ignored historical fixture copies.

### Exhaustive finished-disc audit against x

All **2,095,382,528 bytes** compared; **2,285 changed**, **zero unexplained**:

| Classification | Changed bytes |
|---|---:|
| Inspection/save text pointer owners | 129 |
| ELF translation-segment file length | 2 |
| Two new event hooks and reversion of x reconstruction hook | 10 |
| ISO9660 executable size, both endian copies | 4 |
| Save/load/back caption pixels | 1,115 |
| Obsolete x helper replaced and y private payload appended | 1,025 |

`local/r67-14y-iso-audit.json` independently regenerates expected payloads and classifies every changed byte. 2,563 installed-versus-staged metadata bytes are carried forward exactly. The ELF grows into verified unallocated zero sectors after the last outer ISO file; its extent and total disc size do not change. H.A.N.T., other graphics and data resources are byte-identical. H.A.N.T. Jumping #43/#44 is outside this release and issue persistence was not checked.

## Reproduction and next gate

```sh
python3 -m unittest discover -s tests -p 'test_r67_14y*.py' -v
uv run --python /opt/homebrew/bin/python3 --with pillow python -m unittest discover -s tests -v
python3 -m tools.r67_14y_release
python3 -m tools.r67_14y_validation
```

Build/validation refuse to overwrite existing release/report files; do not delete prior artifacts just to rerun. Read-only `payloads()` and `audit()` can reproduce/verify the existing candidate.

Next: Pablo cold-boots this y ISO when ready, without restoring an older executable-bearing savestate, and supplies screenshots of Anubis/action, Snake Staff variants/action, Heaven Door/action, save choices/prompt/warning/completion, island/“I wonder”/following event lines, opening two-line message and Eerie place, both companion slots, AFK, approved Lion/tablets and history. Do not automate that switch or alter original saves. If anything fails, capture the actual owner/geometry/timing for the failing y state before another patch. Cross-release saving/loading needs a verified golden checkpoint and separately authorized disposable-card procedure. No merge or release-runtime-success claim until visual approval; no commit/push/PR without explicit authorization.
