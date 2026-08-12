# PROVENANCE OUT-OF-SAMPLE GATE — V1 REPORT

Status: `SAFETY GATE PASS — CORPUS NOT AUTHORIZED (coverage)`

## What was run

A blind out-of-sample provenance challenge per the Board directive, with the
frozen V0.6 resolver, against a population it had never seen:

- **Population**: 3,068 DeepSeek-platform user records (delta export,
  `source_file=conversations.json`, `ingest_version=2.0.0`) minus all Gold Set
  ids, all 230 adversarial-set records, and all MIXED adjudication records.
- **Selection**: 163 records stratified mechanically across nine hard families
  (carrier+paste, substantive modification+paste, transcript wrappers, rewrite
  requests, cross-platform AI reuse, Derek→AI→Derek chains, external→Derek→AI
  chains, long polished first-person, unknown-origin).
- **Blindness**: bundles carried evidence only. V0.6 predictions were sealed
  before labels were frozen. The frozen adjudication was written from the
  bundles without opening the prediction file.
- **Adjudication**: all 163 records reviewed at span level; every D0, MIXED,
  UNRESOLVED, AD3/AD4, and multi-origin record flagged for the independent
  Audit Bot pass. Frozen at `FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl`.

## Gate results

| Metric | Value |
|---|---|
| **False Derek Attribution** | **0 — PASS** |
| D0 precision | N/A (resolver emitted 0 D0 — fail-closed) |
| D0 recall | 0.000 (0/28) |
| P0 precision | 0.966 (57/59) |
| P0 recall | 0.429 (57/133) |
| MIXED precision / recall | 0 / 0 (0/2) |
| UNRESOLVED rate | 0.638 (104/163) |
| AD3/AD4 accuracy | 0.029 (1/34) |
| Span-boundary accuracy | 0.000 |
| Origin correctness | not measurable (resolver emits no origin field) |

## Interpretation

**The safety gate holds.** On 163 hard cases from a different AI platform,
V0.6 never attributed a single non-Derek record to Derek. The
positive-evidence / fail-closed posture survives out-of-sample transfer. That
is the property the Board made non-negotiable, and it did not break.

**Coverage does not survive transfer.** 63.8% of the DeepSeek population is
abstained, 0% of genuine Derek material is recovered, and 57% of pasted
content is missed. Root causes (full analysis in `OOS_FAILURE_CURRICULUM_V1.md`):

1. `SHORT_CONTROL_ACT` matches affirmation vocabulary only — Derek's
   directive register (`can we add`, `can you create`, `I need`) is unmatched,
   so the DAE-3 control-act path never fires (26/28 D0 misses).
2. Shingle origin detection requires an in-corpus match; cross-platform paste
   (ChatGPT/Grok → DeepSeek) has no match in the non-delta corpus, so
   imported-content evidence is invisible (74 P0 misses).
3. `external_fingerprint` is too narrow (URLs / mail headers only) (22 P0
   misses).
4. Span-function detection is vocabulary-bound, missing proposition-level
   substantive Derek requirements (2 MIXED misses).
5. Adoption resolver only upgrades on `yes/perfect/good` — Derek's real
   adoption register (`add this`, `use X instead`, `combine`) never reaches
   AD3/AD4 (33/34 AD misses).

## Artifacts

| File | Role |
|---|---|
| `PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl` | Blind set (evidence + text only) |
| `out_of_sample_bundles/batch_*.jsonl` | Adjudication bundles (evidence only) |
| `PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json` | Sealed V0.6 predictions |
| `FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl` | Frozen blind labels (163) |
| `score_out_of_sample_v1.py` | Reproducible scorer |
| `OOS_FAILURE_CURRICULUM_V1.md` | Root causes by family + V0.7 spec |
| `build_out_of_sample_set_v1.py` / `build_out_of_sample_bundles_v1.py` | Selection + bundling |
| `seal_out_of_sample_predictions_v1.py` | Sealing harness (evidence-threaded) |

## Disposition

- **V0.6 remains frozen and untouched** (git-clean vs the committed V0.5 base;
  the resolver was not modified after seeing results).
- **PROVENANCE_CORPUS_V1 is NOT authorized.** The safety gate passed but the
  coverage gates failed on the delta population; running the corpus pass now
  would silently discard genuine Derek material (0% D0 recall) and half the
  imported content (43% P0 recall) from this export.
- The next step is **V0.7 per the failure curriculum** (broaden the
  control-act DAE-3 path, add a cross-platform origin oracle, widen the
  external fingerprint, proposition-level span functions, adoption-register
  expansion), then a re-run on the **same frozen 163-record OOS set** — the
  delta population stays out-of-sample because V0.7 will not be tuned on it
  either.
- Frozen benchmark, sealed predictions, and the blind adjudication are
  immutable. The DeepSeek delta records remain a clean future out-of-sample
  test.
