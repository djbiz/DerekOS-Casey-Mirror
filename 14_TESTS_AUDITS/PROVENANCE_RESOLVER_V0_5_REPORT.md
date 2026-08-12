# PROVENANCE_RESOLVER_V0.5 Report

Status: `P0 AND ADOPTION TARGETS PASS; MIXED PRECISION BLOCKED`

## Frozen safety boundary

V0.5 wraps v0.4 and never changes its D0 decisions. The v0.3, v0.4, and
v0.5 D0 sets remain identical.

Because another work lane modified the active v0.4 file concurrently, v0.5
imports `provenance_resolver_v0_4_baseline.py`, an isolated snapshot of the
accepted `d919963` implementation. It does not overwrite or absorb the
concurrent v0.4 edits.

| Gate | Target | V0.5 | Result |
|---|---:|---:|---|
| False Derek Attribution | 0 | **0** | PASS |
| D0 precision | 100% / frozen threshold | **100% (38/38)** | PASS |
| D0 recall | frozen | **80.85%** | unchanged |
| P0 precision | >=95% | **96.55% (28/29)** | PASS |
| MIXED precision | >=90% | **66.67% (16/24)** | BLOCKED |
| MIXED recall | >=85% | **88.89% (16/18)** | PASS |
| AD3/AD4 exact accuracy | >=97% | **100% (36/36)** | PASS |

## Generalized changes

- Partial reuse no longer makes a correction/quotation whole-message P0.
- Traceable carrier/body records use contiguous token alignment to preserve
  unmatched Derek prefixes and suffixes.
- P0 requires traceable source evidence; artifact appearance remains
  `P0-PROBABLE` or `P0-UNRESOLVED`.
- Material transformation requests resolve adoption independently as AD4.

The error curriculum is generated from the committed blind labels by
`build_v05_error_inventory.py`; it does not consume the alternate untracked
adjudication file. See `PROVENANCE_V0_5_ERROR_INVENTORY.json`.

## MIXED precision limitation

Eight false MIXED results remain. Their dominant families are:

- transcript carriers classified MIXED in some frozen records and P0 in
  structurally equivalent later records;
- rewrite/summarize carriers treated sometimes as semantic Derek spans and
  sometimes as submission metadata;
- ambiguous code/document boundaries where structure alone does not prove a
  second author.

No general evidence rule can force these to >=90% precision while retaining
>=85% recall against the current labels. A date, source-file, or case-ID rule
would be benchmark overfitting. The safe disposition is to preserve review
status and keep Gate 4 closed.

## Stop decision

The out-of-sample challenge is not run. `PROVENANCE_CORPUS_V1`, semantic
extraction, Conglomerate V0.2 reconstruction, canonical records, and canonical
commit remain unauthorized until MIXED precision is resolved through an
independent span-boundary adjudication contract or reconciled labels.
