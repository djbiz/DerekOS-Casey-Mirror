#!/usr/bin/env python3
"""PROVENANCE_RESOLVER_V0.4 — blind benchmark vs frozen 230 (committed key).

Regression gates (automatic fail if violated):
  R1  False Derek Attribution = 0
  R2  D0 precision >= 0.98
  R3  frozen v0.3 safety cases do not regress
      (every v0.3 D0 prediction must remain D0 in v0.4)

Gate 4 metrics: P0 precision/recall, MIXED precision/recall (span level).
Gate 5 metrics: AD3/AD4 accuracy.
"""
from __future__ import annotations

import glob
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent
AUDITS = ROOT / "14_TESTS_AUDITS"
SET = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl"
FROZEN = AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl"
BUNDLE_GLOB = AUDITS / "adjudication_bundles" / "batch_*.jsonl"
V03_PREDS = AUDITS / "PROVENANCE_RESOLVER_V0_3_predictions.json"
OUT = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1_predictions_v0_4_gate5.json"
SCORE_OUT = AUDITS / "BLIND_BENCHMARK_SCORE_V0_4_GATE5.json"

sys.path.insert(0, str(AUDITS))
from provenance_resolver_v0_4_gate5 import classify_gate5  # noqa: E402


def main() -> None:
    # full text + preceding role from bundles (adjudicator view)
    full: dict[str, str] = {}
    preceding: dict[str, str | None] = {}
    for p in sorted(glob.glob(str(BUNDLE_GLOB))):
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            b = json.loads(line)
            aid = b["adversarial_id"]
            full[aid] = b["target"]["text"]
            prev = (b.get("context") or {}).get("prev") or {}
            preceding[aid] = prev.get("role")

    cases = [json.loads(l) for l in open(SET, encoding="utf-8-sig") if l.strip()]
    frozen = [json.loads(l) for l in open(FROZEN, encoding="utf-8-sig") if l.strip()]
    fmap = {r["adversarial_id"]: r for r in frozen}
    v03 = json.load(open(V03_PREDS, encoding="utf-8"))["predictions"]

    predictions = {}
    for c in cases:
        aid = c["adversarial_id"]
        case = dict(c)
        case["text_excerpt"] = full.get(aid, c.get("text_excerpt", ""))
        res = classify_gate5(case, preceding.get(aid)).to_dict()
        predictions[aid] = {
            "adversarial_id": aid,
            "message_id": fmap[aid].get("message_id"),
            "evidence_class": res["evidence_class"],
            "adoption_status": res.get("adoption_status", "N/A"),
            "authored_by": res.get("authored_by"),
            "submitted_by": res.get("submitted_by"),
            "adopted_by": res.get("adopted_by"),
            "derek_attribution_evidence": res.get("derek_attribution_evidence"),
            "reason": res.get("reason", ""),
            "requires_review": res.get("requires_review", True),
            "segments": res.get("positive_evidence", []),
        }

    OUT.write_text(json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.4", "count": len(predictions), "predictions": predictions}, indent=1), encoding="utf-8")
    print(f"predictions written: {OUT.name} ({len(predictions)} records)")

    # ---------------- scoring ----------------
    DEREK = {"D0", "D1"}
    NO_DEREK = {"P0", "A0", "X0", "UNRESOLVED"}

    rows = []
    for aid, p in predictions.items():
        f = fmap[aid]
        rows.append({
            "aid": aid,
            "pred_class": p["evidence_class"],
            "pred_adopt": p.get("adoption_status"),
            "frozen_class": f["evidence_class"],
            "frozen_adopt": f.get("adoption_status"),
            "title": f.get("conversation_title") or "",
        })

    # R1: False Derek Attribution
    fda = [r for r in rows if r["pred_class"] in DEREK and r["frozen_class"] in NO_DEREK]
    # R3: v0.3 safety cases (its D0 predictions) must remain D0 in v0.4
    v03_d0 = {aid for aid, p in v03.items() if p.get("evidence_class") == "D0"}
    regressed = [aid for aid in v03_d0 if predictions[aid]["evidence_class"] != "D0"]

    # R2: D0 precision
    pred_d0 = [r for r in rows if r["pred_class"] == "D0"]
    tp_d0 = [r for r in pred_d0 if r["frozen_class"] in DEREK]
    d0_prec = len(tp_d0) / len(pred_d0) if pred_d0 else 0
    frozen_derek = [r for r in rows if r["frozen_class"] in DEREK]
    d0_rec = sum(1 for r in frozen_derek if r["pred_class"] == "D0") / len(frozen_derek) if frozen_derek else 0

    # Gate 4: P0 + MIXED
    pred_p0 = [r for r in rows if r["pred_class"] == "P0"]
    tp_p0 = [r for r in pred_p0 if r["frozen_class"] == "P0"]
    frozen_p0 = [r for r in rows if r["frozen_class"] == "P0"]
    p0_prec = len(tp_p0) / len(pred_p0) if pred_p0 else 0
    p0_rec = sum(1 for r in frozen_p0 if r["pred_class"] == "P0") / len(frozen_p0) if frozen_p0 else 0

    pred_mixed = [r for r in rows if r["pred_class"] == "MIXED"]
    tp_mixed = [r for r in pred_mixed if r["frozen_class"] == "MIXED"]
    frozen_mixed = [r for r in rows if r["frozen_class"] == "MIXED"]
    mixed_prec = len(tp_mixed) / len(pred_mixed) if pred_mixed else 0
    mixed_rec = sum(1 for r in frozen_mixed if r["pred_class"] == "MIXED") / len(frozen_mixed) if frozen_mixed else 0

    # Gate 5: AD3/AD4
    frozen_ad34 = [r for r in rows if r["frozen_adopt"] in ("AD3", "AD4")]
    ad34_hit = [r for r in frozen_ad34 if r["pred_adopt"] in ("AD3", "AD4")]
    ad34_acc = len(ad34_hit) / len(frozen_ad34) if frozen_ad34 else 0

    # abstention
    frozen_unres = [r for r in rows if r["frozen_class"] == "UNRESOLVED"]
    pred_unres = [r for r in rows if r["pred_class"] == "UNRESOLVED"]
    unres_hit = [r for r in frozen_unres if r["pred_class"] == "UNRESOLVED"]
    unres_prec = len(unres_hit) / len(pred_unres) if pred_unres else 0
    unres_rec = len(unres_hit) / len(frozen_unres) if frozen_unres else 0

    exact = sum(1 for r in rows if r["pred_class"] == r["frozen_class"])
    acc = exact / len(rows)
    conf = Counter((r["pred_class"], r["frozen_class"]) for r in rows)

    r1_pass = len(fda) == 0
    r2_pass = d0_prec >= 0.98
    r3_pass = len(regressed) == 0
    all_pass = r1_pass and r2_pass and r3_pass

    print("=" * 72)
    print("BLIND BENCHMARK V0.4 vs frozen 230 (committed key)")
    print("=" * 72)
    print("REGRESSION GATES")
    print(f"  R1 FDA=0            : {len(fda)}  {'PASS' if r1_pass else 'FAIL'}")
    for r in fda:
        print(f"      {r['aid']}: pred={r['pred_class']} frozen={r['frozen_class']}")
    print(f"  R2 D0 precision>=.98: {d0_prec:.3f} ({len(tp_d0)}/{len(pred_d0)})  {'PASS' if r2_pass else 'FAIL'}")
    print(f"  R3 v0.3 D0 regressed : {len(regressed)}  {'PASS' if r3_pass else 'FAIL'}")
    if regressed:
        for a in regressed[:20]:
            print(f"      {a}: v0.3 D0 -> v0.4 {predictions[a]['evidence_class']}")
    print()
    print("GATE 4 — P0 + MIXED")
    print(f"  P0 precision = {p0_prec:.3f} ({len(tp_p0)}/{len(pred_p0)})   recall = {p0_rec:.3f} ({len(tp_p0)}/{len(frozen_p0)})")
    print(f"  MIXED precision = {mixed_prec:.3f} ({len(tp_mixed)}/{len(pred_mixed)})   recall = {mixed_rec:.3f} ({len(tp_mixed)}/{len(frozen_mixed)})")
    print("GATE 5 — Adoption")
    print(f"  AD3/AD4 accuracy = {ad34_acc:.3f} ({len(ad34_hit)}/{len(frozen_ad34)})")
    print()
    print(f"D0 precision = {d0_prec:.3f}  recall = {d0_rec:.3f}")
    print(f"abstention prec = {unres_prec:.3f} ({len(unres_hit)}/{len(pred_unres)})  recall = {unres_rec:.3f}")
    print(f"exact-class accuracy = {acc:.3f} ({exact}/{len(rows)})")
    print()
    print("CONFUSION (pred -> frozen):")
    for k in sorted(conf):
        print(f"  {k[0]:>10} -> {k[1]:<10} {conf[k]}")
    print()
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}  (R1={r1_pass} R2={r2_pass} R3={r3_pass})")

    result = {
        "n": len(rows), "resolver": "provenance_resolver_v0_4",
        "regression": {
            "R1_false_derek_attribution": len(fda), "R1_pass": r1_pass,
            "R2_d0_precision": round(d0_prec, 4), "R2_pass": r2_pass,
            "R3_v03_d0_regressed": len(regressed), "R3_pass": r3_pass,
            "all_pass": all_pass,
        },
        "gate4": {
            "p0_precision": round(p0_prec, 4), "p0_recall": round(p0_rec, 4),
            "mixed_precision": round(mixed_prec, 4), "mixed_recall": round(mixed_rec, 4),
            "mixed_false_positives": [r["aid"] for r in pred_mixed if r["frozen_class"] != "MIXED"],
            "mixed_misses": [r["aid"] for r in frozen_mixed if r["pred_class"] != "MIXED"],
        },
        "gate5": {"ad3_ad4_accuracy": round(ad34_acc, 4),
                  "ad34_misses": [r["aid"] for r in frozen_ad34 if r["pred_adopt"] not in ("AD3", "AD4")]},
        "overall_accuracy": round(acc, 4),
        "d0_precision": round(d0_prec, 4), "d0_recall": round(d0_rec, 4),
        "abstention_precision": round(unres_prec, 4), "abstention_recall": round(unres_rec, 4),
        "confusion": {f"{a}->{b}": n for (a, b), n in sorted(conf.items())},
    }
    SCORE_OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nscore file written: {SCORE_OUT.name}")


if __name__ == "__main__":
    main()
