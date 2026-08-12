# Notion evidence provenance resolution V0.1 — classification CANDIDATES only
# Inputs: NOTION_EVIDENCE_RELEASE_001 manifest + cross_source_matches.json + corpus timestamps
# Governance: evidence-gated; nothing canonical; unresolved stays UNRESOLVED
import json, os, sys, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
REL = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace", "NOTION_EVIDENCE_RELEASE_001")
MAN = json.load(open(os.path.join(REL, "manifest.json"), encoding="utf-8"))
MATCHES = json.load(open(os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit",
                                      "cross_source_matches.json"), encoding="utf-8"))["matches"]
CORPUS = os.path.join(ROOT, "13_SOURCE_INDEX", "corpus_releases", "CORPUS_RELEASE_001",
                      "messages.jsonl")

HUMAN = "208d872b-594c-81b2-b7d6-0002fd6e9da9"  # Derek Jamieson (verified via /users/me)
BOT = "39edbc2b"  # unresolved bot id

# exact timestamps for matched corpus messages
need = {m["message_id"] for m in MATCHES}
ts_map = {}
with open(CORPUS, encoding="utf-8") as f:
    for line in f:
        r = json.loads(line)
        if r["message_id"] in need:
            ts_map[r["message_id"]] = r.get("timestamp")
            need.discard(r["message_id"])
            if not need: break

by_page = {}
for m in MATCHES:
    by_page.setdefault(m["page_id"], []).append(m)

def day(t):
    return (t or "")[:10]

resolutions = []
for rec in MAN["records"]:
    pid = rec["page_id"]
    page = json.load(open(os.path.join(REL, "pages", pid + ".json"), encoding="utf-8"))
    cb = (rec.get("created_by") or "")
    creator = "HUMAN_DEREK" if cb.startswith("208d872b") else ("BOT_UNRESOLVED_39edbc2b" if cb.startswith("39edbc2b") else "UNKNOWN")
    ms = sorted(by_page.get(pid, []), key=lambda v: -v["matched_shingles"])
    evidence = []
    evidence.append({"type": "created_by", "value": creator,
                     "note": "Notion page metadata created_by"})
    cls, rationale = "UNRESOLVED", []
    strong_assistant, strong_user = [], []
    for m in ms:
        m_ts = ts_map.get(m["message_id"], "")
        evidence.append({"type": "cross_source_match",
                         "conversation_title": m["conversation_title"],
                         "role": m["role"], "matched_shingles": m["matched_shingles"],
                         "corpus_timestamp": m_ts,
                         "notion_created": rec.get("created_time")})
        if m["matched_shingles"] >= 20:
            (strong_assistant if m["role"] == "assistant" else strong_user).append(m)
    if strong_assistant:
        cls = "A0_CANDIDATE"
        rationale.append("substantial overlap (>=20 shingles) with ChatGPT assistant output(s): "
                         + "; ".join(f"{m['conversation_title']} ({day(ts_map.get(m['message_id'],''))}, x{m['matched_shingles']})" for m in strong_assistant))
        if creator == "HUMAN_DEREK":
            rationale.append("page created_by Derek — founder imported/kept AI-drafted material (adoption signal)")
    elif strong_user:
        cls = "REUSE_FOUNDER_MATERIAL_CANDIDATE"
        rationale.append("substantial overlap with USER-role ChatGPT messages (founder-supplied text reused across systems): "
                         + "; ".join(f"{m['conversation_title']} ({day(ts_map.get(m['message_id'],''))}, x{m['matched_shingles']})" for m in strong_user))
    elif ms:
        cls = "WEAK_OVERLAP_UNRESOLVED"
        rationale.append(f"only weak overlaps (max {ms[0]['matched_shingles']} shingles)")
    else:
        if creator == "HUMAN_DEREK":
            cls = "D0_OR_A0_UNRESOLVED"
            rationale.append("no corpus overlap found; created by Derek, but AI-drafting outside corpus cannot be excluded")
        else:
            cls = "BOT_CREATED_UNRESOLVED"
            rationale.append("created by unresolved bot id; no corpus overlap")
    # adoption candidate
    eb = rec.get("last_edited_by") or ""
    adoption = "AD0_UNRESOLVED"
    if cls == "A0_CANDIDATE" and creator == "HUMAN_DEREK":
        adoption = "AD2_CANDIDATE"  # imported into personal OS workspace = retained/use signal, no deeper adoption proof
    if eb.startswith("208d872b") and cb.startswith("39edbc2b"):
        rationale.append("bot-created page later edited by Derek (maintenance signal)")
    resolutions.append({
        "resolution_id": "NR-" + pid[:8],
        "record": {"source_identity": "notion-workspace", "page_id": pid,
                   "page_title": rec.get("title"), "release": "NOTION_EVIDENCE_RELEASE_001",
                   "created_time": rec.get("created_time"),
                   "last_edited_time": rec.get("last_edited_time")},
        "authorship_classification": cls,
        "creator": creator,
        "adoption_candidate": adoption,
        "rationale": rationale,
        "evidence": evidence,
        "status": "CANDIDATE_PENDING_FOUNDER_REVIEW",
        "resolved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })

OUT = os.path.join(ROOT, "14_TESTS_AUDITS", "NOTION_PROVENANCE_RESOLUTION_V0.1.jsonl")
with open(OUT, "w", encoding="utf-8") as f:
    for r in resolutions:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

from collections import Counter
print("classifications:", dict(Counter(r["authorship_classification"] for r in resolutions)))
for r in resolutions:
    print(f"{r['resolution_id']}  {r['authorship_classification']:34s} {str(r['record']['page_title'])[:52]}")
print("\nwritten:", OUT)
