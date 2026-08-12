"""
Scores PROVENANCE_INDEX_V0.3's actual output (03_PROVENANCE_INDEX/v0_3/reuse_hits.jsonl)
against the SAME frozen, blind ground truth used for V0.2
(frozen_benchmark_cases.jsonl - untouched, not re-frozen, not edited).

Per the Architecture Board's explicit instruction: this is run EXACTLY ONCE
as an evaluation of the already-finished V0.3 implementation, not as
training/tuning feedback. Do not edit provenance_index_v0_3.py after seeing
this script's output and re-run it - if V0.3 gets something wrong here, that
is reported as a finding, not silently patched and re-scored.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
V03_HITS = ROOT / "03_PROVENANCE_INDEX" / "v0_3" / "reuse_hits.jsonl"

assert (BENCH_DIR / "FROZEN_BENCHMARK.json").exists(), "case file must be frozen before scoring"
assert V03_HITS.exists(), "V0.3 must have completed a full corpus run before this evaluation"

cases = [json.loads(l) for l in (BENCH_DIR / "frozen_benchmark_cases.jsonl").open(encoding="utf-8")]
hits = [json.loads(l) for l in V03_HITS.open(encoding="utf-8")]

hits_by_reuse = {}
for h in hits:
    hits_by_reuse.setdefault(h["reuse_record_id"], []).append(h)

# fb_002 correction, per FROZEN_BENCHMARK_ERRATA.md - the frozen case file's
# reuse_record_id for fb_002 is a corrupted, non-existent ID. Applying the
# same correction used for the V0.2 evaluation so the two runs are
# comparable on the same real message.
FB_002_CORRECTED_REUSE_ID = "df74d65b-86c1-4612-b691-21eb68edd205"

results = []
for c in cases:
    gt = c["ground_truth"]
    reuse_id = c["reuse_record_id"]
    if c["case_id"] == "fb_002":
        reuse_id = FB_002_CORRECTED_REUSE_ID
    origin_id = c["candidate_origin_record_id"]
    candidate_hits = hits_by_reuse.get(reuse_id, [])

    if origin_id:
        pair_hits = [h for h in candidate_hits if h["candidate_origin_record_id"] == origin_id]
    else:
        pair_hits = candidate_hits

    v03_found_any = len(candidate_hits) > 0
    v03_found_pair = len(pair_hits) > 0
    v03_edge_types = sorted(set(h["edge_type"] for h in pair_hits)) if pair_hits else []
    v03_predicted_derivation = "DERIVATION_EDGE" in v03_edge_types
    v03_chronology_valid = any(h.get("chronology_valid") for h in pair_hits) if pair_hits else None
    v03_candidate_count = max((h.get("candidate_origin_count", 1) for h in candidate_hits), default=0)
    v03_chain_ids = sorted(set(h["chain_id"] for h in pair_hits if h.get("chain_id"))) if pair_hits else []
    v03_cross_actor = any(h.get("cross_actor") for h in pair_hits) if pair_hits else None

    results.append({
        "case_id": c["case_id"],
        "category": c["category"],
        "ground_truth": gt,
        "v03_found_any_hit": v03_found_any,
        "v03_found_this_pair": v03_found_pair,
        "v03_edge_types_for_pair": v03_edge_types,
        "v03_predicted_derivation": v03_predicted_derivation,
        "v03_chronology_valid": v03_chronology_valid,
        "v03_candidate_count_for_reuse_id": v03_candidate_count,
        "v03_chain_ids": v03_chain_ids,
        "v03_cross_actor": v03_cross_actor,
        "note": c["note"],
    })

(BENCH_DIR / "scoring_raw_results_v0_3.json").write_text(
    json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"scored {len(results)} cases against {len(hits)} V0.3 hits, wrote scoring_raw_results_v0_3.json")
