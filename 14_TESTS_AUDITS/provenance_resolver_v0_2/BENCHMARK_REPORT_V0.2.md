# PROVENANCE_RESOLVER_V0.2 — Benchmark Report

## Gate result: PASS

**True False Derek Attribution Rate: 0/13 = 0%** (against `provenance_gold_set_v1_1.jsonl`, the corrected benchmark). This is the primary safety gate per the refined policy: *"v0.2 can pass the small benchmark if it gets zero false Derek attributions, even if abstention increases somewhat."* It does.

`gold_020` — the sole genuine False Derek Attribution in v0.1 — is now correctly `UNRESOLVED` in v0.2, with the classifying agent's own stated reasoning citing the exact signal that should have blocked `D0` all along (third-person listicle voice, social-media call-to-action phrasing, zero-width-space artifacts consistent with a copied post) and no located source. The root-cause fix worked on the actual case it was built for, not just in the abstract.

**D0 precision: 18/23 = 78.3%**, reported per policy but not gating at this sample size (n=40 is too small for the 98% bar to be statistically meaningful either direction — see below for why this dropped from v0.1's number, and it is not the metric that matters here).

## Root-cause table (every v0.1 disagreement, as requested)

| Record | v1.1 (current truth) | v0.1 predicted | Actual finding | Root cause |
|---|---|---|---|---|
| `gold_019` | P0 (origin located, `assistant`) | MIXED | v0.1 correct in substance — segmented the D0 question from the P0 pasted content, which is a more precise application of the spec's own mixed-message rule than the original single-blob `P0` gold label. Not an error. | Gold Set under-segmentation, not resolver error |
| `gold_037` | P0 (origin located, `assistant`) | P0 | v0.1 correct — this is the record whose correction is *in* v1.1. Only "wrong" against the now-superseded v1 label. | Manual Gold Set search gap (fixed in errata) |
| `gold_020` | P0 (external, no located origin — Board ruling: no relabel without new evidence, stays as adjudicated) | **D0** | **The one genuine False Derek Attribution.** Root cause identified precisely: the v0.1 decision rule said a stylistically-suspicious message with no located cross-corpus match "stays D0, confidence lowered" — i.e. absence of a match was treated as if it supported Derek's authorship, when it only means the search didn't find anything. | Decision-rule defect (§6.0a, now fixed) |
| `gold_016` | P0 | MIXED | Same as `gold_019` — the resolver's segmentation is arguably more correct than the original gold label's single-blob `P0`. Not an error. | Gold Set under-segmentation |
| `gold_022` | P0 (Board: unresolved judgment, no relabel) | UNRESOLVED | Reasonable, conservative — the resolver declined to assert `external` origin without a located source, per the "stylistic suspicion is a trigger, not proof" rule. Arguably the more disciplined call given no source was ever located either way. | Legitimate judgment difference, not an error |
| `gold_010` | D0 | UNRESOLVED | Root cause: a coincidental shingle match confined to a *quoted title Derek reuses across his own requests*, not evidence of reuse. Fixed in v0.2 via the `matched_span_mostly_quoted` signal (verified: `gold_010` now correctly registers as quoted-noise; `gold_019`'s genuine unquoted match is correctly kept as strong evidence — both checked directly, not assumed). | Stage 1 evidence-quality gap (fixed) |
| `gold_040` | UNRESOLVED (Board: genuinely ambiguous, kept unresolved) | MIXED | v0.1 leaned toward a specific call (`external`) where v1 deliberately abstained. Neither confirmed nor refuted by located evidence. | Legitimate judgment difference, not an error |

## New finding in v0.2 (not present in v0.1): X0-vs-D0 taxonomy regression

All 5 `X0` (explicit rejection/correction) records — e.g. "No, each department will have a different theme," "That's not what I asked for" — were classified `D0` instead of `X0` in v0.2. **This is a real classification miss, but it is not a safety issue**: `X0` records are still Derek's own words (a rejection is authored by Derek same as any other statement) — this is a semantic sub-classification gap (failing to flag "this is specifically a rejection"), not an authorship-attribution error. It does not count against False Derek Attribution Rate, which is specifically about assistant/external content being misattributed to Derek.

**Root cause**: the v0.2 prompt's decision flowchart, written to fix the `gold_020` issue, is entirely about the `D0` vs. `suspicion`/`UNRESOLVED` boundary. It never routes through an `X0` check at all — a short, clearly-Derek-authored rejection has *zero* suspicion signal (no reuse match, no paste markers, casual voice), so the corrected flowchart correctly lands it on `D0` and stops, without ever asking "is this specifically a correction/rejection of something." The flowchart needs an explicit, parallel `X0` check (independent of the reuse/suspicion branch) before v0.3, not folded into the same tree.

## Scoring reported separately: raw (v1) vs. evidence-adjudicated (v1.1)

Per the instruction not to conflate historical and corrected scoring:

| | vs. v1 (historical, frozen) | vs. v1.1 (corrected, current truth) |
|---|---|---|
| v0.1 exact evidence_class match | 33/40 | 34/40 |
| v0.1 True False Derek Attribution | 1/13 | 1/13 |
| v0.2 exact evidence_class match | 29/40 | 30/40 |
| v0.2 True False Derek Attribution | 0/13 | **0/13** |

(v0.2's raw exact-match count is lower than v0.1's mainly because of the X0-taxonomy regression above, not because of new provenance errors — the safety-relevant number, True False Derek Attribution, improved in both comparisons.)

## What was NOT done, per explicit instruction

- `gold_020` was **not** relabeled — it remains as adjudicated in both v1 and v1.1, pending genuine new evidence or an explicit Board rule interpretation, exactly as instructed. v0.2 abstaining on it (rather than agreeing with the original P0 call) is not treated as "resolving" it either — both are legitimate readings of insufficient evidence.
- No corpus-scale semantic extraction was run.
- `conversations.json` (the newly-located Downloads file) was not touched.
- `03_PROVENANCE_INDEX/` (the reusable origin-index design for the intellectual-lineage graph) was not built — noted as a real next step, design-only, not started.

## Recommendation before v0.3

Fix the X0 taxonomy gap with a parallel, independent check in the decision flow (not nested inside the D0/suspicion branch), then re-run against v1.1 to confirm both the False Derek Attribution gate and X0 precision hold simultaneously. This is a bounded, well-understood fix — not a new investigation.
