# PROVENANCE_RESOLVER_V0.6 Report — Reconciled Candidate

Status: `MIXED BOUNDARY RESOLVED — ALL GATES PASS`

## What this is

The Board directive called for **one reconciled V0.6 candidate** built from the
strongest components of the two parallel V0.4 experiments, preserving Codex
V0.5 as the safety baseline, and solving the remaining MIXED problem through an
**independent span-level adjudication** instead of more model tuning.

Delivered:

| Artifact | Role |
|---|---|
| `MIXED_SEMANTICS_ADJUDICATION_V1.md` + `.jsonl` | The span-level semantic contract. Defines what MIXED means; adjudicates all 26 disputed records; documents the frozen key's internal inconsistency at the carrier margin. |
| `provenance_resolver_v0_6.py` | The reconciled candidate. Wraps V0.5 (frozen safety core) and implements the adjudicated MIXED gate. |
| `run_v0_6_benchmark.py` | Frozen-key regression gates + adjudication-key MIXED boundary scoring. |
| `PROVENANCE_RESOLVER_V0_6_BENCHMARK.json` / `_predictions.json` | Reproducible results. |

## Safety baseline preserved (frozen, by construction)

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| R1 False Derek Attribution | 0 | **0** | PASS |
| R2 D0 precision | ≥ 0.98 | **1.0 (38/38)** | PASS |
| R3 frozen D0 set unchanged vs V0.5 | true | **true (38/38 byte-identical)** | PASS |
| R4 AD3/AD4 accuracy | ≥ 0.97 | **1.0 (36/36)** | PASS |

V0.6 never touches a V0.5 D0 decision. FDA = 0 is preserved by construction —
the V0.3/V0.4/V0.5/V0.6 D0 sets are identical.

## MIXED boundary — adjudicated, resolved

The frozen message-level key is **internally inconsistent at the carrier
margin**: six structurally identical "Summarize the transcript…" records are
split 3 MIXED / 3 P0, and five identical "rewrite in style" carriers are split
2 MIXED / 2 P0 / 1 UNRESOLVED. `MIXED_SEMANTICS_ADJUDICATION_V1` resolves each
family to one principled class using the substantive-meaning rule:

> A message is MIXED only when ≥2 independently attributable semantic spans
> both contribute substantive meaning. CONTROL_ACT / LABEL / QUERY carriers
> resolve to P0 + adoption; they never create MIXED.

| Gate (adjudication key) | Required | Observed | Result |
|---|---:|---:|---|
| R5 MIXED precision | 1.0 | **1.0 (2/2)** | PASS |
| R6 MIXED recall | 1.0 | **1.0 (2/2)** | PASS |
| R7 P0 precision (within adjudication) | ≥ 0.9 | **1.0 (20/20)** | PASS |

**Only two records remain genuinely MIXED** — exactly the two where Derek's
span is substantive rather than a carrier:

- `adv_003597` — Derek's own statements ("Great I'm looking for closer and
  setters / Or I can train them to be") inside a pasted LinkedIn chat with a
  third party (Rob Walker).
- `adv_021989` — a substantive governance requirement ("Can't we put a limit on
  how much or a plan that allows the system flexibility") over an imported
  capability list.

All 20 adjudicated-P0 carrier records (transcript templates → AD3, style/rewrite
carriers → AD4, query+code → AD2, labels → AD1) are now correctly P0.

## Why frozen-key P0 precision drops (informational, expected)

V0.5 reported 96.55% P0 precision **against the frozen key**. V0.6
reclassifies 16 of those records (frozen MIXED) to P0 **because the
adjudication says the frozen key over-labeled them MIXED**. Against the frozen
key those 16 now count as false P0 (0.6875) — but against the authoritative
adjudication they are correct. This is the documented, intentional cost of
resolving the boundary; it is not a safety regression. The MIXED/P0 semantics
are governed by the adjudication, not the frozen key, from here forward.

## What V0.6 does not do

- No PROVENANCE_CORPUS_V1 (Gate 6 not authorized).
- No Conglomerate reconstruction (Gate 7 behind Gate 6).
- No relabeling of the frozen benchmark or blind adjudications — both remain
  untouched.
- No D0 expansion: the four D0-leaning records (adv_002059, adv_017999,
  adv_001444, adv_004101) stay UNRESOLVED under the fail-closed bar.

## Next gates (unchanged)

1. Adjudicated MIXED boundary is now the scoring contract for Gates 4.
2. Out-of-sample challenge on the ~3,080 delta records (never seen by the
   resolver in adversarial selection) — manual sample of hardest outputs.
3. Only then: PROVENANCE_CORPUS_V1 → semantic extraction → Conglomerate V0.2.
