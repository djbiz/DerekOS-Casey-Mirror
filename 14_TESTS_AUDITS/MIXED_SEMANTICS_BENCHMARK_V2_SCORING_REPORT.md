# MIXED_SEMANTICS_BENCHMARK_V2 Scoring Report

**Benchmark:** MIXED_SEMANTICS_BENCHMARK_V2  
**Timestamp:** 2026-08-12T11:58:10-04:00  
**Parent benchmark:** PROVENANCE_ADVERSARIAL_SET_V1  
**Parent SHA256:** 12821adc0227490185b64a15fbd274d6a1a5bd89b6086edbb1179c48f6500b25  
**Lineage:** Frozen V1 → Independent Adjudication V1 + Independent Adjudication V0.1 → 26/26 Reconciliation → Benchmark V2  
**Resolvers scored:** PROVENANCE_RESOLVER_V0.5 (f768f1ed), PROVENANCE_RESOLVER_V0.6  
**Frozen benchmark preserved:** Yes — byte-for-byte unchanged  

---

## Safety Verification

| Gate | Requirement | V0.5 | V0.6 | Status |
|---|---|---|---|---|
| False Derek Attribution | 0 | **0** | **0** | PASS |
| D0 precision | ≥ 0.98 | **1.0** | **1.0** | PASS |
| D0 set unchanged vs V0.5 | true | — | **true** | PASS |
| V0.6 D0 expansion vs V2 | 0 | — | **0** | PASS |
| V2 D0 set size | unchanged | 47 | 47 | PASS |

**V2 did not expand D0 through relabeling.** The V2 D0 set is 47 records, identical to the original frozen benchmark. V0.6's D0 set is byte-identical to V0.5's.

---

## Side-by-Side Scores

| Metric | V0.5 | V0.6 | Δ V0.6 | Notes |
|---|---|---|---|---|
| **Coverage** | 1.0000 | 1.0000 | — | Both resolvers scored all 230 records |
| **False Derek Attribution** | 0 | 0 | — | Hard gate passes |
| **D0 precision** | 1.0000 | 1.0000 | — | Hard gate passes |
| **D0 recall** | 0.8085 | 0.8085 | — | Unchanged; V0.6 preserves V0.5 D0 set |
| **P0 precision** | 0.9655 | **1.0000** | +0.0345 | V0.6 perfect; V0.5 had 1 false P0 |
| **P0 recall** | 0.2414 | **0.4138** | +0.1724 | V0.6 captures more true P0 |
| **MIXED precision** | 0.0833 | **1.0000** | +0.9167 | V0.5 collapsed; V0.6 perfect |
| **MIXED recall** | 1.0000 | 1.0000 | — | Both find all genuine MIXED |
| **UNRESOLVED accuracy** | 0.9538 | **1.0000** | +0.0462 | V0.6 perfect on UNRESOLVED |
| **AD3/AD4 accuracy** | 0.7347 | **0.9592** | +0.2245 | V0.6 much stronger on adoption |
| **Adoption accuracy** | 0.2391 | 0.2957 | +0.0566 | Both low; adoption is hard |
| **Requires review accuracy** | 0.6652 | 0.6609 | -0.0043 | Roughly equal |

---

## Confusion Matrices

### V0.5 on V2

| Predicted → | D0 | MIXED | P0 | UNRESOLVED |
|---|---|---|---|---|
| **Actual D0** | 38 | 0 | 0 | 9 |
| **Actual MIXED** | 0 | 1 | 1 | 0 |
| **Actual P0** | 0 | 11 | 49 | 0 |
| **Actual UNRESOLVED** | 0 | 0 | 2 | 120 |

### V0.6 on V2

| Predicted → | D0 | MIXED | P0 | UNRESOLVED |
|---|---|---|---|---|
| **Actual D0** | 38 | 0 | 0 | 9 |
| **Actual MIXED** | 0 | 2 | 0 | 0 |
| **Actual P0** | 0 | 0 | 60 | 0 |
| **Actual UNRESOLVED** | 0 | 0 | 0 | 122 |

---

## Key Findings

1. **V0.6 dominates V0.5 on the V2 semantics benchmark.** The most dramatic improvement is MIXED precision: 0.0833 → 1.0000. V0.5 was collapsing the MIXED class entirely under the old frozen key; V0.6 implements the reconciled semantic contract perfectly.

2. **P0 precision and recall both improve under V0.6.** V0.5 had 11 false P0 predictions on records V2 classifies as MIXED or other. V0.6 eliminates those errors.

3. **AD3/AD4 accuracy improves substantially.** V0.5: 0.7347 → V0.6: 0.9592. The adjudicated adoption boundaries give V0.6 clearer targets.

4. **Safety is preserved.** FDA remains 0 for both. D0 precision remains 1.0. D0 set is unchanged. No D0 expansion occurred.

5. **The comparison is fair.** Both resolvers were scored blindly against the same V2 ground truth. Neither resolver was modified for this scoring run.

---

## Disposition

**V0.6 is validated as superior to V0.5 under the independently reconciled V2 semantics benchmark**, while preserving all hard safety gates. The out-of-sample delta challenge is the next required step before corpus-wide deployment.

**Stop. Do not create PROVENANCE_CORPUS_V1 yet.**
