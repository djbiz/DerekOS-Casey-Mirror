#!/usr/bin/env python3
"""Score the blind adjudication: frozen labels vs resolver predictions.

Primary gate: False Derek Attribution = 0
(records frozen with ZERO Derek authorship -- P0/UNRESOLVED/A0 -- that the
 resolver labeled D0/D1.)

Secondary metrics:
- D0 precision / recall
- P0 precision / recall
- MIXED segmentation accuracy
- abstention quality (over / under)
- AD3/AD4 classification accuracy
- origin-candidate precision (where predictions carry origin info)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
PREDS = ROOT / "14_TESTS_AUDITS" / "PROVENANCE_ADVERSARIAL_SET_V1_predictions.json"
FROZEN = ROOT / "14_TESTS_AUDITS" / "FROZEN_ADJUDICATION_V1.jsonl"

def main():
    with PREDS.open(encoding="utf-8") as f:
        raw = json.load(f)
    preds = raw["predictions"]
    frozen = [json.loads(l) for l in FROZEN.open(encoding="utf-8")]
    fmap = {r["adversarial_id"]: r for r in frozen}

    assert set(preds) == set(fmap), "prediction/frozen id mismatch"

    DEREK = {"D0", "D1"}
    NO_DEREK = {"P0", "A0", "X0", "UNRESOLVED"}

    rows = []
    for aid, p in preds.items():
        f = fmap[aid]
        rows.append({
            "aid": aid,
            "pred_class": p["evidence_class"],
            "pred_adopt": p.get("adoption_status"),
            "pred_certainty": p.get("provenance_certainty"),
            "pred_review": p.get("requires_review", False),
            "pred_origin": p.get("origin_record_id") or p.get("origin_message_id"),
            "frozen_class": f["evidence_class"],
            "frozen_adopt": f["adoption_status"],
            "frozen_origin": f["origin_record_id"],
            "frozen_review": f["requires_review"],
            "title": f["conversation_title"],
        })

    # ---------------- primary gate ----------------
    fda = [r for r in rows if r["pred_class"] in DEREK and r["frozen_class"] in NO_DEREK]
    fda_mixed_seg = [r for r in rows if r["pred_class"] in DEREK and r["frozen_class"] == "MIXED"]

    # ---------------- D0 precision / recall ----------------
    pred_d0 = [r for r in rows if r["pred_class"] == "D0"]
    tp_d0 = [r for r in pred_d0 if r["frozen_class"] in DEREK]
    frozen_derek = [r for r in rows if r["frozen_class"] in DEREK]
    rec_d0_hit = [r for r in frozen_derek if r["pred_class"] == "D0"]
    d0_prec = len(tp_d0) / len(pred_d0) if pred_d0 else 0
    d0_rec = len(rec_d0_hit) / len(frozen_derek) if frozen_derek else 0

    # ---------------- P0 precision / recall ----------------
    pred_p0 = [r for r in rows if r["pred_class"] == "P0"]
    tp_p0 = [r for r in pred_p0 if r["frozen_class"] == "P0"]
    frozen_p0 = [r for r in rows if r["frozen_class"] == "P0"]
    rec_p0_hit = [r for r in frozen_p0 if r["pred_class"] == "P0"]
    p0_prec = len(tp_p0) / len(pred_p0) if pred_p0 else 0
    p0_rec = len(rec_p0_hit) / len(frozen_p0) if frozen_p0 else 0

    # ---------------- MIXED segmentation ----------------
    frozen_mixed = [r for r in rows if r["frozen_class"] == "MIXED"]
    mixed_hit = [r for r in frozen_mixed if r["pred_class"] == "MIXED"]
    mixed_acc = len(mixed_hit) / len(frozen_mixed) if frozen_mixed else 0

    # ---------------- abstention quality ----------------
    frozen_unres = [r for r in rows if r["frozen_class"] == "UNRESOLVED"]
    unres_hit = [r for r in frozen_unres if r["pred_class"] == "UNRESOLVED"]
    pred_unres = [r for r in rows if r["pred_class"] == "UNRESOLVED"]
    unres_prec = len(unres_hit) / len(pred_unres) if pred_unres else 0
    unres_rec = len(unres_hit) / len(frozen_unres) if frozen_unres else 0
    over_abstain = [r for r in pred_unres if r["frozen_class"] != "UNRESOLVED"]
    under_abstain = [r for r in frozen_unres if r["pred_class"] != "UNRESOLVED"]

    # ---------------- AD3/AD4 classification ----------------
    frozen_ad3 = [r for r in rows if r["frozen_adopt"] in ("AD3", "AD4")]
    ad3_hit = [r for r in frozen_ad3 if r["pred_adopt"] in ("AD3", "AD4")]
    ad3_acc = len(ad3_hit) / len(frozen_ad3) if frozen_ad3 else 0

    # ---------------- overall accuracy ----------------
    exact = sum(1 for r in rows if r["pred_class"] == r["frozen_class"])
    acc = exact / len(rows)

    # ---------------- confusion ----------------
    conf = Counter((r["pred_class"], r["frozen_class"]) for r in rows)

    print("=" * 72)
    print("BLIND BENCHMARK: resolver vs frozen adjudication (230 records)")
    print("=" * 72)
    print(f"overall exact-class accuracy: {acc:.3f}  ({exact}/230)")
    print()
    print("PRIMARY GATE — False Derek Attribution (pred D0/D1 on zero-Derek records):")
    print(f"  FDA = {len(fda)}   {'PASS ✓' if len(fda) == 0 else 'FAIL ✗'}")
    for r in fda:
        print(f"    {r['aid']}: pred={r['pred_class']} frozen={r['frozen_class']} | {r['title'][:50]}")
    print(f"  (D0-predicted on MIXED records = {len(fda_mixed_seg)} — segmentation misses, not FDA)")
    print()
    print("SECONDARY METRICS:")
    print(f"  D0 precision  = {d0_prec:.3f}  ({len(tp_d0)}/{len(pred_d0)})")
    print(f"  D0 recall     = {d0_rec:.3f}  ({len(rec_d0_hit)}/{len(frozen_derek)})")
    print(f"  P0 precision  = {p0_prec:.3f}  ({len(tp_p0)}/{len(pred_p0)})")
    print(f"  P0 recall     = {p0_rec:.3f}  ({len(rec_p0_hit)}/{len(frozen_p0)})")
    print(f"  MIXED seg acc = {mixed_acc:.3f}  ({len(mixed_hit)}/{len(frozen_mixed)})")
    print(f"  abstention prec = {unres_prec:.3f} ({len(unres_hit)}/{len(pred_unres)})  recall = {unres_rec:.3f} ({len(unres_hit)}/{len(frozen_unres)})")
    print(f"  over-abstention = {len(over_abstain)}  under-abstention = {len(under_abstain)}")
    print(f"  AD3/AD4 acc   = {ad3_acc:.3f}  ({len(ad3_hit)}/{len(frozen_ad3)})")
    print()
    print("CONFUSION (pred -> frozen):")
    for k in sorted(conf):
        print(f"  {k[0]:>10} -> {k[1]:<10} {conf[k]}")

    # write a machine-readable result file
    out = ROOT / "14_TESTS_AUDITS" / "BLIND_BENCHMARK_SCORE_V1.json"
    result = {
        "n": len(rows),
        "overall_accuracy": round(acc, 4),
        "primary_gate_false_derek_attribution": len(fda),
        "primary_gate_pass": len(fda) == 0,
        "fda_records": [r["aid"] for r in fda],
        "d0_predictions_on_mixed": len(fda_mixed_seg),
        "d0_precision": round(d0_prec, 4),
        "d0_recall": round(d0_rec, 4),
        "p0_precision": round(p0_prec, 4),
        "p0_recall": round(p0_rec, 4),
        "mixed_segmentation_accuracy": round(mixed_acc, 4),
        "abstention_precision": round(unres_prec, 4),
        "abstention_recall": round(unres_rec, 4),
        "over_abstention": len(over_abstain),
        "under_abstention": len(under_abstain),
        "ad3_ad4_accuracy": round(ad3_acc, 4),
        "confusion": {f"{a}->{b}": n for (a, b), n in sorted(conf.items())},
    }
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print()
    print(f"score file written: {out.name}")

if __name__ == "__main__":
    main()
