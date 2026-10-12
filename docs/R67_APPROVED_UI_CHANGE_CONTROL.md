# r67 visual approval and change-control policy

r67.14q, r67.14t and **r67.14y** have passed user gameplay review. Their approved behavior is protected, not only their nominal release numbers.

## Protected r67.14y baseline

- Approved ISO SHA-256: `079b4d0ed73fb010b0d0020f5a3e84357b44804a9b2a2425fa3328fd497aee8f`.
- Exact staged ELF SHA-256: `73c27c2728609c7ee38f9c21cfcbc1a26ca980dc8b45b19383d64677c8eba369`.
- Immutable approval record: `translations/r67_14y_approved_lock.json`.
- Owner validator: `tools/r67_14y_approved_lock.py`.
- Existing independently immutable q/t manifests are retained as-is.

The protected behavior includes all ordinary event/AFK bubble presentation, the inspected object descriptions and actions, save prompts and footer graphics, the approved Lion Statue and tablets, history, and native save routines. A new release must **not silently alter or rebaseline any of them**.

For a new modification to previously accepted owners, two independent decisions are required **before promotion**: (1) a documented technical review by the working AI, spelling out the native owner, exact byte scope, regression evidence, and side effects; (2) the user's explicit visual/runtime approval for the requested change. Tests enforce exact byte preservation and require recorded dual approval before marking a diagnostic approved for main. A test or static audit alone is never visual approval.

A user may request a new diagnostic before gameplay approval; that is not permission to merge that new implementation. Once the screenshots and prior regression locks pass, document the evidence, commit and open a PR, and merge only with explicit user approval. If a change to an accepted owner is unavoidable, create a scoped exception with its own tested manifest; **do not rewrite an old approved manifest to make new bytes pass**.

### Current requested r67.14z diagnostic exception

The user requested only the Storeroom name and the Stone tablet in that room. The exact five permitted 4-byte pointer owners are `0x5CD6B4`, `0x5CD84C`, `0x591098`, `0x59109C`, `0x5910A0`, plus the ELF filesize and newly appended text. The validator compares every existing original ELF byte against the frozen y baseline, confirms the official PS4 source entries and runs all q/t/y content guards. No existing dialogue, save UI, inspection, tablet other than the designated inscription, history or graphics changes are authorized.

**r67.14z has not yet been visually approved**, so its own new name/inscription must not be promoted to main until the user has tested its screenshot presentation and approved it.
