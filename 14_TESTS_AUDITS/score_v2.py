import json
from datetime import datetime, timezone

# Load V2 benchmark
with open(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\MIXED_SEMANTICS_BENCHMARK_V2.json', 'r', encoding='utf-8') as f:
    v2 = json.load(f)

# Load original V1 labels for unchanged records
v1_labels = {}
with open(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\blind_adjudication\PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl', 'r', encoding='utf-8-sig') as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            v1_labels[rec["adversarial_id"]] = rec

# Build V2 ground truth: V1 labels + V2 overrides
v2_ground_truth = {}
for aid, rec in v1_labels.items():
    if aid in v2["v2_overrides"]:
        override = v2["v2_overrides"][aid]
        v2_ground_truth[aid] = {
            "adversarial_id": aid,
            "evidence_class": override["v2_evidence_class"],
            "adoption_status": override["v2_adoption_status"],
            "requires_review": override["v2_requires_review"],
            "source": "V2_OVERRIDE"
        }
    else:
        v2_ground_truth[aid] = {
            "adversarial_id": aid,
            "evidence_class": rec["evidence_class"],
            "adoption_status": rec["adoption_status"],
            "requires_review": rec["requires_review"],
            "source": "V1_ORIGINAL"
        }

# Load predictions
def load_predictions(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("predictions", {})

v05_preds = load_predictions(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\PROVENANCE_RESOLVER_V0_5_predictions.json')
v06_preds = load_predictions(r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\PROVENANCE_RESOLVER_V0_6_predictions.json')

# Score a resolver against V2
def score_resolver(predictions, ground_truth):
    results = {
        "total_records": 0,
        "covered_records": 0,
        "false_derek_attribution": 0,
        "d0": {"predicted": 0, "adjudicated": 0, "correct": 0},
        "p0": {"predicted": 0, "adjudicated": 0, "correct": 0},
        "mixed": {"predicted": 0, "adjudicated": 0, "correct": 0},
        "unresolved": {"predicted": 0, "adjudicated": 0, "correct": 0},
        "ad3_ad4": {"predicted": 0, "adjudicated": 0, "correct": 0},
        "adoption_correct": 0,
        "requires_review_correct": 0
    }
    
    for aid, gt in ground_truth.items():
        results["total_records"] += 1
        pred = predictions.get(aid)
        if not pred:
            continue
        results["covered_records"] += 1
        
        pred_class = pred.get("evidence_class", "UNRESOLVED")
        gt_class = gt["evidence_class"]
        pred_adoption = pred.get("adoption_status", "AD0")
        gt_adoption = gt["adoption_status"]
        
        # Count adjudicated
        results[gt_class.lower()]["adjudicated"] += 1
        results["d0"]["adjudicated"] += 1 if gt_class == "D0" else 0
        results["p0"]["adjudicated"] += 1 if gt_class == "P0" else 0
        results["mixed"]["adjudicated"] += 1 if gt_class == "MIXED" else 0
        results["unresolved"]["adjudicated"] += 1 if gt_class == "UNRESOLVED" else 0
        
        # Count predicted
        results[pred_class.lower()]["predicted"] += 1
        results["d0"]["predicted"] += 1 if pred_class == "D0" else 0
        results["p0"]["predicted"] += 1 if pred_class == "P0" else 0
        results["mixed"]["predicted"] += 1 if pred_class == "MIXED" else 0
        results["unresolved"]["predicted"] += 1 if pred_class == "UNRESOLVED" else 0
        
        # False Derek Attribution: predicted D0 but gt is not D0
        if pred_class == "D0" and gt_class != "D0":
            results["false_derek_attribution"] += 1
        
        # Correct classification
        if pred_class == gt_class:
            results[gt_class.lower()]["correct"] += 1
            results["d0"]["correct"] += 1 if gt_class == "D0" else 0
            results["p0"]["correct"] += 1 if gt_class == "P0" else 0
            results["mixed"]["correct"] += 1 if gt_class == "MIXED" else 0
            results["unresolved"]["correct"] += 1 if gt_class == "UNRESOLVED" else 0
        
        # Adoption accuracy for AD3/AD4
        if gt_adoption in ["AD3", "AD4"]:
            results["ad3_ad4"]["adjudicated"] += 1
            if pred_adoption == gt_adoption:
                results["ad3_ad4"]["correct"] += 1
            results["ad3_ad4"]["predicted"] += 1 if pred_adoption in ["AD3", "AD4"] else 0
        
        # Overall adoption accuracy
        if pred_adoption == gt_adoption:
            results["adoption_correct"] += 1
        
        # Requires review accuracy
        pred_review = pred.get("requires_review", False)
        gt_review = gt.get("requires_review", False)
        if pred_review == gt_review:
            results["requires_review_correct"] += 1
    
    # Compute rates
    def rate(correct, adjudicated):
        return correct / adjudicated if adjudicated > 0 else 0.0
    
    results["d0"]["precision"] = rate(results["d0"]["correct"], results["d0"]["predicted"])
    results["d0"]["recall"] = rate(results["d0"]["correct"], results["d0"]["adjudicated"])
    results["p0"]["precision"] = rate(results["p0"]["correct"], results["p0"]["predicted"])
    results["p0"]["recall"] = rate(results["p0"]["correct"], results["p0"]["adjudicated"])
    results["mixed"]["precision"] = rate(results["mixed"]["correct"], results["mixed"]["predicted"])
    results["mixed"]["recall"] = rate(results["mixed"]["correct"], results["mixed"]["adjudicated"])
    results["unresolved"]["rate"] = rate(results["unresolved"]["correct"], results["unresolved"]["adjudicated"])
    results["ad3_ad4"]["accuracy"] = rate(results["ad3_ad4"]["correct"], results["ad3_ad4"]["adjudicated"])
    results["adoption_accuracy"] = rate(results["adoption_correct"], results["total_records"])
    results["requires_review_accuracy"] = rate(results["requires_review_correct"], results["total_records"])
    results["coverage"] = results["covered_records"] / results["total_records"] if results["total_records"] > 0 else 0
    
    return results

v05_scores = score_resolver(v05_preds, v2_ground_truth)
v06_scores = score_resolver(v06_preds, v2_ground_truth)

# Verify D0 set unchanged
v05_d0_set = set(aid for aid, pred in v05_preds.items() if pred.get("evidence_class") == "D0")
v06_d0_set = set(aid for aid, pred in v06_preds.items() if pred.get("evidence_class") == "D0")
d0_unchanged = v05_d0_set == v06_d0_set

# Verify no D0 expansion via relabeling
v2_d0_set = set(aid for aid, gt in v2_ground_truth.items() if gt["evidence_class"] == "D0")
v06_d0_expansion = v06_d0_set - v2_d0_set

# Build report
report = {
    "benchmark": "MIXED_SEMANTICS_BENCHMARK_V2",
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "parent_benchmark": "PROVENANCE_ADVERSARIAL_SET_V1",
    "parent_benchmark_sha256": v2["parent_benchmark_sha256"],
    "lineage": v2["lineage"],
    "total_records": v2["total_records"],
    "v2_overrides_count": len(v2["v2_overrides"]),
    "safety_verification": {
        "d0_set_unchanged_v05_v06": d0_unchanged,
        "v06_d0_expansion_vs_v2": list(v06_d0_expansion),
        "v06_d0_expansion_count": len(v06_d0_expansion),
        "no_d0_expansion": len(v06_d0_expansion) == 0
    },
    "resolvers": {
        "PROVENANCE_RESOLVER_V0.5": {
            "resolver": "PROVENANCE_RESOLVER_V0.5",
            "commit": "f768f1ed22f9022918b63efb20c5e7ececae4b73",
            "total_records": v05_scores["total_records"],
            "covered_records": v05_scores["covered_records"],
            "coverage": v05_scores["coverage"],
            "false_derek_attribution": v05_scores["false_derek_attribution"],
            "d0": {
                "predicted": v05_scores["d0"]["predicted"],
                "adjudicated": v05_scores["d0"]["adjudicated"],
                "correct": v05_scores["d0"]["correct"],
                "precision": v05_scores["d0"]["precision"],
                "recall": v05_scores["d0"]["recall"]
            },
            "p0": {
                "predicted": v05_scores["p0"]["predicted"],
                "adjudicated": v05_scores["p0"]["adjudicated"],
                "correct": v05_scores["p0"]["correct"],
                "precision": v05_scores["p0"]["precision"],
                "recall": v05_scores["p0"]["recall"]
            },
            "mixed": {
                "predicted": v05_scores["mixed"]["predicted"],
                "adjudicated": v05_scores["mixed"]["adjudicated"],
                "correct": v05_scores["mixed"]["correct"],
                "precision": v05_scores["mixed"]["precision"],
                "recall": v05_scores["mixed"]["recall"]
            },
            "unresolved": {
                "predicted": v05_scores["unresolved"]["predicted"],
                "adjudicated": v05_scores["unresolved"]["adjudicated"],
                "correct": v05_scores["unresolved"]["correct"],
                "accuracy": v05_scores["unresolved"]["rate"]
            },
            "ad3_ad4_accuracy": v05_scores["ad3_ad4"]["accuracy"],
            "adoption_accuracy": v05_scores["adoption_accuracy"],
            "requires_review_accuracy": v05_scores["requires_review_accuracy"]
        },
        "PROVENANCE_RESOLVER_V0.6": {
            "resolver": "PROVENANCE_RESOLVER_V0.6",
            "total_records": v06_scores["total_records"],
            "covered_records": v06_scores["covered_records"],
            "coverage": v06_scores["coverage"],
            "false_derek_attribution": v06_scores["false_derek_attribution"],
            "d0": {
                "predicted": v06_scores["d0"]["predicted"],
                "adjudicated": v06_scores["d0"]["adjudicated"],
                "correct": v06_scores["d0"]["correct"],
                "precision": v06_scores["d0"]["precision"],
                "recall": v06_scores["d0"]["recall"]
            },
            "p0": {
                "predicted": v06_scores["p0"]["predicted"],
                "adjudicated": v06_scores["p0"]["adjudicated"],
                "correct": v06_scores["p0"]["correct"],
                "precision": v06_scores["p0"]["precision"],
                "recall": v06_scores["p0"]["recall"]
            },
            "mixed": {
                "predicted": v06_scores["mixed"]["predicted"],
                "adjudicated": v06_scores["mixed"]["adjudicated"],
                "correct": v06_scores["mixed"]["correct"],
                "precision": v06_scores["mixed"]["precision"],
                "recall": v06_scores["mixed"]["recall"]
            },
            "unresolved": {
                "predicted": v06_scores["unresolved"]["predicted"],
                "adjudicated": v06_scores["unresolved"]["adjudicated"],
                "correct": v06_scores["unresolved"]["correct"],
                "accuracy": v06_scores["unresolved"]["rate"]
            },
            "ad3_ad4_accuracy": v06_scores["ad3_ad4"]["accuracy"],
            "adoption_accuracy": v06_scores["adoption_accuracy"],
            "requires_review_accuracy": v06_scores["requires_review_accuracy"]
        }
    }
}

# Write report
report_path = r'D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\MIXED_SEMANTICS_BENCHMARK_V2_SCORING_REPORT.json'
with open(report_path, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"Scoring report written: {report_path}")
print(f"\n=== V0.5 vs V0.6 on MIXED_SEMANTICS_BENCHMARK_V2 ===")
print(f"Records: {v05_scores['total_records']}")
print(f"Coverage: V0.5={v05_scores['coverage']:.4f}, V0.6={v06_scores['coverage']:.4f}")
print(f"False Derek Attribution: V0.5={v05_scores['false_derek_attribution']}, V0.6={v06_scores['false_derek_attribution']}")
print(f"D0 precision: V0.5={v05_scores['d0']['precision']:.4f}, V0.6={v06_scores['d0']['precision']:.4f}")
print(f"D0 recall: V0.5={v05_scores['d0']['recall']:.4f}, V0.6={v06_scores['d0']['recall']:.4f}")
print(f"P0 precision: V0.5={v05_scores['p0']['precision']:.4f}, V0.6={v06_scores['p0']['precision']:.4f}")
print(f"P0 recall: V0.5={v05_scores['p0']['recall']:.4f}, V0.6={v06_scores['p0']['recall']:.4f}")
print(f"MIXED precision: V0.5={v05_scores['mixed']['precision']:.4f}, V0.6={v06_scores['mixed']['precision']:.4f}")
print(f"MIXED recall: V0.5={v05_scores['mixed']['recall']:.4f}, V0.6={v06_scores['mixed']['recall']:.4f}")
print(f"UNRESOLVED accuracy: V0.5={v05_scores['unresolved']['rate']:.4f}, V0.6={v06_scores['unresolved']['rate']:.4f}")
print(f"AD3/AD4 accuracy: V0.5={v05_scores['ad3_ad4']['accuracy']:.4f}, V0.6={v06_scores['ad3_ad4']['accuracy']:.4f}")
print(f"Adoption accuracy: V0.5={v05_scores['adoption_accuracy']:.4f}, V0.6={v06_scores['adoption_accuracy']:.4f}")
print(f"Requires review accuracy: V0.5={v05_scores['requires_review_accuracy']:.4f}, V0.6={v06_scores['requires_review_accuracy']:.4f}")
print(f"\nD0 set unchanged V0.5 vs V0.6: {d0_unchanged}")
print(f"V0.6 D0 expansion vs V2: {len(v06_d0_expansion)} records")
print(f"V2 D0 set size: {len(v2_d0_set)}")
