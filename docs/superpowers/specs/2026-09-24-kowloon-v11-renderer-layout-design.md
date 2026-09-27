# Kowloon re:charge v11 Renderer/Layout Localization Design

Date: 2026-09-24
Branch: `fix/renderer-layout-v11`
Base: verified v10 commit `712cf4a`

## Goal

v10 is the first startup build that progresses through the localized name flow into the first old-man dialogue. Runtime evidence now shows the translation corpus is ahead of the PS2 presentation layer: English text is present, but multiple renderer/UI classes still assume Japanese-width text, Japanese vertical layout, or compact Japanese labels.

v11 will address those presentation classes systematically rather than shorten individual strings. The intended result is readable official English that fits the PS2 UI naturally, while preserving fail-closed behavior and leaving uncertain mappings untouched.

## Runtime evidence that defines v11

The latest supervised runtime test established the following:

- startup no longer freezes in the name flow;
- the opening quotation system works and varies across restarts;
- the title menu displays `New Game` / `Load Game`, but the English labels extend well beyond the original purple backing geometry;
- the name-entry keyboard and English startup flow are usable, with the known 3+3 permanent-name limitation still present;
- the game reaches the first old-man scene and its dialogue content is English;
- that dialogue is still presented with the PS2 vertical-Japanese layout instead of horizontal English layout like the official PS4 localization;
- many translated strings later in the flow clip rather than wrap or fit;
- H.A.N.T. is only partially localized in current tooling and translated tutorial text clips;
- some menu labels are technically translated but semantically awkward or still unresolved.

These observations override earlier static assumptions. In particular, the existing four-instruction ADV patch cannot be considered a complete horizontal-dialogue solution merely because its bytes are present in the final ELF.

## Design principles

1. **Renderer-first, not string-shortening-first.** Official English wording remains authoritative when a verified PS4 mapping exists. Fix layout, glyph advance, clipping, wrapping, or backing geometry before abbreviating text.
2. **Classify text by renderer ownership.** Title UI, ADV dialogue, H.A.N.T., fixed command-menu text, and other executable UI are separate presentation classes until runtime/static tracing proves shared behavior.
3. **Patch the live path, not a plausible path.** Every executable patch must be tied to a runtime-visible surface through instruction/data ownership evidence.
4. **Fail closed.** Every binary patch validates exact pristine preimages, pointer ownership, target bounds, and expected structure before modification.
5. **Prefer official remaster semantics.** Menu labels and H.A.N.T. wording use exact PS4 English where correspondence is proven. Re:charge-only labels remain unresolved unless their runtime action establishes a safe semantic mapping.
6. **Keep v10 behavior cumulative.** The no-freeze name-flow fix, memory-card alias fix, title/name input improvements, startup graphics, corpus imports, and ROFS invariants remain regression requirements.

## Scope

### In scope

- promote the latest v10 runtime results into the localization ledger;
- identify and patch the live ADV dialogue renderer used by DG00 so English renders horizontally;
- establish a general English dialogue layout policy for glyph advance, line positioning, and wrapping/clipping;
- identify the title menu's purple backing geometry and resize/reposition it for `New Game` / `Load Game` without changing official wording;
- inventory all executable-resident H.A.N.T. string/pointer tables reachable from the early game and expand localization beyond the single startup tutorial table;
- establish H.A.N.T.-specific wrapping/width/layout rules so translated text does not clip;
- replace the current fixed-slot menu patch list with a semantic menu manifest that records source text, runtime action/owner, official English when proven, storage/renderer class, and localization status;
- relocate proven menu labels such as `Return above ground` and `Report card` when fixed slots are too small and the owning pointers are proven;
- extend static/final-image acceptance so the new renderer/layout invariants cannot silently regress;
- build v11 from pristine sources and prove deterministic output before runtime testing.

### Out of scope

- changing the structural 3+3 permanent-name limit;
- inventing English for PS2/re:charge-only labels whose semantics are not proven;
- wholesale font replacement;
- prerendering dynamic dialogue/H.A.N.T. text as textures;
- translating every remaining PS2-only script before the renderer classes are stable;
- accepting a visual result by screenshot alone without tying it to a reusable patch rule.

## Architecture

### 1. Runtime-surface ledger

`docs/LOCALIZATION_STATUS.md` remains the authoritative state machine for project progress. v11 will promote only what the latest runtime session actually proved and mark new defects explicitly:

- name-flow advancement through first dialogue: runtime-proven;
- first old-man English content: runtime-proven content, buggy layout;
- title labels: runtime-proven text, buggy backing geometry;
- H.A.N.T.: translated/partially translated but buggy due to clipping and incomplete coverage;
- menu text: mixed translated/awkward/unresolved;
- ADV horizontal layout: translated but buggy until the live DG00 renderer is patched and runtime-proven.

Static checks never upgrade a row to runtime-proven.

### 2. Renderer ownership model

Introduce/extend explicit renderer classes in tooling rather than one generic "English UI" patch:

- **Title renderer/layout class** — title strings, text draw parameters, and GP088/title backing geometry.
- **ADV dialogue renderer class** — glyph-position records and the executable routine that consumes them for DG dialogue.
- **H.A.N.T. renderer/layout class** — H.A.N.T.-owned pointer tables, text storage, line width/wrapping, and command/tutorial UI.
- **Menu label class** — semantic label manifest plus either fixed-slot storage or relocated pointer storage depending on the proven owner.

Each class exposes a deterministic patch function with exact preimage validation and a corresponding final-image verifier.

## ADV horizontal dialogue

### Current evidence

The existing patch modifies the coordinate consumer around VA `0x24F9E0`, using record fields `+0x463` and `+0x465`. Runtime shows the first old-man DG00 dialogue remains vertical, so that consumer is not sufficient for the visible dialogue path.

Static scanning found another consumer around VA `0x24ED20` using the same fields. v11 will trace both consumers and their callers/owners to identify which one draws DG message glyphs and which one serves a secondary presentation path.

### Required behavior

For the live DG dialogue path:

- glyph position within a line advances along X;
- script line index advances along Y;
- two-byte PS2 English glyph encoding is normalized exactly once when converting byte position to glyph index;
- line spacing and X advance are independently controllable rather than inferred from Japanese vertical constants;
- translated line breaks from the official PS4/DC localization remain meaningful;
- text must stay inside the dialogue viewport or wrap using a proven width rule;
- speaker-name text and body text may use separate layout parameters if runtime ownership proves distinct renderers.

The first old-man scene is the regression fixture, but the patch must target the renderer class, not DG00-specific text.

## Title menu geometry

`New Game` and `Load Game` are correct strings and already use the title's two-byte glyph renderer. The defect is presentation geometry: English is substantially wider than the Japanese labels and extends beyond the original purple backing.

v11 will trace the `m_title.c` data adjacent to the title string/pointer table and the GP088 sprite records used by the title state. The patch may adjust:

- backing sprite width/source rectangle;
- backing sprite X position;
- text X position;
- text glyph advance if the title renderer has an independent spacing constant.

The selected solution must preserve visual balance and must not shrink the official labels merely to fit the Japanese-sized box. Geometry changes are validated against exact original sprite/layout records.

## H.A.N.T. completion and layout

### Coverage

Current tooling translates only one 17-entry startup tutorial pointer table at `0x5C8C70`; several entries are sentinels/control records. v11 will inventory all H.A.N.T.-owned executable strings and pointer tables reachable in the early-game UI, including labels, help/tutorial pages, and menu-adjacent text.

Each candidate string must be classified as one of:

- exact official PS4 mapping;
- proven semantic counterpart with explicit evidence;
- PS2/re:charge-only unresolved;
- control/sentinel/non-text.

Only the first two classes are translated automatically.

### Layout

H.A.N.T. receives its own measured line-width/wrapping policy. The design does not assume the title or ADV renderer constants apply. v11 will trace the H.A.N.T. text draw routine to determine:

- glyph advance;
- start X/Y;
- maximum line width/clip rectangle;
- explicit/newline behavior;
- controller-glyph placeholders and their occupied width.

Official English lines may be rewrapped without changing wording. Rewrapping is a layout transformation, not a translation change, and must be deterministic/tested.

## Menu semantics and storage

Replace the tuple-only `MENU_UI_PATCHES` model with a manifest entry containing at least:

- source Japanese text;
- executable/string offset or pointer owner;
- runtime action/function owner when known;
- exact official PS4 English mapping when available;
- selected English label;
- evidence/provenance;
- storage class: fixed-slot or relocated;
- status: proven, unresolved, or intentionally pristine.

Existing labels such as `Items`, `Quests`, `H.A.N.T.`, `Save & load`, etc. will be rechecked against official terminology and runtime action rather than retained merely because they fit.

For known official labels that exceed compact slots, such as `Return above ground` and `Report card`, v11 will relocate the string through the existing translation PT_LOAD only after proving all consuming pointers/aliases. The existing pointer table around the command-menu labels is the starting evidence but not sufficient by itself; all live aliases must be validated like the v10 memory-card fix.

`メディア` remains untranslated until its runtime action or an official counterpart proves the intended English semantics.

## General clipping policy

There will be no global "make English smaller" patch. For each renderer class, clipping is solved in this order:

1. prove the live clip rectangle/maximum line width;
2. prove glyph advance and line spacing;
3. preserve official text and rewrap at word boundaries when the renderer supports multiple lines;
4. widen/reposition backing/clip geometry when the surface is a fixed UI panel and space exists;
5. reduce glyph advance only when the renderer supports it cleanly and the result remains legible;
6. abbreviate only if the official localization itself uses a shorter label or if Pablo explicitly approves a non-official compromise.

The chosen rule must generalize to all strings owned by that renderer.

## Data flow

1. Start from the pristine PS2 ISO and pristine `SLPM_665.11`.
2. Apply existing v10 startup/name/menu/corpus transformations.
3. Apply v11 renderer/layout patches with exact pristine/staged preimage checks.
4. Build/extend translation PT_LOAD payload for newly relocated H.A.N.T./menu strings.
5. Generate any title graphics/layout overlays through the existing deterministic graphics pipeline if texture changes are required.
6. Rebuild nested `DATA.CVM`, ISO9660 records, and executable ROFS records through the existing verified builder.
7. Reopen the completed ISO and independently verify every v11 invariant.
8. Repeat the pristine build and require identical SHA-256 plus byte-for-byte `cmp` before runtime testing.

## Error handling / fail-closed rules

Every new patch must refuse to operate when any of the following drift:

- expected executable instruction words;
- expected source Japanese strings;
- pointer-table owners or aliases;
- renderer constants/layout records;
- GP088/TMX dimensions or source-region correspondence;
- translation-segment bounds;
- final ISO/CVM/ROFS ownership relationships.

Unproven aliases or semantics are not guessed. A failed proof leaves the source Japanese and records the item as unresolved.

## Testing strategy

### Unit tests

Add RED/GREEN tests per class:

- ADV: both coordinate consumers are classified; only the proven live DG path receives the horizontal transformation; exact instruction mutation boundary asserted.
- Title: source geometry records validated; English backing width/position asserted; title text bytes/pointers remain exact.
- H.A.N.T.: complete discovered table inventory; official mappings and sentinels classified; deterministic wrap output asserted; relocated pointers all resolve inside the translation PT_LOAD.
- Menus: semantic manifest uniqueness/provenance; fixed-slot vs relocated behavior; all aliases follow relocated values; unresolved labels remain pristine.
- Allowed-region tests prevent unrelated ELF mutation.

### Final-image acceptance

Extend `tools/startup_acceptance.py` or split renderer-specific acceptance helpers if it becomes too large. The completed ISO must verify:

- v10 invariants remain intact;
- title geometry patch and English labels are present;
- the live DG renderer instructions/parameters match the horizontal-English design;
- first DG00 official English content remains present;
- H.A.N.T. discovered/proven English pointer set and wrap payload are present;
- relocated menu labels and all proven aliases resolve correctly;
- unresolved menu/H.A.N.T. entries remain byte-identical to pristine;
- ROFS records resolve all modified embedded files.

### Runtime acceptance

Before launching PCSX2, state an exact visible checklist and wait for Pablo's explicit approval.

The v11 runtime test should specifically verify:

- title backing contains `New Game` / `Load Game` cleanly;
- no newly introduced startup/name regressions;
- H.A.N.T. tutorial/help pages display full English lines without clipping;
- command/menu labels are semantically correct and visually fit;
- first old-man dialogue is horizontal, readable, and wrapped similarly to the PS4 reference while retaining the PS2 scene art;
- later translated dialogue remains horizontal and does not clip under the same renderer rule.

Any vertical English dialogue, clipped translated text, guessed/wrong menu action, Japanese text in a proven-translatable H.A.N.T. item, corrupted UI geometry, or regression of v10 behavior fails the candidate.

## Deliverables

- updated runtime/localization ledger;
- renderer/layout reverse-engineering notes in `docs/DISCOVERY.md` / `docs/ARCHITECTURE.md`;
- generalized renderer/layout tooling and tests;
- semantic menu manifest;
- expanded H.A.N.T. translation coverage and wrap logic;
- deterministic v11 ISO built only from pristine sources and local copyrighted assets;
- no copyrighted game binaries/assets committed to Git;
- committed/pushed tooling, tests, reports schemas, and documentation only.

## Success criteria

v11 is ready for runtime testing only when:

- all existing and new tests pass;
- final-image acceptance covers the live renderer paths rather than only translated bytes;
- a second pristine build is byte-for-byte identical;
- Git staging contains no copyrighted game content;
- the exact runtime checklist has been documented.

v11 is considered runtime-successful only after the user confirms the visible English presentation is horizontal/readable, title/H.A.N.T./menus fit their UI, and v10's startup progression remains intact.
