# r67.15p cumulative geometry diagnostic

r67.15p is a local PS2 diagnostic composed from exact r67.15o. Gameplay and save compatibility await Pablo’s playthrough. The approved gameplay baseline is r67.15k. The draft branch remains open for gameplay review.

| Artifact | SHA-256 |
| --- | --- |
| `67.15p-cumulative-geometry-diagnostic.iso` | `00a3396b40e3c241b81b7852c49284551eebab7d3280d0aa9c41028454f26379` |
| Installed `SLPM_665.11` | `c6bd4b0bfe359ebcff107f9e23fa65d365567cff36e747b578a06dfb7ed088fa` |

Two independent compositions produced byte-identical ISOs, executables, revised inventories and resource fingerprints. Each complete 2,095,382,528-byte audit found zero unexplained bytes. All 10,656 ROFS records matched. The image changes are bounded to the native append and hook sites, their ISO bookkeeping, and the approved H.A.N.T. popup payload. The build leaves 359,140 bytes in the translation reserve and preserves the inherited heap reservation.

Installed evidence verifies all 52 protected producer files, the q/t and Group 4 owners, the four locked history regions and 15 save descriptors. The serial is `SLPM-66511` and the save namespace is `BISLPM-66511Save`. Startup checks passed 154/155 raw and 155/155 with the single inherited `memory_card_8` wording exception.

The baseline suite passed 1,001 of 1,008 tests. The installed candidate suite passed 1,028 of 1,035, with zero failures or errors. Both runs skipped the same seven archived checks because their private graphics inputs or standalone r67.12, r67.14q/t/u/z and r67.15a images or reports were unavailable. The candidate ELF and ISO environment paths exercised the four-region history lock directly.

## Content and owners

- **Scene captions.** The ADV brace dispatcher polls `0x251380`, which runs the original parser, normalizer and history handoff at `0x251260`. The registered callback at `0x250C90` owns construction and timing. Its text and backing calls are redirected at `0x250D6C` and `0x250E00`. Style-0 glyphs and fullwidth spaces occupy 16-pixel horizontal cells. Complete eligible captions use one centered row or two rows in a centered block. The renderer replaces a display-space with the native newline control, or inserts the control between whole glyphs if no suitable word boundary exists. The original script, history pointer, stage transitions, fade, wait, teardown and Japanese branch are preserved. Native replay scanned every MTX pointer region. It found 202 official English captions in 44 files and 25 stock captions. The baseline spilled below Y=447 in 110 examples. Candidate English face and shadow together stayed within X=24–488 and Y=17–53. All original Japanese draws matched the baseline, including backing.
- **Speaker headers.** The original bracket parser and both actor/alias lookups remain in their installed r67.15o form. The owner-local hook at `0x250010` operates on the completed font task. The body anchors and display identity remain the same. The candidate replay renders all 218 distinct raw header payloads from 34,334 bracketed official spans and 7,402 fixed speaker projections. The three overflowing labels fit the viewport with complete glyph streams. Short headers retain their exact geometry. The three outstanding routes reach the actual speaker parser after caption close. MS07_03 key 39661 completes a 30-frame wait and submits effect arguments 9 and 100 before dispatch. MS08_03 keys 19170 and 19278 complete their 30-frame waits. Both revisions preserve the offsets, actor and alias identity, and displayed glyph payload.
- **Choices.** The guarded renderer still owns its 1,079 English entries. The stock constructor regains vertical orientation through the existing bridge at `0x251594`. The style-2 fallback fitter runs at the stock setter boundary. The four blank no-op labels and every installed KSF byte remain exact. The stock-orientation word checked by historical startup evidence remains intact. Native replay covered all 23 stock records including 53 stock labels and one all-blank record, plus four dynamic groups with ordinary, maximum-width, mixed-space and malformed saved names. The 22 observed stock overlaps were eliminated. Representative stock and maximum-name fallback records ran through the native reveal, selection movement, cancel, reopen, confirm and branch lookup. The separate lifecycle log records per-frame alpha, selected slots and branch IDs.
- **Primary dialogue.** The live row constructor `0x24F660` creates three style-2 font objects at X=20, Y=300/316/332. Their 24-pixel advance differs from the style-1 secondary fragment owner’s 12-pixel advance. The long body fixture reached X=932 at unit scale, and its reveal count outgrew the stock 16 child-handle slots. The `0x24EA20` setter fits overflow using converted native nodes, space advances and a 488-pixel budget. The `0x24EA58` call gives its private animator arrays 56 entries, retaining stock callbacks and timing. Native tests cover three rows, mixed Japanese and English, ordinary name expansion, long rows, animated child allocation and a negative restoration of the old allocator. The census classifies 63,665 possible body spans by native owner. It records 2,097 name-bearing rows and 7,948 bracket-plus-three-row lexical runs. At unit scale, the width envelope flags 36,553 body spans with the ordinary editor-length names and 37,534 with the conservative legacy-name envelope. Script-route reachability, a speaker-selected alias’s actual value and the appearance of mixed lines remain gameplay checks.
- **START history.** The four approved regions are byte-exact. An offline replay populated and displayed chronological windows from six and eighteen records. In the eighteen-record case, pressing the older-page input reaches `0x25470C`. That path inserts record 5 at (78, 20), replacing record 11 in the middle of the window. The misplaced row persists through 25 native callbacks in both an all-body fixture and a six-conversation fixture with speaker brackets and mixed Japanese/English body rows. The initial 12-row path uses a separate chronology mapping and the correct vertical axis. This remaining defect requires scrolling-window, row ownership and voice-selection evidence before changing the history navigator. The game’s full history path and legacy name inputs need a dedicated follow-up.
- **H.A.N.T. Help.** Native mode 4 now uses its measured 16-pixel pitch for the scroll extent. The 12/55 pages with terminal clipping in r67.15o passed the candidate probe. The Anubis Enemy body fits the conservative bounds and uses its existing layout. See [UI and artwork evidence](R67P_SURFACES.md).
- **Artwork.** The PS4-derived H.A.N.T. recording popup is the single promoted historical port. The PS2 display owner reads the exact crop from `BLBRD/B_GP059.BIN`; only its existing palette and index bytes are replaced. Group 4 and the exact wheel payload are preserved. The 85 dispositions include individual atlas crops and concrete holds. Wheel evidence covers the normal and forced mode selectors, UVs and native geometry.

The original official census is retained in full. The installed inventory verifies 98,201 official MTX entries, 1,079 guarded English choices and four blank no-ops. The 2,203 unresolved official source-array entries remain explicit. The 7,402 fixed speaker occurrences are counted separately. Phase 2 has not started.

## Evidence and reproduction

The source and evidence archive contains the read-only baseline probes, their byte-for-byte comparison to the earlier audit, the complete installed-disc audit, all resource fingerprints, the rebound inventory, the finished-image geometry reports and the full test logs. Run the archived baseline probes from the repository root using `PYTHONPATH=$PWD` and an isolated copy of their directory.

From the repository root with the owned inputs and pinned environment, replace the paths below as needed. Every build needs a new directory. Place a copy of the baseline `header_draws.json` from the evidence package at `local/r67p-speaker-evidence/baseline-header-draws.json` for the full suite.

```sh
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
export PYTHONDONTWRITEBYTECODE=1
PY=local/r67m-integration/venv314/bin/python
STARTUP_GRAPHICS=/path/to/accepted/startup-graphics

"$PY" -m tools.r67p_release --graphics "$STARTUP_GRAPHICS" --output-dir local/r67p-repro-a
"$PY" -m tools.r67p_release --graphics "$STARTUP_GRAPHICS" --output-dir local/r67p-repro-b
shasum -a 256 local/r67p-repro-{a,b}/{stage.iso,installed.elf}
cmp local/r67p-repro-a/stage.iso local/r67p-repro-b/stage.iso
cmp local/r67p-repro-a/installed.elf local/r67p-repro-b/installed.elf

export R67P_FINAL_ISO="$PWD/local/r67p-repro-a/stage.iso"
export R67P_FINAL_ELF="$PWD/local/r67p-repro-a/installed.elf"
export R67_HISTORY_LOCK_ISO="$R67P_FINAL_ISO"
export R67_HISTORY_LOCK_ELF="$R67P_FINAL_ELF"
export R67P_CHOICE_EVIDENCE="$PWD/local/r67p-choice-native-geometry.json"
export R67P_CAPTION_EVIDENCE="$PWD/local/r67p-caption-draws.json"
export R67P_HISTORY_EVIDENCE="$PWD/local/r67p-history-navigation.json"
export R67P_HEADER_INVENTORY_EVIDENCE="$PWD/local/r67p-speaker-inventory-draws.json"
"$PY" -m unittest discover -s tests -v
"$PY" -m tests.r67p_caption_dispatch --iso "$R67P_FINAL_ISO" \
  --baseline-probe /path/to/evidence/baseline/header_draws.json --report local/r67p-speaker-after-caption.json
"$PY" -m tests.test_r67p_hant_surfaces --iso "$R67P_FINAL_ISO" --report local/r67p-help-final.json
"$PY" -m tools.r67p_dialogue_screen "$R67P_FINAL_ISO" local/r67p-repro-a/inventory local/r67p-dialogue-screen.json
"$PY" -m tools.r67p_surface_art --iso "$R67P_FINAL_ISO" --report local/r67p-artwork-final.json
PYTHONPATH="$PWD" "$PY" /path/to/evidence/candidate/choice-lifecycle.py "$R67P_FINAL_ISO" local/r67p-choice-lifecycle.json
PYTHONPATH="$PWD" "$PY" /path/to/evidence/candidate/history-window.py "$R67P_FINAL_ISO" local/r67p-history-window.json
```

The release tool rereads the exact r67.15o ISO and installed ELF, validates exact byte preimages, composes the native changes within the existing translation segment and regenerates the popup from its pinned PS4 sources. A separate expected-write audit derives the allowed writes from the verified source and replacement inputs. The candidate must pass all 10,656 ROFS lookups, per-resource hashes and extent validation. The process rebinds the preserved ADV census by rereading the installed payloads, guarded choice ranges, fixed speakers and unresolved Japanese spans from the stage.

## Playthrough checklist

1. Boot the ISO in PCSX2. Confirm the serial, open a copied save and verify that the loaded route matches the expected starting position. Use a cold boot to exercise the candidate ELF.
2. On a long English scene caption, check both shadowed rows, backing, fades and the next scene’s first dialogue. Also observe an original Japanese caption.
3. Check a 31+ cell header and the KWLNSCR Act caption/header when its route appears. Check a long three-row body while it reveals and with default and custom names.
4. Compare an ordinary English choice and an FD00 stock choice. Check highlight movement, cancel/reopen, confirm and the selected branch. If a copied legacy name save is available, check all four guarded name-bearing groups.
5. Open START history after several conversations and scroll past twelve records. Check the known older-window defect. In H.A.N.T. Help, scroll to the bottom of Item Screen or Battle Tips, check Anubis, and trigger the recording popup when a record is added.
6. Open the wheel in normal and forced modes. Save and reload using a copied card and compare progression.
