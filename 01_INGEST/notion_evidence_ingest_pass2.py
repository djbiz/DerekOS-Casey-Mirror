# Patch pass 2: child_page recursion + VOX Industry Messaging Matrix + RPM row content
import json, os, sys, time, re, hashlib, urllib.request, urllib.error, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
KEY = open(r"C:\Users\starw\AppData\Local\notion_master_brain\api_key.txt").read().strip()
ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
OUT = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace", "NOTION_EVIDENCE_RELEASE_001")
H = {"Authorization": "Bearer " + KEY, "Notion-Version": "2022-06-28",
     "Content-Type": "application/json"}
SECRET_PAT = re.compile(
    r"(?i)(sk-[a-z0-9]{16,}|ntn_[a-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"]?[a-z0-9_\-]{16,}"
    r"|bearer\s+[a-z0-9_\.\-]{20,}|ghp_[a-z0-9]{20,}|xox[baprs]-[a-z0-9\-]{10,}"
    r"|password\s*[:=]\s*\S{6,})")

def api(path, payload=None, retries=3):
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
            return {"__error__": e.code, "body": e.read().decode()[:300]}
        except Exception as ex:
            time.sleep(1.0)
    return {"__error__": "retries_exhausted"}

def get_paged(path, payload=None):
    out, cursor = [], None
    while True:
        if payload is not None:
            p = dict(payload); p["page_size"] = 100
            if cursor: p["start_cursor"] = cursor
            d = api(path, p)
        else:
            q = "page_size=100" + (("&start_cursor=" + cursor) if cursor else "")
            d = api(path + "?" + q, None)
        if "__error__" in d: return out, d
        out.extend(d.get("results", []))
        if not d.get("has_more"): break
        cursor = d.get("next_cursor"); time.sleep(0.35)
    return out, None

def rich(parts): return "".join(p.get("plain_text", "") for p in (parts or []))

def block_text(b):
    t = b.get("type", "")
    data = b.get(t, {}) if isinstance(b.get(t), dict) else {}
    txt = rich(data.get("rich_text"))
    if t == "to_do": txt = ("[x] " if data.get("checked") else "[ ] ") + txt
    if t in ("bulleted_list_item", "numbered_list_item"): txt = "- " + txt
    if t == "heading_1": txt = "# " + txt
    if t == "heading_2": txt = "## " + txt
    if t == "heading_3": txt = "### " + txt
    if t == "child_page": txt = "[child_page] " + txt
    if t == "child_database": txt = "[child_database] " + txt
    if t == "table_row": txt = " | ".join(rich(c) for c in data.get("cells", []))
    return txt

def walk(block_id, depth=0, acc=None):
    if acc is None: acc = []
    blocks, err = get_paged(f"/blocks/{block_id}/children")
    for b in blocks:
        acc.append({"depth": depth, "id": b["id"], "type": b.get("type"),
                    "text": block_text(b)})
        t = b.get("type")
        if t == "child_page":
            sub, e2 = walk(b["id"], depth + 1)
            acc.extend(sub); time.sleep(0.34)
        elif b.get("has_children") and t != "child_database" and depth < 5:
            sub, e2 = walk(b["id"], depth + 1)
            acc.extend(sub); time.sleep(0.34)
    return acc, None

def page_title(p):
    for v in p.get("properties", {}).values():
        if v.get("type") == "title":
            return rich(v.get("title"))
    return ""

def ingest_page(pid, via):
    meta = api(f"/pages/{pid}")
    if "__error__" in meta:
        return {"page_id": pid, "error": meta}
    blocks, _ = walk(pid)
    text = "\n".join(("  " * b["depth"]) + b["text"] for b in blocks)
    n_sec = len(SECRET_PAT.findall(text))
    if n_sec: text = SECRET_PAT.sub("[REDACTED_SECRET]", text)
    rec = {"record_type": "notion_page", "source_identity": "notion-workspace",
           "page_id": pid, "page_title": page_title(meta), "url": meta.get("url"),
           "created_time": meta.get("created_time"),
           "last_edited_time": meta.get("last_edited_time"),
           "created_by": meta.get("created_by"),
           "last_edited_by": meta.get("last_edited_by"),
           "parent": meta.get("parent"), "via": via,
           "block_count": len(blocks), "blocks": blocks, "raw_text": text,
           "char_count": len(text),
           "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "secret_redactions": n_sec}
    raw = json.dumps(rec, ensure_ascii=False, sort_keys=True)
    rec["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    json.dump(rec, open(os.path.join(OUT, "pages", pid + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"  {pid[:8]} {rec['page_title'][:55]:55s} blocks={rec['block_count']:4d} chars={rec['char_count']}")
    return {"page_id": pid, "title": rec["page_title"], "sha256": rec["sha256"],
            "chars": rec["char_count"], "blocks": rec["block_count"],
            "file": "pages/" + pid + ".json",
            "created_time": rec["created_time"], "last_edited_time": rec["last_edited_time"],
            "created_by": (rec["created_by"] or {}).get("id"),
            "last_edited_by": (rec["last_edited_by"] or {}).get("id"), "via": via}

man = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
existing = {r["page_id"] for r in man["records"]}

# 0. inline databases hold content in the DB page itself — ingest those block trees
for f in os.listdir(os.path.join(OUT, "databases")):
    did = f.replace(".json", "")
    if did not in existing:
        res = ingest_page(did, "db-root-page")
        man["records"].append(res) if "error" not in res else man.setdefault("errors", []).append(res)
        time.sleep(0.35)

# 1. re-ingest all existing pages WITH child_page recursion
new_records = []
for r in list(man["records"]):
    res = ingest_page(r["page_id"], r.get("via", "root"))
    new_records.append(res); time.sleep(0.35)

# 2. VOX Industry Messaging Matrix — try as database, then as block
vox_id = "fc95d7c5-2071-4779-bb86-6d92dac4d18b"
dbmeta = api(f"/databases/{vox_id}")
if "__error__" not in dbmeta:
    rows, err = get_paged(f"/databases/{vox_id}/query", {})
    dbrec = {"record_type": "notion_database", "source_identity": "notion-workspace",
             "database_id": vox_id, "title": "VOX Industry Messaging Matrix",
             "meta": dbmeta, "row_ids": [x["id"] for x in rows],
             "extraction_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    raw = json.dumps(dbrec, ensure_ascii=False, sort_keys=True)
    dbrec["sha256"] = hashlib.sha256(raw.encode()).hexdigest()
    json.dump(dbrec, open(os.path.join(OUT, "databases", vox_id + ".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"  db {vox_id[:8]} VOX Industry Messaging Matrix: {len(rows)} rows")
    for x in rows:
        res = ingest_page(x["id"], "db:VOX Industry Messaging Matrix")
        new_records.append(res); time.sleep(0.35)
else:
    print("VOX Industry Messaging Matrix as database failed:", dbmeta)
    blk = api(f"/blocks/{vox_id}")
    print("as block:", json.dumps(blk)[:200])

# 3. RPM Cycles row content already re-ingested in step 1 (it was in records)
secret_total = 0
for fn in os.listdir(os.path.join(OUT, "pages")):
    d = json.load(open(os.path.join(OUT, "pages", fn), encoding="utf-8"))
    secret_total += d.get("secret_redactions", 0)

man["records"] = [r for r in new_records if "error" not in r]
man["errors"] = [r for r in new_records if "error" in r]
man["record_count"] = len(man["records"])
man["database_count"] = len([f for f in os.listdir(os.path.join(OUT, "databases"))])
man["secret_redactions"] = [{"total": secret_total}]
man["patch"] = "pass-2 child_page recursion + VOX Industry Messaging Matrix db; 2026-08-12"
man["extraction_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
rel = hashlib.sha256(json.dumps([r["sha256"] for r in sorted(man["records"], key=lambda v: v["page_id"])],
                                sort_keys=True).encode()).hexdigest()
print(f"\nDONE pass 2: {man['record_count']} records, errors={len(man['errors'])}, "
      f"secret redactions={secret_total}")
print("release content hash:", rel)
