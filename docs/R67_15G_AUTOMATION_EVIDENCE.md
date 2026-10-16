# r67.15g — evidence for a later automated translation pass

This is a record of observed ownership and verification requirements, not a claim of whole-game translation readiness. See the component reports and final release report for actual completion status.

## Distinct text owners must stay distinct

| Surface | Proven entry point or data owner | Automation rule |
| --- | --- | --- |
| Item name | Getter EE `0x134AB0`; primary pointer table file `0x3912B4` | A translated name is not evidence that its description is translated. Preserve accepted 15f title metrics. |
| SELECT item Details | Getter EE `0x134B80`; primary base VA `0x49BEF4`, alternate base VA `0x49CB00`; caller EE `0x115148` | Validate real catalogue IDs and the sentinel/alternate branches; do not treat an instruction's nominal array limit as a count of valid records. |
| Details paragraph | Text construction at EE `0x11518C`, background group4/resource0xB, handle instance `+0x190` | Measure paragraph geometry at this consumer. Do not shrink a shared font or mutate recipe rows to fix this panel. |
| H.A.N.T. Help | Separate text-table and icon-metadata descriptors per page | Fit complete rendered rectangles, not just string length or one-row placeholders. Keep icon meaning attached to its instruction when reflow moves text. |
| Tablet inscription | Six-pointer object record; title, description, body and reading are distinct fields | Native ornament glyphs and leading spaces can look like punctuation defects. Classify them before changing the text. Preserve puzzle semantics. |
| Altar of Anubis room | File `0x5CD794` -> original source `0x5CCDC0` | A translated glossary entry does not establish a translated room label. |
| Anubis battle name | File `0x594E78` -> original source `0x594B08` | Battle name and optional Enemy encyclopaedia page are independent owners. |

## Official text provenance

Native labels and paragraphs must resolve against the owned `English.bytes` corpus, SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`. Scenario script text uses the matching PS4 ADV DC maps and original script bytes. These are different provenance paths.

The 9mm Details witness demonstrates another distinction: the native description is one C string containing four `＠改行` fragments, while the official corpus supplies individual fragment keys. Matching only the whole paragraph would incorrectly classify a translated source as unavailable. Conversely, joining fragments must retain their order and complete meaning; a unique first-line match is not proof for the rest of a paragraph.

Temporary extracted directories may exist while their files are absent. Check actual files and hashes, not directory names. In this run the restored `English.bytes` exists in `/tmp/kowloon-ps4-recovered`, but complete ADV originals/maps reside under the previously verified extractor's `pkg-extract-fixed-read/uroot/Media/StreamingAssets/data/ADV`. Missing sources must fail closed rather than silently switching to authored wording.

## Route evidence versus whole-file counts

The currently installed `MS00_02.MTX` contains the military ambush and subsequent hospital material. Its 593 official map entries are a whole-file count, not 593 ambush dialogue lines. Existing English after the requested endpoint remains preserved; it is not newly added scope.

`MS00_01.MTX` illustrates a platform difference: the original PS2 file is 104 bytes of controls, while the remaster file is 1,432 bytes with 43 localization-map entries. Those 43 entries cannot simply be copied or counted as missing PS2 dialogue. The original PS2 control file remains the authority for its own flow.

The walkthrough at <https://spwiki.net/kowloon/wikis/35.html> is supporting route evidence only: it places the storeroom acid puzzle before the Altar of Anubis and boss. It is not an English translation source or proof of all optional state-dependent screens.

## Tests that are necessary but insufficient alone

- A lexical Japanese scan can find remaining literal text, but zero matches do not prove every native owner or texture is translated.
- Row-cell limits must be paired with actual glyph advance, page pitch, sprite bounds and scroll limits.
- Modelled collision-free rectangles do not constitute a screenshot from the game.
- Immutable accepted manifests remain historical truth. A new scoped exception must name the exact authorized owner and reconstruct only that owner's old words in memory; never rewrite the old expected hash to make a check pass.
- Changed-byte classification must compare the complete finished disc, including unchanged assets and both endian copies of ISO size metadata. A deterministic ELF alone is not an audited ISO.
- Save identifiers and descriptor windows are static gates. They do not establish actual cross-release save/reload compatibility.

## Screenshot acceptance checklist for this milestone

Use the new versioned ISO only after its final artifact and hash are reported. The user operates PCSX2; this checklist does not authorize automated input or changes to cards/settings/savestates.

1. Western Anubis tablet: no colon-like quotation ornaments; readable, balanced rows; other inscriptions and Lion Statue presentation unchanged.
2. SELECT Details: 9mm Luger, long weapon/equipment descriptions, food/medicine, acids, synthesis ingredients and key items. Confirm full English, readable text, no spill into the first recipe row, no name/stat regressions, and no stale description when changing selection or closing/reopening Details.
3. Item Synthesis Help: top, both item steps, warning and guide instruction, including the bottom of the page. Icons must retain the correct PS2 meaning and remain beside the intended explanation.
4. Save & Load Help: warning symbol must not cover prose; first and last rows must remain reachable.
5. Wire Gun Controls: all steps, button icons and diagrams; capture this page explicitly because supplied image 5 was a duplicate of Save & Load.
6. Jumping: radar/landing diagrams, warnings and final range explanation; no text/diagram intersection across scroll positions.
7. Continue through storeroom, Gold Chains, Altar of Anubis, boss, exit passage and the military ambush. Check interaction variants, combat labels, treasure acquisition and choices, not only mandatory dialogue.
8. Check optional Enemy entries that become available on this route and any other reachable screen still marked unresolved in the component inventory.
9. In a separately authorized disposable-card test, save normally, cold-boot, reload and compare state. Never use or overwrite the original card as a test artifact.

Any missing correspondence, unvisited state or incomplete component must remain visible in the final report. It is not converted into a pass by this checklist.
