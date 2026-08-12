#!/usr/bin/env python3
"""Build a blind adjudication bundle for PROVENANCE_OUT_OF_SAMPLE_SET_V2.

Mirrors build_out_of_sample_bundles_v1.py: full target text, prev/next context,
origin candidate, evidence flags. No resolver predictions are included.
Writes to 14_TESTS_AUDITS/out_of_sample_v2_bundles/batch_*.jsonl.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "14_TESTS_AUDITS" / "PROVENANCE_OUT_OF_SAMPLE_SET_V2.jsonl"
MESSAGES = ROOT / "01_INGEST" / "messages.jsonl"
OUT_DIR = ROOT / "14_TESTS_AUDITS" / "out_of_sample_v2_bundles"

C_EXCERPT = 700
O_EXCERPT = 400


def load_corpus():
    msgs = {}
    delta_by_cid_mid = {}
    conv_seq = defaultdict(list)
    with MESSAGES.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            mid = r["message_id"]
            if r.get("ingest_version") == "2.0.0":
                delta_by_cid_mid[(r["conversation_id"], mid)] = r
            else:
                msgs.setdefault(mid, r)
            conv_seq[r["conversation_id"]].append((r.get("sequence_index") or 0, mid))
    for cid, lst in conv_seq.items():
        lst.sort()
    return msgs, delta_by_cid_mid, conv_seq


def resolve(msgs, delta_by_cid_mid, mid, cid=None):
    if cid is not None:
        hit = delta_by_cid_mid.get((cid, mid))
        if hit is not None:
            return hit
    r = msgs.get(mid)
    if r is not None:
        if cid is not None and r.get("conversation_id") != cid:
            hit = delta_by_cid_mid.get((cid, mid))
            if hit is not None:
                return hit
        return r
    return None


def excerpt(text, n):
    if text is None:
        return ""
    t = text.strip()
    if len(t) <= n:
        return t
    return t[:n] + f" …[{len(t) - n} more chars]"


def ctx_summary(r):
    if r is None:
        return None
    return {
        "role": r["role"],
        "ts": r["timestamp"],
        "seq": r.get("sequence_index"),
        "text": excerpt(r.get("text") or "", O_EXCERPT),
    }


def main():
    with SET.open(encoding="utf-8") as f:
        recs = [json.loads(l) for l in f if l.strip()]
    print(f"V2 out-of-sample records: {len(recs)}")

    msgs, delta_by_cid_mid, conv_seq = load_corpus()

    conv_msgs = {}
    for cid, lst in conv_seq.items():
        conv_msgs[cid] = [
            r for r in (resolve(msgs, delta_by_cid_mid, mid, cid) for _, mid in lst)
            if r is not None
        ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    bundles = []
    missing = 0
    for rec in recs:
        mid = rec["message_id"]
        cid = rec["conversation_id"]
        m = resolve(msgs, delta_by_cid_mid, mid, cid)
        if m is None:
            print(f"!! missing corpus record for {rec['oos_id']} ({mid})")
            missing += 1
            continue
        cm = conv_msgs.get(cid, [])
        idx = next((i for i, x in enumerate(cm) if x["message_id"] == mid), None)
        prev = cm[idx - 1] if idx and idx > 0 else None
        nxt = cm[idx + 1] if idx is not None and idx + 1 < len(cm) else None

        ev = rec.get("evidence", {})
        reuse = ev.get("reuse") or {}
        origin = None
        omid = reuse.get("origin_message_id")
        o = resolve(msgs, delta_by_cid_mid, omid, reuse.get("origin_conversation_id")) if omid else None
        if o is not None:
            origin = {
                "message_id": omid,
                "role": o["role"],
                "ts": o["timestamp"],
                "conversation_title": o.get("conversation_title"),
                "text": excerpt(o.get("text") or "", O_EXCERPT),
                "matched_frac": reuse.get("matched_frac"),
                "gap_days": reuse.get("gap_days"),
                "same_conversation": reuse.get("same_conversation"),
                "distinct_origin_messages": reuse.get("distinct_origin_messages"),
            }

        bundles.append({
            "oos_id": rec["oos_id"],
            "families": rec.get("families", []),
            "target": {
                "role": m["role"],
                "ts": m["timestamp"],
                "seq": m.get("sequence_index"),
                "is_opening": (m.get("sequence_index") == 0),
                "conversation_title": m.get("conversation_title"),
                "source_file": m.get("source_file"),
                "ingest_version": m.get("ingest_version"),
                "text": excerpt(m.get("text") or "", C_EXCERPT),
                "text_len": len(m.get("text") or ""),
            },
            "context": {
                "prev": ctx_summary(prev),
                "next": ctx_summary(nxt),
            },
            "evidence_flags": {
                "structured": ev.get("structured"),
                "paste_markers": ev.get("paste_markers"),
                "submission_phrases": ev.get("submission_phrases"),
                "external_fingerprint": ev.get("external_fingerprint"),
            },
            "origin_candidate": origin,
        })

    for i in range(0, len(bundles), 15):
        batch = bundles[i:i + 15]
        n = i // 15
        path = OUT_DIR / f"batch_{n:02d}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for b in batch:
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
        print(f"wrote {path.name}: {len(batch)} records")

    print(f"total bundled: {len(bundles)} | missing: {missing}")


if __name__ == "__main__":
    main()
