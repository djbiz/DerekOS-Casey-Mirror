# PROVENANCE_OUT_OF_SAMPLE_SET_V1 — Build Report

Blind out-of-sample provenance challenge. Population: the 3,080 delta-export
records (DeepSeek platform) minus all Gold Set ids, all 230 adversarial-set
records, and all MIXED adjudication records. None of these records were used
in Gold Set construction, adversarial selection, MIXED adjudication, or V0.6
development.

- **Records**: 163 unique user-role delta messages
- **Population**: 1494 delta user messages after exclusions
- **Excluded**: 40 gold ids, 230 adversarial keys
- **Selection**: mechanical family signals only; stratified F01-F09,
  24 target per family, seed 20260812
- **Blindness**: the set file carries evidence + text only; V0.6 predictions
  are sealed in PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json

## Family distribution

| Family | Meaning | Selected |
|--------|---------|----------|
| F01 | carrier + paste | 82 |
| F02 | substantive Derek modification + paste | 73 |
| F03 | transcript wrappers | 0 |
| F04 | rewrite requests | 24 |
| F05 | cross-platform AI reuse | 131 |
| F06 | Derek->AI->Derek chains | 131 |
| F07 | external->Derek->AI chains | 31 |
| F08 | long polished first-person material | 5 |
| F09 | unknown-origin content | 26 |

## Next step

Manual blind adjudication of all records (Claude / Audit Bot). Assign per
record: evidence_class, adoption_status, provenance_certainty, requires_review,
origin_record_id. Primary gate: **False Derek Attribution = 0**. Then reveal
the sealed V0.6 predictions and score. No tuning after seeing results.
