# H.A.N.T. Content Expansion r13

## Goal
Translate the runtime-proven Japanese H.A.N.T. datasets reported after r12 while freezing every pre-H.A.N.T. surface and the already accepted H.A.N.T. main/chrome/navigation presentation.

## Runtime ground truth
- Main H.A.N.T. screen: accepted English.
- Help labels/navigation: accepted English.
- H.A.N.T Functions body: accepted English.
- ADV Controls, Exploration Controls, Moving in Ruins bodies: Japanese.
- Mail empty state: Japanese.
- Config labels are English but selected values remain partly Japanese.
- Enemy L1/R1 category names: Japanese.
- Dictionary tabs, terms and definitions: predominantly Japanese.
- Everything before H.A.N.T. remains accepted and must not change.

## Evidence-backed implementation order
1. Promote the three observed Help bodies through the proven `(mode=4, category, topic)` body tree. Preserve row counts and page metadata byte-for-byte; redirect only text-table descriptors.
2. Promote Config value owners: Stereo/Mono, Japanese/English and the 20-entry ringtone pointer table.
3. Promote the three Enemy category pointers (`Small`, `Large`, `Human`) and the Mail empty-state pointer.
4. Promote the Dictionary kana-tab table and all real term-list pointer entries with semantic English/romanized names. Preserve placeholder slots.
5. Model Dictionary definition descriptor tables separately; relocate translated definition row tables only when owner/table correspondence is exact and fail-closed.
6. Add final-image gates for each new class and preserve all previous gates.
7. Run focused/full/Pillow tests, pristine ISO build, final-image acceptance and deterministic repeat. No PCSX2 launch by the agent.

## Provenance
The localized remaster TextAsset is not present in the current owned extraction. New H.A.N.T. wording in this pass is therefore `semantic`, not `official`, unless an exact already-owned English counterpart is independently proven.
