# ABSENCE_OF_EVIDENCE_RULE_V0.1
# Global Master Brain governance rule
# Created: 2026-08-12
# Authority: Founder directive
# Status: CURRENT — applies to ALL reconstructions and provenance claims

---

## Rule Statement

Master Brain must never canonicalize an absence-of-evidence conclusion as a
global negative. "No matching evidence found" is a statement about the
corpus that was searched, not about reality.

## Decision Flow

```
No matching evidence found
        ↓
Was corpus coverage complete
through the relevant period/sources?
        ↓
      NO
        ↓
NOT ESTABLISHED IN SEARCHED CORPUS
        ↓
OUT-OF-CORPUS EVIDENCE MAY EXIST
```

Only when coverage is known to be sufficiently complete for the relevant
period and source systems may DerekOS make a stronger absence claim —
and even then it must state the coverage basis explicitly.

## Valid Epistemic States

| State | Meaning |
|---|---|
| ESTABLISHED | Supported by cited corpus evidence |
| PARTIALLY ESTABLISHED | Some aspects supported, others not |
| NOT ESTABLISHED IN SEARCHED CORPUS | No evidence found in the searched corpus snapshot; no claim made about reality outside it |
| OUT_OF_CORPUS_EVIDENCE_PENDING | Founder or other channel indicates relevant evidence exists outside the searched corpus; ingestion required before status can advance |
| REJECTED | Explicitly abandoned with cited evidence |
| SUPERSEDED | Replaced by a later documented position |
| UNRESOLVED | Evidence conflicts or is insufficient to decide |

**Banned:** bare `NOT ESTABLISHED` as a final state without a coverage basis.

## Required Corpus Coverage Header (every reconstruction)

Every reconstruction output MUST begin with this header:

```
corpus version:
record count:
included source systems:
source files:
earliest timestamp:
latest timestamp:
snapshot/hash:
known missing sources:
reconstruction timestamp:
```

A reconstruction that omits this header is non-conformant and must not be
used as a basis for canonical knowledge proposals.

## Founder Directives Attached to This Rule

1. Do not canonicalize the conclusion that the Conglomerate / Corporate
   Takeover plan does not exist. V0.1 established only that it is not
   supported by the searched snapshot.
2. Newer founder statements exist outside the snapshot and explicitly
   describe several concepts V0.1 marked as not established. These are
   OUT_OF_CORPUS_EVIDENCE_PENDING until ingested and provenance-resolved.
3. FD-001, FD-002, FD-003 remain OPEN. Do not resolve them.
4. V0.1 is preserved as a historical reconstruction result. Do not rewrite it.
5. V0.2 may be created only AFTER the latest ChatGPT conversations
   containing the acquisition/conglomerate plan have been ingested and
   provenance-resolved.
6. Do not tell the reconstructing agent what the plan "really is." Give it
   the missing source conversations; V0.2 must prove the transition from
   older empire concepts into the newer acquisition/conglomerate
   architecture using actual evidence.

## Evolution Hypothesis (to be PROVEN, not assumed)

The working hypothesis is that the acquisition conglomerate is a LATER
evolutionary layer:

```
Older generation (in corpus):
  DAC → Blockverse → network-marketing portfolio → media concepts → DerekOS

Newer generation (pending ingestion):
  AI operating infrastructure → portfolio of businesses → acquisitions →
  corporate takeover → manufacturing/logistics → international expansion →
  Africa → corporate talent/education → physical infrastructure
```

V0.2's acceptance test is to document the documented evolution from the
first generation to the second using source evidence for every transition.
This hypothesis itself carries no authorship weight until evidenced.

---
# END OF RULE
