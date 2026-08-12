#!/usr/bin/env python3
"""Print adjudication bundles compactly for review."""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

def show(path):
    with open(path, encoding="utf-8") as f:
        recs = [json.loads(l) for l in f if l.strip()]
    for r in recs:
        t = r["target"]
        print("=" * 100)
        print(f"{r['adversarial_id']}  cats={','.join(r['categories'])}")
        print(f"  role={t['role']} ts={t['ts']} seq={t['seq']} opening={t['is_opening']} len={t['text_len']}")
        print(f"  conv={t['conversation_title']}  src={t['source_file']}")
        fl = r.get("evidence_flags") or {}
        print(f"  flags: structured={fl.get('structured')} paste_markers={fl.get('paste_markers')} "
              f"submission_phrases={fl.get('submission_phrases')} external={fl.get('external_fingerprint')}")
        print(f"  TEXT: {t['text']}")
        c = r.get("context") or {}
        p, n = c.get("prev"), c.get("next")
        if p:
            print(f"  [PREV {p['role']}] {p['text'][:250]}")
        if n:
            print(f"  [NEXT {n['role']}] {n['text'][:250]}")
        o = r.get("origin_candidate")
        if o:
            print(f"  ORIGIN role={o['role']} ts={o['ts']} frac={o['matched_frac']} gap={o['gap_days']} "
                  f"same_conv={o['same_conversation']} distinct={o['distinct_origin_messages']}")
            print(f"  ORIGIN CONV: {o['conversation_title']}")
            print(f"  ORIGIN TEXT: {o['text']}")
        else:
            print("  ORIGIN: none located")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        show(p)
