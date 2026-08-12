# PROVENANCE_ADVERSARIAL_SET_V1 — Build Report

Resolver-selected hard cases for manual adjudication beyond the 40-record gold set.

- **Records**: 230 unique user-role messages (excludes all gold-set records)
- **Corpus**: 35176 user-role messages from the snapshot at build time (merged corpus)
- **Selection**: mechanical evidence signals only (never gold labels); stratified
  across 14 adversarial categories, 20 target per category, seed 20260812
- **Blindness**: `PROVENANCE_ADVERSARIAL_SET_V1.jsonl` carries evidence + text only;
  resolver predictions are in `PROVENANCE_ADVERSARIAL_SET_V1_predictions.json`
  (keyed by adversarial_id) so adjudication happens blind to resolver output.

## Category distribution

| Cat | Meaning | Selected |
|-----|---------|----------|
| C01 | high-confidence-looking D0, unusually polished | 24 |
| C02 | strong earlier-assistant similarity | 70 |
| C03 | long user messages, no located origin | 50 |
| C04 | multiple reuse candidates | 81 |
| C05 | mixed pasted + Derek commentary (segmentation) | 32 |
| C06 | cross-conversation reuse, weeks/months apart | 55 |
| C07 | partial rather than exact reuse | 29 |
| C08 | assistant text substantially rewritten | 48 |
| C09 | external material, no corpus origin | 0 |
| C10 | short yes/add-this/do-this | 38 |
| C11 | contradictory evidence | 9 |
| C12 | resolver abstentions (UNRESOLVED) | 38 |
| C13 | low-confidence D0 | 72 |
| C14 | AD3/AD4 adoption candidates | 53 |

## C09 note (verified finding, not a bug)

C09 (external material with no corpus origin) selected **0 records**. Direct
verification: 16 user messages in the corpus carry an external-content
fingerprint; 3 are the already-adjudicated gold records (gold_020/021/022,
excluded by design) and the other 13 all have a **located reuse origin**
(so they are P0-with-origin, not external-no-origin). The corpus therefore
contains no un-adjudicated C09 candidates - the category's real cases are
already in the gold set. This is a reported finding, not a selection gap.

## Next step

Manual adjudication (Claude / Audit Bot), blind to resolver predictions. For each
record assign: evidence_class, adoption_status, provenance_certainty, requires_review.
Primary gate: **False Derek Attribution = 0** on the adjudicated set. After
adjudication, compare against the predictions key file and report per-category
precision, then decide whether to authorize full-corpus provenance resolution.
