# Dataset provenance

## Simulation versions

Historical Phase 1 clamped-bore labels, Phase 2 cosine-bearing labels and Phase 3 deterministic-mesh labels remain separate. Phase 2's 120 records across 60 geometry groups are 8 mm coarse-mesh responses; its four-geometry paired fine study is historical transfer evidence only. Phase 3 uses simulation version `phase3-deterministic-bearing-v1`, geometry `rod-2-filleted-pocket`, 4340 model material, cosine-bearing equivalent pressure, fixed 145 mm center distance and 50/24 mm bores. Dataset loading rejects mixed simulation versions, and Phase 3 optimizer verification requires an exact mesh-configuration match.

Each validated record contains geometry, material, signed load, mesh and solver provenance, CAD volume/mass, node/element counts, equilibrium audit, raw integration-point outputs and field path. Paths in datasets are portable relative paths. The local run folder also retains input decks, logs, DAT/FRD and meshes. A result JSON or JSONL label alone does not provide enough data to reconstruct the full field.

## Phase 3 paired fidelities

The 40-point Latin-hypercube study used seed 7301. Twelve successful CAD/FEA geometries were selected by minimum distance of the coarse maximum stress to the 394.444 MPa limit, followed by maximin distance in normalized geometry space. The already-completed 6 mm coarse compression/tension cases were reused; no duplicate coarse solver runs were performed. New 1.25 mm intermediate and 0.75 mm fine transition-refined compression/tension runs were checkpointed per case. All 48 new runs completed successfully.

| Fidelity | Analyses | Geometry groups | Loads | Mesh configuration |
|---|---:|---:|---|---|
| Coarse | 24 | 12 | Compression and tension | 6 mm global; default all-feature refinement setting, no hotspot target |
| Intermediate | 24 | 12 | Compression and tension | 4 mm bulk; 1.25 mm big-end transition |
| Fine | 24 | 12 | Compression and tension | 4 mm bulk; 0.75 mm big-end transition |

The exact mesh settings, IDs and SHA-256 values are in `data/phase3/paired/manifest.json`. The JSONL datasets are `coarse.jsonl`, `intermediate.jsonl` and `fine.jsonl`. Fine dataset SHA-256: `ff3a0bf2fad26f1e2bf3c89634d66b06264ca529e3b87fde55143eb6349d2fb7`. Coarse records point back to `data/phase3/feasibility/candidates.json`; its source SHA-256 is recorded in the manifest. Fine/intermediate records retain successful per-case `result.json`, with raw fields available in the local run folders.

The mesh comparison itself demonstrates why fine is a fidelity label rather than a convergence truth. From intermediate to fine, median paired peak-stress change is +4.67% in compression (range −2.31% to +29.76%) and +6.60% in tension (−4.66% to +31.68%). Displacement changes are much smaller: median +0.082% overall, with all paired changes between +0.005% and +0.25%. The 12-geometry study does not prove convergence for each design; see the full paired rows and [ML evaluation](ML_EVALUATION.md).

## Splitting and package limits

All fine-mesh load cases for one geometry stay in the same group. The model's 1% normalized-distance grouping produced 12 groups; seeded held-out partitions use 6 train, 3 validation and 3 test geometries (12/6/6 analysis records). The groups are disjoint. This is too few held-out geometries for broad generalization, so the model is marked `EXPLORATORY_SCREENING_ONLY`; actual FEA remains the acceptance path and the optimizer refuses this model.

The compact evidence package includes the JSONL labels, model evaluation and raw fields for critical baseline, contact, and nearest-boundary candidate cases. It does not bundle all 48 fine/intermediate raw fields, which remain beside their local solver runs. `package_evidence.py` records hashes for included artifacts and omitted raw fields.
