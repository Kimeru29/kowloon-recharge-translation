# Runtime investigation from Pablo's new slot-2 save (2026-10-09)

## Isolated reproducibility

- Source: the existing user's original PCSX2 savestate `SLPM-66511 (8E083A26).02.p2s`, timestamp 2026-10-09 21:36:52, copied without modification into the private `local/pcsx2-67.06-isolated` profile.
- Source and copied SHA-256: `15896a89c0cd2cb54af42cc15a5621fa9517217610a6ea22e05c8e34a73edfb4`. User's original memory cards, savestates, running PCSX2 process and 8BitDo mapping were not changed.
- Replayed `local/r67-candidates/67.07-containment.iso` (not an approved release) through the initial `Heracleion` scene. Moving forward reproduces the opening ADV dialogue `[Old man's voice]` / `Hey; over here.` in correctly horizontal text. START reproduces two vertical single-character columns on the black history screen; the content is good but presentation is not.
- Advancing with Circle reaches the first H.A.N.T. Function Help onboarding screen. D-pad down successfully scrolls. The isolated temporary keyboard bindings used in the investigation did not dismiss that screen with Circle/Cross/Triangle/Square/Start/Select or L1/R1, so the later Chamber of Lions story-comment and item-popup defects have **not yet** been reproduced from this save. Do not infer a game freeze from this alone: user has navigated beyond it on a physical controller.

## Exact executable ownership discoveries

- `y_AdvLog.c` at original ELF file `0x5780D0`, runtime string VA `0x678050`: live source references at `0x255DB0` and `0x256B7C` (MIPS `lui 0x68` and signed `addiu`).
- `ADV LOG PROC` at file `0x5780E0`, VA `0x678060`, MIPS direct source reference `0x255DD0`.
- `MesLineX` at file `0x5780F0`, VA `0x678070`, is referenced by routine `0x25628C`; `MesLogNum` at file `0x578130`, VA `0x6780B0`, around `0x25628C-0x2562D0`. These references are consistent with ADV log navigation/layout debugging but are **not yet proof** of glyph ownership.
- The earlier 72-byte history helper, called at MIPS `0x259CD4` (ELF file `0x159D54`), sits at runtime VA `0x962FFC`. Its X override instruction is at staged ELF offset `0x863254`: `lui t0,0x41A0` (20.0f). The previous hook remains present in 67.07.

## Negative tests (do not repeat as candidate fixes)

- Changing the upstream `lui v0,0x421C` at VA `0x259C60` (39.0f) to 200.0f in an ISO diagnostic did **not** alter the displayed history columns. This test is **inconclusive** on ownership because the existing history helper overwrites F12 after that instruction.
- Changing the actual previous helper's X override to 230.0f (one verified word at translated ELF offset `0x863254`) in a second, isolated diagnostic ISO still left the START-history columns unmoved and vertical. This argues that the helper does **not** control the visible column origin, despite being callable in other contexts. No diagnostic ISO was published as a release.
- An attempted direct MIPS code write through isolated PCSX2's PINE interface made only the isolated emulator process exit. Stop live-code writes; use immutable ISO variants and copied savestates for bounded A/B tests.

## External control and safety

- PCSX2 v2.9.115 isolated profile exposes local UNIX PINE socket `pcsx2.sock.28012` (not TCP), which successfully serviced read-only Version, Status and Read32, and loaded *the isolated copy* of slot 2. This can replay the original dialogue without restarting the game, while keeping original user saves untouched.
- Before any renderer correction, establish glyph/canvas ownership by tracing the native `ADV LOG PROC` call chain. Do not assume `MesLineX` is a glyph position, modify the accepted ADV/DG renderer, break official text, or weaken static acceptance.
- The **user-approved H.A.N.T. Basic Attack page is frozen**. The user still requires full `Change target` in bounds, old-man chamber comments and blue backing contained, and the Lion Statue item-pickup title inside the yellow card. All remain open.
- No new numeric prerelease, no PR merge, and no claim of first-save completion are authorized on the basis of these tests.
