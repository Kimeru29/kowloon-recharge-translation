# FN02_31, FD00 and ADV player-name substitution

## Owners and selection

Static analysis of the original PS2 executable, approved k executable, PS4 IL2CPP user assembly and its matching v24 global metadata. All file hashes, selected native code section hashes, per-MTX/KSF/DC hashes, every FN key and value digest, and every FD00 DC key, containing pointer region and candidate PS2 region are in `dynamic.json`. All five disassembled PS2 ranges are identical in pristine and k. No emulator was run.

PS2 EE 0x215580 handles scenario loads. At 0x21567c the signed script-kind selects VA 0x6714d0, with FD at index 1 and FN at index 2. At 0x215690..0x2156c8 it formats `adv/%s%02d_%02d.MTX` and the paired KSF using the two actual caller parameters. At 0x2156dc it requests the MTX; 0x215720 loads the MTX base into work +0x3114. The current chapter at +0x3150 indexes a little-endian 16-bit quarter-offset, `MTX + 4*u16[chapter]`, at 0x215820..0x215840. This CPU path does not load a dictionary. It proves selection and ownership for a supplied script-kind, id, time and chapter; individual playthrough reachability remains unobserved.

On PS4 the corresponding material is in the plain x86-64 text segment of Il2CppUserAssemblies.prx. Text RVAs below convert to physical module file offsets by adding 0x1f610. Metadata method definitions are 52 bytes, with `methodIndex` at +20. The 40,788-entry method pointer registration at PRX file 0x3fce648 points to VA 0x3f309c0. The metadata registration generic specs, generic function index and metadata usage pointers permit identifying generic calls and literal strings independently of their proximity. The local readers can disassemble both platforms and print the metadata-referenced string literals and method names.

`Y_AdvScenarioRead` (RVA 0x189d840) uses the concrete path format strings at 0x189e19f, 0x189e2b3, 0x189e66e, 0x189e805 and 0x189e94c for the MTX, KSF and language-specific dictionaries. It reads MTX bytes, resolves the chapter through `GetMtxTopPtr` at 0x189ec01, then uses `ReadAllText`, `JsonUtility.FromJson` and `JsonDictionary.ToDictionary` for the language files. The ordinary ADV message analysis at 0x1428080 checks dictionary keys then reads them (e.g. 0x142b543, 0x142b5a0), with a diagnostic explicitly naming MTXForeignLangDic. Ruby processing also calls ContainsKey/get_Item at 0x142fac7/0x142fc59. The loader and lookup do not establish per-key alternative scenario ownership.

## FN02_31

Both platforms' file is the same 604-byte Japanese sample, with 11 nonzero entry points at 24,100,128,176,216,284,352,396,448,520,556. English DC has 1,294 array entries, 1,150 unique keys, 961 entries with keys outside the file and 22 distinct values. Positions 0..17 reproduce the 18 opening English sample lines of FD00_00 by exact value; positions 18..1282 form 115 blocks of 11 variants; positions 1283..1293 are the 11 speaker labels. Key 33 repeats already at positions 0 and 18.

On the actual PS4 specialization, `JsonDictionary<int,string>.OnAfterDeserialize` RVA 0x314f150 iterates to Min(keys.Count,values.Count), constructs a new dictionary and calls class RGCTX slot 12 at 0x314f3bd for each key/value. Type-definition 4841 has RGCTX start 1419 and count 13. Slot 12 (generic spec 26309) resolves to `Dictionary.Add`. Standard duplicate keys fail in this operation. ToDictionary 0x314ee90 returns its backing field. A first-wins, last-wins or multiplexed-by-event interpretation cannot be justified here. Whether this specific file is requested in gameplay and how an outer Unity deserializer reports a callback exception remain unobserved. 605 PS4 MTX files have the exact sample bytes; 604 parseable matching dictionaries divide into **11 different** English profiles. None supplies a unique whole-file substitute. The source JSON array cannot be installed literally.

## FD00

PS2 FD00_00..23 and FD00_29 contain distinct physical script bodies, many with character/voice/stage controls and chapter structures absent from their same-name PS4 sample. None of these 25 PS2 files has a complete byte-identical counterpart in the recovered two-level PS4 ADV MTX collection. None of their pointer regions equals the complete region owning a same-name PS4 DC key. Examples include FD00_01 with `vo40002` and a girls' dormitory scene, and FD00_06 with `ch00602` and Rika. Same-name DC describes Minakami's sample. The index records candidate complete-subregion matches against *all* PS4 MTX files, including small common control fragments. Such a hit does not by itself establish a translated line for its caller. FD00_24..28 and 30 already match the sample exactly, and FD00_31 is the existing bounded structural import. Further recovery requires scene/voice/command-context ownership for an alternate official text or direct alternate script resources. Platform exclusivity is undetermined.

## Name controls

PS4 `Y_AdvOriginalNameChangeProc_Localize` RVA 0x1434e40 allocates six 101-unit rows. The English marker table is initialized at 0x145dfb0..0x145e13b in the order (pmyh),(pnyh),(pm1),(pn1),(pm),(pn). At 0x14351e1/0x1435272 it reads phonetic names. At 0x1435300 and 0x1435420 it calls GetPlayerName, and 0x1435390 and 0x14354b0 call GetPlayer1StName. In all four cases it uses full-copy routine 0x1432140. Each matching marker is replaced with that row at 0x1435850. `GetCharaNameProc` at 0x143232d selects (px) for localized mode; 0x14354f8..0x14356ab resolves it through current speaker context, Y_CheckMyName, St_GetCallPcName and String.Replace.

PS2 script dispatcher at EE 0x2158c8..0x215980 routes an initial p to the ordinary dialogue driver, which calls the text scanner at 0x24e6f0. The latter detects p-controls anywhere on native text lines (0x24d154..0x24d2bc) and invokes the replacement routine 0x24d5a0 on line/final flush at 0x24d384 and 0x24d4a0. There is no per-asset macro whitelist. The marker-pointer array at 0x677240 contains pmyh,pnyh,pm1,pn1,pm,pn. The table at 0x785b90 dispatches these six variants then px; lengths are at 0x785b88. Full pm and pn are filled through 0x12f5f0 (0x7c4bc0) and 0x12f5e0 (0x7c4ba0) with string copies at 0x24d6d8/0x24d6f0. The four preceding slots copy at most two bytes: a single native glyph. The px route at 0x24d704..0x24d7ec reads the ADV work's context bytes +0x31b9/+0x31ba, uses 0x2523c0 and 0x12f600, replaces the two-byte opcode and appends the original tail.

| Official English | PS2 ordinary ADV representation | Reason |
|---|---|---|
| (px) | px | Speaker-selected form of address on each platform |
| (pm1) | pm | Full player family-name field in localized English |
| (pn1) | pn | Full player given-name field in localized English |
| (pmyh), (pnyh) | Deferred | Remaster copies the complete phonetic field; PS2's spellings copy one glyph. The accepted English name editor also skips the reading phase. |

The official English can move a name across DC groups in a page. For DG06_00 the old pm is consumed by 195..207 and re-emitted in the English group at 208..237. In FD01_23 px moves from 270..284 to 285..301. In MS07_01 pm + pn move from 14583..14591 into English at 14545..14569 in English name order. A full, exact historical replay can preserve such movement. For a partial overlay, verify ownership of any retained source names around the entire affected page. All claims are static. A custom-name playthrough remains necessary for displayed spelling, fit and actual speaker-selection acceptance.

## Reproduction

Run `PYTHONPATH=.:local/r67n-research local/r67m-integration/venv314/bin/python local/r67n-research/dynamic_assets.py` at the repository root. Use `dynamic_disasm.py 0x24d5a0 240` for EE instructions and `dynamic_ps4.py 0x1434e40 0x14358e0` for the localized routine. Import `dynamic_ps4.trace(start,end)` to resolve metadata operands. Exact input hashes are recorded in the JSON.
