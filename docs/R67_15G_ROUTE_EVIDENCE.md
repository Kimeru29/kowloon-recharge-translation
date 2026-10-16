# r67.15g route payload evidence

Status: static, read-only finished-image evidence. This is not a gameplay,
runtime, or closed-world route-completion approval.

## Reproduction

From the repository root, run:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m tools.r67_15g_route_audit local/r67-candidates/67.15f-item-panel-layout.iso
```

The command prints a JSON report and opens both ISO images read-only. The
Python interface is `audit(iso_path: Path) -> dict`. It locates nested
`DATA.CVM` at `outer_extent * 2048 + 0x1800`, indexes the embedded ISO, then
compares the named ADV records in the finished image. It does not create or
modify an ISO.

Inputs are pinned by source/map/manifest SHA-256 in
`tools/r67_15g_route_audit.py`:

- Pristine PS2 image: `/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`.
- Recovered PS4 ADV assets and English maps:
  `/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/Media/StreamingAssets/data/ADV`.
- Approved historical choice compaction:
  `translations/DG00_00.vertical-slice.json`.

Each exact-tier MTX is regenerated with `import_exact_mtx`; choice fields use
`import_exact_ksf`, with only the two hash-pinned, historically accepted
`DG00_00.KSF` compactions applied afterward. The final output bytes—not a
lexical scan—must match the installed finished-image records exactly. Missing
or altered sources, maps, approval manifest, or scenario instructions fail
closed.

## Finished-image results

The audited image is the existing r67.15f candidate. `MTX entries` below means
official import-map entries, not dialogue lines or route completion.

| Finished-image record | Official/source evidence | Installed result |
|---|---|---|
| `ADV/DG/DG00_00.MTX` | 195 import entries; pristine source `ed15d040…9753819b`; output `eba4a22a…c5cfd6e` | Exact official regeneration |
| `ADV/DG/DG00_01.MTX` | 34 import entries; pristine source `5e91a8ff…326e54a7c`; output `eb5b6a17…5825b04b` | Exact official regeneration |
| `ADV/MS/MS00_02.MTX` | 593 import entries; pristine source `d1ff7c51…ae68ea654`; output `e53e5b3e…1a4ac095` | Exact official regeneration |
| `ADV/DG/DG00_02.MTX` | 32 bytes; SHA-256 `381b9c97…0d87a54` | Unchanged control-only script |
| `ADV/MS/MS00_00.MTX` | 28 bytes; SHA-256 `317426cc…1ea01d80` | Unchanged control-only script |
| `ADV/MS/MS00_01.MTX` | PS2 source/installed: 104 bytes, SHA-256 `4d48327f…941ce61d` | Unchanged PS2 control script |

`MS00_02.MTX` includes the military attack after Salah’s escape and also later
hospital content. Its 593 mapped entries are the whole imported asset count;
they are not attributed only to the ambush. The separate PS4 `MS00_01.MTX` is
1,432 bytes with 43 map entries and is structurally different from the 104-byte
PS2 file. The audit records this platform difference and deliberately neither
imports the PS4-only asset nor labels its 43 entries as missing PS2 dialogue.
`MS00_00.MTX` and `MS00_01.MTX` KSF files are each 2,322 bytes and remain
unchanged control scripts.

| Choice script | Official entries | Audit |
|---|---:|---|
| `ADV/DG/DG00_00.KSF` | 5 | 3 exact fits; 2 previously approved compactions at byte offsets 9339 and 11689 to “Pick up device on the ground”; 0 unresolved; final SHA-256 `db445fb…b9bd6179ecd` |
| `ADV/MS/MS00_02.KSF` | 10 | 10 exact fits; 0 compactions; 0 unresolved; final SHA-256 `1f5deba5…e01192e` |

The accepted compactions are regenerated from the pinned official map and
manifest. They are not reported as new unresolved choices. The audit also
confirms unchanged `DG00_01.KSF`, `DG00_02.KSF`, `MS00_00.KSF`, and
`MS00_01.KSF` controls.

## Route context and capture checklist

The linked Japanese walkthrough is used only as background route context, not
as a translation source: [Heracleion Shrine walkthrough](https://spwiki.net/kowloon/wikis/35.html).
Its listed stops include the Shrine/Salah introduction, Chamber of Lions,
Gate of Anubis, storeroom, and Anubis Altar. It does not establish the later
military-attack endpoint or prove in-game reachability.

Runtime endpoint captures remain pending. When authorized, record each listed
screen with a full-screen image, scene/room label, and the transition that
entered it; do not infer an unobserved screen from asset hashes:

1. Heracleion Shrine route start, Salah encounter, and escape transition.
2. Initial H.A.N.T. setup and route handoff.
3. Chamber of Lions: pedestal/door transition, encounter, and exit.
4. Gate of Anubis: raised stepping stone, wire-gun crossing, Snake Staff
   lever, and east inscription door.
5. Optional Soul Well branch, captured separately from mandatory-route proof.
6. Storeroom: nitric-acid and hydrochloric-acid pickups, aqua-regia synthesis,
   and golden-chain door.
7. Anubis Altar: ladder/encounter, throne inscription, and boss transition.
8. Post-Salah-escape military attack, including the wheelchair man and
   soldiers; stop before subsequent hospital content.

No emulator was launched or controlled for this evidence. A finished-image
payload match proves the bounded bytes and their official-source provenance;
it does not prove that every optional/conditional surface is reachable, that
every other dependency is translated, that the scenes render correctly, or
that a player can complete the route. A lexical-zero result is not used to
assert closed-world reachability.

## Regression evidence

Focused command:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m unittest tests.test_r67_15g_route_audit tests.test_r67_15g_help_layout -q
```

The route-audit tests cover exact installed output, import/choice counts,
approved offsets, altered installed script rejection, changed scenario-map
rejection, corrupt choice-map rejection, and missing-map rejection. The Help
tests also confirm that its permitted ELF ranges use half-open
`(start, end)` spans and exclude shared segment-size metadata `[0x64, 0x68)`.
The parent owns integrated full-suite and release verification.
