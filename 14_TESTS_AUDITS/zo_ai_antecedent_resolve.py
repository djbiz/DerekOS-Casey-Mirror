# Resolve the 2025-07-15 user-role antecedent of Zo AI Business OS.
# Question: is the user message itself a reuse of earlier (AI or other)
# material, or does it originate with the founder in the searched corpus?
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
                   "ZO_AI_ANTECEDENT_RESOLUTION_V0.1.json")
TARGET_MID = "bbb21af4-fd69-461f-9fff-12ec6ab8da00"
K = 8
MIN_MATCH = 3
NORM = re.compile(r"[^a-z0-9 ]+")

def norm(t):
    return NORM.sub(" ", (t or "").lower())

def shingles(text, k=K):
    w = norm(text).split()
    return {" ".join(w[i:i + k]) for i in range(len(w) - k + 1)}

# 1. load target + conversation context
target = None
conv_msgs = []
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("message_id") == TARGET_MID:
            target = r
        if target and r.get("conversation_id") == target["conversation_id"]:
            conv_msgs.append(r)
        elif not target:
            pass
if not target:
    raise SystemExit("target message not found")
# second pass for conversation if needed
if len(conv_msgs) < 2:
    conv_msgs = []
    with open(CORPUS, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("conversation_id") == target["conversation_id"]:
                conv_msgs.append(r)
conv_msgs.sort(key=lambda m: (str(m.get("timestamp")), m.get("sequence_index") or 0))
print(f"target: {target['message_id']} role={target['role']} ts={target['timestamp']}")
print(f"conversation: '{target.get('conversation_title')}' msgs={len(conv_msgs)}")
text = target.get("text") or ""
print(f"target text length: {len(text)} chars")
print("---- target text ----")
print(text[:2000])
print("---- conversation context ----")
for m in conv_msgs:
    mark = ">>" if m["message_id"] == TARGET_MID else "  "
    print(f"{mark} {str(m.get('timestamp'))[:19]} {m.get('role'):9s} "
          f"seq={m.get('sequence_index')} len={len(m.get('text') or '')} | "
          f"{(m.get('text') or '')[:120].replace(chr(10),' ')}")

# 2. overlap with the Zo AI page
page = json.load(open(PAGE, encoding="utf-8"))
page_sh = shingles(page.get("raw_text", ""))
t_sh = shingles(text)
shared_page = sorted(t_sh & page_sh)
print(f"\nshingles: target {len(t_sh)}, page {len(page_sh)}, shared {len(shared_page)}")
for s in shared_page[:15]:
    print("   shared-with-page:", s)

# 3. earlier occurrences of the target material anywhere in the corpus
tgt_ts = datetime.fromisoformat(str(target["timestamp"]).replace("Z", "+00:00"))
prior, later = [], []
t0 = time.time()
n = 0
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        n += 1
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("message_id") == TARGET_MID:
            continue
        mtext = r.get("text") or ""
        if len(mtext) < 80:
            continue
        msh = shingles(mtext)
        c = len(msh & t_sh)
        if c >= MIN_MATCH:
            ts = None
            try:
                ts = datetime.fromisoformat(str(r.get("timestamp")).replace("Z", "+00:00"))
            except Exception:
                pass
            entry = {"message_id": r["message_id"], "role": r.get("role"),
                     "timestamp": r.get("timestamp"),
                     "conversation_title": r.get("conversation_title"),
                     "conversation_id": r.get("conversation_id"),
                     "source_file": r.get("source_file"),
                     "matched_shingles": c,
                     "preview": mtext[:240].replace("\n", " ")}
            (prior if (ts and ts < tgt_ts) else later).append(entry)
        if n % 20000 == 0:
            print(f"  scanned {n}, prior {len(prior)} later {len(later)}, {time.time()-t0:.0f}s")
prior.sort(key=lambda e: str(e["timestamp"]))
later.sort(key=lambda e: str(e["timestamp"]))
print(f"\nscan done in {time.time()-t0:.0f}s; prior matches {len(prior)}, later matches {len(later)}")
for e in prior[:20]:
    print(f"  PRIOR {str(e['timestamp'])[:19]} {e['role']:9s} x{e['matched_shingles']:3d} "
          f"| {str(e['conversation_title'])[:40]:40s} | {str(e['source_file'])[:30]}")
for e in later[:10]:
    print(f"  LATER {str(e['timestamp'])[:19]} {e['role']:9s} x{e['matched_shingles']:3d} "
          f"| {str(e['conversation_title'])[:40]:40s} | {str(e['source_file'])[:30]}")

json.dump({
    "trace": "ZO_AI_ANTECEDENT_RESOLUTION_V0.1",
    "status": "CANDIDATE_EVIDENCE — founder review required; nothing canonical",
    "generated": "2026-08-12",
    "target_message": {"message_id": target["message_id"], "role": target["role"],
                       "timestamp": target["timestamp"],
                       "conversation_id": target["conversation_id"],
                       "conversation_title": target.get("conversation_title"),
                       "source_file": target.get("source_file"),
                       "char_count": len(text),
                       "text": text},
    "conversation_context": [
        {"message_id": m["message_id"], "role": m.get("role"),
         "timestamp": m.get("timestamp"), "sequence_index": m.get("sequence_index"),
         "char_count": len(m.get("text") or ""),
         "preview": (m.get("text") or "")[:200].replace("\n", " ")}
        for m in conv_msgs],
    "shared_shingles_with_zo_ai_page": shared_page,
    "method": {"k": K, "min_matched_shingles": MIN_MATCH,
               "corpus": "CORPUS_RELEASE_001 messages.jsonl"},
    "prior_matches": prior,
    "later_matches": later,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nwrote {OUT}")
