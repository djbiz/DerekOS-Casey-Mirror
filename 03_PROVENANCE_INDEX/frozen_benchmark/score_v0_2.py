"""
Scores PROVENANCE_INDEX_V0.2's actual output (03_PROVENANCE_INDEX/v0_2/reuse_hits.jsonl)
against the frozen, blind ground truth in frozen_benchmark_cases.jsonl.

Run only AFTER the case file is frozen (FROZEN_BENCHMARK.json exists) - this
script must never influence the case file's ground truth, only read it.

Per the Architecture Board directive: this script does not tune or modify
V0.2. It reports what V0.2 actually did, honestly, including failures.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
V02_HITS = ROOT / "03_PROVENANCE_INDEX" / "v0_2" / "reuse_hits.jsonl"

assert (BENCH_DIR / "FROZEN_BENCHMARK.json").exists(), "case file must be frozen before scoring"

cases = [json.loads(l) for l in (BENCH_DIR / "frozen_benchmark_cases.jsonl").open(encoding="utf-8")]
hits = [json.loads(l) for l in V02_HITS.open(encoding="utf-8")]

hits_by_reuse = {}
for h in hits:
    hits_by_reuse.setdefault(h["reuse_record_id"], []).append(h)

results = []
for c in cases:
    gt = c["ground_truth"]
    reuse_id = c["reuse_record_id"]
    origin_id = c["candidate_origin_record_id"]
    candidate_hits = hits_by_reuse.get(reuse_id, [])

    # narrow to the specific candidate pair this case is about, if one is given
    if origin_id:
        pair_hits = [h for h in candidate_hits if h["candidate_origin_record_id"] == origin_id]
    else:
        pair_hits = candidate_hits

    v02_found_any = len(candidate_hits) > 0
    v02_found_pair = len(pair_hits) > 0
    v02_edge_types = sorted(set(h["edge_type"] for h in pair_hits)) if pair_hits else []
    v02_predicted_derivation = "DERIVATION_EDGE" in v02_edge_types
    v02_predicted_similarity_only = v02_edge_types == ["SIMILARITY_EDGE"]
    v02_chronology_valid = any(h.get("chronology_valid") for h in pair_hits) if pair_hits else None
    v02_candidate_count = max((h.get("candidate_origin_count", 1) for h in candidate_hits), default=0)

    results.append({
        "case_id": c["case_id"],
        "category": c["category"],
        "ground_truth": gt,
        "v02_found_any_hit": v02_found_any,
        "v02_found_this_pair": v02_found_pair,
        "v02_edge_types_for_pair": v02_edge_types,
        "v02_predicted_derivation": v02_predicted_derivation,
        "v02_chronology_valid": v02_chronology_valid,
        "v02_candidate_count_for_reuse_id": v02_candidate_count,
        "note": c["note"],
    })

(BENCH_DIR / "scoring_raw_results.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"scored {len(results)} cases against {len(hits)} V0.2 hits, wrote scoring_raw_results.json")
