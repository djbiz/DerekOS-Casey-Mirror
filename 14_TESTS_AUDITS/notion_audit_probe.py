# Notion audit — keyword probes + classification counts (AUDIT STEP 2)
import json, os, sys, time, urllib.request, urllib.error

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
KEY_PATH = r"C:\Users\starw\AppData\Local\notion_master_brain\api_key.txt"
OUT_DIR = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain",
                       "14_TESTS_AUDITS", "notion_audit")
HEADERS = {
    "Authorization": "Bearer " + open(KEY_PATH).read().strip(),
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def search(query, filt=None, limit=20):
    payload = {"query": query, "page_size": limit}
    if filt: payload["filter"] = filt
    req = urllib.request.Request("https://api.notion.com/v1/search",
                                 data=json.dumps(payload).encode(),
                                 headers=HEADERS, method="POST")
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5); continue
            print("  HTTP", e.code, query); return {"results": []}
    return {"results": []}

def title_of(r):
    if r["object"] == "page":
        for v in r.get("properties", {}).values():
            if v.get("type") == "title":
                return "".join(t.get("plain_text", "") for t in v.get("title", []))
    return "".join(t.get("plain_text", "") for t in r.get("title", []))

KEYWORDS = [
    "conglomerate", "acquisition", "acquire", "holding company", "capital allocation",
    "Africa", "Lagos", "Nairobi", "Johannesburg", "takeover", "warehouse",
    "high-rise", "headquarters", "franchise", "300 businesses",
    "DerekOS", "VOX", "RPM", "7D", "Company in-a-Box", "Ghost Protocol",
]
probe = {}
for kw in KEYWORDS:
    d = search(kw)
    hits = []
    for r in d.get("results", []):
        hits.append({"object": r["object"], "id": r["id"],
                     "title": title_of(r),
                     "last_edited_time": r.get("last_edited_time")})
    probe[kw] = hits
    print(f"[{kw}] -> {len(hits)} hits")
    for h in hits[:6]:
        print(f"    {h['object']:8s} {h['last_edited_time']}  {h['title'][:70]}")
    time.sleep(0.4)

json.dump(probe, open(os.path.join(OUT_DIR, "keyword_probe.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- classification counts from inventory ----
inv = json.load(open(os.path.join(OUT_DIR, "inventory.json"), encoding="utf-8"))["objects"]
pages = [x for x in inv if x["object"] == "page"]
from collections import Counter
edit_dates = Counter((x.get("last_edited_time") or "")[:10] for x in pages)
print("\n== PAGE last_edited distribution (top 15 days) ==")
for day, n in sorted(edit_dates.items())[:5] + sorted(edit_dates.items(), key=lambda kv: -kv[1])[:15]:
    print(f"  {day}: {n}")
created_dates = Counter((x.get("created_time") or "")[:7] for x in pages)
print("\n== PAGE created by month ==")
for m, n in sorted(created_dates.items()):
    print(f"  {m}: {n}")
archived = sum(1 for x in pages if x.get("archived") or x.get("in_trash"))
print("\narchived/in_trash pages:", archived)
db_pages = sum(1 for x in pages if x.get("parent_type") == "database_id")
print("pages that are database rows:", db_pages)
print("standalone pages:", len(pages) - db_pages)
