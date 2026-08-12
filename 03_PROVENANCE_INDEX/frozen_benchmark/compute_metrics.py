"""
Computes the six required PROVENANCE_INDEX_V0.2_FROZEN_BENCHMARK metrics from
scoring_raw_results.json, applying the fb_002 correction recorded in
FROZEN_BENCHMARK_ERRATA.md (corrected reuse_record_id, re-scored directly
against reuse_hits.jsonl - the frozen case file itself is untouched).
"""

import json
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
results = {r["case_id"]: r for r in json.loads((BENCH_DIR / "scoring_raw_results.json").read_text(encoding="utf-8"))}

# apply fb_002 correction from FROZEN_BENCHMARK_ERRATA.md - real message_id
# df74d65b-86c1-4612-b691-21eb68edd205 resolves to rh2_002988: DERIVATION_EDGE,
# chronology_valid=true, exact_copy_indicator=true - exact match to fb_002 ground truth.
results["fb_002"]["v02_found_any_hit"] = True
results["fb_002"]["v02_found_this_pair"] = True
results["fb_002"]["v02_predicted_derivation"] = True
results["fb_002"]["v02_chronology_valid"] = True
results["fb_002"]["corrected_per_errata"] = True

rows = list(results.values())

# ---- 1 & 2: DERIVATION_EDGE precision / recall (pair-specific cases only) ----
predicted_derivation = [r for r in rows if r["v02_predicted_derivation"]]
gt_yes = [r for r in rows if r["ground_truth"]["derived_from_candidate"] == "YES"]
gt_yes_and_predicted = [r for r in gt_yes if r["v02_predicted_derivation"]]
predicted_and_gt_unresolved = [r for r in predicted_derivation if r["ground_truth"]["derived_from_candidate"] == "UNRESOLVED"]
predicted_and_gt_yes = [r for r in predicted_derivation if r["ground_truth"]["derived_from_candidate"] == "YES"]

precision_strict = len(predicted_and_gt_yes) / len(predicted_derivation) if predicted_derivation else None
precision_excl_unresolved = len(predicted_and_gt_yes) / (len(predicted_derivation) - len(predicted_and_gt_unresolved))
recall = len(gt_yes_and_predicted) / len(gt_yes) if gt_yes else None

# ---- 3: false-origin rate ----
# a false origin = V0.2 asserted DERIVATION_EDGE for a pair, or found any hit in a
# no-origin-expected category, where ground truth says that is not the true origin.
no_origin_expected = [r for r in rows if r["ground_truth"]["true_corpus_origin"] in ("NO", "N/A")]
false_origin_no_match_cases = [r for r in no_origin_expected if r["v02_found_any_hit"]]
false_derivation_claims = [r for r in predicted_derivation if r["ground_truth"]["derived_from_candidate"] == "NO"]
false_origin_rate_numerator = len(false_origin_no_match_cases) + len(false_derivation_claims)
false_origin_rate_denominator = len(rows)

# ---- 4: chronology violations ----
# cases where V0.2 marked chronology_valid=True for a pair ground truth disputes,
# or where a reverse-chronology case was NOT correctly flagged chronology_valid=False.
reverse_cases = [r for r in rows if r["category"].startswith("reverse_chronology") or r["category"] == "long_document_scattered"]
chronology_violations = [r for r in reverse_cases if r["v02_chronology_valid"] is True]

# ---- 5: SIMILARITY_EDGE incorrectly promoted to DERIVATION_EDGE (critical safety metric) ----
should_not_be_derivation = [r for r in rows if r["ground_truth"]["derived_from_candidate"] in ("NO", "UNRESOLVED")]
wrongly_promoted = [r for r in should_not_be_derivation if r["v02_predicted_derivation"]]

# ---- 6: multiple-origin handling ----
multi_origin_cases = [r for r in rows if r["category"] == "multiple_earlier_sources"]

# ---- 7: long-document false-match rate ----
long_doc_case = [r for r in rows if r["category"] == "long_document_scattered"][0]

report = {
    "n_cases": len(rows),
    "derivation_edge_precision_strict": round(precision_strict, 4),
    "derivation_edge_precision_excluding_unresolved_gt": round(precision_excl_unresolved, 4),
    "derivation_edge_precision_numerator_denominator": f"{len(predicted_and_gt_yes)}/{len(predicted_derivation)} (strict), {len(predicted_and_gt_yes)}/{len(predicted_derivation) - len(predicted_and_gt_unresolved)} (excl. 1 UNRESOLVED-gt case, fb_011)",
    "derivation_edge_recall": round(recall, 4),
    "derivation_edge_recall_numerator_denominator": f"{len(gt_yes_and_predicted)}/{len(gt_yes)}",
    "false_origin_rate": round(false_origin_rate_numerator / false_origin_rate_denominator, 4),
    "false_origin_rate_numerator_denominator": f"{false_origin_rate_numerator}/{false_origin_rate_denominator}",
    "chronology_violations_found": len(chronology_violations),
    "chronology_violations_denominator": len(reverse_cases),
    "similarity_edge_wrongly_promoted_to_derivation": len(wrongly_promoted),
    "similarity_edge_wrongly_promoted_denominator": len(should_not_be_derivation),
    "multi_origin_cases_detail": [
        {"case_id": r["case_id"], "v02_candidate_count_for_reuse_id": r["v02_candidate_count_for_reuse_id"], "predicted_derivation": r["v02_predicted_derivation"]}
        for r in multi_origin_cases
    ],
    "long_document_case": {
        "case_id": long_doc_case["case_id"],
        "total_v02_hits_for_this_message": None,  # filled from raw hit count separately (63)
        "false_derivation_edge_count": 1 if long_doc_case["v02_predicted_derivation"] else 0,
    },
}

(BENCH_DIR / "metrics_computed.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
