#!/usr/bin/env python3
"""Build a blind adjudication bundle for PROVENANCE_ADVERSARIAL_SET_V1.

For each of the 230 adversarial records, assemble from the canonical corpus:
  - full target message text, role, timestamp, sequence position
  - previous and next message in the conversation (context / adoption signals)
  - the evidence-package origin candidate (full text, role, timing) if any
  - category set

Output is written to 14_TESTS_AUDITS/adjudication_bundles/batch_*.jsonl
(one file per ~15 records). No resolver predictions are included: the
predictions file stays sealed until labels are frozen.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SET = ROOT / "14_TESTS_AUDITS" / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl"
MESSAGES = ROOT / "01_INGEST" / "messages.jsonl"
OUT_DIR = ROOT / "14_TESTS_AUDITS" / "adjudication_bundles"

C_EXCERPT = 700      # max chars for target text in bundle
O_EXCERPT = 400      # max chars for origin / context text in bundle

def load_corpus():
    msgs = {}                # message_id -> record (non-delta)
    delta_by_cid_mid = {}    # (conversation_id, message_id) -> record (delta exports: message_id not unique)
    conv_seq = defaultdict(list)  # conversation_id -> [(sequence_index, message_id)]
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
    """Resolve a message record, preferring the (conversation_id, message_id)
    key for delta-export records whose message_id values collide across
    conversations."""
    if cid is not None:
        hit = delta_by_cid_mid.get((cid, mid))
        if hit is not None:
            return hit
    r = msgs.get(mid)
    if r is not None:
        # sanity: if a non-delta id also exists under a delta conversation key,
        # the delta key wins only when conversation matches
        if cid is not None and r.get("conversation_id") != cid:
            hit = delta_by_cid_mid.get((cid, mid))
            if hit is not None:
                return hit
        return r
    return None

def excerpt(text: str, n: int) -> str:
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
        adv = [json.loads(l) for l in f if l.strip()]
    print(f"adversarial records: {len(adv)}")

    msgs, delta_by_cid_mid, conv_seq = load_corpus()
    print(f"corpus messages: {len(msgs)} + delta {len(delta_by_cid_mid)}")

    # conversation_id -> ordered list of message records
    conv_msgs = {}
    for cid, lst in conv_seq.items():
        conv_msgs[cid] = [
            r for r in (resolve(msgs, delta_by_cid_mid, mid, cid) for _, mid in lst)
            if r is not None
        ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    bundles = []
    for rec in adv:
        mid = rec["message_id"]
        m = resolve(msgs, delta_by_cid_mid, mid, rec.get("conversation_id"))
        if m is None:
            print(f"!! missing corpus record for {rec['adversarial_id']} ({mid})")
            continue
        cid = m["conversation_id"]
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
            "adversarial_id": rec["adversarial_id"],
            "categories": rec.get("categories", []),
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

    # write batches of ~15
    for i in range(0, len(bundles), 15):
        batch = bundles[i:i + 15]
        n = i // 15
        path = OUT_DIR / f"batch_{n:02d}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for b in batch:
                f.write(json.dumps(b, ensure_ascii=False) + "\n")
        print(f"wrote {path.name}: {len(batch)} records")

    print(f"total bundled: {len(bundles)}")

if __name__ == "__main__":
    main()
