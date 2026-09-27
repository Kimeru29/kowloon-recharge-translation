# Kowloon re:charge v11 Renderer/Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the v10 English startup/dialogue slice into a readable v11 presentation layer: horizontal ADV dialogue, title geometry sized for English, broader non-clipping H.A.N.T. localization, and semantically verified menu labels without regressing the v10 boot/name flow.

**Architecture:** Keep the existing corpus/ISO builder intact and add renderer-owned patch classes with exact preimage validation. Reverse-engineering proof tasks identify the live owner before any binary mutation; patch tasks then modify only that owner. Relocated executable text shares the existing translation PT_LOAD through one deterministic payload build, while unresolved semantics remain pristine.

**Tech Stack:** Python 3 standard library, `unittest`, `uv` + Pillow for graphics tests, PS2/R5900 executable inspection, CP932 two-byte glyph encoding, existing ISO9660/CVM/ROFS builder, Git.

**Spec:** `docs/superpowers/specs/2026-09-24-kowloon-v11-renderer-layout-design.md`

## Global Constraints

- Start every generated candidate from pristine PS2 ISO `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`, SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`.
- Never modify pristine PS2/PS4 sources.
- Never commit ISO/PKG/CVM files, game executables, extracted game assets, fonts, textures, generated translated binaries, or bulk official localization data.
- Preserve all v10 invariants: memory-card boot aliases, state-9 skip-reading flow, title/name text, 3+3 name behavior, startup graphics, ROFS/ISO/CVM validation, serial `SLPM-66511`, and save directory `BISLPM-66511Save`.
- The structural 3+3 permanent-name limit is out of scope.
- Do not invent English for `メディア` or any PS2/re:charge-only item whose semantics are not proven.
- Keep official PS4 wording when a verified mapping exists; solve clipping through renderer/layout rules before abbreviation.
- Every executable mutation validates exact source/staged instruction words, pointers, bounds, or layout records and fails closed on drift.
- Do not launch PCSX2 until the final v11 candidate has passed all static gates, an exact visible checklist has been stated, and Pablo explicitly approves launch.
- Static verification never upgrades a surface to runtime-proven.

## Review Focus

- **Wrong ADV consumer:** a syntactically valid axis patch applied to the non-DG consumer must fail ownership tests rather than produce another green-but-vertical candidate. Task 2 pins both consumers and Task 3 asserts only the proven DG owner changes.
- **Controller-glyph width in H.A.N.T.:** wrapping must reserve the actual display width of button/directional placeholders instead of treating their blank source gaps as ordinary spaces. Task 7 includes placeholder-aware wrap tests.
- **Missed relocated-string alias:** every proven pointer/alias to `Return above ground`, `Report card`, H.A.N.T. text, or other relocated strings must resolve to one PT_LOAD target. Tasks 6, 8, and 9 test alias completeness and fail on stale owners.
- **Wrong title backing owner:** title geometry changes must validate the exact `m_title.c`/GP088 record and leave neighboring sprite records byte-identical. Tasks 4 and 5 assert ownership and mutation boundaries.
- **Unproven semantics accidentally translated:** `メディア` and every inventory entry classified unresolved/control must remain byte-identical to pristine. Tasks 6, 8, 9, and final-image acceptance explicitly assert this.

---

### Task 1: Promote v10 Runtime Evidence and Re-establish the v11 Baseline

**Files:**
- Modify: `docs/LOCALIZATION_STATUS.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/DISCOVERY.md`
- Modify: `docs/REGRESSION.md`

**Interfaces:**
- Produces the authoritative v10 runtime baseline that all v11 tasks preserve.
- No product-code interface changes.

- [ ] **Step 1: Update the runtime ledger from the accepted observation**

Record these facts without promoting anything not explicitly observed:

```text
startup/name flow: advances into first old-man scene
opening quote rotation: working
New Game / Load Game text: correct text, backing geometry buggy
first old-man DG00 English content: runtime-proven content, vertical-layout bug
H.A.N.T.: partially translated, clipped/incomplete
menus: mixed translated/awkward/unresolved
3+3 name storage: still buggy/out of scope
```

Change the v10 candidate heading from a static gate to a runtime-tested checkpoint and retain the exact v10 SHA-256 `24d425433af97b1617e820cac05aa2a4d9389aa9fa19c1767a57eb763812da8e`.

- [ ] **Step 2: Run the regression gate and baseline test suites**

Run:

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
python3 -m unittest discover -s tests -v
uv run --with pillow python -m unittest discover -s tests -v
```

Expected: regression reports no changed/removed entries; dependency-free suite has zero failures/errors; Pillow suite has zero failures/errors.

- [ ] **Step 3: Verify local source prerequisites without substituting missing data**

Run:

```bash
test -f '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso'
test -f '/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg'
test -f fixtures/elf/SLPM_665.11 || test -f ../startup-flow-v10/fixtures/elf/SLPM_665.11
```

For PS4 official-text discovery, use only the extracted `English.bytes` when present at:

```text
/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes
```

If that extracted file is absent, Tasks 6 and 8 must stop before mapping new official strings; they may still inventory PS2 ownership, but must not infer translations from model knowledge.

- [ ] **Step 4: Commit the evidence checkpoint**

```bash
git add docs/LOCALIZATION_STATUS.md docs/HANDOFF.md docs/DISCOVERY.md docs/REGRESSION.md
git commit -m "Record v10 runtime renderer findings"
```

---

### Task 2: Prove ADV Coordinate-Consumer Ownership

**Files:**
- Modify: `tools/adv_layout.py`
- Modify: `tests/test_adv_layout.py`
- Modify: `docs/DISCOVERY.md`
- Generate ignored: `local/adv-renderer-ownership-v11.json`

**Interfaces:**
- Produces `AdvCoordinateConsumer` and `inspect_adv_coordinate_consumers(raw: bytes) -> tuple[AdvCoordinateConsumer, ...]`.
- Produces a deterministic ownership report for the two known consumers at file offsets `0x14EDA0` (VA `0x24ED20`) and `0x14FA60` (VA `0x24F9E0`).
- Task 3 consumes exactly one consumer classified `dg_dialogue`.

- [ ] **Step 1: Write the failing ownership tests**

Add to `tests/test_adv_layout.py`:

```python
from tools.adv_layout import inspect_adv_coordinate_consumers


def test_finds_both_known_adv_coordinate_consumers():
    consumers = inspect_adv_coordinate_consumers(RAW)
    assert [(c.file_offset, c.va) for c in consumers] == [
        (0x14EDA0, 0x24ED20),
        (0x14FA60, 0x24F9E0),
    ]
    assert all(c.line_field == 0x463 for c in consumers)
    assert all(c.position_field == 0x465 for c in consumers)


def test_consumer_probe_fails_closed_on_known_load_drift():
    tampered = bytearray(RAW)
    tampered[0x14EDA0] ^= 1
    with self.assertRaisesRegex(ValueError, "ADV consumer preimage"):
        inspect_adv_coordinate_consumers(bytes(tampered))
```

- [ ] **Step 2: Run RED**

Run:

```bash
python3 -m unittest tests.test_adv_layout -v
```

Expected: import/attribute failure because `inspect_adv_coordinate_consumers` does not exist.

- [ ] **Step 3: Implement a bounded consumer model and preimage checks**

Add to `tools/adv_layout.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AdvCoordinateConsumer:
    file_offset: int
    va: int
    line_field: int
    position_field: int
    line_load_word: int
    position_load_word: int
    role: str
```

`inspect_adv_coordinate_consumers()` must validate the exact known load instructions around both consumers and return them in file-offset order. Initial `role` values are `"unclassified"`; do not patch either consumer merely because it matches the field pattern.

- [ ] **Step 4: Trace callers/data ownership and emit the local proof report**

Write a bounded one-shot analysis in `tools/adv_layout.py` (or a private helper invoked from a Python snippet) that records, for each consumer:

```json
{
  "file_offset": 1371552,
  "va": 2411808,
  "line_field": 1123,
  "position_field": 1125,
  "callers": [],
  "nearby_global_refs": [],
  "role": "unclassified",
  "evidence": []
}
```

Populate `callers`, nearby globals, and `evidence` from executable references/call structure. The committed code must not hard-code `dg_dialogue` until the evidence uniquely ties one consumer to the DG message path. Save the detailed report only under `local/`.

Proof gate: exactly one consumer must be classified `dg_dialogue`; the other must receive a distinct role or remain `secondary_unknown`. If this cannot be proven, stop Task 3 and update `docs/DISCOVERY.md` rather than patching both.

- [ ] **Step 5: Pin the proven role in a test**

Once the evidence uniquely identifies the live DG consumer, add:

```python
def test_exactly_one_consumer_is_live_dg_dialogue_path():
    consumers = inspect_adv_coordinate_consumers(RAW)
    dg = [c for c in consumers if c.role == "dg_dialogue"]
    self.assertEqual(1, len(dg))
```

Do not encode the expected offset until the trace proves it. The test's committed expected offset must match the report and `docs/DISCOVERY.md` evidence.

- [ ] **Step 6: Run GREEN and commit**

```bash
python3 -m unittest tests.test_adv_layout -v
git add tools/adv_layout.py tests/test_adv_layout.py docs/DISCOVERY.md
git commit -m "Classify ADV dialogue render paths"
```

---

### Task 3: Patch the Proven Live DG Renderer and Pin English Layout Policy

**Files:**
- Modify: `tools/adv_layout.py`
- Modify: `tests/test_adv_layout.py`
- Modify: `tests/test_early_ui.py`
- Modify: `tools/startup_acceptance.py`
- Modify: `tests/test_startup_acceptance.py`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- `patch_adv_horizontal_layout(raw: bytes) -> bytes` patches only the proven live DG consumer plus any separately proven DG spacing/clip constants.
- Produces `ADV_DG_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...]` as the single source of truth used by unit tests and final-image acceptance.

- [ ] **Step 1: Replace the old green-but-insufficient test with a live-path RED test**

The new test must assert:

```python
def test_horizontal_patch_mutates_only_proven_dg_consumer():
    consumers = inspect_adv_coordinate_consumers(RAW)
    live = next(c for c in consumers if c.role == "dg_dialogue")
    secondary = next(c for c in consumers if c is not live)

    result = patch_adv_horizontal_layout(RAW)
    self.assertNotEqual(
        RAW[live.file_offset:live.file_offset + 0x80],
        result[live.file_offset:live.file_offset + 0x80],
    )
    self.assertEqual(
        RAW[secondary.file_offset:secondary.file_offset + 0x80],
        result[secondary.file_offset:secondary.file_offset + 0x80],
    )
```

Also assert byte-position is normalized exactly once (`/2` for two-byte glyphs) and line index is not halved.

- [ ] **Step 2: Run RED against the existing v10 patch**

```bash
python3 -m unittest tests.test_adv_layout -v
```

Expected: failure because the old implementation patches the previously assumed `0x24F9E0` path regardless of the new ownership classification.

- [ ] **Step 3: Implement the minimal renderer mutation**

Build `ADV_DG_LAYOUT_PATCHES` only from the proven live routine. For the live path, implement these semantics in the existing instruction sequence:

```text
X = horizontal_origin + (byte_position / 2) * english_glyph_advance
Y = vertical_origin + line_index * english_line_spacing
```

Do not globally change the PS2 font renderer. Any `english_glyph_advance`, `english_line_spacing`, or clip-width constant is patched only after its exact load/immediate owner has been traced to this DG routine. If the current routine already obtains acceptable spacing after the axis correction, do not add spacing patches.

- [ ] **Step 4: Add mutation-boundary and preimage-drift tests**

Compute changed byte offsets and assert they are a subset of `ADV_DG_LAYOUT_PATCHES`. Flip one byte in every preimage class (coordinate load, normalization instruction, any spacing/clip constant) and assert `ValueError("ADV layout preimage...")`.

- [ ] **Step 5: Update final-image acceptance to consume the patch table**

Replace duplicated hard-coded `_ADV_PATCH_WORDS` with an import/derived view of `ADV_DG_LAYOUT_PATCHES` so tests and acceptance cannot disagree.

Add a named check:

```text
adv_dg_horizontal_layout
```

The verifier must reject an ELF that contains the old secondary-path patch but not the proven DG patch.

- [ ] **Step 6: Run targeted/full tests and commit**

```bash
python3 -m unittest tests.test_adv_layout tests.test_early_ui tests.test_startup_acceptance -v
python3 -m unittest discover -s tests -v
git add tools/adv_layout.py tests/test_adv_layout.py tests/test_early_ui.py tools/startup_acceptance.py tests/test_startup_acceptance.py docs/ARCHITECTURE.md
git commit -m "Patch live DG dialogue layout"
```

---

### Task 4: Prove the Title Backing/Layout Owner

**Files:**
- Create: `tools/title_layout.py`
- Create: `tests/test_title_layout.py`
- Modify: `docs/DISCOVERY.md`
- Generate ignored: `local/title-layout-v11.json`

**Interfaces:**
- Produces `TitleLayoutRecord` and `inspect_title_layout(raw: bytes) -> TitleLayoutEvidence`.
- Task 5 consumes one proven backing record plus the exact neighboring mutation boundary.

- [ ] **Step 1: Write a failing title-layout inventory test**

Create `tests/test_title_layout.py` with:

```python
from tools.title_layout import inspect_title_layout


def test_title_layout_inventory_is_tied_to_m_title_region():
    evidence = inspect_title_layout(RAW)
    self.assertEqual(0x5CBDE8, evidence.string_arena_start)
    self.assertEqual(0x5CBE50, evidence.string_pointer_table)
    self.assertTrue(evidence.sprite_records)
    self.assertTrue(all(r.group in (88, 91) for r in evidence.sprite_records))
```

Also assert the probe fails if the `m_title.c` region or one candidate sprite record drifts.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests.test_title_layout -v
```

Expected: import failure because `tools.title_layout` does not exist.

- [ ] **Step 3: Implement read-only parsing of the adjacent title records**

Define:

```python
@dataclass(frozen=True)
class TitleLayoutRecord:
    file_offset: int
    group: int
    index: int
    values: tuple[float, ...]


@dataclass(frozen=True)
class TitleBackingGeometry:
    record_offset: int
    x: float
    y: float
    width: float
    height: float


@dataclass(frozen=True)
class TitleLayoutEvidence:
    string_arena_start: int
    string_pointer_table: int
    sprite_records: tuple[TitleLayoutRecord, ...]
    backing: TitleBackingGeometry | None
    unrelated_record_bytes: tuple[tuple[int, bytes], ...]
    evidence: tuple[str, ...]
```

Parse only the bounded `m_title.c` region around `0x5CBE60..0x5CBFC0`. Do not infer arbitrary floats elsewhere in the ELF.

- [ ] **Step 4: Trace record consumers and identify the purple backing record**

Use references/call sites from the title state to tie one record to the background drawn behind `New Game` / `Load Game`. Save the full evidence under `local/title-layout-v11.json` and summarize the proven record in `docs/DISCOVERY.md`.

Proof gate: `backing` must be non-null and have a unique live owner. If the purple panel is instead a baked GP088 pixel region, record that outcome explicitly and Task 5 must use the graphics branch below rather than patching an unrelated float record.

- [ ] **Step 5: Run GREEN and commit proof tooling**

```bash
python3 -m unittest tests.test_title_layout -v
git add tools/title_layout.py tests/test_title_layout.py docs/DISCOVERY.md
git commit -m "Trace title menu layout ownership"
```

---

### Task 5: Fit the Title Backing to Official English Labels

**Files:**
- Modify: `tools/title_layout.py` **or**, if Task 4 proves baked pixels, modify `tools/startup_graphics.py`
- Modify/Create: `tests/test_title_layout.py` and, for baked pixels, `tests/test_startup_graphics.py`
- Modify: `tools/startup_ui.py`
- Modify: `tests/test_startup_ui.py`
- Modify: `tools/early_ui.py`
- Modify: `tests/test_early_ui.py`
- Modify: `tools/startup_acceptance.py`
- Modify: `tests/test_startup_acceptance.py`

**Interfaces:**
- Executable-layout branch produces `patch_title_layout(raw: bytes) -> bytes`.
- Graphics branch produces a deterministic GP088 overlay using the existing indexed-texture pipeline.
- Both branches preserve exact `New Game` / `Load Game` bytes and pointers from `patch_title_labels()`.

- [ ] **Step 1: Write RED tests for the proven owner**

If Task 4 proves executable geometry, assert:

```python
def test_title_backing_is_widened_without_touching_neighbor_records():
    result = patch_title_layout(RAW)
    before = inspect_title_layout(RAW)
    after = inspect_title_layout(result)
    self.assertIsNotNone(before.backing)
    self.assertIsNotNone(after.backing)
    self.assertGreater(after.backing.width, before.backing.width)
    self.assertEqual(before.unrelated_record_bytes, after.unrelated_record_bytes)
```

If Task 4 proves baked GP088 pixels, assert the generated PS2 container preserves file size, palette/index format, and all non-backing named chunks byte-identically.

- [ ] **Step 2: Run RED**

Run only the branch's targeted tests and confirm the existing v10 output retains Japanese-sized backing geometry.

- [ ] **Step 3: Implement the minimal geometry change**

Use the measured English label extent from the title renderer; keep official wording and readable glyph size. Widen/recenter the backing enough to contain the longer of `New Game` and `Load Game` plus the same left/right visual padding measured from the pristine Japanese label/background relationship.

Do not change title text encoding or abbreviate labels.

- [ ] **Step 4: Assert exact mutation boundary and final-image invariant**

Add a named final-image check:

```text
title_english_backing_geometry
```

It must verify both the exact English label pointers/bytes and the proven layout/graphics record. Neighboring title records/chunks must remain pristine unless separately enumerated.

- [ ] **Step 5: Run tests and commit**

```bash
python3 -m unittest tests.test_title_layout tests.test_startup_ui tests.test_early_ui tests.test_startup_acceptance -v
uv run --with pillow python -m unittest tests.test_startup_graphics tests.test_title_layout -v
python3 -m unittest discover -s tests -v
git add tools/title_layout.py tools/startup_graphics.py tools/startup_ui.py tools/early_ui.py tools/startup_acceptance.py tests/test_title_layout.py tests/test_startup_graphics.py tests/test_startup_ui.py tests/test_early_ui.py tests/test_startup_acceptance.py
git commit -m "Fit title menu geometry to English"
```

Only add files that actually changed; never stage generated texture/ISO artifacts.

---

### Task 6: Inventory H.A.N.T. Text Ownership and Official Mappings

**Files:**
- Create: `tools/hant_inventory.py`
- Create: `tests/test_hant_inventory.py`
- Create: `translations/hant_ui.json`
- Modify: `docs/DISCOVERY.md`
- Generate ignored: `local/hant-inventory-v11.json`

**Interfaces:**
- Produces `HantTextEntry` and `inventory_hant_text(raw: bytes, english_rows: Iterable[tuple[str, str, int]] | None) -> tuple[HantTextEntry, ...]`.
- Produces classifications: `official_exact`, `official_semantic`, `unresolved`, `control`.
- Task 7 translates only the first two classes.

- [ ] **Step 1: Write failing inventory tests against the known tutorial table**

Create synthetic/unit expectations that the current `0x5C8C70` 17-entry table is classified as:

```text
translatable text: 0,2,3,4,7,8,9,10,12,13,14
control/sentinel: 1,5,6,11,15,16
```

Also assert executable H.A.N.T. occurrences outside that table are surfaced as candidate owners instead of silently ignored.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests.test_hant_inventory -v
```

Expected: import failure because `tools.hant_inventory` does not exist.

- [ ] **Step 3: Implement bounded executable inventory**

Define:

```python
@dataclass(frozen=True)
class HantTextEntry:
    key: str
    source_offset: int
    pointer_offsets: tuple[int, ...]
    source_text: str
    official_english: str | None
    classification: str
    owner: str
    evidence: str
```

The scanner may use known H.A.N.T. anchors/string regions, pointer references, and nearby handler/task names. It must not treat every executable occurrence of the generic Japanese word `情報` as H.A.N.T.-owned without pointer/task evidence.

- [ ] **Step 4: Join official PS4 mappings only from `English.bytes`**

Use `tools.inspect_english_bytes.parse()` against:

```text
/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes
```

If that file is absent, emit inventory entries with `official_english=None` and stop before translating newly discovered entries. Do not fill them from memory.

Exact source-key matches become `official_exact`. A semantic counterpart requires a documented source mismatch plus specific evidence (as already done for `方向キー`/`方向ボタン`) and becomes `official_semantic`.

- [ ] **Step 5: Save/report inventory and pin uniqueness/sentinels**

Write the full local evidence to `local/hant-inventory-v11.json`. Commit only the small proven early-UI subset to `translations/hant_ui.json` with fields `key`, `source_offset`, `pointer_offsets`, `source_text`, `official_english`, `classification`, `owner`, and `evidence`. Do not commit the bulk `English.bytes` corpus. Update `docs/DISCOVERY.md`, and test:

```python
self.assertEqual(len(entries), len({entry.key for entry in entries}))
self.assertTrue(all(e.official_english is None for e in entries if e.classification == "unresolved"))
translated = [e for e in entries if e.classification in {"official_exact", "official_semantic"}]
self.assertTrue(all(e.classification != "control" for e in translated))
```

- [ ] **Step 6: Commit inventory tooling**

```bash
python3 -m unittest tests.test_hant_inventory -v
git add tools/hant_inventory.py tests/test_hant_inventory.py translations/hant_ui.json docs/DISCOVERY.md
git commit -m "Inventory HANT executable text"
```

---

### Task 7: Expand H.A.N.T. Translation and Add Placeholder-Aware Wrapping

**Files:**
- Modify: `tools/hant_ui.py`
- Create: `tools/hant_layout.py`
- Modify: `tests/test_hant_ui.py`
- Create: `tests/test_hant_layout.py`
- Modify: `tools/early_ui.py`
- Modify: `tools/startup_acceptance.py`
- Modify: `tests/test_startup_acceptance.py`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- `measured_hant_cells(text: str, reserved_spans: tuple[tuple[int, int], ...] = (), controller_gap_cells: int = 5) -> int`.
- `wrap_hant_text(text: str, max_cells: int, reserved_spans: tuple[tuple[int, int], ...] = ()) -> tuple[str, ...]`.
- `patch_hant_tutorial()` becomes a broader H.A.N.T. executable patch consuming Task 6's committed manifest/constants, while preserving existing public behavior for known tutorial entries.
- Produces a deterministic list of relocated H.A.N.T. targets for final-image acceptance.

- [ ] **Step 1: Write RED wrapping tests**

Create `tests/test_hant_layout.py`:

```python
def test_wraps_at_words_without_changing_official_wording():
    lines = wrap_hant_text(
        "The H.A.N.T is a mini info device designed to support exploration.",
        max_cells=32,
    )
    self.assertTrue(all(len(line) <= 32 for line in lines))
    self.assertEqual(
        " ".join(lines),
        "The H.A.N.T is a mini info device designed to support exploration.",
    )


def test_controller_placeholder_reserves_display_width():
    lines = wrap_hant_text(
        "Press the      button to bring up the command thumbnails.",
        max_cells=32,
        reserved_spans=((10, 15),),
    )
    self.assertTrue(all(measured_hant_cells(line) <= 32 for line in lines))
```

`measured_hant_cells()` must count controller-placeholder spans according to the proven renderer width, not collapse them as normal spaces.

- [ ] **Step 2: Run RED and trace the H.A.N.T. draw limits**

Run:

```bash
python3 -m unittest tests.test_hant_layout -v
```

Before implementing constants, trace the H.A.N.T.-owned draw routine from the Task 6 pointer/table owners and record exact glyph advance, start position, clip/maximum width, line spacing, and explicit newline behavior in `docs/DISCOVERY.md`. If multiple H.A.N.T. renderers exist, give each a separate layout profile rather than a shared guessed width.

- [ ] **Step 3: Implement deterministic word wrapping**

Define:

```python
@dataclass(frozen=True)
class HantLayoutProfile:
    max_cells: int
    glyph_advance: float
    line_spacing: float
    controller_gap_cells: int
```

`wrap_hant_text` must:

1. preserve official words/punctuation;
2. wrap only at word boundaries unless a single token exceeds the width;
3. preserve intentional controller-glyph gaps as protected spans;
4. produce deterministic lines;
5. raise `ValueError` if a single unbreakable token cannot fit the proven line width.

- [ ] **Step 4: Expand H.A.N.T. payload to every proven inventory entry**

Translate only entries classified `official_exact` or `official_semantic`. Keep control/sentinel/unresolved source pointers byte-identical.

Refactor hard-coded `HANT_ENGLISH_LINES` into a proven manifest/derived dictionary if necessary, but retain stable keys for acceptance reporting.

- [ ] **Step 5: Test pointer targets, aliases, unresolved preservation, and wrap output**

For every translated entry:

```python
for pointer_offset in entry.pointer_offsets:
    self.assertEqual(target_va, struct.unpack_from("<I", result, pointer_offset)[0])
self.assertGreaterEqual(target_va, info.segment_vaddr)
self.assertLess(target_va, info.segment_vaddr + info.payload_size)
```

For every unresolved/control entry, compare its pointer/source region to pristine.

- [ ] **Step 6: Extend final-image acceptance**

Add checks such as:

```text
hant_inventory_proven_targets
hant_wrapped_layout_payload
hant_unresolved_pristine
```

Acceptance must verify the completed ISO's ELF, not only an intermediate translated ELF.

- [ ] **Step 7: Run targeted/full tests and commit**

```bash
python3 -m unittest tests.test_hant_inventory tests.test_hant_layout tests.test_hant_ui tests.test_startup_acceptance -v
python3 -m unittest discover -s tests -v
git add tools/hant_inventory.py tools/hant_layout.py tools/hant_ui.py tools/early_ui.py tools/startup_acceptance.py tests/test_hant_inventory.py tests/test_hant_layout.py tests/test_hant_ui.py tests/test_startup_acceptance.py docs/ARCHITECTURE.md docs/DISCOVERY.md
git commit -m "Expand HANT localization and wrapping"
```

---

### Task 8: Replace Fixed Menu Patches with a Semantic Manifest and Prove Pointer Ownership

**Files:**
- Create: `tools/menu_ui.py`
- Create: `tests/test_menu_ui.py`
- Modify: `tools/early_ui.py`
- Modify: `tests/test_early_ui.py`
- Modify: `docs/DISCOVERY.md`
- Generate ignored: `local/menu-ownership-v11.json`

**Interfaces:**
- Produces `MenuLabelSpec` and `MENU_LABELS: tuple[MenuLabelSpec, ...]`.
- Produces `patch_menu_labels(raw: bytes, relocated_targets: Mapping[str, int] | None = None) -> bytes`.
- Task 9 consumes `storage == "relocated"` entries and proven pointer aliases.

- [ ] **Step 1: Write RED manifest tests**

Create:

```python
@dataclass(frozen=True)
class MenuLabelSpec:
    key: str
    source_offset: int
    capacity: int
    source_text: str
    action_owner: str | None
    official_english: str | None
    selected_english: str | None
    evidence: str
    storage: str       # fixed-slot | relocated | pristine
    status: str        # proven | unresolved | intentionally-pristine
    pointer_offsets: tuple[int, ...] = ()
```

Tests must assert unique keys/source offsets, proven entries have evidence, unresolved entries have `selected_english is None`, and `メディア` is unresolved/pristine.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests.test_menu_ui -v
```

Expected: import failure because `tools.menu_ui` does not exist.

- [ ] **Step 3: Migrate existing menu patches without changing behavior**

Move the existing `Items`, `Quests`, `H.A.N.T.`, `Save & load`, `Leave room`, `Shop`, `Guild site`, `Broadband`, `Collection`, `Next chapter`, `End turn`, `Interior`, `None`, `Map`, `Noise`, `Battle` entries from `MENU_UI_PATCHES` into `MENU_LABELS` as `fixed-slot` entries only after preserving their current official/proven evidence.

`tools.early_ui.build_early_ui_elf()` must call `patch_menu_labels()` rather than patching the old tuple directly.

- [ ] **Step 4: Trace action owners and exact official terminology**

For every menu label visible in the early H.A.N.T./command UI, tie the string/pointer entry to its runtime action/function/table. Use `English.bytes` exact mappings where available.

Record the evidence under `local/menu-ownership-v11.json` and summarize in `docs/DISCOVERY.md`.

`Return above ground` and `Report card` may become `relocated` only after all consuming pointer offsets are proven. `メディア` remains pristine unless this trace yields a proven official counterpart/action semantic.

- [ ] **Step 5: Assert fixed-slot and pristine behavior**

Tests must verify fitting fixed entries still fit NUL-terminated capacity and mutate only their own slots; unresolved/pristine entries are byte-identical to the pristine ELF.

- [ ] **Step 6: Commit semantic manifest and ownership proof**

```bash
python3 -m unittest tests.test_menu_ui tests.test_early_ui -v
git add tools/menu_ui.py tools/early_ui.py tests/test_menu_ui.py tests/test_early_ui.py docs/DISCOVERY.md
git commit -m "Model menu labels by runtime semantics"
```

---

### Task 9: Generalize Relocated Executable Text and Add Long Menu Labels

**Files:**
- Create: `tools/executable_text.py`
- Create: `tests/test_executable_text.py`
- Modify: `tools/hant_ui.py`
- Modify: `tools/memory_card_ui.py` only if needed to consume the shared helper
- Modify: `tools/menu_ui.py`
- Modify: `tools/early_ui.py`
- Modify: `tests/test_hant_ui.py`
- Modify: `tests/test_memory_card_ui.py`
- Modify: `tests/test_menu_ui.py`
- Modify: `tests/test_early_ui.py`

**Interfaces:**
- Produces `RelocatedText` and one deterministic `install_executable_text(raw: bytes, entries: Sequence[RelocatedText], reserve_size: int = 0x100000) -> ExecutableTextResult`.
- All relocated name-reading provenance strings, H.A.N.T., memory-card messages, and proven long menu labels share one PT_LOAD installation.

- [ ] **Step 1: Write RED generic relocation tests**

Create:

```python
@dataclass(frozen=True)
class RelocatedText:
    key: str
    encoded: bytes
    pointer_offsets: tuple[int, ...]


@dataclass(frozen=True)
class ExecutableTextResult:
    raw: bytes
    info: TranslationSegmentInfo
    target_vas: dict[str, int]
```

Synthetic test: construct a minimal ELF fixture using the same program-header shape already exercised by `tests/test_elf_translation_segment.py`, and define the pointer reader in the test:

```python
def read_ptr(raw: bytes, offset: int) -> int:
    return struct.unpack_from("<I", raw, offset)[0]


def test_packs_once_and_repoints_all_aliases():
    fake_elf = make_translation_segment_fixture(pointer_offsets=(0x10, 0x14, 0x18))
    entries = (
        RelocatedText("a", b"AA\0", (0x10, 0x14)),
        RelocatedText("b", b"BBBB\0", (0x18,)),
    )
    result = install_executable_text(fake_elf, entries)
    self.assertEqual(result.target_vas["a"], read_ptr(result.raw, 0x10))
    self.assertEqual(result.target_vas["a"], read_ptr(result.raw, 0x14))
    self.assertNotEqual(result.target_vas["a"], result.target_vas["b"])
```

Add `make_translation_segment_fixture(...)` to `tests/test_executable_text.py` by copying the minimal synthetic ELF construction pattern from `tests/test_elf_translation_segment.py`; do not depend on the copyrighted local executable for this unit test.

Also test duplicate keys and pointer ownership conflicts reject.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests.test_executable_text -v
```

- [ ] **Step 3: Implement one deterministic payload builder**

Requirements:

```text
sort/order is explicit and stable
2-byte align each payload entry
install translation PT_LOAD exactly once
reject duplicate keys
reject one pointer offset owned by two entries
reject payload > reserve_size
return target VA map for acceptance/tests
```

Callers remain responsible for validating pristine source strings/pointers before supplying entries.

- [ ] **Step 4: Refactor current H.A.N.T./memory/name payload through the generic helper with no byte-level regression**

Before adding menu entries, build the translated v10-equivalent ELF before and after refactor and assert identical SHA-256. Add a unit test that compares the relevant pointer targets/payload bytes rather than relying only on whole-file hash.

- [ ] **Step 5: Add proven `relocated` menu entries**

Create `RelocatedText` entries from Task 8's manifest only for labels with proven official English and complete pointer ownership, including `Return above ground` and `Report card` if their Task 8 proof passed.

Do not add `メディア` unless Task 8 promoted it to proven.

- [ ] **Step 6: Add alias/preimage/mutation-boundary tests**

For each relocated label, all proven pointer aliases must equal one target VA inside the translation segment; original compact source bytes may remain pristine/unreferenced unless a separately proven reason requires clearing them.

- [ ] **Step 7: Run tests and commit**

```bash
python3 -m unittest tests.test_executable_text tests.test_hant_ui tests.test_memory_card_ui tests.test_menu_ui tests.test_early_ui -v
python3 -m unittest discover -s tests -v
git add tools/executable_text.py tools/hant_ui.py tools/memory_card_ui.py tools/menu_ui.py tools/early_ui.py tests/test_executable_text.py tests/test_hant_ui.py tests/test_memory_card_ui.py tests/test_menu_ui.py tests/test_early_ui.py
git commit -m "Generalize executable text relocation"
```

---

### Task 10: Extend Final-Image Acceptance and Whole-ELF Mutation Guards

**Files:**
- Modify: `tools/startup_acceptance.py`
- Modify: `tests/test_startup_acceptance.py`
- Modify: `tests/test_early_ui.py`
- Modify: `docs/REGRESSION.md`

**Interfaces:**
- Final-image acceptance names each v11 invariant independently.
- Allowed-region tests enumerate every executable byte range changed by v11.

- [ ] **Step 1: Add RED acceptance-name tests**

Require at least these named checks:

```text
adv_dg_horizontal_layout
title_english_backing_geometry
hant_inventory_proven_targets
hant_wrapped_layout_payload
hant_unresolved_pristine
menu_semantic_fixed_labels
menu_relocated_labels
menu_unresolved_pristine
```

Keep every v10 acceptance check.

- [ ] **Step 2: Run RED**

```bash
python3 -m unittest tests.test_startup_acceptance -v
```

Expected: missing v11 check names.

- [ ] **Step 3: Implement final-ISO verifiers from shared manifests/constants**

Do not duplicate offsets when a tooling module already exports them. The verifier must reopen the completed ISO, locate `SLPM_665.11`, resolve translation-segment VAs to file offsets, and validate final post-ROFS bytes.

- [ ] **Step 4: Extend allowed-region tests**

`tests/test_early_ui.py` must compute changed bytes between pristine ELF and `build_early_ui_elf(RAW)` and prove every change belongs to an explicitly exported patch/pointer/layout region. Unexpected mutation fails even if all semantic acceptance checks pass.

- [ ] **Step 5: Verify unresolved-source preservation**

Acceptance must explicitly compare unresolved menu/H.A.N.T. source/pointer records against pristine bytes available through the local fixture/source extraction.

- [ ] **Step 6: Run full tests and commit**

```bash
python3 -m unittest tests.test_startup_acceptance tests.test_early_ui -v
python3 -m unittest discover -s tests -v
uv run --with pillow python -m unittest discover -s tests -v
git add tools/startup_acceptance.py tests/test_startup_acceptance.py tests/test_early_ui.py docs/REGRESSION.md
git commit -m "Verify v11 renderer invariants"
```

---

### Task 11: Build v11 Twice from Pristine Sources, Refresh Documentation, and Stop at Runtime Gate

**Files:**
- Modify: `docs/BUILD.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/DISCOVERY.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/LOCALIZATION_STATUS.md`
- Modify: `docs/REGRESSION.md`
- Generate ignored: `local/startup-build-v11.json`, `local/startup-acceptance-v11.json`, `local/startup-build-v11-repeat.json`
- Generate local-only: `/private/tmp/kowloon-recharge-startup-en-v11.iso`, `/private/tmp/kowloon-recharge-startup-en-v11-repeat.iso`

**Interfaces:**
- Produces the reproducible v11 runtime candidate and exact supervised runtime checklist.
- Does not launch PCSX2.

- [ ] **Step 1: Regenerate the executable UI from the pristine local ELF fixture**

```bash
python3 -m tools.build_early_ui_elf
```

Expected: fail-closed success with no source-preimage drift.

- [ ] **Step 2: Build v11 from the pristine ISO**

```bash
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11.json
```

- [ ] **Step 3: Run final-image acceptance**

```bash
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11.json
```

Expected: every v10 and v11 check passes. Any one failed named check blocks runtime testing.

- [ ] **Step 4: Rebuild independently to a second path**

Run the same builder from the pristine ISO with output `/private/tmp/kowloon-recharge-startup-en-v11-repeat.iso` and report `local/startup-build-v11-repeat.json`.

Then run:

```bash
shasum -a 256 /private/tmp/kowloon-recharge-startup-en-v11.iso /private/tmp/kowloon-recharge-startup-en-v11-repeat.iso
cmp /private/tmp/kowloon-recharge-startup-en-v11.iso /private/tmp/kowloon-recharge-startup-en-v11-repeat.iso
```

Expected: identical SHA-256 and `cmp` exit code 0.

- [ ] **Step 5: Run final regression/test/safety audit**

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
python3 -m unittest discover -s tests -v
uv run --with pillow python -m unittest discover -s tests -v
git diff --check
git status --short
```

Audit tracked/staged files and reject any ISO, PKG, CVM, `SLPM_665.11`, TMX/BIN extracted asset, font, or local report/artifact.

- [ ] **Step 6: Update documentation with measured values only**

Record actual v11 test counts, acceptance count, candidate SHA-256, final ELF SHA-256, overlay/relocation counts, deterministic-build result, proven ADV/title/H.A.N.T./menu ownership, and remaining unresolved items. Do not copy expected counts from this plan if the measured values differ.

`docs/LOCALIZATION_STATUS.md` must keep v11 surfaces **Not runtime-tested** or **Translated but buggy** until Pablo observes them in PCSX2.

- [ ] **Step 7: Write the exact v11 runtime checklist**

The checklist must include:

```text
1. v10 boot/name flow still progresses without the kana-reading screen or freeze.
2. memory-card/startup/title graphics retain accepted English behavior.
3. New Game / Load Game fit fully inside the resized purple backing.
4. H.A.N.T. tutorial/help pages show complete official English without clipping.
5. menu labels match their proven actions and fit; unresolved labels remain intentionally Japanese rather than guessed.
6. first old-man speaker/body dialogue is horizontal and readable, with PS2 scene art retained.
7. at least one later translated dialogue page uses the same horizontal renderer rule without clipping.
8. any vertical English, clipped translated text, wrong menu semantic, unexpected Japanese in a proven H.A.N.T. entry, or v10 regression fails the candidate.
```

- [ ] **Step 8: Commit/push safe source only**

```bash
git add tools tests docs translations .gitignore
git status --short
git commit -m "Complete v11 renderer localization pass"
git push -u origin fix/renderer-layout-v11
```

Before committing, unstage/remove any generated local artifact if it appears. Do not use a broad `git add` if it would stage ignored-rule mistakes; inspect the index first.

- [ ] **Step 9: Stop before emulator launch**

Report the candidate path, SHA-256, acceptance result, test results, branch/commit, and exact visible checklist. Wait for Pablo's explicit approval before launching PCSX2.
