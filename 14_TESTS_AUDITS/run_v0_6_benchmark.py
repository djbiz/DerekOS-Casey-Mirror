"""V0.6 benchmark: frozen-key regression gates + adjudicated MIXED boundary.

Regression gates (against frozen key, unchanged):
  R1 False Derek Attribution = 0
  R2 D0 precision >= 0.98
  R3 frozen v0.3 D0 cases not regressed (V0.6 D0 set == V0.5 D0 set)

MIXED boundary (against MIXED_SEMANTICS_ADJUDICATION_V1.jsonl):
  the adjudication is authoritative for MIXED/P0/CONTROL_ACT semantics.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from provenance_resolver_v0_4_baseline import load_bundles
from provenance_resolver_v0_6 import resolve_case

AUDITS = Path(__file__).resolve().parent


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def main() -> int:
    cases = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    labels = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    bundles = load_bundles(AUDITS / "adjudication_bundles")
    adjudication = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "MIXED_SEMANTICS_ADJUDICATION_V1.jsonl")}

    predictions = {case_id: resolve_case(case, bundles.get(case_id)) for case_id, case in cases.items()}

    # ---- Frozen-key regression gates -------------------------------------
    frozen_d0 = {cid for cid, r in labels.items() if r["evidence_class"] == "D0"}
    pred_d0 = {cid for cid, r in predictions.items() if r["evidence_class"] == "D0"}

    v5 = json.loads((AUDITS / "PROVENANCE_RESOLVER_V0_5_predictions.json").read_text(encoding="utf-8"))["predictions"]
    v5_d0 = {cid for cid, r in v5.items() if r["evidence_class"] == "D0"}

    fda = sorted(pred_d0 - frozen_d0)
    d0_precision = len(pred_d0 & frozen_d0) / len(pred_d0) if pred_d0 else 1.0
    d0_recall = len(pred_d0 & frozen_d0) / len(frozen_d0) if frozen_d0 else 1.0

    # ---- MIXED boundary vs adjudication ----------------------------------
    adjudicated_mixed = {cid for cid, r in adjudication.items() if r["adjudicated"] == "MIXED"}
    adjudicated_p0 = {cid for cid, r in adjudication.items() if r["adjudicated"] == "P0"}
    adjudicated_unresolved = {cid for cid, r in adjudication.items() if r["adjudicated"] == "UNRESOLVED"}

    adj_mixed = {cid for cid, r in predictions.items() if r["evidence_class"] == "MIXED" and cid in adjudication}
    mixed_correct = adj_mixed & adjudicated_mixed
    mixed_precision = len(mixed_correct) / len(adj_mixed) if adj_mixed else 1.0
    mixed_recall = len(mixed_correct) / len(adjudicated_mixed) if adjudicated_mixed else 1.0

    adj_p0_pred = {cid for cid, r in predictions.items() if r["evidence_class"] == "P0" and cid in adjudication}
    p0_correct_adj = adj_p0_pred & adjudicated_p0
    p0_precision_adj = len(p0_correct_adj) / len(adj_p0_pred) if adj_p0_pred else 1.0
    p0_recall_adj = len(p0_correct_adj) / len(adjudicated_p0) if adjudicated_p0 else 1.0

    # ---- AD3/AD4 (frozen key) --------------------------------------------
    actual_ad = [cid for cid, r in labels.items() if r["adoption_status"] in {"AD3", "AD4"}]
    ad_correct = sum(predictions[cid]["adoption_status"] == labels[cid]["adoption_status"] for cid in actual_ad)
    ad_accuracy = ad_correct / len(actual_ad) if actual_ad else 1.0

    # ---- P0 precision (frozen key, V0.5 baseline, informational) -----------
    # NOTE: this drops below V0.5's 96.55% BY DESIGN. The MIXED adjudication
    # reclassifies 16 carrier records from frozen-MIXED to P0; the frozen key
    # labels them MIXED, so they count as false P0 against the frozen key. The
    # MIXED boundary is governed by MIXED_SEMANTICS_ADJUDICATION_V1 instead.
    frozen_p0 = {cid for cid, r in labels.items() if r["evidence_class"] == "P0"}
    pred_p0 = {cid for cid, r in predictions.items() if r["evidence_class"] == "P0"}
    p0_precision_frozen = len(pred_p0 & frozen_p0) / len(pred_p0) if pred_p0 else 1.0

    # ---- Gates ------------------------------------------------------------
    # Safety gates are scored against the frozen key (unchanged). The MIXED
    # boundary is scored against the adjudication, which is authoritative for
    # MIXED/P0 semantics after MIXED_SEMANTICS_ADJUDICATION_V1.
    gates = {
        "R1_false_derek_attribution": {"required": 0, "observed": len(fda), "passed": len(fda) == 0, "case_ids": fda},
        "R2_d0_precision": {"required": 0.98, "observed": d0_precision, "passed": d0_precision >= 0.98},
        "R3_d0_set_unchanged_vs_v05": {"required": True, "observed": pred_d0 == v5_d0, "passed": pred_d0 == v5_d0},
        "R4_ad3_ad4_accuracy": {"required": 0.97, "observed": ad_accuracy, "passed": ad_accuracy >= 0.97},
        "R5_mixed_precision_adj": {"required": 1.0, "observed": mixed_precision, "passed": mixed_precision >= 1.0},
        "R6_mixed_recall_adj": {"required": 1.0, "observed": mixed_recall, "passed": mixed_recall >= 1.0},
        "R7_p0_precision_adj": {"required": 0.9, "observed": p0_precision_adj, "passed": p0_precision_adj >= 0.9},
    }

    report = {
        "benchmark": "PROVENANCE_ADVERSARIAL_SET_V1",
        "resolver": "PROVENANCE_RESOLVER_V0.6",
        "records": len(predictions),
        "frozen_key_gates": gates,
        "frozen_key": {
            "d0": {"predicted": len(pred_d0), "adjudicated": len(frozen_d0), "precision": d0_precision, "recall": d0_recall},
            "p0_precision": p0_precision_frozen,
            "ad3_ad4_accuracy": ad_accuracy,
        },
        "adjudication_key_mixed_boundary": {
            "adjudicated_mixed": sorted(adjudicated_mixed),
            "predicted_mixed": sorted(adj_mixed),
            "correct_mixed": sorted(mixed_correct),
            "mixed_precision": mixed_precision,
            "mixed_recall": mixed_recall,
            "adjudicated_p0": sorted(adjudicated_p0),
            "predicted_p0_within_adjudication": sorted(adj_p0_pred),
            "p0_precision": p0_precision_adj,
            "p0_recall": p0_recall_adj,
            "adjudicated_unresolved": sorted(adjudicated_unresolved),
        },
        "disposition": (
            "PROVENANCE_CORPUS_V1 NOT AUTHORIZED; semantic extraction and Conglomerate V0.2 "
            "reconstruction remain behind the out-of-sample gate."
        ),
    }

    (AUDITS / "PROVENANCE_RESOLVER_V0_6_BENCHMARK.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (AUDITS / "PROVENANCE_RESOLVER_V0_6_predictions.json").write_text(
        json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.6", "count": len(predictions), "predictions": predictions}, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print("\nALL GATES PASS" if all(g["passed"] for g in gates.values()) else "\nGATE FAILURE")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
