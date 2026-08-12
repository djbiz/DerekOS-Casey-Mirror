# Cross-source reuse scan: NOTION_EVIDENCE_RELEASE_001 vs CORPUS_RELEASE_001
import json, os, sys, re, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
PAGES = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace",
                     "NOTION_EVIDENCE_RELEASE_001", "pages")
CORPUS = os.path.join(ROOT, "13_SOURCE_INDEX", "corpus_releases",
                      "CORPUS_RELEASE_001", "messages.jsonl")
OUT = os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit",
                   "cross_source_matches.json")
K = 8
NORM = re.compile(r"[^a-z0-9 ]+")

def norm(t):
    return NORM.sub(" ", (t or "").lower())

def shingles(text, k=K):
    words = norm(text).split()
    return {" ".join(words[i:i + k]) for i in range(len(words) - k + 1)}

index = {}  # shingle -> set(page_id)
page_titles = {}
for fn in os.listdir(PAGES):
    rec = json.load(open(os.path.join(PAGES, fn), encoding="utf-8"))
    pid = rec["page_id"]
    page_titles[pid] = rec.get("page_title", "")
    ss = sorted(shingles(rec.get("raw_text", "")))
    if len(ss) > 400:
        step = len(ss) / 400
        ss = [ss[int(i * step)] for i in range(400)]
    for s in ss:
        index.setdefault(s, set()).add(pid)
print("notion shingles indexed:", len(index), "pages:", len(page_titles))

hits = {}  # (page_id, message_id) -> info
t0 = time.time()
n = 0
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        n += 1
        try:
            r = json.loads(line)
        except Exception:
            continue
        text = r.get("text") or ""
        if len(text) < 80:
            continue
        words = norm(text).split()
        if len(words) < K:
            continue
        local = {}
        for i in range(len(words) - K + 1):
            s = " ".join(words[i:i + K])
            pids = index.get(s)
            if pids:
                for p in pids:
                    local[p] = local.get(p, 0) + 1
        for pid, c in local.items():
            if c >= 3:
                key = (pid, r["message_id"])
                prev = hits.get(key)
                if not prev or c > prev["matched_shingles"]:
                    hits[key] = {"page_id": pid, "page_title": page_titles[pid],
                                 "message_id": r["message_id"],
                                 "conversation_id": r["conversation_id"],
                                 "conversation_title": r.get("conversation_title"),
                                 "source_file": r.get("source_file"),
                                 "role": r.get("role"),
                                 "timestamp": r.get("timestamp"),
                                 "matched_shingles": c,
                                 "text_preview": text[:160].replace("\n", " ")}
        if n % 10000 == 0:
            print(f"  scanned {n} messages, hits so far {len(hits)}, {time.time()-t0:.0f}s")

matches = sorted(hits.values(), key=lambda v: -v["matched_shingles"])
json.dump({"scan": {"k": K, "min_matched_shingles": 3,
                    "messages_scanned": n,
                    "release_compared": ["NOTION_EVIDENCE_RELEASE_001", "CORPUS_RELEASE_001"]},
           "match_count": len(matches), "matches": matches[:200]},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nDONE: scanned {n} messages in {time.time()-t0:.0f}s; matches (>=3 shingles): {len(matches)}")
for m in matches[:20]:
    print(f"  x{m['matched_shingles']:4d}  {m['page_title'][:38]:38s} <- {str(m['conversation_title'])[:36]:36s} {str(m['timestamp'])[:10]} {m['role']}")
