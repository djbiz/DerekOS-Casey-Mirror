# Notion workspace inventory crawl — AUDIT STEP 1 (pre-ingestion)
# Governed by 08_MASTER_PLAN/NOTION_EVIDENCE_SOURCE_POLICY_V0.1.md
# Output: 14_TESTS_AUDITS/notion_audit/inventory.json (AUDIT WORKING DATA — NOT INGESTED)
import json, os, sys, time, urllib.request, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KEY_PATH = r"C:\Users\starw\AppData\Local\notion_master_brain\api_key.txt"
OUT_DIR = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain",
                       "14_TESTS_AUDITS", "notion_audit")
BASE = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": "Bearer " + open(KEY_PATH).read().strip(),
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def api(path, payload=None, retries=4):
    url = BASE + path
    data = json.dumps(payload).encode() if payload is not None else None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=HEADERS,
                                     method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:300]
            if e.code == 429:
                time.sleep(1.5 * (attempt + 1)); continue
            print("HTTP", e.code, url, body); raise
        except Exception as ex:
            print("ERR", url, ex)
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError("failed: " + url)

def page_title(p):
    props = p.get("properties", {})
    for v in props.values():
        if v.get("type") == "title":
            return "".join(t.get("plain_text", "") for t in v.get("title", []))
    return ""

def db_title(d):
    return "".join(t.get("plain_text", "") for t in d.get("title", []))

os.makedirs(OUT_DIR, exist_ok=True)

# ---- Phase 1: full search crawl (empty query, paginate) ----
results, cursor, pages_n = [], None, 0
while True:
    payload = {"page_size": 100}
    if cursor: payload["start_cursor"] = cursor
    d = api("/search", payload)
    results.extend(d.get("results", []))
    pages_n += 1
    if not d.get("has_more"): break
    cursor = d.get("next_cursor")
    time.sleep(0.4)

inv = []
for r in results:
    rec = {
        "object": r.get("object"),
        "id": r.get("id"),
        "url": r.get("url"),
        "created_time": r.get("created_time"),
        "last_edited_time": r.get("last_edited_time"),
    }
    if r["object"] == "page":
        rec["title"] = page_title(r)
        par = r.get("parent", {})
        rec["parent_type"] = par.get("type")
        rec["parent_id"] = par.get(par.get("type", ""), None) if par.get("type") in ("workspace", "page_id", "database_id", "block_id") else None
        if par.get("type") == "database_id":
            rec["parent_id"] = par.get("database_id")
        rec["archived"] = r.get("archived")
        rec["in_trash"] = r.get("in_trash")
    else:
        rec["title"] = db_title(r)
        rec["parent_type"] = r.get("parent", {}).get("type")
        rec["properties"] = sorted((r.get("properties") or {}).keys())
    inv.append(rec)

pages = [x for x in inv if x["object"] == "page"]
dbs = [x for x in inv if x["object"] == "database"]
ws_pages = [x for x in pages if x["parent_type"] == "workspace"]

summary = {
    "crawl_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "search_api_pages_fetched": pages_n,
    "total_objects": len(inv),
    "pages": len(pages),
    "databases": len(dbs),
    "top_level_workspace_pages": len(ws_pages),
    "status": "AUDIT_WORKING_DATA_NOT_INGESTED",
}
print(json.dumps(summary, indent=2))

print("\n== TOP-LEVEL WORKSPACE PAGES ==")
for x in sorted(ws_pages, key=lambda v: v.get("last_edited_time") or "", reverse=True):
    print(f"{x['last_edited_time']}  {x['title'] or '(untitled)'}  {x['id']}")

print("\n== DATABASES ==")
for x in dbs:
    print(f"{x['last_edited_time']}  {x['title'] or '(untitled)'}  parent={x['parent_type']}  props={x['properties']}")

json.dump({"summary": summary, "objects": inv},
          open(os.path.join(OUT_DIR, "inventory.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\ninventory written:", os.path.join(OUT_DIR, "inventory.json"))
