# First corpus-wide test of the MULTI_AGENT_RELAY_CHAIN pattern.
# Detection v0.1: user-role messages containing labeled relay headers like
# "WorkClaw  [7:51 AM]" / "Genspark [7:32 AM]", plus control-act lead-in
# markers. Results are CANDIDATE relay events until reviewed. No authorship
# claims. Read-only over the frozen CORPUS_RELEASE_001.
import json, os, re, sys, time
from collections import Counter, defaultdict
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
CORPUS = os.path.join(ROOT, "13_SOURCE_INDEX", "corpus_releases",
                      "CORPUS_RELEASE_001", "messages.jsonl")
OUT = os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit",
                   "RELAY_PATTERN_TEST_V0.1.json")

RELAY_HDR = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9][A-Za-z0-9 ._&'-]{1,40}?)"
    r"\s{1,6}\[\s*\d{1,2}:\d{2}(?::\d{2})?\s*(?:[APap][Mm])?\s*\]",
    re.M)
CONTROL_WORDS = re.compile(
    r"^(yes|ok|okay|do it|let'?s|build|add|what if|proceed|run|deploy|"
    r"i want|bring|make|create|give|show|continue)\b", re.I)

events = []
n = 0
t0 = time.time()
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        n += 1
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("role") != "user":
            continue
        text = r.get("text") or ""
        if len(text) < 200:
            continue
        actors = [m.group(1).strip() for m in RELAY_HDR.finditer(text)]
        if not actors:
            continue
        head = text.strip().split("\n", 1)[0][:120]
        control = bool(CONTROL_WORDS.match(head.strip()))
        events.append({
            "message_id": r["message_id"],
            "timestamp": r.get("timestamp"),
            "conversation_id": r["conversation_id"],
            "conversation_title": r.get("conversation_title"),
            "source_file": r.get("source_file"),
            "char_count": len(text),
            "actors": actors,
            "control_act_lead_in": control,
            "lead_in": head.replace("\n", " "),
        })
print(f"scanned {n} messages in {time.time()-t0:.0f}s; candidate relay events: {len(events)}")

actor_counts = Counter(a.lower() for e in events for a in e["actors"])
conv_counts = Counter(e["conversation_title"] for e in events)
month_counts = Counter(str(e["timestamp"])[:7] for e in events)
src_counts = Counter(str(e["source_file"]) for e in events)
control_n = sum(1 for e in events if e["control_act_lead_in"])

print("\n-- top actors --")
for a, c in actor_counts.most_common(30):
    print(f"  {c:4d}  {a}")
print("\n-- top conversations --")
for t, c in conv_counts.most_common(20):
    print(f"  {c:4d}  {str(t)[:60]}")
print("\n-- timeline by month --")
for m, c in sorted(month_counts.items()):
    print(f"  {m}  {c}")
print("\n-- source files --")
for s, c in src_counts.most_common(15):
    print(f"  {c:4d}  {str(s)[:60]}")
print(f"\ncontrol-act lead-ins among events: {control_n}")
print("\n-- 20 sample events --")
for e in events[:20]:
    print(f"  {str(e['timestamp'])[:10]} x{len(e['actors'])} len{e['char_count']:6d} "
          f"{'CTRL' if e['control_act_lead_in'] else '    '} | "
          f"{str(e['conversation_title'])[:38]:38s} | {e['lead_in'][:70]}")

json.dump({
    "test": "RELAY_PATTERN_TEST_V0.1",
    "status": "CANDIDATE_EVENTS — review required; no authorship claims; nothing canonical",
    "generated": "2026-08-12",
    "pattern": "MULTI_AGENT_RELAY_CHAIN (08_MASTER_PLAN/MULTI_AGENT_RELAY_CHAIN_PATTERN_V0.1.md)",
    "corpus": {"release": "CORPUS_RELEASE_001", "messages_scanned": n},
    "method": {"relay_header_regex": RELAY_HDR.pattern,
               "min_message_chars": 200, "role_filter": "user",
               "note": "labeled-header heuristic only; unlabeled transports NOT detected"},
    "summary": {"candidate_events": len(events),
                "with_control_act_lead_in": control_n,
                "distinct_actors": len(actor_counts),
                "conversations_with_events": len(conv_counts)},
    "actor_counts": actor_counts.most_common(),
    "conversation_counts": conv_counts.most_common(),
    "month_counts": dict(sorted(month_counts.items())),
    "source_counts": src_counts.most_common(),
    "events": events,
}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"\nwrote {OUT}")
