# Provenance Adversarial Benchmark V1

Status: `FAILED — RESOLVER NOT AUTHORIZED FOR CORPUS RECONCILIATION`

The 230-case answer key was adjudicated blind and frozen in commit `c44dfc8`
before the sealed resolver predictions were opened. The combined label file has
SHA-256 `6d7fa776e8b3a6a9adda3739a5a7d408db694dd98eae79215cf2c66347ebff12`.

## Result

- Records: 230
- False Derek Attribution requirement: 0
- False Derek Attribution observed: 69
- D0 predictions: 113
- Correct D0 predictions: 44
- D0 precision: 38.94%
- D0 recall: 93.62%
- Evidence-class exact accuracy: 33.91%

The primary gate failed. No `PROVENANCE_CORPUS_V1` may be produced from this
resolver result, and no discovery record may be promoted to Derek canonical
knowledge. The machine-readable confusion matrix, category results, and failed
case IDs are in `PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json`.

## Disposition

The resolver over-attributes polished or long user-role text when no reliable
origin is located. The largest observed concentrations are C01 (polished D0
lookalikes), C03 (long messages without a located origin), C06 (cross-session
reuse), and C13 (low-confidence D0). The next provenance iteration must prefer
`UNRESOLVED` over D0 whenever authorship is not positively established, then be
evaluated against this unchanged frozen answer key.

Track B Conglomerate discovery remains valid only as `CANDIDATE_EVIDENCE`.
