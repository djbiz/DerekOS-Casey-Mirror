# PROVENANCE_RESOLVER_V0.4 Report

Status: `D0 SAFETY PRESERVED; CLASS/ADOPTION GATES STILL BLOCKED`

## Scope

V0.4 leaves the accepted v0.3 D0 decision path unchanged and adds only:

- span-level MIXED provenance;
- `P0-CERTAIN`, `P0-PROBABLE`, and `P0-UNRESOLVED` tiers;
- independent submission, authorship, and adoption fields;
- proposition-context adoption rules.

An imported-content marker without a traceable origin remains message-level
`UNRESOLVED` with `P0-PROBABLE`; it is not promoted to P0 merely because it
looks like an artifact. The atomic-thought stage can consume resolved spans
instead of laundering a carrier phrase across an entire pasted body.

## Frozen benchmark

| Metric | V0.3 | V0.4 | Status |
|---|---:|---:|---|
| False Derek Attribution | 0 | **0** | PASS |
| D0 precision | 100% | **100% (38/38)** | PASS |
| D0 recall | 80.85% | **80.85%** | Frozen |
| P0 precision | 68.42% | **84.85% (28/33)** | Improved; not accepted |
| P0 recall | 25.74% | **27.72% (28/101)** | Improved slightly |
| MIXED precision | 0% | **61.90% (13/21)** | Improved; not accepted |
| MIXED recall | 0% | **72.22% (13/18)** | Improved; not accepted |
| AD3/AD4 exact accuracy | 91.67% | **91.67% (33/36)** | Unchanged; not accepted |
| UNRESOLVED | 64.78% | **60.00% (138/230)** | Coverage earned conservatively |

The v0.3 and v0.4 predicted D0 ID sets are identical. Any future change that
produces one false Derek attribution fails before other metrics are considered.

## Gate disposition

- Gates 1–2: pass and remain frozen.
- Gate 3: measured; unresolved coverage remains acceptable safety behavior.
- Gate 4: blocked pending stronger P0 precision and MIXED segmentation.
- Gate 5: blocked pending improved AD3/AD4 accuracy.
- Gate 6: `PROVENANCE_CORPUS_V1` remains unauthorized.
- Gate 7: Conglomerate reconstruction remains `CANDIDATE_EVIDENCE` only.

## Next technical work

Improve contiguous cross-source matching in Provenance Index V0.2 and use
traceable span offsets rather than broad document similarity. Then validate
V0.4 on an independently adjudicated corpus delta before any corpus-scale run.
