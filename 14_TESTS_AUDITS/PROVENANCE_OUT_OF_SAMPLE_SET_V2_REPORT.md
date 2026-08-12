# PROVENANCE_OUT_OF_SAMPLE_SET_V2 — Build Report

Blind out-of-sample provenance challenge. Population: the DeepSeek delta-export
user messages (ingest_version 2.0.0, source_file=conversations.json) MINUS:
  - all Gold Set message ids (v1 and v1.1)
  - all 230 adversarial-set keys
  - all MIXED adjudication records
None of these records were used in Gold Set construction, adversarial selection,
MIXED adjudication, or V0.3-V0.6 development.

- **Records**: 201 unique user-role delta messages
- **Population**: 1494 delta user messages after exclusions
- **Excluded**: 40 gold ids, 230 adversarial keys, 26 mixed ids
- **Selection**: mechanical family signals only; stratified explicit families,
  24 target per family, seed 20260812
- **Blindness**: the set file carries record + evidence + text only;
  V0.6 predictions will be sealed separately AFTER this set is frozen.

## Family distribution

| Family | Meaning | Selected |
|--------|---------|----------|
| USER_ROLE_PASTED_ARTIFACT | user-role pasted artifacts | 135 |
| MULTI_AGENT_RELAY_CHAIN | multi-agent relay chains | 146 |
| CONTROL_ACT_PLUS_IMPORTED_BODY | control-act carrier + imported body | 89 |
| CROSS_PLATFORM_AI_REUSE | cross-platform AI reuse | 148 |
| EXTERNAL_MATERIAL | external material / fingerprints | 115 |
| REWRITTEN_AI_MATERIAL | rewritten AI material | 24 |
| CHRONOLOGY_ANOMALY | chronology anomalies | 15 |
| MISSING_ORIGIN | missing-origin content | 30 |
| LONG_POLISHED_FIRST_PERSON | long polished first-person material | 5 |
| SHORT_FOUNDER_DIRECTIVE | short founder directives | 31 |
| D0_POSITIVE_CONTROL | D0-positive controls | 1 |
| GENUINE_MIXED_SPANS | genuine mixed spans (mechanical proxy) | 0 |

## Next step

1. Freeze this V2 set as the challenge input.
2. Run PROVENANCE_RESOLVER_V0.6 on V2 and seal predictions in a separate key file.
3. Build blind adjudication bundles from V2.
4. Independent human adjudication establishes answer key WITHOUT access to V0.6 predictions.
5. Reveal sealed predictions and score. Primary gates: FDA=0, D0 precision ≥98%.
6. If V0.6 passes, freeze result and stop for authorization before PROVENANCE_CORPUS_V1.
7. If V0.6 fails, preserve failure set as next curriculum. No tuning against challenge.
