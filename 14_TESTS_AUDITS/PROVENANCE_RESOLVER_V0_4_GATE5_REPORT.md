# PROVENANCE_RESOLVER_V0.4-GATE5 — Parallel Variant Report

Status: `REGRESSION GATES PASS — GATE 5 (AD3/AD4) 100% — GATE 4 IMPROVED, NOT COMPLETE`

Date: 2026-08-12
Benchmark: frozen `PROVENANCE_ADVERSARIAL_SET_V1` (230 records), committed key
(`blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl`, commit `c44dfc8`).

## Why two v0.4 implementations exist

A concurrent lane committed `provenance_resolver_v0_4.py` (commit `d919963`,
"span provenance, P0 tiers, adoption") while this work was in flight. That
implementation is **canonical** and left untouched. This document describes a
**parallel variant**, `provenance_resolver_v0_4_gate5.py`, with a
complementary design:

| | committed v0.4 (`d919963`) | this variant (`v0.4-gate5`) |
|---|---|---|
| Frozen v0.3 D0 core | unchanged | unchanged |
| Span model | `resolve_case(case, bundle)` + P0 tiers | `classify_gate5(case)` + `segment_spans` |
| MIXED recall | **72.2%** (13/18) | 44.4% (8/18) |
| MIXED precision | 61.9% (13/21) | **72.7%** (8/11) |
| P0 precision | **84.9%** (28/33) | 79.5% (31/39) |
| AD3/AD4 accuracy | 91.7% (33/36) | **100% (36/36)** |
| v0.3 mixed-flag demotion | — | yes |

Both share the same safety boundary (D0 sets identical to v0.3, FDA = 0).
Neither is accepted for corpus promotion yet; the committed variant is the
baseline and this one is evidence that **Gate 5 is closable**.

## This variant's results

| Metric | v0.3 | v0.4-gate5 |
|---|---:|---:|
| R1 False Derek Attribution | 0 | **0** PASS |
| R2 D0 precision | 100% | **100%** (38/38) PASS |
| R3 v0.3 D0 regressed | — | **0** PASS |
| MIXED precision | 0% | **72.7%** (8/11) |
| MIXED recall | 0% | **44.4%** (8/18) |
| P0 precision | 68.4% | **79.5%** (31/39) |
| AD3/AD4 accuracy | 91.7% | **100%** (36/36) |
| Exact-class accuracy | 55.2% | **60.9%** (140/230) |

## Gate 4 — span-level MIXED (this variant)

`segment_spans` emits `message → spans → class` for three deterministic
patterns: transcript wrapper, "Her reply." label, and transformation
directives on substantially reused assistant text (matched_frac ≥ 0.8).
A Derek carrier lead never transfers authorship to the imported body
(unit-tested). v0.3's over-broad mixed flag is demoted when no lead/body
split is justified, removing 5 false-MIXED predictions.

**Honest limits:** the remaining MIXED misses (10 records) sit on the
key-inconsistency margin — the committed adjudication splits near-identical
short-lead + reuse cases in both directions (six structurally identical
transcript wrappers split 3 MIXED / 3 P0). Forcing them would overfit to
label choices, which the directive forbids.

## Gate 5 — adoption (this variant's strength)

`resolve_adoption` implements the Board's rules independently of authorship,
all unit-tested:

- rejection/correction overrides → AD0
- discussion / plain question → AD0
- continuation ("what if we added X?") → AD1
- explicit "add this / use this / build this" → AD3
- "yes, but …" and transformation directives → AD4

**AD3/AD4 accuracy reached 100% (36/36)**, including the 3 AD4 transformation
records (adv_001324/001443/007563) that both v0.3 and committed v0.4 missed.
`submitted_by / authored_by / adopted_by` remain separate axes.

## Reconciliation and next step

- The committed `provenance_resolver_v0_4.py` remains canonical and is not
  modified by this work.
- Recommend merging the two: take the committed variant's span/P0 machinery
  (higher MIXED recall) and this variant's adoption resolver (Gate 5 = 100%),
  then re-benchmark on the same frozen 230.
- `PROVENANCE_CORPUS_V1` (Gate 6) and Conglomerate reconstruction (Gate 7)
  remain unauthorized. Frozen benchmark/adjudications unchanged.
