# First memory-card save: pre-save translation audit (2026-10-09)

**Scope:** original Japanese PS2 *Kowloon Youma Gakuenki re:charge*,
from New Game to the **first ordinary in-game memory-card save**, preserving
the user-accepted **v11-r66** game and AFK/L1 visuals. This is a **static,
read-only discovery audit**, not an implementation or runtime approval.

## Stop point and playable path

Two independent walkthroughs identify the *Heracleion Shrine* tutorial path:

1. New Game, protagonist name and Heracleion arrival; old merchant Salah;
   H.A.N.T. introduction.
2. **Chamber of Lions**: read the stone inscription, obtain/place Lion Statue,
   fight two Umara enemies.
3. **Door of Anubis**: read the stone inscriptions, align Anubis statues,
   jump onto the rising stones, use the wire gun, crawl west, operate
   Snake Staff switch.
4. **Soul Well** via the south passage; choose its **Heaven Door / Save**,
   write a **real PS2 memory-card save**, close/restart and verify Load.

**Stop before** the later storage-area acids, boss, desert/hospital story,
profile sheets, or Yachiho dorm scenes. Their translations are future scopes.

Sources: https://spwiki.net/kowloon/wikis/35.html and
https://www.h1g.jp/kowloon_ooa/?%E3%83%97%E3%83%AD%E3%83%AD%E3%83%BC%E3%82%B0=
(the latter explicitly states that the Soul Well after Snake Staff permits
saving); official Soul Well/Heaven Door operation:
https://www.arcsystemworks.jp/kowloon/faq/ .
Exact PS2/re:charge first-save behavior still requires a runtime observation.

## Coverage already present in accepted r66

- Title, name flow, old-man horizontal DG renderer, starter H.A.N.T. tutorial,
  normal dungeon action palette, SELECT menu, 446 owned item names, and
  companion/AFK/L1 texts are accepted in `docs/LOCALIZATION_STATUS.md`.
  Keep the AFK nine and L1 six approved SHA-256 golden barriers untouched.
- `ADV/DG/DG00_00.MTX`: **195** official English entries imported;
  `DG00_01.MTX`: **34** official English entries imported. The generated
  overlays have no Japanese CP932 lexical runs under the repository's
  conservative scanning heuristic; this does **not** prove live scene
  completeness or presentation.
- `DG00_02.MTX` is a **32-byte control-only** source with zero Japanese
  lexical runs and no official text map. This is not an unaddressed dialogue.
- `DG00_00.KSF` has **five** localized choice fields; three fit directly.
  The other **two** official strings exceed the available 31-byte slots,
  but the existing source-approved KSF override replaces both with shorter
  English ("Pick up device on the ground"). The current r66 override is
  SHA-256 `db445fbce3a0fc6111ca2e0f121ba29bbd40dcab646eb4ce43b2db9bd6179ecd`.
  The source is unchanged; inspect runtime choice geometry at first play.
- Initial puzzle inventory item name `獅子の像` has exact official-English
  `Lion Statue` via `tools/dungeon_item_names_data.py` item ID **413**.
- In-game generic `Save & load` command is translated in
  `tools/menu_ui.py`; **19** validated memory-card pointer-table
  messages, including normal save/load status and confirmation, are
  localized by `tools/memory_card_ui.py`. The remaining eight specialized
  clear-data messages are a distinct re:charge-only class, not proof of
  ordinary first-save completion.

## Confirmed missing owner classes with exact official PS4 correspondence

Every row below is **found in the original PS2 executable, remains at the
same Japanese source location in the r66 executable, and has unchanged
consuming literal 32-bit pointer(s)**. Existing code does not contain an
approved redirect for these owners. Some live-screen uses still require
runtime confirmation.

| Required surface | PS2 source file offset | Pristine owner pointer offsets | Official English (PS4 English.bytes) |
| --- | --- | --- | --- |
| Lion room name | `0x5CCD80` | `0x5CD78C` | Chamber of Lions |
| Anubis gate room name | `0x5CCDA0` | `0x5CD790` | Door of Anubis |
| Soul Well room name | `0x5CC7C0` | **13** references, including `0x5CD6C0` and `0x5CD718` | Soul Well |
| Lion room stone inscription, first/second rows | `0x58A200` / `0x58A230` | `0x58A258` / `0x58A25C` | Two original remaster text rows |
| Anubis gate alignment inscription, three rows | `0x590EC0` / `0x590EE0` / `0x590F00` | `0x590F38` / `0x590F3C` / `0x590F40` | Three official remaster rows |
| Anubis gate crouch/west inscription, three rows | `0x590F50` / `0x590F70` / `0x590F90` | `0x590FB8` / `0x590FBC` / `0x590FC0` | Three official remaster rows |
| First monster name | `0x695E70` | `0x594DF4` | Umara |
| Treasure vase interaction name | `0x695DD0` | `0x590DD0`, `0x590E20`, `0x590E40` | Treasure Vase |
| Snake Staff interaction name | `0x695C38` | Seven original references (incl. `0x58A2C0`) | Snake Staff |
| Soul Well Heaven Door name | `0x695D90` | `0x58FD60`, `0x592CB0` | Heaven Door |
| Soul Well Earth Door name | `0x695D88` | `0x58FD10` | Earth Door |
| Soul Well third gate name | `0x58FC18` | `0x58FC90`, `0x591540` | Door to Yomi |

The official English corpus under
`/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`
has **11,711** decoded key/value records and file SHA-256
`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`.
Every named English string above was found by an exact Japanese key in it.
The corpus is owned/local and must **not** be committed.

**Important:** the H.A.N.T. glossary pointer for a separate "Soul Well"
source at `0x588170` *was* redirected in r66; **the 13 gameplay room-name
pointers at `0x5CC7C0` were not**. Do not mistake the translated glossary
for a translated in-dungeon location name.

The primary executable location label at `0x5CCD40` was already translated
to `Heracleion Shrine`. Do not alter that accepted label.

## Optional but reachable first-save screens still not wholly English

- The **55 H.A.N.T. Help topic labels** are translated, but only **four**
  distinct topic bodies are promoted: `adv_controls`,
  `exploration_controls`, `moving_in_ruins`, `shop`; H.A.N.T.'s
  initial tutorial is a separate accepted body. The **Wire Gun Controls**,
  **Jumping**, **Moving Objects**, **Opening Doors**, **Basic Attack** and
  **Save & Load** Help bodies are among the untranslated/unpromoted set
  and can be opened before the first save. Do not claim all H.A.N.T. pages
  are localized.
- Some general interactive help/error/object descriptions and
  image/texture-baked Japanese content may be reachable before saving.
  The project has **not** established a complete early-screen reachability
  or first-dungeon graphics-owner inventory. This remains a discovery gate,
  **not** an assertion that all graphics are untranslated.
- The first Umara **battle-name owner** is unchanged, even though broader
  H.A.N.T. Enemy tabs and the item names have accepted English paths.
  Distinguish name rendering, battle HUD and item-name tables.

## Recommended bounded implementation order

**P0: Required progression to initial save.**

1. Prove and translate the two room-name owners plus the 13-alias Soul Well
   name family. For English text too long for a fixed PS2 slot, relocate to
   the shared text segment and repoint all proven references; never truncate
   or shift adjacent labels.
2. Translate the exact PS4 puzzle-inscription rows at the original
   table-owner level; verify ordered row selection, sentinel/format tokens,
   column width and pointer cardinality without mutating scenario flags,
   object IDs or puzzle execution.
3. Translate the observed early object/enemy names and all three Soul Well
   door names, each through its proven pointer owners; preserve command IDs.
4. Confirm normal Save/Load prompt and status presentation and memory-card
   writes against disposable cards only. Existing message relocation
   covers the ordinary 19 entries statically, but runtime save behavior
   is not yet proven.

**P1: Literal everything reachable before first save.**

5. Expand the **relevant** unpromoted Help bodies through their own generic
   body/metadata renderer class, with consistent official PS4 text proof
   when available; preserve accepted Help page layout.
6. Audit graphics, item descriptions, combat/error overlays and optional
   interactions. Close the resource-owner inventory only after tracing
   their early game reachability; unknowns must be reported as such.

## Acceptance gate

- Use the accepted r66 ISO as baseline; PR #34 / MS04_00 is a **later-game
  scene** and has no role in reaching the first Soul Well.
- Never edit the pristine PS2/PS4 sources, fonts, extracted proprietary
  corpora, r66 AFK/L1 resources, save serial/namespace or save-state data.
- For each owner family: SHA-pin pristine source and official-English
  correspondence, fail closed on pointer aliases, add tests for all
  fixed-slot capacities, recompile a deterministic candidate ISO, re-run
  all r66 golden acceptance tests, classify all changed bytes.
- No AI-controlled PCSX2 launch without explicit approval.
- Pablo performs a fresh **New Game** walkthrough through the first
  Soul Well (including optionals, puzzle inscriptions and battle),
  using a disposable PS2 memory-card image. Confirm Save, close emulator,
  cold-boot and Load; record a SHA-256 golden Kowloon card for future
  cross-release compatibility comparisons. Do not use savestates.
- Until that supervised runtime walkthrough, **zero** changes in this
  report are deemed runtime approved.
