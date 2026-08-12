"""
PROVENANCE_ADVERSARIAL_SET_V1 builder (spec directive 2026-08-12).

Goal: produce a resolver-SELECTED set of ~200-300 hard provenance cases that
stress the PROVENANCE_RESOLVER_V0.1 where it is most likely to fail, so manual
adjudication can measure generalization beyond the 40-record gold set. This is
deliberately NOT a random sample: the resolver hunts its own hardest cases.

Selection happens by MECHANICAL EVIDENCE SIGNALS (stage-1/2 output), not by
reading gold labels. The resolver's own prediction is written to a SEPARATE
key file so manual adjudication can be done blind to resolver predictions.

Memory strategy: ONE shared shingle index (the resolver's ReuseIndex, built
from a stable snapshot when ADV_SET_SNAPSHOT is set). Evidence and
classification both read from it; no second index is built.

Categories (from the Board directive):
  C01  high-confidence D0 that looks unusually polished
  C02  strong earlier-assistant similarity (near/over reuse threshold)
  C03  long user messages with no located origin
  C04  multiple reuse candidates (ambiguous origin)
  C05  mixed pasted + Derek commentary (segmentation stress)
  C06  cross-conversation reuse separated by weeks/months
  C07  partial rather than exact reuse
  C08  assistant text that Derek substantially rewrote (rewrite stress)
  C09  external material with no corpus origin (PC2-style)
  C10  short 'yes/add this/do this' messages (AD3/AD4 stress)
  C11  contradictory evidence
  C12  resolver abstentions (UNRESOLVED)
  C13  low-confidence D0
  C14  AD3/AD4 adoption candidates

Blindness: PROVENANCE_ADVERSARIAL_SET_V1.jsonl contains the record + evidence
package + category ONLY. Resolver predictions go to
PROVENANCE_ADVERSARIAL_SET_V1_predictions.json keyed by adversarial_id.
"""

from __future__ import annotations

import importlib.util as _ilu
import binascii as _binascii
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST = ROOT / "01_INGEST"
AUDITS = Path(__file__).resolve().parent

SNAPSHOT = os.environ.get("ADV_SET_SNAPSHOT")
MESSAGES_FILE = Path(SNAPSHOT) if SNAPSHOT else INGEST / "messages.jsonl"

OUT_SET = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl"
OUT_PREDS = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1_predictions.json"
OUT_REPORT = AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1_REPORT.md"

TARGET_PER_CATEGORY = 20
RANDOM_SEED = 20260812

# Load the resolver module for its signal helpers + classification.
_spec = _ilu.spec_from_file_location("resolver", AUDITS / "provenance_resolver_v0_1.py")
_resolver = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_resolver)

normalize_words = _resolver.normalize_words
shingles = _resolver.shingles
has_paste_markers = _resolver.has_paste_markers
has_submission_phrases = _resolver.has_submission_phrases
is_structured_prose = _resolver.is_structured_prose
classify_record = _resolver.classify_record


def load_user_messages() -> list[dict]:
    """Only user-role messages are candidates; load them directly."""
    msgs = []
    with MESSAGES_FILE.open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m["role"] == "user":
                msgs.append(m)
    return msgs


def shingle_key(sh: str) -> int:
    """Compact deterministic integer key for a shingle (CRC32; collisions
    astronomically unlikely at ~20M entries and only affect selection pool
    membership, not adjudication truth)."""
    return _binascii.crc32(sh.encode("utf-8")) & 0xFFFFFFFF


class CompactIndex:
    """Memory-lean shingle index with a find_origin() interface compatible with
    the resolver's ReuseIndex, so both evidence_for and classify_record share
    ONE structure. Uses interned ids (ids repeat heavily across the corpus)
    and integer shingle keys to stay small enough for a ~1GB headroom machine.
    Stores only the origin timestamp, not full assistant records."""

    def __init__(self) -> None:
        self.index: dict[int, tuple[str, str]] = {}  # shingle_key -> (mid, cid) [interned]
        self.origin_ts: dict[tuple[str, str], str] = {}  # (mid,cid) -> timestamp

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

    def find_origin(self, text: str, conv_id: str) -> dict | None:
        """Same return shape as ReuseIndex.find_origin (best origin by count)."""
        words = normalize_words(text)
        if len(words) < _resolver.SHINGLE_SIZE:
            return None
        origins: dict[tuple[str, str], int] = defaultdict(int)
        for sh in shingles(words):
            origin = self.index.get(shingle_key(sh))
            if origin:
                origins[origin] += 1
        if not origins:
            return None
        best_origin, count = max(origins.items(), key=lambda kv: kv[1])
        if count < _resolver.MIN_MATCH_SHINGLES:
            return None
        return {
            "origin_message_id": best_origin[0],
            "origin_conversation_id": best_origin[1],
            "same_conversation": best_origin[1] == conv_id,
            "matching_shingle_count": count,
        }

    def origin_ts_for(self, mid: str, cid: str) -> str:
        return self.origin_ts.get((mid, cid), "")


def build_convs() -> dict[str, dict]:
    """Conversation topology. classify_record only uses sequence_index (for
    opening detection) via opening_message(); preceding_assistant's result is
    never used by any branch. An empty map satisfies the interface."""
    return {}


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def evidence_for(rec: dict, reuse_idx: CompactIndex) -> dict:
    """Mechanical evidence package for one user message, from the shared index."""
    text = rec.get("text", "")
    words = normalize_words(text)
    ev = {
        "message_id": rec["message_id"],
        "conversation_id": rec["conversation_id"],
        "conversation_title": rec.get("conversation_title"),
        "timestamp": rec.get("timestamp"),
        "char_length": len(text),
        "word_count": len(words),
        "is_opening": (rec.get("sequence_index") or 999) <= 1,
        "structured": is_structured_prose(text),
        "paste_markers": has_paste_markers(text),
        "submission_phrases": has_submission_phrases(text),
        "external_fingerprint": _resolver._external_content_fingerprint(text),
        "reuse": None,
    }
    if len(words) >= _resolver.SHINGLE_SIZE:
        origins: dict[tuple[str, str], int] = defaultdict(int)
        for sh in shingles(words):
            origin = reuse_idx.index.get(shingle_key(sh))
            if origin:
                origins[origin] += 1
        if origins:
            ranked = sorted(origins.items(), key=lambda kv: (-kv[1], kv[0][1]))
            (best_mid, best_cid), best_count = ranked[0]
            same_conv = best_cid == rec["conversation_id"]
            best_ts = reuse_idx.origin_ts_for(best_mid, best_cid)
            gap_days = None
            t_reuse = parse_ts(rec.get("timestamp", ""))
            t_origin = parse_ts(best_ts)
            if t_reuse and t_origin:
                gap_days = round(abs((t_reuse - t_origin).total_seconds()) / 86400, 2)
            ev["reuse"] = {
                "origin_message_id": best_mid,
                "origin_conversation_id": best_cid,
                "same_conversation": same_conv,
                "matching_shingle_count": best_count,
                "distinct_origin_messages": len(origins),
                "distinct_origin_conversations": len({c for _, c in origins}),
                "matched_frac": round(best_count / max(1, len(words) - _resolver.SHINGLE_SIZE + 1), 3),
                "origin_timestamp": best_ts,
                "gap_days": gap_days,
            }
    return ev


def category_for(rec: dict, ev: dict) -> list[str]:
    """Which adversarial categories does this record exercise? (mechanical only)."""
    text = rec.get("text", "")
    cats: list[str] = []
    ru = ev.get("reuse")

    if not ru and ev["structured"] and ev["char_length"] > 250 and not ev["is_opening"]:
        cats.append("C01")  # high-confidence-looking D0 that is unusually polished
    if ru and ru["matching_shingle_count"] >= _resolver.MIN_MATCH_SHINGLES:
        cats.append("C02")  # strong earlier-assistant similarity
    if not ru and ev["char_length"] > 500:
        cats.append("C03")  # long, no located origin
    if ru and ru["distinct_origin_messages"] >= 3:
        cats.append("C04")  # multiple reuse candidates
    if (ev["paste_markers"] or ev["submission_phrases"]) and ev["char_length"] > 300:
        cats.append("C05")  # mixed pasted + Derek commentary
    if ru and not ru["same_conversation"] and (ru.get("gap_days") or 0) >= 14:
        cats.append("C06")  # cross-conversation reuse, weeks/months apart
    if ru and 0.15 <= ru["matched_frac"] <= 0.7:
        cats.append("C07")  # partial rather than exact reuse
    if ru and ru["same_conversation"] and ru["matched_frac"] < 0.9:
        cats.append("C08")  # assistant text Derek substantially rewrote
    if not ru and ev["external_fingerprint"]:
        cats.append("C09")  # external material, no corpus origin
    if ev["char_length"] < 90 and (
        _resolver.APPROVAL_PATTERNS.match(text.strip())
        or _resolver.SUBMISSION_PHRASES.search(text)
        or _resolver.MODIFICATION_PATTERNS.search(text)
    ):
        cats.append("C10")  # short yes/add-this/do-this
    if ev["paste_markers"] and ev["submission_phrases"]:
        cats.append("C11")  # contradictory evidence
    if ru and _resolver.REJECTION_PATTERNS.search(text):
        cats.append("C11")
    if _resolver.APPROVAL_PATTERNS.match(text.strip()) or _resolver.MODIFICATION_PATTERNS.search(text):
        cats.append("C14")  # AD3/AD4 adoption candidates
    return cats


def main() -> None:
    print("Loading user messages...", flush=True)
    user_msgs = load_user_messages()
    print(f"  {len(user_msgs)} user-role", flush=True)

    gold_ids: set[str] = set()
    for gpath in ("provenance_gold_set_v1.jsonl", "provenance_gold_set_v1_1.jsonl"):
        with (AUDITS / gpath).open(encoding="utf-8") as f:
            for line in f:
                gold_ids.add(json.loads(line)["message_id"])
    print(f"  excluding {len(gold_ids)} gold-set message ids", flush=True)

    print("Building shared shingle index + conversation topology...", flush=True)
    reuse_idx = CompactIndex.build(MESSAGES_FILE)
    print(f"  index size: {len(reuse_idx.index)}", flush=True)
    convs = build_convs()
    print(f"  conversations: {len(convs)}", flush=True)

    print("Classifying user messages...", flush=True)
    pools: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    preds: dict[str, dict] = {}
    counter = 0
    for i, rec in enumerate(user_msgs):
        if i and i % 5000 == 0:
            print(f"  ...{i}/{len(user_msgs)}", flush=True)
        if rec["message_id"] in gold_ids:
            continue
        ev = evidence_for(rec, reuse_idx)
        pred = classify_record(rec, reuse_idx, convs)
        aid = f"adv_{counter:06d}"
        counter += 1
        preds[aid] = {
            "adversarial_id": aid,
            "message_id": rec["message_id"],
            "evidence_class": pred["evidence_class"],
            "provenance_certainty": pred.get("provenance_certainty"),
            "adoption_status": pred.get("adoption_status"),
            "reason": pred.get("reason", ""),
            "requires_review": pred.get("requires_review", False),
        }
        cats = category_for(rec, ev)
        if pred["evidence_class"] == "UNRESOLVED":
            cats.append("C12")
        if pred["evidence_class"] == "D0" and pred.get("provenance_certainty") in ("PC1", "PC2"):
            cats.append("C13")
        record = {
            "adversarial_id": aid,
            "message_id": rec["message_id"],
            "conversation_id": rec["conversation_id"],
            "conversation_title": rec.get("conversation_title"),
            "timestamp": rec.get("timestamp"),
            "source_file": rec.get("source_file"),
            "categories": cats,
            "evidence": ev,
            # NOTE: text included for adjudication; predictions are NOT here.
            "text_excerpt": rec["text"][:600],
            "text_len": len(rec["text"]),
        }
        for cat in cats:
            pools[cat].append((aid, record))

    print("Selecting stratified sample...", flush=True)
    rng = random.Random(RANDOM_SEED)
    selected: dict[str, list[tuple[str, dict]]] = {}
    for cat in sorted(pools):
        pool = pools[cat]
        rng.shuffle(pool)
        selected[cat] = pool[:TARGET_PER_CATEGORY]
        print(f"  {cat}: pool={len(pool):6d}  selected={len(selected[cat])}", flush=True)

    chosen_by_id: dict[str, dict] = {}
    chosen_preds: dict[str, dict] = {}
    for cat in sorted(selected):
        for aid, record in selected[cat]:
            if record["message_id"] in chosen_by_id:
                continue
            chosen_by_id[record["message_id"]] = record
            chosen_preds[aid] = preds[aid]

    records = list(chosen_by_id.values())
    records.sort(key=lambda r: r["adversarial_id"])
    print(f"\nTOTAL selected (unique messages): {len(records)}", flush=True)

    cat_dist: Counter[str] = Counter()
    for r in records:
        for c in r["categories"]:
            cat_dist[c] += 1
    print("Category distribution:", dict(sorted(cat_dist.items())), flush=True)

    with OUT_SET.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Wrote {OUT_SET}", flush=True)

    with OUT_PREDS.open("w", encoding="utf-8") as f:
        json.dump({"seed": RANDOM_SEED, "count": len(chosen_preds), "predictions": chosen_preds},
                  f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_PREDS}", flush=True)

    lines = [
        "# PROVENANCE_ADVERSARIAL_SET_V1 — Build Report",
        "",
        "Resolver-selected hard cases for manual adjudication beyond the 40-record gold set.",
        "",
        f"- **Records**: {len(records)} unique user-role messages (excludes all gold-set records)",
        f"- **Corpus**: {len(user_msgs)} user-role messages from the snapshot at build time "
        f"({'merged corpus' if SNAPSHOT else '01_INGEST/messages.jsonl'})",
        f"- **Selection**: mechanical evidence signals only (never gold labels); stratified",
        f"  across 14 adversarial categories, {TARGET_PER_CATEGORY} target per category, seed {RANDOM_SEED}",
        f"- **Blindness**: `PROVENANCE_ADVERSARIAL_SET_V1.jsonl` carries evidence + text only;",
        f"  resolver predictions are in `PROVENANCE_ADVERSARIAL_SET_V1_predictions.json`",
        "  (keyed by adversarial_id) so adjudication happens blind to resolver output.",
        "",
        "## Category distribution",
        "",
        "| Cat | Meaning | Selected |",
        "|-----|---------|----------|",
    ]
    for cat, label in [
        ("C01", "high-confidence-looking D0, unusually polished"),
        ("C02", "strong earlier-assistant similarity"),
        ("C03", "long user messages, no located origin"),
        ("C04", "multiple reuse candidates"),
        ("C05", "mixed pasted + Derek commentary (segmentation)"),
        ("C06", "cross-conversation reuse, weeks/months apart"),
        ("C07", "partial rather than exact reuse"),
        ("C08", "assistant text substantially rewritten"),
        ("C09", "external material, no corpus origin"),
        ("C10", "short yes/add-this/do-this"),
        ("C11", "contradictory evidence"),
        ("C12", "resolver abstentions (UNRESOLVED)"),
        ("C13", "low-confidence D0"),
        ("C14", "AD3/AD4 adoption candidates"),
    ]:
        lines.append(f"| {cat} | {label} | {cat_dist.get(cat, 0)} |")
    lines += [
        "",
        "## Next step",
        "",
        "Manual adjudication (Claude / Audit Bot), blind to resolver predictions. For each",
        "record assign: evidence_class, adoption_status, provenance_certainty, requires_review.",
        "Primary gate: **False Derek Attribution = 0** on the adjudicated set. After",
        "adjudication, compare against the predictions key file and report per-category",
        "precision, then decide whether to authorize full-corpus provenance resolution.",
    ]
    OUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_REPORT}", flush=True)


if __name__ == "__main__":
    main()
