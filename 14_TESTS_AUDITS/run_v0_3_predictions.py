#!/usr/bin/env python3
"""Run the canonical PROVENANCE_RESOLVER_V0.3 (resolve_authorship design) on the
frozen 230-record adversarial benchmark using FULL bundle text (the same text the
adjudicators saw), then score it with the v0.1 scoring rules.

The v0.1 blind benchmark (BLIND_BENCHMARK_SCORE_V1.json) is NEVER mutated; the
v0.3 score goes to a separate file.
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
FROZEN = AUDITS / "FROZEN_ADJUDICATION_V1.jsonl"
BUNDLE_GLOB = AUDITS / "adjudication_bundles" / "batch_*.jsonl"
OUT = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1_predictions_v0_3.json"
SCORE_OUT = AUDITS / "BLIND_BENCHMARK_SCORE_V0_3.json"

sys.path.insert(0, str(AUDITS))
from provenance_resolver_v0_3 import classify_adversarial_case  # noqa: E402


def main() -> None:
    # full text + preceding role from the adjudication bundles
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

    cases = [json.loads(l) for l in open(SET, encoding="utf-8") if l.strip()]
    with FROZEN.open(encoding="utf-8") as f:
        frozen = [json.loads(l) for l in f if l.strip()]
    fmap = {r["adversarial_id"]: r for r in frozen}

    assert len(cases) == len(fmap) == 230, f"counts {len(cases)}/{len(fmap)}"
    missing = [c["adversarial_id"] for c in cases if c["adversarial_id"] not in full]
    if missing:
        print(f"WARN: no bundle text for {len(missing)}: {missing[:10]}")

    predictions = {}
    for c in cases:
        aid = c["adversarial_id"]
        # feed FULL text (adjudicator view) into the resolver
        case = dict(c)
        case["text_excerpt"] = full.get(aid, c.get("text_excerpt", ""))
        res = classify_adversarial_case(case, preceding.get(aid)).to_dict()
        predictions[aid] = {
            "adversarial_id": aid,
            "message_id": fmap[aid].get("message_id"),
            "evidence_class": res["evidence_class"],
            "adoption_status": res.get("adoption_status", "N/A"),
            "authored_by": res.get("authored_by"),
            "reason": res.get("reason", ""),
            "requires_review": res.get("requires_review", True),
            "derek_attribution_evidence": res.get("derek_attribution_evidence"),
        }

    OUT.write_text(json.dumps(
        {"resolver": "PROVENANCE_RESOLVER_V0.3", "count": len(predictions), "predictions": predictions},
        indent=1), encoding="utf-8")
    print(f"predictions written: {OUT.name} ({len(predictions)} records)")

    # ---------------- scoring (identical rules to v0.1 scorer) ----------------
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
            "title": f["conversation_title"],
        })

    fda = [r for r in rows if r["pred_class"] in DEREK and r["frozen_class"] in NO_DEREK]
    fda_mixed_seg = [r for r in rows if r["pred_class"] in DEREK and r["frozen_class"] == "MIXED"]

    pred_d0 = [r for r in rows if r["pred_class"] == "D0"]
    tp_d0 = [r for r in pred_d0 if r["frozen_class"] in DEREK]
    frozen_derek = [r for r in rows if r["frozen_class"] in DEREK]
    rec_d0_hit = [r for r in frozen_derek if r["pred_class"] == "D0"]
    d0_prec = len(tp_d0) / len(pred_d0) if pred_d0 else 0
    d0_rec = len(rec_d0_hit) / len(frozen_derek) if frozen_derek else 0

    pred_p0 = [r for r in rows if r["pred_class"] == "P0"]
    tp_p0 = [r for r in pred_p0 if r["frozen_class"] == "P0"]
    frozen_p0 = [r for r in rows if r["frozen_class"] == "P0"]
    rec_p0_hit = [r for r in frozen_p0 if r["pred_class"] == "P0"]
    p0_prec = len(tp_p0) / len(pred_p0) if pred_p0 else 0
    p0_rec = len(rec_p0_hit) / len(frozen_p0) if frozen_p0 else 0

    frozen_mixed = [r for r in rows if r["frozen_class"] == "MIXED"]
    mixed_hit = [r for r in frozen_mixed if r["pred_class"] == "MIXED"]
    mixed_acc = len(mixed_hit) / len(frozen_mixed) if frozen_mixed else 0

    frozen_unres = [r for r in rows if r["frozen_class"] == "UNRESOLVED"]
    unres_hit = [r for r in frozen_unres if r["pred_class"] == "UNRESOLVED"]
    pred_unres = [r for r in rows if r["pred_class"] == "UNRESOLVED"]
    unres_prec = len(unres_hit) / len(pred_unres) if pred_unres else 0
    unres_rec = len(unres_hit) / len(frozen_unres) if frozen_unres else 0
    over_abstain = [r for r in pred_unres if r["frozen_class"] != "UNRESOLVED"]
    under_abstain = [r for r in frozen_unres if r["pred_class"] != "UNRESOLVED"]

    frozen_ad3 = [r for r in rows if r["frozen_adopt"] in ("AD3", "AD4")]
    ad3_hit = [r for r in frozen_ad3 if r["pred_adopt"] in ("AD3", "AD4")]
    ad3_acc = len(ad3_hit) / len(frozen_ad3) if frozen_ad3 else 0

    exact = sum(1 for r in rows if r["pred_class"] == r["frozen_class"])
    acc = exact / len(rows)
    conf = Counter((r["pred_class"], r["frozen_class"]) for r in rows)

    print("=" * 72)
    print("BLIND BENCHMARK V0.3: resolver v0.3 vs frozen adjudication (230)")
    print("=" * 72)
    print(f"overall exact-class accuracy: {acc:.3f}  ({exact}/230)")
    print()
    print("PRIMARY GATE — False Derek Attribution:")
    print(f"  FDA = {len(fda)}   {'PASS ✓' if len(fda) == 0 else 'FAIL ✗'}")
    for r in fda:
        print(f"    {r['aid']}: pred={r['pred_class']} frozen={r['frozen_class']} | {r['title'][:50]}")
    print(f"  (D0-predicted on MIXED = {len(fda_mixed_seg)} — segmentation misses, not FDA)")
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

    result = {
        "n": len(rows),
        "resolver": "provenance_resolver_v0_3",
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
    SCORE_OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print()
    print(f"score file written: {SCORE_OUT.name}")


if __name__ == "__main__":
    main()
