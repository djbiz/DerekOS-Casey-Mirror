"""Score PROVENANCE_OUT_OF_SAMPLE_SET_V1: reveal sealed V0.6 predictions against
the frozen blind adjudication, report failures by family first.

Metrics (per the Board directive):
  FDA, D0 precision/recall, P0 precision/recall, MIXED precision/recall,
  UNRESOLVED rate, AD3/AD4 accuracy, span-boundary accuracy, provenance-origin
  correctness.

No tuning after seeing results. If a gate fails, a failure curriculum is
produced (separate step); V0.6 is not modified.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

AUDITS = Path(__file__).resolve().parent
LABELS = AUDITS / "FROZEN_OUT_OF_SAMPLE_ADJUDICATION_V1.jsonl"
PREDS = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json"
BUNDLES = AUDITS / "out_of_sample_bundles"

labels = {}
for line in LABELS.read_text(encoding="utf-8").splitlines():
    if line.strip():
        r = json.loads(line)
        labels[r["oos_id"]] = r

preds = json.loads(PREDS.read_text(encoding="utf-8"))["predictions"]

# family map
fam = {}
for p in sorted(BUNDLES.glob("batch_*.jsonl")):
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            r = json.loads(line)
            fam[r["oos_id"]] = r["families"]

assert set(labels) == set(preds) == set(fam), "id sets must match"

# ---------------- primary gate: False Derek Attribution ----------------
fda = [oid for oid in labels if preds[oid]["evidence_class"] == "D0" and labels[oid]["evidence_class"] != "D0"]
print("=" * 70)
print("PRIMARY GATE: False Derek Attribution (resolver says D0, truth != D0)")
print(f"  FDA = {len(fda)}   {'PASS' if not fda else 'FAIL'}")
for oid in fda:
    print(f"    {oid}: pred={preds[oid]['evidence_class']} truth={labels[oid]['evidence_class']}")

# ---------------- confusion matrix over evidence_class ----------------
classes = ["D0", "P0", "MIXED", "UNRESOLVED"]
cm = Counter((labels[oid]["evidence_class"], preds[oid]["evidence_class"]) for oid in labels)
print("\nConfusion matrix (truth -> pred):")
print("       " + "".join(f"{c:>10}" for c in classes))
for t in classes:
    row = "".join(f"{cm.get((t, p), 0):>10}" for p in classes)
    print(f"{t:>6} " + row)

# ---------------- per-class metrics ----------------
def metrics(truth_cls, pred_cls):
    tp = sum(1 for o in labels if labels[o]["evidence_class"] == truth_cls and preds[o]["evidence_class"] == pred_cls)
    fp = sum(1 for o in labels if labels[o]["evidence_class"] != truth_cls and preds[o]["evidence_class"] == pred_cls)
    fn = sum(1 for o in labels if labels[o]["evidence_class"] == truth_cls and preds[o]["evidence_class"] != pred_cls)
    prec = tp / (tp + fp) if (tp + fp) else None
    rec = tp / (tp + fn) if (tp + fn) else None
    return tp, fp, fn, prec, rec

print("\nPer-class metrics (against frozen labels):")
for cls in classes:
    tp, fp, fn, prec, rec = metrics(cls, cls)
    prec_s = f"{prec:.3f}" if prec is not None else "N/A"
    rec_s = f"{rec:.3f}" if rec is not None else "N/A"
    print(f"  {cls:>10}: TP={tp:>3} FP={fp:>3} FN={fn:>3} precision={prec_s} recall={rec_s}")

# UNRESOLVED rate
n_unres_pred = sum(1 for o in labels if preds[o]["evidence_class"] == "UNRESOLVED")
print(f"\nUNRESOLVED rate (pred): {n_unres_pred}/{len(labels)} = {n_unres_pred/len(labels):.3f}")
n_unres_truth = sum(1 for o in labels if labels[o]["evidence_class"] == "UNRESOLVED")
print(f"UNRESOLVED rate (truth): {n_unres_truth}/{len(labels)} = {n_unres_truth/len(labels):.3f}")

# ---------------- AD3/AD4 accuracy (only where truth has AD3/AD4) ----------------
ad_cases = [o for o in labels if labels[o]["adoption_status"] in ("AD3", "AD4")]
ad_correct = sum(1 for o in ad_cases if preds[o].get("adoption_status") == labels[o]["adoption_status"])
print(f"\nAD3/AD4 accuracy: {ad_correct}/{len(ad_cases)} = {ad_correct/len(ad_cases):.3f}" if ad_cases else "\nAD3/AD4: no frozen AD3/AD4 cases")
for o in ad_cases:
    if preds[o].get("adoption_status") != labels[o]["adoption_status"]:
        print(f"    AD mismatch {o}: truth={labels[o]['adoption_status']} pred={preds[o].get('adoption_status')}")

# ---------------- span-boundary accuracy (MIXED) ----------------
mixed_truth = [o for o in labels if labels[o]["evidence_class"] == "MIXED"]
mixed_pred = [o for o in labels if preds[o]["evidence_class"] == "MIXED"]
print(f"\nMIXED span-boundary: truth={len(mixed_truth)} pred={len(mixed_pred)}")

# ---------------- provenance-origin correctness ----------------
# For P0 with a located origin candidate in the bundle, check the resolver
# located an origin. (Approximate: resolver origin vs bundle origin_candidate)
origin_ok = 0
origin_total = 0
for p in sorted(BUNDLES.glob("batch_*.jsonl")):
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        oid = r["oos_id"]
        if labels[oid]["evidence_class"] == "P0":
            bundle_has_origin = r.get("origin_candidate") is not None
            pred_origin = preds[oid].get("origin_message_id") or preds[oid].get("origin_record_id")
            origin_total += 1
            if pred_origin or (not bundle_has_origin):
                origin_ok += 1
print(f"\nProvenance-origin correctness (P0, approx): {origin_ok}/{origin_total} = {origin_ok/max(1,origin_total):.3f}")

# ---------------- failures by family first ----------------
print("\n" + "=" * 70)
print("FAILURES BY FAMILY (truth class != pred class)")
fam_fail = defaultdict(list)
for oid in labels:
    if labels[oid]["evidence_class"] != preds[oid]["evidence_class"]:
        for f in fam[oid]:
            fam_fail[f].append((oid, labels[oid]["evidence_class"], preds[oid]["evidence_class"]))
for f in sorted(fam_fail):
    print(f"  {f}: {len(fam_fail[f])} mismatches")
    for oid, t, p in fam_fail[f][:12]:
        print(f"      {oid}: truth={t} pred={p}")

# family-level detail
print("\nFamily-level truth/pred class distribution:")
for f in sorted(set(x for v in fam.values() for x in v)):
    truth_c = Counter(labels[o]["evidence_class"] for o in fam if f in fam[o])
    pred_c = Counter(preds[o]["evidence_class"] for o in fam if f in fam[o])
    print(f"  {f}: truth={dict(truth_c)} pred={dict(pred_c)}")
