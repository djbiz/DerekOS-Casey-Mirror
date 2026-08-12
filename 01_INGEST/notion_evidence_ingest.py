# Notion evidence ingestion — founder-approved scope (2026-08-12)
# Governance: NOTION_EVIDENCE_SOURCE_POLICY_V0.1.md + founder directive "Approved with boundaries"
# Output: 00_RAW_ARCHIVE/notion-workspace/NOTION_EVIDENCE_RELEASE_001/ (immutable snapshots)
import json, os, sys, time, re, hashlib, urllib.request, urllib.error, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
KEY = open(r"C:\Users\starw\AppData\Local\notion_master_brain\api_key.txt").read().strip()
ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
OUT = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace", "NOTION_EVIDENCE_RELEASE_001")
os.makedirs(os.path.join(OUT, "pages"), exist_ok=True)
os.makedirs(os.path.join(OUT, "databases"), exist_ok=True)
H = {"Authorization": "Bearer " + KEY, "Notion-Version": "2022-06-28",
     "Content-Type": "application/json"}

def api(path, payload=None, retries=5):
    url = "https://api.notion.com/v1" + path
    data = json.dumps(payload).encode() if payload is not None else None
    for a in range(retries):
        req = urllib.request.Request(url, data=data, headers=H,
                                     method="POST" if data else "GET")
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.2 * (a + 1)); continue
            if e.code in (404, 403):
                return {"__error__": e.code, "body": e.read().decode()[:200]}
            print("  HTTP", e.code, path); time.sleep(1.0)
        except Exception as ex:
            print("  ERR", path, ex); time.sleep(1.0)
    return {"__error__": "retries_exhausted"}

def get_paged(path, payload=None, key="results"):
    out, cursor = [], None
    while True:
        p = dict(payload or {})
        p["page_size"] = 100
        if cursor: p["start_cursor"] = cursor
        d = api(path, p if payload is not None else None)
        if "__error__" in d: return out, d
        out.extend(d.get(key, []))
        if not d.get("has_more"): break
        cursor = d.get("next_cursor")
        time.sleep(0.35)
    return out, None

SECRET_PAT = re.compile(
    r"(?i)(sk-[a-z0-9]{16,}|ntn_[a-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"]?[a-z0-9_\-]{16,}"
    r"|bearer\s+[a-z0-9_\.\-]{20,}|ghp_[a-z0-9]{20,}|xox[baprs]-[a-z0-9\-]{10,}"
    r"|password\s*[:=]\s*\S{6,})")

def rich(parts):
    return "".join(p.get("plain_text", "") for p in (parts or []))

def block_text(b):
    t = b.get("type", "")
    data = b.get(t, {}) if isinstance(b.get(t), dict) else {}
    txt = rich(data.get("rich_text"))
    if t == "code": txt += "\n[lang=" + str(data.get("language")) + "]"
    if t == "to_do": txt = ("[x] " if data.get("checked") else "[ ] ") + txt
    if t in ("bulleted_list_item", "numbered_list_item"): txt = "- " + txt
    if t == "heading_1": txt = "# " + txt
    if t == "heading_2": txt = "## " + txt
    if t == "heading_3": txt = "### " + txt
    if t == "child_page": txt = "[child_page] " + txt
    if t == "child_database": txt = "[child_database] " + txt
    if t == "table": txt = "[table]"
    if t == "table_row": txt = " | ".join(rich(c) for c in data.get("cells", []))
    return txt

def walk_blocks(block_id, depth=0, acc=None):
    if acc is None: acc = []
    blocks, err = get_paged(f"/blocks/{block_id}/children")
    for b in blocks:
        acc.append({"depth": depth, "id": b["id"], "type": b.get("type"),
                    "text": block_text(b)})
        if b.get("has_children") and b.get("type") not in ("child_page", "child_database") and depth < 4:
            walk_blocks(b["id"], depth + 1, acc)
            time.sleep(0.34)
    return acc

def page_title(p):
    for v in p.get("properties", {}).values():
        if v.get("type") == "title":
            return rich(v.get("title"))
    return ""

# ---- approved scope ----
ROOT_PAGES = {
    # DerekOS cluster
    "3abdbc2b-713e-8100-b55d-ef669cfb3610": "DerekOS Master Dashboard — RPM + 7D + Story Engine",
    "3abdbc2b-713e-81d4-b835-c4811f989690": "Derek OS — Personal Operating System",
    "3abdbc2b-713e-8173-b5ae-d845644ec894": "90-Day Solitude Cycle 1 — DerekOS 1.0",
    # VOX cluster
    "39edbc2b-713e-819d-be14-c647dffcb22b": "VOX Command Center — Live OS Bridge",
    "3a7dbc2b-713e-8198-afbc-c1a43943edba": "VOX AI 12-Month Revenue & Force Sequencing Plan",
    "3aedbc2b-713e-818d-9e0f-c461b06e1650": "VOX AI: Business Mastery Operating System (7 Forces & RPM)",
    "3a9dbc2b-713e-81fb-95d0-e62ca08ddd1b": "VOX AI Operating System: Momentum & Value Mastery",
    "3aedbc2b-713e-81b5-9631-c64d0d071df7": "VOX AI: The Four 10% Pillars Execution Plan (HVAC MVP)",
    "3a9dbc2b-713e-81b5-9f69-f4ba65915242": "Day 2: Ideal Customer Profile (HVAC) - VOX AI",
    "fc95d7c5-2071-4779-bb86-6d92dac4d18b": "VOX Industry Messaging Matrix",
    # Ghost Protocol
    "39cdbc2b-713e-81c0-971a-f43c62a786d2": "Ghost Protocol Ops — Pipeline Map & Agent Network",
    # Company in-a-Box / DAC non-template
    "208dbc2b-713e-8090-aa91-eeedca9ea190": "Company in-a-Box",
    "208dbc2b-713e-8099-ba47-ef714b6cb739": "Vision and Strategy",
    "208dbc2b-713e-800b-9e70-d322eb178d89": "Portfolio",
    "208dbc2b-713e-800e-a7da-d58af030b180": "DAC Marketing Meeting Agenda",
    "208dbc2b-713e-8061-af57-fc1acf2e034f": "DAC Performance Dashboard – Growth & ROI Tracking",
    "20adbc2b-713e-8041-be0c-f6258f640311": "THE ULTIMATE PROMPT STACK FOR YOUR DAC EMPIRE",
    "20fdbc2b-713e-806e-a761-c608a674bb79": "DAC 30-Day Content Plan",
    # OS-concept material
    "30edbc2b-713e-80e5-8042-f826c3e5b8e3": "Startup OS — The All-in-One Operating System",
    "208dbc2b-713e-8044-a1c0-fcdb32aa8d06": "Ultimate Business OS.",
    "208dbc2b-713e-80fe-a1f8-e4281beb3623": "Marketing OS",
    "33ddbc2b-713e-81de-9e7c-f6369f862744": "Zo AI Business OS",
}
ROOT_DBS = {
    "97f53ea5-4c43-441c-b611-7737ff4869b2": "DerekOS Rules & Principles",
}
# RPM Cycles DB id: find from inventory
inv = json.load(open(os.path.join(ROOT, "14_TESTS_AUDITS", "notion_audit", "inventory.json"),
                     encoding="utf-8"))["objects"]
for x in inv:
    if x["object"] == "database" and (x.get("title") or "").strip() == "RPM Cycles":
        ROOT_DBS[x["id"]] = "RPM Cycles"

records, errors, secret_flags = [], [], []

def ingest_page(pid, expected_title, via):
    meta = api(f"/pages/{pid}")
    if "__error__" in meta:
        errors.append({"id": pid, "title": expected_title, "error": meta}); return
    blocks = walk_blocks(pid)
    text = "\n".join(("  " * b["depth"]) + b["text"] for b in blocks)
    n_sec = len(SECRET_PAT.findall(text))
    if n_sec:
        text = SECRET_PAT.sub("[REDACTED_SECRET]", text)
        secret_flags.append({"id": pid, "title": page_title(meta), "count": n_sec})
    rec = {
        "record_type": "notion_page",
        "source_identity": "notion-workspace",
        "page_id": pid,
        "page_title": page_title(meta) or expected_title,
        "url": meta.get("url"),
        "created_time": meta.get("created_time"),
        "last_edited_time": meta.get("last_edited_time"),
        "created_by": meta.get("created_by"),
        "last_edited_by": meta.get("last_edited_by"),
        "parent": meta.get("parent"),
        "archived": meta.get("archived"),
        "via": via,
        "block_count": len(blocks),
        "blocks": blocks,
        "raw_text": text,
        "char_count": len(text),
        "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    raw = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    rec["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    fn = os.path.join(OUT, "pages", pid + ".json")
    json.dump(rec, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    records.append({"page_id": pid, "title": rec["page_title"], "via": via,
                    "sha256": rec["sha256"], "chars": rec["char_count"],
                    "blocks": rec["block_count"], "file": "pages/" + pid + ".json",
                    "created_time": rec["created_time"],
                    "last_edited_time": rec["last_edited_time"],
                    "created_by": (rec["created_by"] or {}).get("id"),
                    "last_edited_by": (rec["last_edited_by"] or {}).get("id")})
    print(f"  page {pid[:8]} {rec['page_title'][:50]:50s} blocks={rec['block_count']:4d} chars={rec['char_count']}")

for pid, title in ROOT_PAGES.items():
    ingest_page(pid, title, "root")
    time.sleep(0.35)

for dbid, dbname in ROOT_DBS.items():
    dbmeta = api(f"/databases/{dbid}")
    rows, err = get_paged(f"/databases/{dbid}/query", {})
    dbrec = {"record_type": "notion_database", "source_identity": "notion-workspace",
             "database_id": dbid, "title": dbname, "meta": dbmeta,
             "row_ids": [r["id"] for r in rows],
             "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    raw = json.dumps(dbrec, ensure_ascii=False, sort_keys=True)
    dbrec["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    json.dump(dbrec, open(os.path.join(OUT, "databases", dbid + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"  db   {dbid[:8]} {dbname}: {len(rows)} rows")
    for r in rows:
        ingest_page(r["id"], page_title(r) or "(row)", "db:" + dbname)
        time.sleep(0.35)

manifest = {
    "release_id": "NOTION_EVIDENCE_RELEASE_001",
    "source_identity": "notion-workspace",
    "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "record_count": len(records),
    "database_count": len(ROOT_DBS),
    "records": records,
    "errors": errors,
    "secret_redactions": secret_flags,
    "exclusions_applied": [
        "marketplace/template bulk content (1,827 pages, 2025-06 import)",
        "CRM/client/contact PII (entire client/contact dataset)",
        "credentials/secrets (regex-scanned; matches redacted)",
        "obvious duplicate/template instances",
    ],
    "status": "EVIDENCE_ONLY_NOT_CANONICAL",
}
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\nDONE: {len(records)} page records, {len(ROOT_DBS)} databases, "
      f"{len(errors)} errors, {len(secret_flags)} secret redactions")
total = hashlib.sha256(json.dumps([r["sha256"] for r in sorted(records, key=lambda v: v["page_id"])],
                                  sort_keys=True).encode()).hexdigest()
print("release content hash (over record hashes):", total)
