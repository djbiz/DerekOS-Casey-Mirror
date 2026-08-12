# MIXED_SEMANTICS_RECONCILIATION_MATRIX_V0.1

**Purpose:** Record-by-record reconciliation of `MIXED_LABEL_SEMANTICS_ADJUDICATION_V0.1` against `MIXED_SEMANTICS_ADJUDICATION_V1`.
**Rule:** Neither source adjudication is modified. This matrix only classifies the relationship between them.
**Benchmark policy:** Original frozen benchmark is preserved permanently. Any revision is append-only/superseding.

---

## Summary

| Metric | Count | Notes |
|---|---|---|
| Total disputed records | 26 | Full set |
| AGREEMENT | 26 | Substantive semantic class and span function taxonomy agree |
| DISAGREEMENT | 0 | None |
| SCHEMA-ONLY DIFFERENCE | 0 | None on substantive class; schema fields differ but conclusions align |

**Verdict:** Both independent adjudications reach the same substantive conclusion on all 26 records. This supports creating `MIXED_SEMANTICS_BENCHMARK_V2` as an append-only/superseding semantics benchmark.

---

## Record-by-record matrix

| # | adversarial_id | V1 adjudicated | V0.1 proposed | V1 adoption | V0.1 adoption | V1 family | V0.1 family | Relationship |
|---|---|---|---|---|---|---|---|---|
| 1 | adv_000346 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 2 | adv_000735 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 3 | adv_000941 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 4 | adv_030261 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 5 | adv_030897 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 6 | adv_032963 | P0 | P0 | AD3 | AD3 | FAMILY_A | FAMILY_A | AGREEMENT |
| 7 | adv_001324 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 8 | adv_001326 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 9 | adv_029474 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 10 | adv_031597 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 11 | adv_033054 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 12 | adv_007563 | P0 | P0 | AD4 | AD4 | FAMILY_C | FAMILY_C | AGREEMENT |
| 13 | adv_007820 | P0 | P0 | AD4 | AD4 | FAMILY_C | FAMILY_C | AGREEMENT |
| 14 | adv_001443 | P0 | P0 | AD4 | AD4 | FAMILY_B | FAMILY_B | AGREEMENT |
| 15 | adv_018155 | P0 | P0 | AD2 | AD2 | FAMILY_D | FAMILY_D | AGREEMENT |
| 16 | adv_019425 | P0 | P0 | AD2 | AD2 | FAMILY_D | FAMILY_D | AGREEMENT |
| 17 | adv_013001 | P0 | P0 | AD0 | AD0 | FAMILY_D | FAMILY_D | AGREEMENT |
| 18 | adv_014438 | P0 | P0 | AD1 | AD1 | FAMILY_E | FAMILY_E | AGREEMENT |
| 19 | adv_006905 | P0 | P0 | AD2 | AD2 | FAMILY_F | FAMILY_F | AGREEMENT |
| 20 | adv_009750 | P0 | P0 | AD1 | AD1 | FAMILY_G | FAMILY_G | AGREEMENT |
| 21 | adv_002059 | UNRESOLVED | UNRESOLVED | AD4 | AD4 | FAMILY_H | FAMILY_H | AGREEMENT |
| 22 | adv_017999 | UNRESOLVED | UNRESOLVED | AD0 | AD0 | FAMILY_I | FAMILY_I | AGREEMENT |
| 23 | adv_001444 | UNRESOLVED | UNRESOLVED | AD2 | AD2 | FAMILY_I | FAMILY_I | AGREEMENT |
| 24 | adv_004101 | UNRESOLVED | UNRESOLVED | AD1 | AD1 | FAMILY_J | FAMILY_J | AGREEMENT |
| 25 | adv_003597 | MIXED | MIXED | AD1 | AD1 | FAMILY_K | FAMILY_K | AGREEMENT |
| 26 | adv_021989 | MIXED | MIXED | AD4 | AD4 | FAMILY_K | FAMILY_K | AGREEMENT |

---

## Family-level agreement

| Family | Records | V1 conclusion | V0.1 conclusion | Agreement |
|---|---|---|---|---|
| FAMILY_A_TRANSCRIPT_TEMPLATE | 6 | P0 + AD3 | P0 + AD3 | Full |
| FAMILY_B_STYLE_CARRIER | 7 | P0 + AD4 | P0 + AD4 | Full |
| FAMILY_C_RECREATE | 2 | P0 + AD4 | P0 + AD4 | Full |
| FAMILY_D_QUERY_CODE | 3 | P0 + AD2/AD0 | P0 + AD2/AD0 | Full |
| FAMILY_E_LABEL_QUOTE | 1 | P0 + AD1 | P0 + AD1 | Full |
| FAMILY_F_INTENT_URL | 1 | P0 + AD2 | P0 + AD2 | Full |
| FAMILY_G_QUERY_LIST | 1 | P0 + AD1 | P0 + AD1 | Full |
| FAMILY_H_OWN_MESSAGE | 1 | UNRESOLVED + AD4 | UNRESOLVED + AD4 | Full |
| FAMILY_I_PURE_REQUIREMENT | 2 | UNRESOLVED + AD0/AD2 | UNRESOLVED + AD0/AD2 | Full |
| FAMILY_J_OWN_DATA | 1 | UNRESOLVED + AD1 | UNRESOLVED + AD1 | Full |
| FAMILY_K_GENUINE_MIXED | 2 | MIXED + AD1/AD4 | MIXED + AD1/AD4 | Full |

---

## Cross-audit findings

1. **Substantive class agreement is 100%.** Both adjudications classify the same records as P0, MIXED, or UNRESOLVED.
2. **Adoption agreement is 100%.** Both assign the same AD level to every record.
3. **Family taxonomy agreement is 100%.** Both use identical family groupings.
4. **Span function agreement is 100%.** Both assign CONTROL_ACT, QUERY, LABEL, REQUIREMENT, DATA_SUBMISSION, and IMPORTED_CONTENT identically.
5. **Genuine MIXED set is identical.** Both retain exactly `adv_003597` and `adv_021989` as the only genuine MIXED records.

---

## Recommendation

Because two independent semantic adjudications agree on all 26 disputed records, the frozen benchmark's MIXED boundary should be superseded by a **MIXED_SEMANTICS_BENCHMARK_V2** with the following properties:

- **Append-only:** V2 is appended after V1 in the benchmark file. V1 is never modified.
- **Semantic contract:** V2 encodes the substantive-meaning rule:
  > A message is MIXED only when at least two independently attributable semantic spans exist and both contribute substantive meaning to the resulting message.
- **Carrier collapse rule:** CONTROL_ACT, LABEL, and QUERY spans do not create MIXED. They resolve to P0 + adoption.
- **Dual-authorship requirement:** Both spans must have different supported provenance.
- **Fail-closed D0:** D0-leaning records stay UNRESOLVED unless affirmative Derek-authorship evidence clears the threshold.

This V2 should then be used to score V0.5 and V0.6 unchanged, preserving the original frozen benchmark for regression gates.
