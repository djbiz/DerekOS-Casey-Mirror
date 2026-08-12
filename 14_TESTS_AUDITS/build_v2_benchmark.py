import json
import hashlib
from datetime import datetime, timezone

# Load original frozen benchmark
with open(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json', 'r', encoding='utf-8') as f:
    original = json.load(f)

# Compute SHA256 of original benchmark JSON (canonical form)
original_bytes = json.dumps(original, sort_keys=True, ensure_ascii=False).encode('utf-8')
original_hash = hashlib.sha256(original_bytes).hexdigest()

# Load V0.1 adjudication (reconciled) - it's a JSON array, not JSONL
with open(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\MIXED_LABEL_SEMANTICS_ADJUDICATION_V0.1.jsonl', 'r', encoding='utf-8') as f:
    v01_data = json.load(f)
    v01_lines = v01_data if isinstance(v01_data, list) else [v01_data]

# Load V1 adjudication (independent) - actual JSONL
with open(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\MIXED_SEMANTICS_ADJUDICATION_V1.jsonl', 'r', encoding='utf-8') as f:
    v1_lines = [json.loads(line) for line in f if line.strip()]

# Build V2 benchmark
v2 = {
    "benchmark": "MIXED_SEMANTICS_BENCHMARK_V2",
    "schema_version": "2.0",
    "parent_benchmark": "PROVENANCE_ADVERSARIAL_SET_V1",
    "parent_benchmark_sha256": original_hash,
    "lineage": [
        "Frozen V1 (PROVENANCE_ADVERSARIAL_SET_V1)",
        "Independent Adjudication V1 (MIXED_SEMANTICS_ADJUDICATION_V1)",
        "Independent Adjudication V0.1 (MIXED_LABEL_SEMANTICS_ADJUDICATION_V0.1)",
        "26/26 Reconciliation (MIXED_SEMANTICS_RECONCILIATION_MATRIX_V0.1)",
        "Benchmark V2 (this file)"
    ],
    "reconciliation_references": {
        "v1_adjudication": "MIXED_SEMANTICS_ADJUDICATION_V1.jsonl",
        "v01_adjudication": "MIXED_LABEL_SEMANTICS_ADJUDICATION_V0.1.jsonl",
        "reconciliation_matrix": "MIXED_SEMANTICS_RECONCILIATION_MATRIX_V0.1.md",
        "agreement_count": 26,
        "disagreement_count": 0,
        "schema_only_difference_count": 0
    },
    "frozen_benchmark_preserved": True,
    "frozen_benchmark_path": "PROVENANCE_ADVERSARIAL_BENCHMARK_V1.json",
    "frozen_benchmark_sha256": original_hash,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "total_records": 230,
    "semantic_contract": {
        "rule": "A message is MIXED only when at least two independently attributable semantic spans exist and both contribute substantive meaning to the resulting message.",
        "carrier_collapse": "CONTROL_ACT, LABEL, and QUERY spans do not independently establish MIXED authorship. Carrier + imported/assistant-authored substantive body -> P0 + appropriate adoption status.",
        "dual_authorship_requirement": "Both spans must have different supported provenance.",
        "d0_rule": "D0 requires positive Derek-authorship evidence; ambiguity remains UNRESOLVED.",
        "genuine_mixed_set": ["adv_003597", "adv_021989"]
    },
    "original_benchmark": original,
    "v2_overrides": {}
}

# Build overrides for the 26 disputed records
for rec in v01_lines:
    aid = rec["adversarial_id"]
    v2["v2_overrides"][aid] = {
        "adversarial_id": aid,
        "v2_evidence_class": rec["proposed_semantics_label"],
        "v2_adoption_status": rec["adoption"],
        "v2_requires_review": rec["requires_review"],
        "v2_family": rec["families"],
        "v2_span_boundaries": rec["span_boundaries"],
        "v2_derek_span_substantive": rec["derek_span_substantive"],
        "v2_governing_rule": rec["governing_rule"],
        "v2_evidence": rec["evidence"],
        "v2_rationale": rec["rationale"],
        "frozen_label": rec["current_frozen_label"],
        "v1_adjudicated": rec["proposed_semantics_label"],
        "v01_adjudicated": rec["proposed_semantics_label"],
        "reconciliation_status": "AGREEMENT"
    }

# Write V2 benchmark
v2_path = r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\MIXED_SEMANTICS_BENCHMARK_V2.json'
with open(v2_path, 'w', encoding='utf-8') as f:
    json.dump(v2, f, indent=2, ensure_ascii=False)

print(f"V2 benchmark written: {v2_path}")
print(f"Original benchmark SHA256: {original_hash}")
print(f"V2 overrides: {len(v2['v2_overrides'])}")
print(f"V2 total records: {v2['total_records']}")
