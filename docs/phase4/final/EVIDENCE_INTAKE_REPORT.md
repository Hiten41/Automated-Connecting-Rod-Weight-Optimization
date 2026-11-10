# Phase 4 evidence intake report

## Repository and intake

- Branch: `feature/phase4-physics-guided-redesign`
- Original intake source revision recorded in the previously supplied evidence archive: `dd86225d4465b759dc273ed8aa81e1cb283d15d4`. The final Phase 4 source and solver evidence packages are generated after the final branch commit and are documented in the final release section below.
- The attachment cache did not contain separate files with the submitted ZIP filenames. The project-local copies under `outputs/` were inspected; all five part sizes and SHA-256 values match the values in the supplied review brief.
- The original local evidence archive was retained unchanged at `outputs/phase4-final-solver-evidence.zip`.

## Preserved original solver evidence

- ZIP integrity: PASS (every listed member was read to EOF, validating CRC).
- ZIP entries: 2,263 (2,262 evidence files plus `evidence_manifest.json`).
- Original manifest source revision: `dd86225d4465b759dc273ed8aa81e1cb283d15d4`.
- Original evidence manifest SHA-256: `61b4fcf6fcc849be2bb3c5dc87a788abb5d3cf8e81bc5fe749e1d5a13efc7503`.
- Original archive size: 1806307474 bytes.
- Original archive SHA-256: `9e5ae4d71a68c927f57ca973577218ea5450b3996803e77244e733dd0f5cfc03`.
- Every original manifest entry path, byte size and SHA-256 was checked against the archive contents.

## Five submitted evidence parts

Each part opens as an independent ZIP archive. They are not multipart ZIP volumes and must not be concatenated. Each part contains a `__split__/part-NN-of-05-manifest.json` listing the original paths and hashes it carries. Part 01 contains the original `evidence_manifest.json`. Extract all five into one destination folder to reconstruct the original artifact tree.

| Part | Bytes | ZIP entries | Original evidence entries | SHA-256 |
|---|---:|---:|---:|---|
| `RodLab-Phase4-Solver-Evidence-Part-01-of-05.zip` | 361281497 | 453 | 451 | `6945dc9d45783af3c97cf2df1d1062c9f4e5587442575748153a09658af0f3d9` |
| `RodLab-Phase4-Solver-Evidence-Part-02-of-05.zip` | 361281189 | 452 | 451 | `bc1e95dca051d36985268ebbf180c7f68f48cf18e7322d1c4fbe1d39879160dd` |
| `RodLab-Phase4-Solver-Evidence-Part-03-of-05.zip` | 361280842 | 452 | 451 | `ebed61193b2e72c54bdca9e0ed695276b35122bde0d860ad5bc7681c3e97c719` |
| `RodLab-Phase4-Solver-Evidence-Part-04-of-05.zip` | 361282024 | 460 | 459 | `84333d1f6b9097a1fd2be970a23c2aa2845ef0fedd98f82cfd56588bafc770de` |
| `RodLab-Phase4-Solver-Evidence-Part-05-of-05.zip` | 361281071 | 452 | 451 | `1ef21c849aaa56ef6af1839d54f80c47e6d71e5111e8a4c1c68cc063e338cd5b` |

Combined original evidence members verified: **2,262**; missing: **0**; duplicate source paths: **0**; unexpected source paths: **0**.

## Original core review package

This is the prior intake package and retains its original identity; it is not the new final source release package.

- Path: `outputs/RodLab-Phase4-Core-Deliverables-under512MB.zip`
- Size: 19179847 bytes.
- SHA-256: `b8f43499ca42610c679bc9c5350a98d3f5dfca34e0155b4dc27a7dc75d696487`.
- ZIP entries: 114.
- Core manifest source revision matches the original solver evidence and identifies all five evidence parts.

## Limits

This intake verifies archive integrity, membership, sizes, hashes and recorded source revision. It does not claim that a separate ChatGPT reviewer has inspected the package, does not independently rerun the solver, and does not establish production or mechanical qualification.

## Final Phase 4 release package

The completed source/UI ZIP, full evidence archive, five evidence-part ZIPs, file sizes, SHA-256 digests, final Git commit, test counts and browser-QA result are recorded in `outputs/phase4-final-release-manifest.json`. The source and evidence ZIPs contain their own per-file SHA-256 manifests. Each of the five final evidence ZIP parts is independently readable, verified against the full evidence manifest and below 512,000,000 bytes. The original intake archive and its five original parts listed above are preserved unchanged.
