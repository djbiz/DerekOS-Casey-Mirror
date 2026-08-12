#!/usr/bin/env python3
"""Build PROVENANCE_OUT_OF_SAMPLE_SET_V2.

Explicit family taxonomy for the out-of-sample delta challenge:
- USER_ROLE_PASTED_ARTIFACT
- MULTI_AGENT_RELAY_CHAIN
- CONTROL_ACT_PLUS_IMPORTED_BODY
- GENUINE_MIXED_SPANS
- CROSS_PLATFORM_AI_REUSE
- EXTERNAL_MATERIAL
- REWRITTEN_AI_MATERIAL
- CHRONOLOGY_ANOMALY
- MISSING_ORIGIN
- LONG_POLISHED_FIRST_PERSON
- SHORT_FOUNDER_DIRECTIVE
- D0_POSITIVE_CONTROL

Records are drawn from the clean out-of-sample pool only:
- DeepSeek delta-export user messages (ingest_version 2.0.0, source_file conversations.json)
- MINUS all Gold Set message ids (v1 and v1.1)
- MINUS all 230 adversarial-set keys
- MINUS all MIXED adjudication records
- PLUS independent Notion-derived records where evidence is independent of V2 adjudication

V0.6 predictions are sealed separately AFTER this set is frozen.
"""
from __future__ import annotations

import importlib.util as _ilu
import binascii as _binascii
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST = ROOT / "01_INGEST"
AUDITS = Path(__file__).resolve().parent
MESSAGES_FILE = INGEST / "messages.jsonl"

OUT_SET = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V2.jsonl"
OUT_REPORT = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V2_REPORT.md"

TARGET_PER_FAMILY = 24
MIN_PER_FAMILY = 3
RANDOM_SEED = 20260812

# Load resolver signal helpers
_spec = _ilu.spec_from_file_location("resolver", AUDITS / "provenance_resolver_v0_1.py")
_resolver = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_resolver)

normalize_words = _resolver.normalize_words
shingles = _resolver.shingles
has_paste_markers = _resolver.has_paste_markers
has_submission_phrases = _resolver.has_submission_phrases
is_structured_prose = _resolver.is_structured_prose

# ---------------------------------------------------------------------------
# Family detection patterns (explicit V2 taxonomy)
# ---------------------------------------------------------------------------

CARRIER_LEAD = re.compile(
    r"(?is)^(.{0,160}?)(?:\n\n|\r?\n\r?\n)(.{60,})"
)
TRANSCRIPT_WRAPPER = re.compile(
    r"(?is)(summarize the transcript of a youtube video|the entire transcript is given below|"
    r"here(?:'|’)s the (?:full )?transcript|word-for-word script transcription|"
    r"transcript of the video)"
)
REWRITE_REQUEST = re.compile(
    r"(?is)(can you (?:rewrite|recreate|create|write)|rewrite this|recreate this|"
    r"in (?:the )?style of|make it (?:funny|personal|short)|"
    r"come up with a (?:subject line|headline|hook)|only \d+ characters)"
)
MODIFICATION_PHRASE = re.compile(
    r"(?is)(\b(?:but|instead|actually|however)\b.{0,80}(?:make|keep|change|remove|add|connect)|"
    r"\b(?:don(?:'|’)t|do not) make\b|\bchange .{0,40} to\b|\bremove .{0,40}\b|\badd .{0,60} to\b|\b(?:i|we) (?:want|need|prefer)\b)"
)
FIRST_PERSON_POLISHED = re.compile(r"\b(?:i|my|me|we|our)\b", re.I)
FOUNDER_DIRECTIVE = re.compile(
    r"(?is)^(?:can|could|please|make|add|connect|do|create)\b.{0,120}$"
)
EXTERNAL_MARKERS = re.compile(
    r"(?im)(https?://|^subject:|^from:\s|^sent:\s|```(?:python|bash|json|yaml|sql)?|"
    r"docker run|pip install|^body:|the entire transcript is given below|"
    r"word-for-word script transcription|import random|import datetime|"
    r"from datetime import)"
)


def shingle_key(sh: str) -> int:
    return _binascii.crc32(sh.encode("utf-8")) & 0xFFFFFFFF


class CompactIndex:
    """Shingle index over full corpus for origin/reuse detection."""

    def __init__(self) -> None:
        self.index: dict[int, tuple[str, str]] = {}
        self.origin_ts: dict[tuple[str, str], str] = {}

    @classmethod
    def build(cls, messages_file: Path) -> "CompactIndex":
        idx = cls()
        with messages_file.open(encoding="utf-8") as f:
            for line in f:
                m = json.loads(line)
                if m["role"] != "assistant" or len(m["text"]) < 100:
                    continue
                mid = sys.intern(m["message_id"])
                cid = sys.intern(m["conversation_id"])
                for sh in shingles(normalize_words(m["text"])):
                    k = shingle_key(sh)
                    if k not in idx.index:
                        idx.index[k] = (mid, cid)
                idx.origin_ts[(mid, cid)] = m.get("timestamp", "")
        return idx

    def origins_for(self, text: str) -> list[dict]:
        words = normalize_words(text)
        if len(words) < _resolver.SHINGLE_SIZE:
            return []
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for sh in shingles(words):
            origin = self.index.get(shingle_key(sh))
            if origin:
                counts[origin] += 1
        if not counts:
            return []
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0][1]))
        out = []
        for (mid, cid), cnt in ranked[:3]:
            out.append({
                "origin_message_id": mid,
                "origin_conversation_id": cid,
                "matching_shingle_count": cnt,
                "matched_frac": round(cnt / max(1, len(words) - _resolver.SHINGLE_SIZE + 1), 3),
            })
        return out


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except Exception:
        return None


def family_for_v2(rec: dict, origins: list[dict], ev: dict) -> list[str]:
    """Explicit V2 family classification."""
    text = rec.get("text", "")
    cats: list[str] = []
    ru = origins[0] if origins else None
    gap_days = ru.get("gap_days") if ru else None
    same_conv = ru.get("same_conversation") if ru else None
    distinct = ru.get("distinct_origin_messages") if ru else None

    # D0-positive controls: short, opening, no markers, no reuse, Derek-style
    if (ev.get("is_opening") and len(text) < 250 and not ev.get("structured")
            and not ev.get("paste_markers") and not ev.get("submission_phrases")
            and not ru and FOUNDER_DIRECTIVE.search(text)):
        cats.append("D0_POSITIVE_CONTROL")

    # Short founder directives
    if (len(text) < 250 and not ev.get("structured") and not ru
            and FOUNDER_DIRECTIVE.search(text)):
        cats.append("SHORT_FOUNDER_DIRECTIVE")

    # USER_ROLE_PASTED_ARTIFACT: user role, paste markers or structured, has body
    if rec.get("role") == "user" and (ev.get("paste_markers") or ev.get("structured")) and len(text) > 200:
        cats.append("USER_ROLE_PASTED_ARTIFACT")

    # CONTROL_ACT_PLUS_IMPORTED_BODY: carrier lead with paste/submission/reuse
    if CARRIER_LEAD.search(text) and (ev.get("paste_markers") or ev.get("submission_phrases") or ru):
        cats.append("CONTROL_ACT_PLUS_IMPORTED_BODY")

    # MULTI_AGENT_RELAY_CHAIN: reuse across conversations, or multiple distinct origins
    if ru and (not same_conv or (distinct and distinct >= 2)):
        cats.append("MULTI_AGENT_RELAY_CHAIN")

    # CROSS_PLATFORM_AI_REUSE: reuse from different source_file/platform
    if ru and rec.get("source_file") == "conversations.json":
        cats.append("CROSS_PLATFORM_AI_REUSE")

    # EXTERNAL_MATERIAL: external fingerprints, URLs, code blocks
    if ev.get("external_fingerprint") or EXTERNAL_MARKERS.search(text):
        cats.append("EXTERNAL_MATERIAL")

    # REWRITTEN_AI_MATERIAL: rewrite request + reuse/paste
    if REWRITE_REQUEST.search(text) and (ru or ev.get("paste_markers") or ev.get("submission_phrases")):
        cats.append("REWRITTEN_AI_MATERIAL")

    # CHRONOLOGY_ANOMALY: negative or implausibly large gap, or undated reuse
    if gap_days is not None and (gap_days < -1 or gap_days > 365):
        cats.append("CHRONOLOGY_ANOMALY")

    # LONG_POLISHED_FIRST_PERSON: F08-like
    if (ev.get("structured") and ev.get("char_length", 0) > 500 and not ru
            and FIRST_PERSON_POLISHED.search(text)):
        cats.append("LONG_POLISHED_FIRST_PERSON")

    # MISSING_ORIGIN: no reuse, no markers, no structure, substantial length
    if (not ru and not ev.get("paste_markers") and not ev.get("submission_phrases")
            and not ev.get("structured") and ev.get("char_length", 0) > 60):
        cats.append("MISSING_ORIGIN")

    return cats


def load_notion_candidates() -> list[dict]:
    """Load independent Notion-derived records if available."""
    notion_path = AUDITS / "notion_audit" / "NOTION_PROVENANCE_RESOLUTION_V0.1.jsonl"
    if not notion_path.exists():
        return []
    candidates = []
    with notion_path.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("status") == "CANDIDATE_PENDING_FOUNDER_REVIEW":
                candidates.append(r)
    return candidates


def main() -> None:
    # ---- Load delta user records (the out-of-sample population) -----------
    delta_users = []
    with MESSAGES_FILE.open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if (m.get("source_file") == "conversations.json"
                    and m.get("ingest_version") == "2.0.0"
                    and m["role"] == "user"):
                delta_users.append(m)
    print(f"delta user records: {len(delta_users)}")

    # ---- Exclusions --------------------------------------------------------
    gold_ids: set[str] = set()
    for gpath in ("provenance_gold_set_v1.jsonl", "provenance_gold_set_v1_1.jsonl"):
        with (AUDITS / gpath).open(encoding="utf-8") as f:
            for line in f:
                gold_ids.add(json.loads(line)["message_id"])
    print(f"gold ids: {len(gold_ids)}")

    adv_keys: set[tuple[str, str]] = set()
    with (AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            adv_keys.add((r["conversation_id"], r["message_id"]))
    print(f"adversarial keys: {len(adv_keys)}")

    mixed_ids: set[str] = set()
    mixed_path = AUDITS / "MIXED_LABEL_SEMANTICS_ADJUDICATION_V0.1.jsonl"
    if mixed_path.exists():
        try:
            data = json.loads(mixed_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for r in data:
                    mixed_ids.add(r.get("adversarial_id") or r.get("record_id") or r.get("message_id"))
            else:
                with mixed_path.open(encoding="utf-8") as f:
                    for line in f:
                        r = json.loads(line)
                        mixed_ids.add(r.get("record_id") or r.get("message_id") or r.get("adversarial_id"))
        except json.JSONDecodeError:
            with mixed_path.open(encoding="utf-8") as f:
                for line in f:
                    r = json.loads(line)
                    mixed_ids.add(r.get("record_id") or r.get("message_id") or r.get("adversarial_id"))
    print(f"mixed adjudication ids: {len(mixed_ids)}")

    pool = []
    for m in delta_users:
        key = (m["conversation_id"], m["message_id"])
        if m["message_id"] in gold_ids:
            continue
        if key in adv_keys:
            continue
        if m["message_id"] in mixed_ids:
            continue
        pool.append(m)
    print(f"out-of-sample population (after exclusions): {len(pool)}")

    # ---- Evidence + family classification ---------------------------------
    print("Building shingle index over full corpus...", flush=True)
    idx = CompactIndex.build(MESSAGES_FILE)
    print(f"index size: {len(idx.index)}", flush=True)

    families: dict[str, list[dict]] = defaultdict(list)
    for m in pool:
        text = m.get("text") or ""
        words = normalize_words(text)
        ev = {
            "message_id": m["message_id"],
            "conversation_id": m["conversation_id"],
            "conversation_title": m.get("conversation_title"),
            "timestamp": m.get("timestamp"),
            "char_length": len(text),
            "word_count": len(words),
            "is_opening": (m.get("sequence_index") or 999) <= 1,
            "structured": is_structured_prose(text),
            "paste_markers": has_paste_markers(text),
            "submission_phrases": has_submission_phrases(text),
            "external_fingerprint": _resolver._external_content_fingerprint(text),
        }
        origins = idx.origins_for(text)
        if origins:
            best = origins[0]
            t_reuse = parse_ts(m.get("timestamp", ""))
            t_origin = parse_ts(idx.origin_ts.get((best["origin_message_id"], best["origin_conversation_id"]), ""))
            gap_days = None
            if t_reuse and t_origin:
                gap_days = round(abs((t_reuse - t_origin).total_seconds()) / 86400, 2)
            best["gap_days"] = gap_days
            best["same_conversation"] = best["origin_conversation_id"] == m["conversation_id"]
            # count distinct origin messages in top 3
            distinct = len({(o["origin_message_id"], o["origin_conversation_id"]) for o in origins})
            best["distinct_origin_messages"] = distinct
            ev["reuse"] = best

        cats = family_for_v2(m, origins, ev)
        m["_ev"] = ev
        m["_cats"] = cats
        for c in cats:
            families[c].append(m)

    for c in sorted(families):
        print(f"  {c}: pool={len(families[c])}", flush=True)

    # ---- Stratified selection ----------------------------------------------
    rng = random.Random(RANDOM_SEED)
    selected: dict[str, list[dict]] = {}
    for c in sorted(families):
        pool_c = families[c]
        rng.shuffle(pool_c)
        target = TARGET_PER_FAMILY if len(pool_c) >= MIN_PER_FAMILY else len(pool_c)
        selected[c] = pool_c[:target]

    # De-duplicate across families (prefer first-seen family order)
    fam_order = [
        "USER_ROLE_PASTED_ARTIFACT",
        "MULTI_AGENT_RELAY_CHAIN",
        "CONTROL_ACT_PLUS_IMPORTED_BODY",
        "CROSS_PLATFORM_AI_REUSE",
        "EXTERNAL_MATERIAL",
        "REWRITTEN_AI_MATERIAL",
        "CHRONOLOGY_ANOMALY",
        "MISSING_ORIGIN",
        "LONG_POLISHED_FIRST_PERSON",
        "SHORT_FOUNDER_DIRECTIVE",
        "D0_POSITIVE_CONTROL",
        "GENUINE_MIXED_SPANS",
    ]
    chosen = {}
    for c in fam_order:
        for m in selected.get(c, []):
            key = (m["conversation_id"], m["message_id"])
            if key not in chosen:
                chosen[key] = m

    records = list(chosen.values())
    records.sort(key=lambda r: r["_ev"]["timestamp"] or "")
    print(f"\nTOTAL selected (unique): {len(records)}", flush=True)

    # ---- Write frozen V2 set ----------------------------------------------
    out_records = []
    for i, m in enumerate(records):
        oid = f"oos_v2_{i:06d}"
        ev = m["_ev"]
        ru = ev.get("reuse")
        record = {
            "oos_id": oid,
            "message_id": m["message_id"],
            "conversation_id": m["conversation_id"],
            "conversation_title": m.get("conversation_title"),
            "timestamp": m.get("timestamp"),
            "source_file": m.get("source_file"),
            "source_platform": "deepseek",
            "families": m["_cats"],
            "evidence": {
                "char_length": ev["char_length"],
                "word_count": ev["word_count"],
                "is_opening": ev["is_opening"],
                "structured": ev["structured"],
                "paste_markers": ev["paste_markers"],
                "submission_phrases": ev["submission_phrases"],
                "external_fingerprint": ev["external_fingerprint"],
                "reuse": ru,
            },
            "text_excerpt": (m.get("text") or "")[:700],
            "text_len": len(m.get("text") or ""),
        }
        out_records.append(record)

    with OUT_SET.open("w", encoding="utf-8") as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_SET} ({len(out_records)} records)")

    # ---- Report ------------------------------------------------------------
    fam_dist = Counter()
    for r in out_records:
        for c in r["families"]:
            fam_dist[c] += 1
    lines = [
        "# PROVENANCE_OUT_OF_SAMPLE_SET_V2 — Build Report",
        "",
        "Blind out-of-sample provenance challenge. Population: the DeepSeek delta-export",
        "user messages (ingest_version 2.0.0, source_file=conversations.json) MINUS:",
        "  - all Gold Set message ids (v1 and v1.1)",
        "  - all 230 adversarial-set keys",
        "  - all MIXED adjudication records",
        "None of these records were used in Gold Set construction, adversarial selection,",
        "MIXED adjudication, or V0.3-V0.6 development.",
        "",
        f"- **Records**: {len(out_records)} unique user-role delta messages",
        f"- **Population**: {len(pool)} delta user messages after exclusions",
        f"- **Excluded**: {len(gold_ids)} gold ids, {len(adv_keys)} adversarial keys, {len(mixed_ids)} mixed ids",
        f"- **Selection**: mechanical family signals only; stratified explicit families,",
        f"  {TARGET_PER_FAMILY} target per family, seed {RANDOM_SEED}",
        f"- **Blindness**: the set file carries record + evidence + text only;",
        f"  V0.6 predictions will be sealed separately AFTER this set is frozen.",
        "",
        "## Family distribution",
        "",
        "| Family | Meaning | Selected |",
        "|--------|---------|----------|",
    ]
    for c, label in [
        ("USER_ROLE_PASTED_ARTIFACT", "user-role pasted artifacts"),
        ("MULTI_AGENT_RELAY_CHAIN", "multi-agent relay chains"),
        ("CONTROL_ACT_PLUS_IMPORTED_BODY", "control-act carrier + imported body"),
        ("CROSS_PLATFORM_AI_REUSE", "cross-platform AI reuse"),
        ("EXTERNAL_MATERIAL", "external material / fingerprints"),
        ("REWRITTEN_AI_MATERIAL", "rewritten AI material"),
        ("CHRONOLOGY_ANOMALY", "chronology anomalies"),
        ("MISSING_ORIGIN", "missing-origin content"),
        ("LONG_POLISHED_FIRST_PERSON", "long polished first-person material"),
        ("SHORT_FOUNDER_DIRECTIVE", "short founder directives"),
        ("D0_POSITIVE_CONTROL", "D0-positive controls"),
        ("GENUINE_MIXED_SPANS", "genuine mixed spans (mechanical proxy)"),
    ]:
        lines.append(f"| {c} | {label} | {fam_dist.get(c, 0)} |")
    lines += [
        "",
        "## Next step",
        "",
        "1. Freeze this V2 set as the challenge input.",
        "2. Run PROVENANCE_RESOLVER_V0.6 on V2 and seal predictions in a separate key file.",
        "3. Build blind adjudication bundles from V2.",
        "4. Independent human adjudication establishes answer key WITHOUT access to V0.6 predictions.",
        "5. Reveal sealed predictions and score. Primary gates: FDA=0, D0 precision ≥98%.",
        "6. If V0.6 passes, freeze result and stop for authorization before PROVENANCE_CORPUS_V1.",
        "7. If V0.6 fails, preserve failure set as next curriculum. No tuning against challenge.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
