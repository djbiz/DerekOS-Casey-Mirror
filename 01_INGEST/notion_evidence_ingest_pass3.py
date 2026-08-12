# Pass 3: capture database-row PROPERTY values (RPM cycle fields, matrix cells),
# recompute hashes, dedupe manifest.
import json, os, sys, time, re, hashlib, urllib.request, urllib.error, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
KEY = open(r"C:\Users\starw\AppData\Local\notion_master_brain\api_key.txt").read().strip()
ROOT = os.path.join("D:", os.sep, "Projects", "VOX", "DerekOS_Master_Brain")
OUT = os.path.join(ROOT, "00_RAW_ARCHIVE", "notion-workspace", "NOTION_EVIDENCE_RELEASE_001")
H = {"Authorization": "Bearer " + KEY, "Notion-Version": "2022-06-28"}
SECRET_PAT = re.compile(
    r"(?i)(sk-[a-z0-9]{16,}|ntn_[a-z0-9]{20,}|api[_-]?key\s*[:=]\s*['\"]?[a-z0-9_\-]{16,}"
    r"|bearer\s+[a-z0-9_\.\-]{20,}|ghp_[a-z0-9]{20,}|xox[baprs]-[a-z0-9\-]{10,}"
    r"|password\s*[:=]\s*\S{6,})")

def get(url):
    for a in range(4):
        req = urllib.request.Request("https://api.notion.com/v1" + url, headers=H)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(1.2 * (a + 1)); continue
            return {"__error__": e.code}
    return {"__error__": "retries_exhausted"}

def rich(parts): return "".join(p.get("plain_text", "") for p in (parts or []))

def prop_value(v):
    t = v.get("type")
    if t in ("rich_text", "title"): return rich(v.get(t))
    if t == "select": return (v.get("select") or {}).get("name", "")
    if t == "multi_select": return ", ".join(x.get("name", "") for x in v.get("multi_select", []))
    if t == "number": return str(v.get("number"))
    if t == "checkbox": return str(v.get("checkbox"))
    if t == "date":
        d = v.get("date") or {}
        return f"{d.get('start','')}..{d.get('end','')}".rstrip('.')
    if t == "url": return v.get("url") or ""
    if t == "email": return v.get("email") or ""
    if t == "phone_number": return "[phone-redacted]"
    if t == "people": return "[people-ids:" + str(len(v.get("people", []))) + "]"
    if t == "relation": return "[relation:" + str(len(v.get("relation", []))) + "]"
    if t == "status": return (v.get("status") or {}).get("name", "")
    return ""

man = json.load(open(os.path.join(OUT, "manifest.json"), encoding="utf-8"))
seen, records = set(), []
for r in man["records"]:
    if r["page_id"] in seen: continue
    seen.add(r["page_id"])
    fn = os.path.join(OUT, "pages", r["page_id"] + ".json")
    rec = json.load(open(fn, encoding="utf-8"))
    meta = get("/pages/" + r["page_id"])
    time.sleep(0.35)
    if "__error__" in meta:
        records.append(r); continue
    props = meta.get("properties", {})
    lines = []
    for name, v in props.items():
        val = prop_value(v)
        if val and val not in ("False", "None"):
            lines.append(f"[property:{name}] {val}")
    prop_text = "\n".join(lines)
    n_sec = len(SECRET_PAT.findall(prop_text))
    if n_sec: prop_text = SECRET_PAT.sub("[REDACTED_SECRET]", prop_text)
    rec["property_count"] = len([l for l in lines])
    rec["property_text"] = prop_text
    rec["raw_text"] = (rec.get("raw_text") or "") + ("\n\n" + prop_text if prop_text else "")
    rec["char_count"] = len(rec["raw_text"])
    rec["secret_redactions"] = rec.get("secret_redactions", 0) + n_sec
    rec["extraction_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    body = dict(rec); body.pop("sha256", None)
    rec["sha256"] = hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    json.dump(rec, open(fn, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    r["sha256"] = rec["sha256"]; r["chars"] = rec["char_count"]
    records.append(r)
    print(f"  {r['page_id'][:8]} props={rec['property_count']:3d} chars={rec['char_count']}  {str(r.get('title'))[:45]}")

man["records"] = records
man["record_count"] = len(records)
man["patch"] = "pass-3 property capture + dedupe; 2026-08-12"
man["extraction_timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
rel = hashlib.sha256(json.dumps([r["sha256"] for r in sorted(records, key=lambda v: v["page_id"])],
                                sort_keys=True).encode()).hexdigest()
print("\nDONE pass 3:", len(records), "records; release content hash:", rel)
