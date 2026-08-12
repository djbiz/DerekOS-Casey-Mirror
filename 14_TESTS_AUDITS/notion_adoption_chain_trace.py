# Adoption chain trace for the five founder-approved Notion candidates.
# Chain: earliest located occurrence -> transformations -> Notion creation
#        -> later reuse/implementation evidence.
# Sources: CORPUS_RELEASE_001 messages.jsonl vs NOTION_EVIDENCE_RELEASE_001 pages.
import json, os, re, sys, time
from datetime import datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
PAGES = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace",
                     "NOTION_EVIDENCE_RELEASE_001", "pages")
CORPUS = os.path.join(ROOT, "13_SOURCE_INDEX", "corpus_releases",
                      "CORPUS_RELEASE_001", "messages.jsonl")
OUT = os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit",
                   "NOTION_ADOPTION_CHAINS_V0.1.json")
K = 8
MIN_MATCH = 3
NORM = re.compile(r"[^a-z0-9 ]+")

def norm(t):
    return NORM.sub(" ", (t or "").lower())

def shingles(text, k=K):
    w = norm(text).split()
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}

def ts(x):
    if not x:
        return None
    try:
        return datetime.fromisoformat(str(x).replace("Z", "+00:00"))
    except Exception:
        return None

targets = ["DAC Marketing Meeting Agenda",
           "DAC Performance Dashboard",
           "THE ULTIMATE PROMPT STACK",
           "DAC 30-Day Content Plan",
           "Zo AI Business OS"]

pages = {}   # pid -> record
index = {}   # shingle -> set(pid)
for fn in os.listdir(PAGES):
    rec = json.load(open(os.path.join(PAGES, fn), encoding="utf-8"))
    title = rec.get("page_title", "")
    if not any(t in title for t in targets):
        continue
    pid = rec["page_id"]
    pages[pid] = rec
    for s in shingles(rec.get("raw_text", "")):
        index.setdefault(s, set()).add(pid)
print(f"target pages: {len(pages)}; shingles indexed: {len(index)}")

hits = {}
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
            pids = index.get(" ".join(words[i:i + K]))
            if pids:
                for p in pids:
                    local[p] = local.get(p, 0) + 1
        for pid, c in local.items():
            if c >= MIN_MATCH:
                hits[(pid, r["message_id"])] = {
                    "page_id": pid, "message_id": r["message_id"],
                    "conversation_id": r["conversation_id"],
                    "conversation_title": r.get("conversation_title"),
                    "source_file": r.get("source_file"),
                    "role": r.get("role"), "timestamp": r.get("timestamp"),
                    "matched_shingles": c,
                    "text_preview": text[:240].replace("\n", " ")}
        if n % 20000 == 0:
            print(f"  scanned {n}, hits {len(hits)}, {time.time()-t0:.0f}s")
print(f"scan done: {n} messages in {time.time()-t0:.0f}s; hits {len(hits)}")

chains = []
for pid, rec in sorted(pages.items(), key=lambda kv: kv[1]["page_title"]):
    ms = sorted((h for h in hits.values() if h["page_id"] == pid),
                key=lambda h: str(h["timestamp"]))
    created = ts(rec.get("created_time"))
    edited = ts(rec.get("last_edited_time"))
    pre, post, undated = [], [], []
    for h in ms:
        t = ts(h["timestamp"])
        if not created or not t:
            undated.append(h)
        elif t <= created:
            pre.append(h)
        else:
            post.append(h)
    user_msgs = [h for h in ms if h["role"] == "user"]
    chain = {
        "page_id": pid,
        "page_title": rec.get("page_title"),
        "notion_created_time": rec.get("created_time"),
        "notion_last_edited_time": rec.get("last_edited_time"),
        "created_by": rec.get("created_by"),
        "last_edited_by": rec.get("last_edited_by"),
        "total_corpus_matches": len(ms),
        "matches_before_notion_creation": len(pre),
        "matches_after_notion_creation": len(post),
        "matches_undated": len(undated),
        "user_role_matches": len(user_msgs),
        "earliest_occurrence": ms[0] if ms else None,
        "pre_creation_timeline": pre,
        "post_creation_reuse": post,
        "undated_matches": undated,
    }
    chains.append(chain)
    print(f"\n== {rec.get('page_title')}")
    print(f"   notion created {rec.get('created_time')} by {rec.get('created_by')}")
    print(f"   corpus matches: {len(ms)} (pre {len(pre)} / post {len(post)}; user-role {len(user_msgs)})")
    if ms:
        e = ms[0]
        print(f"   earliest: {e['timestamp']} role={e['role']} x{e['matched_shingles']} '{e['conversation_title']}'")

json.dump({
    "trace": "NOTION_ADOPTION_CHAINS_V0.1",
    "status": "CANDIDATE_EVIDENCE — founder review required; nothing canonical",
    "generated": "2026-08-12",
    "method": {"k": K, "min_matched_shingles": MIN_MATCH,
               "corpus": "CORPUS_RELEASE_001 messages.jsonl",
               "notion": "NOTION_EVIDENCE_RELEASE_001"},
    "chains": chains,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nwrote {OUT}")
