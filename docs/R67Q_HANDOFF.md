# r67.15q cumulative PS2 diagnostic

The START history viewer now shows the twelve consecutive records belonging to the selected window. For an 18-record log numbered 0–17, opening history shows 6–17. Pressing older shows 5–16. Repeated presses stop at 0–11, and scrolling back restores the original text and coordinates. Pablo owns the in-game and save-compatibility checks.

| Artifact | SHA-256 |
|---|---|
| r67.15q ISO | `77cf9c15c229dd434a9d54f60e4eb0ad4e868d6ffb4dfac988e762e4e9b3fdae` |
| Installed `SLPM_665.11` | `3de1ff79df07819ba6a318d7955b52b36a70f852d6471ce3f2832d634442a644` |
| Immediate r67.15p input ISO | `00a3396b40e3c241b81b7852c49284551eebab7d3280d0aa9c41028454f26379` |

## Failure and fix

The p renderer constructed the first screen in chronological order. Its older-input routine still recycled a single handle on the original Japanese horizontal axis. In the 18-record replay, it put record 5 at (78, 20), displaced record 11 and left record 17 visible.

Two instructions at history callback VA `0x253DB4` and `0x253DB8` now route navigation through a history-specific helper. For a log longer than twelve records, it clamps the distance from the newest screen to the retained 255-record ring. Single-step input moves one record. Fast input moves one twelve-record screen. On a changed window, it releases the old font tasks, clears each slot's highlight state, and constructs rows from the selected ring entries using a guarded copy of the approved row loop. The scrollbar uses the absolute window position. Short logs retain the original handler.

## Installed-image evidence

- The native callback replay checks every visible record, X alignment and increasing Y positions across repeated older and newer presses. The mixed Japanese/English and all-body fixtures return to their initial rows after 25 idle callbacks. The focused tests cover ring rollover after 258 writes and page navigation on a 40-record log. Reverting the age subtraction in a copy of the installed ELF reproduces an incorrect first older window.
- Native tagged speaker headers keep their original X position of 59 in the fixture, body rows keep X 20, and the next row begins 25 pixels below a header or 37 below a body. The tagged fixture returns to exactly the same text and coordinates as p.
- The game identifies the record highlight as an affection increase. The producer at `0x22CE28` writes a positive amount to the latest record via `0x253290` and plays a sound effect. The history constructor reads that field on a tagged row to configure its flash. Ordinary body rows explicitly clear the flash flag. The native color dispatcher targets records 5 and 8 on the older screen, then 8 and 17 on return. Its 28 recorded calls all target live handles. In the 18-record fixture the scrollbar moves from X 26 to 50 on the first older press and back to 26 on newer, with its length held at 319.
- Two independent builds produced byte-identical discs and installed executables. Whole-disc comparisons covered all 2,095,382,528 bytes against both p and o. There are 777 differing bytes from p, 265,459 from o, and zero unexplained bytes in either comparison.
- All 10,656 embedded resource fingerprints and extents match p. The inventory rechecked 99,284 installed ranges and records the final ISO and ELF hashes. It retains 98,201 official MTX entries, 1,079 guarded choices, four blank no-ops, 2,203 unresolved correspondences and 7,402 separately counted fixed speaker occurrences. The p artwork dispositions continue to apply. The wheel, protected Group 4, H.A.N.T. popup and 52 protected producer sources passed their checks.
- The four approved history regions, approved q/t owners, 15 native save descriptors, serial `SLPM-66511` and namespace `BISLPM-66511Save` passed their static checks. The translation segment has 357,952 bytes of reserve. Startup passed 154 of 155 raw checks and 155 of 155 scoped checks with the inherited `memory_card_8` wording exception.
- The full installed-image run discovered 1,043 tests. It passed 1,036 and skipped seven historical checks for unavailable private graphics inputs or archived ISO/report fixtures. The history-lock test checked both the final ELF and the ELF embedded in the final ISO. The evidence archive includes the full log and separate native replays.

## Reproduction

Run from the translation worktree with the pinned local inputs and Python 3.14.7 environment. The evidence archive contains the additional Python probes used below. Set `EVIDENCE` to its extracted `evidence` directory and `STARTUP_GRAPHICS` to the accepted startup-graphics directory.

```sh
export DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD"
PY=local/r67m-integration/venv314/bin/python
"$PY" -m tools.r67q_release --graphics "$STARTUP_GRAPHICS" --output-dir local/r67q-repro-a
"$PY" -m tools.r67q_release --graphics "$STARTUP_GRAPHICS" --output-dir local/r67q-repro-b
cmp local/r67q-repro-a/stage.iso local/r67q-repro-b/stage.iso
cmp local/r67q-repro-a/installed.elf local/r67q-repro-b/installed.elf
export R67Q_FINAL_ISO="$PWD/local/r67q-repro-a/stage.iso"
export R67Q_FINAL_ELF="$PWD/local/r67q-repro-a/installed.elf"
export R67P_FINAL_ELF="$R67Q_FINAL_ELF" R67P_FINAL_ISO="$R67Q_FINAL_ISO"
export R67_HISTORY_LOCK_ELF="$R67Q_FINAL_ELF" R67_HISTORY_LOCK_ISO="$R67Q_FINAL_ISO"
"$PY" -m unittest discover -s tests -v
"$PY" "$EVIDENCE/history-probe.py" "$R67Q_FINAL_ISO" local/r67q-repro-a/windows.json
"$PY" "$EVIDENCE/verify-window.py" local/r67q-repro-a/windows.json
"$PY" "$EVIDENCE/row-index-mutation.py" "$R67Q_FINAL_ELF"
"$PY" "$EVIDENCE/history-color-scrollbar-probe.py" "$R67Q_FINAL_ELF" local/r67q-repro-a/color.json
"$PY" "$EVIDENCE/disc-preservation.py" "$R67Q_FINAL_ISO" local/r67q-repro-a/o-audit.json
```

## Playthrough checklist

1. After more than twelve history entries, open START. Move one row older and newer across a speaker/body boundary. Check the names, line order, highlight, spacing and scrollbar.
2. Use fast paging in both directions. Check that adjacent pages have no skipped entries and that further input at either end keeps the same rows.
3. Check a scene with voiced dialogue, listen for the expected audio, then close and reopen history. Confirm ordinary dialogue resumes correctly and check the window again after a normal save reload.

The offline harness executes the installed history code with modeled platform services. Audio playback, PCSX2 frame timing, controller feel and live save compatibility await Pablo's playthrough. The draft PR remains open for his decision.
