"""
PROVENANCE_OUT_OF_SAMPLE_SET_V1 builder.

Out-of-sample population: the 3,080 delta-export records (DeepSeek platform,
source_file='conversations.json', ingest_version 2.0.0) MINUS:
  - the 12 delta records already selected into PROVENANCE_ADVERSARIAL_SET_V1
  - all Gold Set message ids (v1 and v1.1)
  - all MIXED_SEMANTICS_ADJUDICATION_V1 records (subset of the adversarial set)

These records were never used for Gold Set construction, adversarial selection,
MIXED adjudication, or V0.6 development. They are a genuine out-of-sample
population from a DIFFERENT AI platform, which stresses cross-platform reuse.

Selection: stratified across nine hard families (F01-F09) by mechanical
evidence signals. The resolver's own prediction is sealed in a separate key
file so adjudication happens blind.

Blindness: PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl carries record + evidence
package + family ONLY. Resolver predictions go to
PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json keyed by oos_id.
"""

from __future__ import annotations

import importlib.util as _ilu
import binascii as _binascii
import json
import os
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
OUT_SET = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl"
OUT_PREDS = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json"
OUT_REPORT = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1_REPORT.md"

TARGET_PER_FAMILY = 24
RANDOM_SEED = 20260812

# Load the resolver for its signal helpers + classification.
_spec = _ilu.spec_from_file_location("resolver", AUDITS / "provenance_resolver_v0_1.py")
_resolver = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_resolver)

normalize_words = _resolver.normalize_words
shingles = _resolver.shingles
has_paste_markers = _resolver.has_paste_markers
has_submission_phrases = _resolver.has_submission_phrases
is_structured_prose = _resolver.is_structured_prose

# --- Family detection patterns (mechanical, from the Board's hard families) --
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

# F08: long polished first-person material (looks D0, often pasted)
# F09: unknown-origin content (no reuse, no markers, no structure)


def shingle_key(sh: str) -> int:
    return _binascii.crc32(sh.encode("utf-8")) & 0xFFFFFFFF


class CompactIndex:
    """Same shingle index as the adversarial builder, over the full corpus."""

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
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def family_for(rec: dict, origins: list[dict], ev: dict) -> list[str]:
    text = rec.get("text", "")
    cats: list[str] = []
    ru = origins[0] if origins else None

    if CARRIER_LEAD.search(text) and (ev["paste_markers"] or ev["submission_phrases"] or ru):
        cats.append("F01")  # carrier + paste
    if MODIFICATION_PHRASE.search(text) and (ev["paste_markers"] or ev["submission_phrases"] or (ru and ru["matched_frac"] >= 0.15)):
        cats.append("F02")  # substantive Derek modification + paste
    if TRANSCRIPT_WRAPPER.search(text):
        cats.append("F03")  # transcript wrappers
    if REWRITE_REQUEST.search(text):
        cats.append("F04")  # rewrite requests
    if ru and rec.get("source_file") == "conversations.json":
        # origin from a different platform/export => cross-platform reuse
        cats.append("F05")
    if ru and not rec.get("is_opening"):
        cats.append("F06")  # Derek->AI->Derek chain candidates (reuse + not opening)
    if ev["external_fingerprint"] or (ev["submission_phrases"] and ev["structured"]):
        cats.append("F07")  # external -> Derek -> AI chain
    if ev["structured"] and ev["char_length"] > 500 and not ru and FIRST_PERSON_POLISHED.search(text):
        cats.append("F08")  # long polished first-person material
    if not ru and not ev["paste_markers"] and not ev["submission_phrases"] and not ev["structured"] and ev["char_length"] > 60:
        cats.append("F09")  # unknown-origin content
    return cats


def main() -> None:
    # ---- Load delta user records (the out-of-sample population) -----------
    delta_users = []
    with MESSAGES_FILE.open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m.get("source_file") == "conversations.json" and m.get("ingest_version") == "2.0.0" and m["role"] == "user":
                delta_users.append(m)
    print(f"delta user records: {len(delta_users)}")

    # ---- Exclusions --------------------------------------------------------
    gold_ids: set[str] = set()
    for gpath in ("provenance_gold_set_v1.jsonl", "provenance_gold_set_v1_1.jsonl"):
        with (AUDITS / gpath).open(encoding="utf-8") as f:
            for line in f:
                gold_ids.add(json.loads(line)["message_id"])
    print(f"gold ids: {len(gold_ids)}")

    adv_keys: set[tuple[str, str]] = set()  # (conversation_id, message_id)
    with (AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            adv_keys.add((r["conversation_id"], r["message_id"]))
    print(f"adversarial keys: {len(adv_keys)}")

    pool = []
    for m in delta_users:
        key = (m["conversation_id"], m["message_id"])
        if m["message_id"] in gold_ids:
            continue
        if key in adv_keys:
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
            ev["reuse"] = best
        cats = family_for(m, origins, ev)
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
        selected[c] = pool_c[:TARGET_PER_FAMILY]

    chosen = {}
    for c in sorted(selected):
        for m in selected[c]:
            key = (m["conversation_id"], m["message_id"])
            chosen[key] = m

    records = list(chosen.values())
    records.sort(key=lambda r: r["_ev"]["timestamp"] or "")
    print(f"\nTOTAL selected (unique): {len(records)}", flush=True)

    # ---- Write blind set ---------------------------------------------------
    out_records = []
    for i, m in enumerate(records):
        oid = f"oos_{i:06d}"
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
            "text_excerpt": (m.get("text") or "")[:600],
            "text_len": len(m.get("text") or ""),
        }
        out_records.append(record)

    with OUT_SET.open("w", encoding="utf-8") as f:
        for r in out_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_SET} ({len(out_records)} records)")

    # NOTE: sealed predictions are produced in a separate step
    # (build_out_of_sample_bundles_v1.py) AFTER the bundles exist, so
    # adjudication stays blind to resolver output. This file writes the blind
    # set + report only.

    # ---- Report ------------------------------------------------------------
    fam_dist = Counter()
    for r in out_records:
        for c in r["families"]:
            fam_dist[c] += 1
    lines = [
        "# PROVENANCE_OUT_OF_SAMPLE_SET_V1 — Build Report",
        "",
        "Blind out-of-sample provenance challenge. Population: the 3,080 delta-export",
        "records (DeepSeek platform) minus all Gold Set ids, all 230 adversarial-set",
        "records, and all MIXED adjudication records. None of these records were used",
        "in Gold Set construction, adversarial selection, MIXED adjudication, or V0.6",
        "development.",
        "",
        f"- **Records**: {len(out_records)} unique user-role delta messages",
        f"- **Population**: {len(pool)} delta user messages after exclusions",
        f"- **Excluded**: {len(gold_ids)} gold ids, {len(adv_keys)} adversarial keys",
        f"- **Selection**: mechanical family signals only; stratified F01-F09,",
        f"  {TARGET_PER_FAMILY} target per family, seed {RANDOM_SEED}",
        f"- **Blindness**: the set file carries evidence + text only; V0.6 predictions",
        "  are sealed in PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json",
        "",
        "## Family distribution",
        "",
        "| Family | Meaning | Selected |",
        "|--------|---------|----------|",
    ]
    for c, label in [
        ("F01", "carrier + paste"),
        ("F02", "substantive Derek modification + paste"),
        ("F03", "transcript wrappers"),
        ("F04", "rewrite requests"),
        ("F05", "cross-platform AI reuse"),
        ("F06", "Derek->AI->Derek chains"),
        ("F07", "external->Derek->AI chains"),
        ("F08", "long polished first-person material"),
        ("F09", "unknown-origin content"),
    ]:
        lines.append(f"| {c} | {label} | {fam_dist.get(c, 0)} |")
    lines += [
        "",
        "## Next step",
        "",
        "Manual blind adjudication of all records (Claude / Audit Bot). Assign per",
        "record: evidence_class, adoption_status, provenance_certainty, requires_review,",
        "origin_record_id. Primary gate: **False Derek Attribution = 0**. Then reveal",
        "the sealed V0.6 predictions and score. No tuning after seeing results.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_REPORT}")


if __name__ == "__main__":
    main()
