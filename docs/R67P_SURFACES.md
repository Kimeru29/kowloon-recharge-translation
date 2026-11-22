# r67.15p inherited UI and artwork

The Help scroll fix uses the existing Help row pitch in the native extent calculation. The H.A.N.T. recording popup uses a previously generated and independently reproduced official artwork port. Both are diagnostic pending gameplay.

## H.A.N.T. Help

Help mode 4 stages its text at X=85, Y=131 and advances 16 px per row at EE `0x2907BC–0x290824`. The shared extent at `0x2909F0–0x290A90` still computes `21 * row_count + 12` for pages with at least 11 rows. The scrollbar uses that height and subtracts the existing 222 px viewport. At `0x291128–0x29116C`, a down input increments the scroll value by five pixels and snaps the final incomplete step to the maximum. The row renderer rejects origins at or below Y=89 and at or above Y=383.

The installed o executable and tables reproduce the issue on 12 of 55 Help pages. At terminal scroll, Moving in Ruins submits only its trailing blank row, and Item Screen, Battle Tips, Buddies, Status Effects, Enemy Status Effects and Command Thumbnails submit no text handles. Item Screen has 57 staged rows, a maximum of 987 px, and its last nonblank row starts at Y=40. The final content is reachable at intermediate positions.

The native hook replaces the two words at EE `0x290A00` and `0x290A04` with a jump and no-op. The 28-byte helper reads the selected page mode at private offset `+0x17E4`, supplies 16.0 only in mode 4, and returns to `0x290A08`. The other modes keep 21.0. The shared 12 px padding, 222 px viewport, under-11 branch, scrollbar and input/fade code stay native. Exact source/destination words and three surrounding owner fingerprints are validated before composition.

Offline coverage executes the native extent and viewport against all 55 installed page tables, separately bounds every referenced animation frame, and rejects a mutated neighboring instruction. For all 36 pages with at least 11 rows, the revised terminal viewport has the final nonblank row at Y=117–325. The largest final glyph bottom is Y=337 and the deepest terminal animation frame reaches Y=335. Both clear the conservative content boundary at Y=341, derived from the native content base Y=119 and the 222 px viewport. The 19 shorter page results stay identical, including 15 ADV pages that share the one-row translated placeholder and existing animation metadata.

Gameplay should check the down-scroll snap and scrollbar thumb at the end of Item Screen, Moving in Ruins and one long animated page such as Status Effects. Check that the arrows, controller icons, fades and return to Help still work. GPU clipping, timer input cadence and rendered animation color are outside the instruction-level measurements.

## H.A.N.T. Enemy, Anubis

The selected Enemy owner resolves mode 2, category 1, record 0 from call `0x291EC0 → 0x2A9FE0` and consumes the table at file offset `0x5C2410`. The 17 installed nonblank fields use at most 57 bytes including NUL, within the real 64-byte row copy at `0x290694 → 0x39FCC0`. The fixed source indices 5, 7 and 18 retain the native dynamic handling for HP, weak spot and treasure. The original blank and EOF sentinels are present. The shared pool now provides up to 19 handles, while the staging pitch for Enemy remains 21 px.

The native style-1 glyph layout submits static rows through X=420 from X=85. This fits the conservative 336 px usable span previously established for the Help font. The 512 px constructor extent is a wider canvas. The actual Enemy page border and scrollbar position, the result of live HP/weak-spot/treasure generation, and optional unlock/reachability still need a gameplay pass. There is no demonstrated need to rewrite these rows.

## Artwork

The artwork census rereads r67.15k, r67.15o, the pristine PS2 disc, and the candidate. It decodes every historical texture and matches the freshly recovered official PS4 JP and EN assets to each historical manifest entry, then records all 85 decisions and 638 native frame regions by sprite ID, animation frame, UV, dimensions and pivot. It independently verifies all 150 installed BLBRD containers.

| Outcome | Textures |
| --- | ---: |
| Reproduced and installed the recording popup | 1 |
| Retained matching historical ports | 5 |
| Retained newer wheel ports | 4 |
| Retained existing English No Data card | 1 |
| Held with named ownership, layout or protection blocker | 74 |

The earlier 72/5/8 census describes decoded o pixels against pristine and the historical port. It is a separate measurement from these decisions. In particular, 50 portrait cards in groups 54–56 have genuine baked Japanese names. Their individual native atlas/UV mappings are resolved, but the specific gameplay routes that select and draw them are not established. The per-item evidence also protects later Group 4, title, character entry, save and H.A.N.T. changes from broad earlier imports.

### Recording popup

The native H.A.N.T. recording owner loads Group 59 at `0x2929F8 → 0x105FE0` and creates sprite IDs 0–4 at `0x292B48 → 0x107D60`. ID 0 uses frame `0x473B90`, sampling X=0–272, Y=40–208 from `GP059_00.TMX`. The original popup has a Japanese heading and choices within that crop. The historical English render has the heading and both readable choices, with the same border, arrows and circle/cross controls inside the unchanged crop. Native state 6 action branches at `0x292F14` and `0x292F3C` retain their original masks and targets. Neighboring pause/record/saving status strips also use their original sprite and animation records.

The old payload regenerates byte-identically through the existing official importer. The input and output stay 263,744 bytes and the only writes are the palette and image data within the named TMX. The baseline container SHA-256 is `2dd9d977b3bcd4c5cecfa29bbc5902b93b044461156b25c82810a4355527362d`. The installed port is `f0ba2ba39ea16940c46e3a73d3966b41a346448f06a536f04dcd68c99c55ffb3`. A deliberately damaged input branch fails the owner check. Gameplay should test View Data and View Later from two popup entries and check that recording completion and cancel return as expected.

### Emotion Wheel

The installed container is pinned to `d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee`. The installed executable resolves the ordinary paired plaques, all eight forced-mode plaque sets, all completion glows and the remaining Group 1 textures through the same 146 descriptor records and 820 frame geometries as approved. The bounded native mapper runs 13 fixture cases against mapper instructions and dispatch data proved byte-identical to the installed executable. Crop and palette mutations both fail the new gate. An ordinary wheel selection and a forced prompt remain playthrough checks.

## Inherited surface checks

The focused run against the o history inputs discovered 140 tests. It passed
138 and skipped the two standalone historical ISO checks whose original
r67.12 and r67.14t diagnostic inputs were unavailable. The supplied
history paths still exercised the o-installed four-region lock. The release
gate uses the final candidate paths and checks its installed q/t, history and
save owners directly.

| Surface | Offline evidence | Gameplay gap |
| --- | --- | --- |
| Item Details, recipe names and actions | Live glyph quad fixture checks cover all 431 Details records, all 446 official names at the three recipe owners, the accepted bounded panel, real glyph width/word wrap, repeat draws, guard mutations and exact Group 4 bytes. | Open Details repeatedly, cycle recipes and equip/store items. Verify controls, alpha/focus and transitions while changing panels. |
| Inspection | Live fixture tests cover actual six-field object records, wrapper guards, genuine font quads, alignment, shared fades and approved short-string cases. | Inspect long descriptions, alternate object states and actions, and recheck their reveal/fade in game. |
| Tablet and title | Scoped q/t owner locks cover inscriptions, title and startup text/geometry checks, with only the inherited bounded `memory_card_8` wording exception. | Check tablet readability including Western and Anubis, title focus and opening flow in the candidate. |
| Menus and HUD | Native source locks and focused fixture tests cover menu pointer ownership, dungeon action labels, companion AFK and L1 geometry and their protected display owners. | Check multiple companion slots and status states, scrolling/cancel after category changes, and effects around area transitions. |
| History | Two input paths bind the existing four-region lock to the actual installed candidate. The case designed from the approved old-man example is the preserved baseline. | Open the list after multiple conversations, scroll beyond 12 records, return to current conversation and check history across a save reload. |

## Reproduction

Run from the translation worktree with the pinned environment and fresh report destinations.

```sh
PY=local/r67m-integration/venv314/bin/python
"$PY" -m unittest tests.test_r67p_hant_surfaces tests.test_r67p_surface_art -v
"$PY" -m tests.test_r67p_hant_surfaces --iso "$CANDIDATE" --report "$NEW_HELP_REPORT"
"$PY" -m tools.r67p_surface_art --source-only --report "$NEW_BASELINE_ARTWORK_REPORT"
"$PY" -m tools.r67p_surface_art --iso "$CANDIDATE" --report "$NEW_INSTALLED_ARTWORK_REPORT"
```

The per-item report includes palette/payload fingerprints, official source bundle and RGBA fingerprints, exact texture byte ranges and native sampled UVs. Contact sheets and all original or generated game bytes are local evidence.
