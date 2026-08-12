# PROVENANCE_RESOLVER_V0.3 Report

Status: `SAFETY AND D0 PRECISION PASSED; CORPUS PROMOTION BLOCKED`

## Model

V0.3 implements a positive-evidence authorship model:

- `role=user` establishes `submitted_by=derek`; it never establishes authorship.
- `submitted_by`, `authored_by`, and `adopted_by` are separate outputs.
- User-submitted records default to `UNRESOLVED / authored_by=unknown / DAE-0`.
- D0 requires auditable DAE-3 or DAE-4 evidence.
- First person, style, repetition, topical alignment, lack of contradiction, and
  failure to locate another origin do not count as positive Derek evidence.
- Traceable assistant or external origins produce P0, while explicit mixed
  evidence produces MIXED.
- Brief direct conversational control acts can establish Derek authorship of
  that act only. They do not transfer authorship of the preceding proposition.

DAE is a categorical evidence tier, not an additive confidence score:

| Tier | Meaning | D0 eligible |
|---|---|---:|
| DAE-0 | No authorship evidence | No |
| DAE-1 | Weak contextual evidence | No |
| DAE-2 | Multiple contextual indicators without direct trace | No |
| DAE-3 | Strong proposition-specific direct evidence | Yes |
| DAE-4 | Explicit, traceable Derek origination | Yes |

## Frozen adversarial benchmark

The committed 230 cases, blind labels, and original sealed predictions were
not modified.

| Gate | Result |
|---|---|
| Gate 1 — False Derek Attribution = 0 | **PASS: 0** |
| Gate 2 — D0 precision >= 98% | **PASS: 100% (38/38)** |
| D0 recall | 80.85% (38/47) |
| Gate 3 — unresolved coverage measured | **149/230 (64.78%)** |
| Gate 4 — P0 precision | **BLOCKED: 68.42%** |
| Gate 4 — MIXED precision/recall | **BLOCKED: 0% / 0%** |
| Gate 5 — AD3/AD4 exact accuracy | **BLOCKED: 91.67% (33/36)** |
| Gate 6 — `PROVENANCE_CORPUS_V1` | **NOT AUTHORIZED** |

The high unresolved rate is an accepted safety tradeoff. It must not be
reduced by weakening D0 evidence requirements. Work should next improve
origin detection, segment-level classification, and proposition-linked
adoption while keeping the frozen Gate 1 result at zero.

## Root-cause curriculum

The 69 prior false Derek attributions were independently classified. The
largest families are cross-platform AI reuse (21), AI-polished frameworks
(15), external pasted material (14), and carrier phrase plus pasted body (6).
See `FALSE_DEREK_ATTRIBUTION_ROOT_CAUSE_V1.md` for the case-level audit.

## Scope and disposition

V0.3 is a benchmarked resolver candidate, not a corpus-scale promotion. It
does not create canonical records, candidate knowledge, Obsidian notes,
published projections, or a canonical commit mechanism. The Conglomerate
discovery package remains `CANDIDATE_EVIDENCE` behind the provenance gate.
