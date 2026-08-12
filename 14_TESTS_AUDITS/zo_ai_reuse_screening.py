# Pasted-artifact screening for the two high-value user-role overlaps of
# Zo AI Business OS: Growth Hacker Brief (x1566) and Market Intent
# Prediction Stack (x807). Same method as ZO_AI_ANTECEDENT_RESOLUTION_V0.1:
# full text + surrounding context, shared-shingle substance check against
# the Zo AI page, earlier-source search across CORPUS_RELEASE_001.
import json, os, re, sys, time
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
CORPUS = os.path.join(ROOT, "13_SOURCE_INDEX", "corpus_releases",
                      "CORPUS_RELEASE_001", "messages.jsonl")
PAGE = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace",
                    "NOTION_EVIDENCE_RELEASE_001", "pages",
                    "33ddbc2b-713e-81de-9e7c-f6369f862744.json")
OUT = os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit",
                   "ZO_AI_REUSE_SCREENING_V0.1.json")
TARGETS = [
    "588c0736-2894-48d3-bcdf-2f2c0f6d2632",  # Growth Hacker Brief, user x1566
    "f3284e76-6f74-4a11-b93c-dcd709ca17f0",  # Market Intent Prediction Stack, user x807
]
K = 8
MIN_MATCH = 3
NORM = re.compile(r"[^a-z0-9 ]+")

def norm(t):
    return NORM.sub(" ", (t or "").lower())

def shingles(text, k=K):
    w = norm(text).split()
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}

page = json.load(open(PAGE, encoding="utf-8"))
page_sh = shingles(page.get("raw_text", ""))
print(f"page shingles: {len(page_sh)}")

# pass 1: collect target messages + their conversations
targets = {}
conv_ids = set()
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("message_id") in TARGETS:
            targets[r["message_id"]] = r
            conv_ids.add(r["conversation_id"])
convs = {cid: [] for cid in conv_ids}
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("conversation_id") in convs:
            convs[r["conversation_id"]].append(r)
for cid in convs:
    convs[cid].sort(key=lambda m: (str(m.get("timestamp")), m.get("sequence_index") or 0))
print(f"targets found: {len(targets)}")

results = []
for mid, tgt in targets.items():
    text = tgt.get("text") or ""
    t_sh = shingles(text)
    shared_page = sorted(t_sh & page_sh)
    tgt_ts = datetime.fromisoformat(str(tgt["timestamp"]).replace("Z", "+00:00"))
    print("\n" + "=" * 70)
    print(f"TARGET {mid}  role={tgt['role']}  ts={tgt['timestamp']}")
    print(f"conversation: '{tgt.get('conversation_title')}' chars={len(text)} shingles={len(t_sh)}")
    print(f"shared with Zo AI page: {len(shared_page)}")
    print("---- target text (first 1800 chars) ----")
    print(text[:1800])
    print("---- shared shingles sample (first 25 sorted) ----")
    for s in shared_page[:25]:
        print("   ", s)
    print("---- shared shingles sample (middle 15) ----")
    mid_i = len(shared_page) // 2
    for s in shared_page[mid_i:mid_i + 15]:
        print("   ", s)
    # surrounding context in same conversation
    cm = convs[tgt["conversation_id"]]
    idx = next((i for i, m in enumerate(cm) if m["message_id"] == mid), None)
    lo, hi = max(0, idx - 8), min(len(cm), idx + 9) if idx is not None else (0, 0)
    print("---- surrounding conversation context ----")
    ctx = []
    for m in cm[lo:hi]:
        mark = ">>" if m["message_id"] == mid else "  "
        print(f"{mark} {str(m.get('timestamp'))[:19]} {m.get('role'):9s} "
              f"seq={m.get('sequence_index')} len={len(m.get('text') or '')} | "
              f"{(m.get('text') or '')[:110].replace(chr(10),' ')}")
        ctx.append({"message_id": m["message_id"], "role": m.get("role"),
                    "timestamp": m.get("timestamp"),
                    "sequence_index": m.get("sequence_index"),
                    "char_count": len(m.get("text") or ""),
                    "preview": (m.get("text") or "")[:200].replace("\n", " ")})
    results.append({"target": tgt, "text": text, "shared_page": shared_page,
                    "context": ctx, "tgt_ts": tgt_ts, "t_sh": t_sh})

# pass 2: earlier-source search per target
t0 = time.time()
n = 0
prior = {mid: [] for mid in TARGETS}
later = {mid: [] for mid in TARGETS}
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        n += 1
        try:
            r = json.loads(line)
        except Exception:
            continue
        rid = r.get("message_id")
        if rid in TARGETS:
            continue
        mtext = r.get("text") or ""
        if len(mtext) < 80:
            continue
        msh = shingles(mtext)
        ts = None
        try:
            ts = datetime.fromisoformat(str(r.get("timestamp")).replace("Z", "+00:00"))
        except Exception:
            pass
        for res in results:
            c = len(msh & res["t_sh"])
            if c >= MIN_MATCH:
                entry = {"message_id": rid, "role": r.get("role"),
                         "timestamp": r.get("timestamp"),
                         "conversation_title": r.get("conversation_title"),
                         "conversation_id": r.get("conversation_id"),
                         "source_file": r.get("source_file"),
                         "matched_shingles": c,
                         "preview": mtext[:240].replace("\n", " ")}
                mid = res["target"]["message_id"]
                (prior[mid] if (ts and ts < res["tgt_ts"]) else later[mid]).append(entry)
        if n % 20000 == 0:
            print(f"  scanned {n}, {time.time()-t0:.0f}s")
print(f"scan done in {time.time()-t0:.0f}s")

out = []
for res in results:
    mid = res["target"]["message_id"]
    pr = sorted(prior[mid], key=lambda e: str(e["timestamp"]))
    la = sorted(later[mid], key=lambda e: str(e["timestamp"]))
    print(f"\n{mid}: prior {len(pr)}, later {len(la)}")
    for e in pr[:15]:
        print(f"  PRIOR {str(e['timestamp'])[:19]} {e['role']:9s} x{e['matched_shingles']:4d} "
              f"| {str(e['conversation_title'])[:42]:42s} | {str(e['source_file'])[:28]}")
    for e in la[:8]:
        print(f"  LATER {str(e['timestamp'])[:19]} {e['role']:9s} x{e['matched_shingles']:4d} "
              f"| {str(e['conversation_title'])[:42]:42s} | {str(e['source_file'])[:28]}")
    out.append({
        "target_message": {"message_id": mid, "role": res["target"]["role"],
                           "timestamp": res["target"]["timestamp"],
                           "conversation_id": res["target"]["conversation_id"],
                           "conversation_title": res["target"].get("conversation_title"),
                           "source_file": res["target"].get("source_file"),
                           "char_count": len(res["text"]), "text": res["text"]},
        "shared_shingles_with_zo_ai_page": res["shared_page"],
        "surrounding_context": res["context"],
        "prior_matches": pr,
        "later_matches": la,
    })

json.dump({
    "trace": "ZO_AI_REUSE_SCREENING_V0.1",
    "status": "CANDIDATE EVIDENCE — founder review required; nothing canonical",
    "generated": "2026-08-12",
    "method": {"k": K, "min_matched_shingles": MIN_MATCH,
               "corpus": "CORPUS_RELEASE_001 messages.jsonl",
               "page": "33ddbc2b-713e-81de-9e7c-f6369f862744 (Zo AI Business OS)"},
    "screenings": out,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nwrote {OUT}")
