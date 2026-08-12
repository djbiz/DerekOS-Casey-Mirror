# CORPUS_RELEASE_002: Gen 4 Transformation Analysis Framework

**Status:** PLANNING  
**Depends on:** GEN3_ADOPTION_CHAINS_V0.1, GEN3_PRIORITY_PROVENANCE_SET_V0.1  
**Resolver:** PROVENANCE_RESOLVER_V0.4_OR_V0.5  
**Safety Gate:** FROZEN_ADVERSARIAL_GATE

## Objective

Determine whether Gen 4 contains Derek's own new requirements, corrections, combinations, constraints, business structures, dependencies, and decisions **built on** Gen 3 propositions—or whether Gen 4 merely repeats them.

## Core Question

Did Gen 4 **transform** Gen 3's AI proposals into a substantially different corporate architecture?

## Methodology

### 1. Proposition Mapping

For each of the 18 Gen 3 propositions:
- Identify all Gen 4 occurrences
- Classify each occurrence as:
  - **VERBATIM_REUSE** — exact or near-exact repetition
  - **MODIFIED_REUSE** — same concept, altered wording/structure
  - **TRANSFORMED** — incorporated into a larger, different architecture
  - **INDEPENDENT_EXPRESSION** — Derek states the same idea in his own words
  - **SUPERSEDED** — explicitly corrected, rejected, or replaced
  - **NOT_FOUND** — no occurrence in Gen 4

### 2. Transformation Detection

Look for evidence of transformation:
- **New constraints** added to Gen 3 concepts (e.g., "HoldCos must also satisfy X")
- **Combination** with non-Gen 3 concepts (e.g., "HoldCos + Africa logistics + DerekOS")
- **Dependency creation** (e.g., "ESC depends on VOX infrastructure")
- **Implementation references** (budgets, teams, timelines, deliverables)
- **Corrections** (e.g., "not X, but Y" where X was a Gen 3 proposition)
- **Scale shifts** (e.g., from theoretical to concrete numbers, dates, locations)

### 3. Integration Depth Scoring

For each proposition in Gen 4:
- **Surface:** mentioned in passing
- **Operational:** appears in plans, SOPs, or implementation docs
- **Structural:** part of system architecture or dependencies
- **Foundational:** treated as given/assumed in later discussions

### 4. Output Schema

```json
{
  "proposition_id": "GEN3-XXX",
  "claim": "...",
  "gen4_occurrences": [
    {
      "file": "...",
      "conversation_id": "...",
      "timestamp": ...,
      "author": "user" | "assistant",
      "classification": "VERBATIM_REUSE | MODIFIED_REUSE | TRANSFORMED | INDEPENDENT_EXPRESSION | SUPERSEDED | NOT_FOUND",
      "transformation_type": "...",
      "integration_depth": "surface | operational | structural | foundational",
      "snippet": "..."
    }
  ],
  "gen4_classification": "...",
  "transformation_summary": "...",
  "integration_depth": "...",
  "evidence": "..."
}
```

## Key Distinctions to Preserve

1. **Origin ≠ Adoption ≠ Integration**
   - Origin: Who first proposed it?
   - Adoption: Was it reused/operationalized?
   - Integration: How deeply is it embedded in the broader system?

2. **Echo/Paste ≠ Transformation**
   - Echo/paste: proposition appears unchanged
   - Transformation: proposition becomes part of a larger, different architecture

3. **Gen 3 AI-origin ≠ Derek-authored**
   - Even transformed propositions retain `authored_by: assistant`
   - Transformation demonstrates Derek's *use* of the idea, not *authorship*

## Expected Outcomes

- **Best case:** Gen 4 shows Derek transforming multiple Gen 3 propositions into a new, integrated corporate architecture
- **Worst case:** Gen 4 merely echoes Gen 3 without transformation
- **Neutral case:** Mix of transformed and repeated propositions

## Next Steps

1. Identify Gen 4 corpus files
2. Run transformation detection script
3. Classify each proposition
4. Produce GEN4_TRANSFORMATION_ANALYSIS_V0.1
5. Feed results into PROVENANCE_RESOLVER_V0.4_OR_V0.5
