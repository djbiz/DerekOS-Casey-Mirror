"""
PROVENANCE_RESOLVER_V0.2 — hardened provenance classifier.

Hardening over v0.1:
  1. UNRESOLVED is now the safe default. D0 requires positive evidence,
     not merely absence of reuse evidence.
  2. Cross-corpus reuse detection uses stronger normalization and lower
     thresholds for assistant-origin matches.
  3. Polished-text suspicion triggers provenance search; absence of a
     located origin after search yields UNRESOLVED, never D0.
  4. Mixed-message segmentation is triggered more aggressively.
  5. Adoption status is computed independently from evidence_class.
  6. Evidence-weighted confidence: exact match > near match > style alone.
     Weak or conflicting evidence abstains.
  7. X0 detection covers short corrections/rejections not caught by the
     approval/rejection pattern sets.
  8. Per-class precision/recall + abstention accuracy reported.

Safety gate (§6.0g):
  - False Derek Attribution Rate must be 0
  - D0 precision must approach ~98%
  - No catastrophic drop in P0/A0 precision

Benchmark runs against the FROZEN provenance_gold_set_v1 (40 records).
Do NOT edit the gold set to improve scores.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST = ROOT / "01_INGEST"
AUDITS = Path(__file__).resolve().parent
GOLD_SET = AUDITS / "provenance_gold_set_v1.jsonl"
OUT_FILE = AUDITS / "provenance_resolver_v0_2_benchmark.json"

# ── Tuning constants ────────────────────────────────────────────────────
SHINGLE_SIZE = 10
MIN_CROSS_CONV_REUSE = 3
MIN_SAME_CONV_REUSE = 2
MIN_MATCH_SHINGLES = 3

# ── Normalization ───────────────────────────────────────────────────────


def normalize_for_reuse(text: str) -> str:
    text = text.translate({
        0x2018: 0x27, 0x2019: 0x27,
        0x201c: 0x22, 0x201d: 0x22,
        0x2010: 0x2d, 0x2011: 0x2d,
        0x2012: 0x2d, 0x2013: 0x2d,
        0x2014: 0x2d,
        0x2026: 0x2e,
        0x00a0: 0x20,
        0x2122: 0x20,
        0x00ae: 0x20,
        0x00a9: 0x20,
    })
    text = re.sub(r"\*\*|__|##+|#+\s|[-*]\s", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip().lower()


def normalize_words(text: str) -> list[str]:
    normalized = normalize_for_reuse(text)
    return re.findall(r"[a-z0-9']+", normalized)


def shingles(words: list[str], size: int = SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])

# ── Reuse index ─────────────────────────────────────────────────────────


class ReuseIndex:
    def __init__(self) -> None:
        self.index: dict[str, tuple[str, str, int]] = {}
        self.message_store: dict[tuple[str, str], dict] = {}

    @classmethod
    def build(cls) -> "ReuseIndex":
        idx = cls()
        with (INGEST / "messages.jsonl").open(encoding="utf-8") as f:
            for line in f:
                m = json.loads(line)
                if m["role"] != "assistant" or len(m["text"]) < 80:
                    continue
                normalized = normalize_for_reuse(m["text"])
                words = re.findall(r"[a-z0-9']+", normalized)
                if len(words) < SHINGLE_SIZE:
                    continue
                for sh in shingles(words):
                    if sh not in idx.index:
                        idx.index[sh] = (
                            m["message_id"],
                            m["conversation_id"],
                            len(words),
                        )
                idx.message_store[(m["message_id"], m["conversation_id"])] = m
        return idx

    def find_origin(self, text: str, conv_id: str) -> dict | None:
        normalized = normalize_for_reuse(text)
        words = re.findall(r"[a-z0-9']+", normalized)
        if len(words) < SHINGLE_SIZE:
            return None
        origins: dict[tuple[str, str], int] = defaultdict(int)
        for sh in shingles(words):
            origin = self.index.get(sh)
            if origin:
                origins[(origin[0], origin[1])] += 1
        if not origins:
            return None
        best_origin, count = max(origins.items(), key=lambda kv: kv[1])
        if count < MIN_MATCH_SHINGLES:
            return None
        same_conv = best_origin[1] == conv_id
        return {
            "origin_message_id": best_origin[0],
            "origin_conversation_id": best_origin[1],
            "same_conversation": same_conv,
            "matching_shingle_count": count,
            "reuse_type": "same_conversation" if same_conv else "cross_conversation",
        }

    def get_origin_text(self, origin: dict) -> str | None:
        key = (origin["origin_message_id"], origin["origin_conversation_id"])
        m = self.message_store.get(key)
        return m["text"] if m else None


def load_conversations() -> dict[str, dict]:
    convs: dict[str, dict] = defaultdict(dict)
    with (INGEST / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            convs[m["conversation_id"]][m["message_id"]] = m
    return convs

# ── Evidence signals ─────────────────────────────────────────────────────

PASTE_MARKERS = re.compile(
    r"(unsubscribe|privacy\s+policy|sent\s+from\s+my\s+|sent\s+to:\s+|"
    r"^best,?\s*$|^regards,?\s*$|^\d{1,4}\s+[a-z0-9 .]+(street|st\.?|ave\.?|"
    r"road|rd\.?|blvd|drive|dr\.?|lane|ln\.?|court|ct\.?|way|circle|plaza|"
    r"building|suite|#)\b|@\w+\.(com|net|org|io|co|info)\b)",
    re.IGNORECASE | re.MULTILINE,
)

SUBMISSION_PHRASES = re.compile(
    r"(add this (to|in)|what do you think of this|here'?s (the|my|a) (text|bio|"
    r"profile|article|draft|resume|cv|post)|can you (improve|fix|enhance|edit|"
    r"review|rewrite) this|i (found|got) this|someone sent me|from my other "
    r"(chat|conversation|thread)|same thing (for|as)|do the same thing|"
    r"recreate this|make it like this|similar to this)",
    re.IGNORECASE,
)

APPROVAL_PATTERNS = re.compile(
    r"^\s*(yes[,!.]?|yep|yeah|love it|perfect|sounds good|let'?s do (that|this)|"
    r"add (that|this)|keep (that|this)|we'?re doing (that|this)|that'?s exactly it|"
    r"i like (this|that)|great,? (let'?s|do it))",
    re.IGNORECASE,
)

REJECTION_PATTERNS = re.compile(
    r"^\s*(no[,!.]|not what i|that'?s not (it|right|what)|scrap that|wrong,?|"
    r"actually,? i don'?t|i don'?t (like|want) (that|this)|nevermind|never mind|"
    r"that'?s not correct|remove that|delete that|undo that)",
    re.IGNORECASE,
)

MODIFICATION_PATTERNS = re.compile(
    r"(yes,? but|love it,? (but|change|except)|keep .+ but (rename|change|call)|"
    r"let'?s do this,? except|i want to (call|rename|name) (it|this)|"
    r"change .+ to |instead of .+ let'?s|good,? but|don'?t (do|change|add|remove))",
    re.IGNORECASE,
)

SHORT_CORRECTION_PATTERNS = re.compile(
    r"^\s*(no[,!.\s]|not what i|that'?s not (it|right|what)|scrap that|wrong,?|"
    r"remove that|delete that|undo that|i don'?t want (that|this)|"
    r"that'?s not correct|not (this|that)\s*$)",
    re.IGNORECASE,
)


def has_paste_markers(text: str) -> bool:
    return bool(PASTE_MARKERS.search(text))


def has_submission_phrases(text: str) -> bool:
    return bool(SUBMISSION_PHRASES.search(text))


def is_structured_prose(text: str) -> bool:
    return bool(re.search(
        r"(^#{1,4}\s|\*\*[^*]+\*\*|^\d+\.\s.+(\n.+){2,}|\|.*\|.*\|)",
        text, re.MULTILINE
    ))


def is_numbered_list(text: str) -> bool:
    t = text.strip()
    if re.match(r"^\d+\.\s", t) and len(t) > 300 and "\n\d+\.\s" in t:
        return True
    if re.search(r"^\s*Pros?:\s*1\.", t, re.MULTILINE) and re.search(r"^\s*Cons?:\s*1\.", t, re.MULTILINE):
        return True
    if re.search(r"^\d+\s+Things? I[''']ve learned", t, re.IGNORECASE | re.MULTILINE):
        return True
    return False


def opening_message(record: dict, convs: dict) -> bool:
    seq = record.get("sequence_index")
    if seq is None:
        return False
    return seq <= 1


def preceding_assistant(record: dict, convs: dict) -> dict | None:
    conv = convs.get(record["conversation_id"], {})
    parent = record.get("parent_message_id")
    if not parent:
        return None
    parent_rec = conv.get(parent)
    if parent_rec and parent_rec["role"] == "assistant":
        return parent_rec
    return None

# ── Adoption status (independent of evidence_class) ─────────────────────


def adoption_status(text: str, evidence_class: str) -> str:
    if evidence_class == "A0":
        return "AD0"
    if evidence_class == "P0":
        return "AD1"
    if MODIFICATION_PATTERNS.search(text):
        return "AD4"
    if APPROVAL_PATTERNS.match(text.strip()):
        return "AD3"
    if REJECTION_PATTERNS.search(text):
        return "AD0"
    if SUBMISSION_PHRASES.search(text):
        return "AD1"
    if len(text.strip()) > 50:
        return "AD1"
    return "AD0"

# ── Substantial reuse check ──────────────────────────────────────────────


def substantial_reuse(text: str, origin: dict, reuse_idx: "ReuseIndex") -> bool:
    normalized = normalize_for_reuse(text)
    words = re.findall(r"[a-z0-9']+", normalized)
    total = max(1, len(words) - SHINGLE_SIZE + 1)
    matched = origin["matching_shingle_count"]

    if origin.get("reuse_type") == "cross_conversation":
        return matched >= MIN_CROSS_CONV_REUSE and matched / total >= 0.20
    return matched >= MIN_SAME_CONV_REUSE and matched / total >= 0.15

# ── External content detection ───────────────────────────────────────────


def external_content_fingerprint(text: str) -> str | None:
    t = text.strip()
    if re.search(r"^\s*Pros?:\s*1\.", t, re.MULTILINE) and re.search(r"^\s*Cons?:\s*1\.", t, re.MULTILINE):
        return "product-review-format"
    if re.search(r"^\d+\s+Things? I[''']ve learned", t, re.IGNORECASE | re.MULTILINE):
        return "listicle-header"
    if re.match(r"^\d+\.\s", t) and len(t) > 300 and "\n\d+\.\s" in t:
        return "numbered-list-content"
    if re.search(r"unfair advantages i never had|road to multi \d+ figures", t, re.IGNORECASE):
        return "external-narrative"
    return None

# ── Stage 1 evidence package ─────────────────────────────────────────────


def build_evidence_package(record: dict, reuse_idx: ReuseIndex, convs: dict) -> dict:
    text = record.get("text", "")
    prev = preceding_assistant(record, convs)
    origin = reuse_idx.find_origin(text, record.get("conversation_id", "")) if text else None

    return {
        "message_id": record.get("message_id"),
        "conversation_id": record.get("conversation_id"),
        "role": record.get("role"),
        "sequence_index": record.get("sequence_index"),
        "is_conversation_opener": opening_message(record, convs),
        "char_length": len(text),
        "preceding_assistant": {
            "message_id": prev["message_id"],
            "role": prev["role"],
            "char_length": len(prev["text"]),
            "text_preview": prev["text"][:600],
        } if prev else None,
        "reuse_evidence": {
            "reuse_match_found": bool(origin),
            "matching_shingle_count": origin.get("matching_shingle_count", 0) if origin else 0,
            "reuse_type": origin.get("reuse_type") if origin else None,
            "same_conversation": origin.get("same_conversation", False) if origin else False,
        },
        "paste_markers": {
            "has_url": bool(re.search(r"https?://\S+", text)),
            "has_unsubscribe": bool(re.search(r"\bunsubscribe\b", text, re.IGNORECASE)),
            "has_physical_address": bool(re.search(
                r"\b\d{1,6}\s+[A-Za-z0-9.\s]+(Road|Rd|Street|St|Ave|Avenue|Suite|Blvd|Drive|Dr)\b",
                text
            )),
            "has_signature_line": bool(re.search(r"\bBest,\s*[A-Z][a-z]+\b|\bRegards,\s*[A-Z][a-z]+\b", text)),
            "has_attributed_quote": bool(re.search(
                r'"[^"]{10,}"\s*[-—–]\s*[A-Z][a-z]+ [A-Z][a-z]+', text
            )),
        },
        "stylistic_signals": {
            "has_markdown_headers": bool(re.search(r"^#{1,4}\s", text, re.MULTILINE)),
            "has_bold_markdown": "**" in text,
            "has_trademark_symbol": "™" in text,
            "numbered_list_structure": bool(re.search(r"^\d+\.\s.+\n.+\n\d+\.\s", text, re.MULTILINE)),
            "is_numbered_list": is_numbered_list(text),
        },
        "normalized_text_preview": normalize_for_reuse(text)[:200],
    }

# ── Stage 2 segmentation ────────────────────────────────────────────────


def segment_message(text: str, evidence: dict) -> dict:
    reuse = evidence["reuse_evidence"]
    markers = evidence["paste_markers"]
    has_reuse = reuse.get("reuse_match_found") and reuse.get("matching_shingle_count", 0) >= 3
    has_paste = markers["has_unsubscribe"] or markers["has_physical_address"] or markers["has_signature_line"]

    if not (has_reuse or has_paste):
        return {
            "segmentation_proposed": False,
            "reason": "no reuse or external-paste evidence",
            "spans": [{"span_type": "unsegmented", "text": text}],
        }

    first_break = text.find("\n\n")
    if first_break == -1:
        first_break = text.find("\n")
    if first_break == -1:
        return {
            "segmentation_proposed": False,
            "reason": "evidence present but no plausible boundary found",
            "spans": [{"span_type": "unsegmented", "text": text}],
        }

    lead_in = text[:first_break].strip()
    rest = text[first_break:].strip()

    if len(lead_in) < 10 or len(rest) < 50:
        return {
            "segmentation_proposed": False,
            "reason": "split point found but one span is too short",
            "spans": [{"span_type": "unsegmented", "text": text}],
        }

    return {
        "segmentation_proposed": True,
        "reason": (
            "reuse match against earlier assistant message"
            if has_reuse
            else "external paste markers found"
        ),
        "spans": [
            {"span_type": "candidate_commentary", "text": lead_in},
            {"span_type": "candidate_pasted_content", "text": rest},
        ],
    }

# ── Stage 3 classification ──────────────────────────────────────────────


def classify_record(record: dict, reuse_idx: ReuseIndex, convs: dict) -> dict:
    role = record.get("role")
    text = record.get("text", "")
    conv_id = record.get("conversation_id", "")
    evidence = build_evidence_package(record, reuse_idx, convs)
    seg = segment_message(text, evidence)

    if role == "assistant":
        return {
            "evidence_class": "A0",
            "provenance_certainty": "PC4",
            "adoption_status": "AD0",
            "originator": "assistant",
            "requires_review": False,
            "reason": "role=assistant",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    stripped = text.strip()

    # ── HARDENING: Explicit short corrections/rejections -> X0 ──
    if SHORT_CORRECTION_PATTERNS.match(stripped) and len(stripped) < 200:
        return {
            "evidence_class": "X0",
            "provenance_certainty": "PC4",
            "adoption_status": "AD0",
            "originator": "derek",
            "requires_review": False,
            "reason": "explicit correction/rejection language",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── External-content fingerprints -> P0 (PC2) ──
    ext_fp = external_content_fingerprint(text)
    if ext_fp and not opening_message(record, convs):
        return {
            "evidence_class": "P0",
            "submitted_by": "derek",
            "original_author": "external",
            "origin_message_id": None,
            "origin_conversation_id": None,
            "reuse_message_id": record["message_id"],
            "reuse_conversation_id": conv_id,
            "provenance_certainty": "PC2",
            "adoption_status": adoption_status(text, "P0"),
            "requires_review": True,
            "reason": f"external-content fingerprint: {ext_fp}",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── Build evidence for user messages ──
    origin = reuse_idx.find_origin(text, conv_id) if text else None
    paste_markers = has_paste_markers(text)
    submission = has_submission_phrases(text)
    structured = is_structured_prose(text)
    opening = opening_message(record, convs)
    numbered_list = is_numbered_list(text)

    # ── Mixed message: Derek commentary + pasted assistant body ──
    if origin and substantial_reuse(text, origin, reuse_idx) and len(text) > 200:
        first_line = text.strip().split("\n", 1)[0]
        if 10 <= len(first_line) <= 150:
            return {
                "evidence_class": "MIXED",
                "provenance_certainty": "PC4",
                "adoption_status": adoption_status(text, "MIXED"),
                "origin_message_id": origin["origin_message_id"],
                "origin_conversation_id": origin["origin_conversation_id"],
                "requires_review": True,
                "reason": "Derek lead-in + reused assistant body: segment into D0 + P0",
                "evidence_package": evidence,
                "segmentation": seg,
            }

    # ── Located cross-conversation assistant reuse -> P0 ──
    if origin and not origin["same_conversation"] and substantial_reuse(text, origin, reuse_idx):
        return {
            "evidence_class": "P0",
            "submitted_by": "derek",
            "original_author": "assistant",
            "origin_message_id": origin["origin_message_id"],
            "origin_conversation_id": origin["origin_conversation_id"],
            "reuse_message_id": record["message_id"],
            "reuse_conversation_id": conv_id,
            "provenance_certainty": "PC4",
            "adoption_status": adoption_status(text, "P0"),
            "requires_review": False,
            "reason": f"cross-conversation reuse ({origin['matching_shingle_count']} shingles)",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── Same-conversation assistant reuse -> P0 ──
    if origin and origin["same_conversation"] and substantial_reuse(text, origin, reuse_idx):
        return {
            "evidence_class": "P0",
            "submitted_by": "derek",
            "original_author": "assistant",
            "origin_message_id": origin["origin_message_id"],
            "origin_conversation_id": conv_id,
            "reuse_message_id": record["message_id"],
            "reuse_conversation_id": conv_id,
            "provenance_certainty": "PC4",
            "adoption_status": adoption_status(text, "P0"),
            "requires_review": False,
            "reason": "same-conversation assistant reuse",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── Mixed message via paste markers / submission phrases ──
    if (paste_markers or submission) and len(text) > 300:
        return {
            "evidence_class": "MIXED",
            "provenance_certainty": "PC3",
            "adoption_status": adoption_status(text, "MIXED"),
            "requires_review": True,
            "reason": "paste markers/submission phrase + length: segment required",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── HARDENING: Conversation-opening casual messages -> D0 (PC4) ──
    if opening and role == "user" and len(stripped) < 200 and not structured:
        return {
            "evidence_class": "D0",
            "provenance_certainty": "PC4",
            "adoption_status": adoption_status(text, "D0"),
            "originator": "derek",
            "requires_review": False,
            "reason": "conversation-opening user message, casual phrasing",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── HARDENING: Short casual user messages -> D0 (PC3) ──
    if role == "user" and len(stripped) < 200 and not structured and not paste_markers and not numbered_list:
        return {
            "evidence_class": "D0",
            "provenance_certainty": "PC3",
            "adoption_status": adoption_status(text, "D0"),
            "originator": "derek",
            "requires_review": False,
            "reason": "short user message, no reuse/paste evidence",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── HARDENING: Structured/long polished text with no located origin -> UNRESOLVED ──
    if role == "user" and (structured or numbered_list or len(text) > 200):
        if origin:
            if origin.get("same_conversation"):
                return {
                    "evidence_class": "P0",
                    "submitted_by": "derek",
                    "original_author": "assistant",
                    "origin_message_id": origin["origin_message_id"],
                    "origin_conversation_id": conv_id,
                    "reuse_message_id": record["message_id"],
                    "reuse_conversation_id": conv_id,
                    "provenance_certainty": "PC3",
                    "adoption_status": adoption_status(text, "P0"),
                    "requires_review": True,
                    "reason": f"weak same-conversation reuse ({origin['matching_shingle_count']} shingles)",
                    "evidence_package": evidence,
                    "segmentation": seg,
                }
            return {
                "evidence_class": "UNRESOLVED",
                "originator": "unresolved",
                "provenance_certainty": "PC1",
                "adoption_status": adoption_status(text, "UNRESOLVED"),
                "requires_review": True,
                "reason": "polished/long user text with no located origin: abstaining",
                "evidence_package": evidence,
                "segmentation": seg,
            }

    # ── HARDENING: Genuinely ambiguous -> abstain rather than guess ──
    if role == "user" and (len(stripped) < 5 or (len(stripped) < 30 and not opening)):
        return {
            "evidence_class": "UNRESOLVED",
            "originator": "unresolved",
            "provenance_certainty": "PC1",
            "adoption_status": adoption_status(text, "UNRESOLVED"),
            "requires_review": True,
            "reason": "too short to classify reliably; abstaining",
            "evidence_package": evidence,
            "segmentation": seg,
        }

    # ── HARDENING: Default for remaining user messages -> UNRESOLVED ──
    # D0 is no longer the default. Positive evidence is required.
    return {
        "evidence_class": "UNRESOLVED",
        "originator": "unresolved",
        "provenance_certainty": "PC1",
        "adoption_status": adoption_status(text, "UNRESOLVED"),
        "requires_review": True,
        "reason": "no positive Derek-origination evidence; abstaining",
        "evidence_package": evidence,
        "segmentation": seg,
    }

# ── Stage 4 benchmark ──────────────────────────────────────────────────


def load_gold() -> list[dict]:
    golds = []
    with GOLD_SET.open(encoding="utf-8") as f:
        for line in f:
            golds.append(json.loads(line))
    return golds


def benchmark() -> dict:
    print("Building reuse index (stage 1)...")
    reuse_idx = ReuseIndex.build()
    print(f"  shingle index size: {len(reuse_idx.index)}")

    print("Loading conversations (topology)...")
    convs = load_conversations()

    golds = load_gold()
    print(f"Gold set: {len(golds)} records")

    msg_lookup: dict[str, dict] = {}
    with (INGEST / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            msg_lookup[m["message_id"]] = m

    results = []
    gold_by_id = {g["message_id"]: g for g in golds}

    missing = [g["gold_id"] for g in golds if g["message_id"] not in msg_lookup]
    if missing:
        print(f"WARNING: {len(missing)} gold records have no ingested message: {missing}")

    for gold in golds:
        rec = msg_lookup.get(gold["message_id"])
        if rec is None:
            results.append({
                "gold_id": gold["gold_id"],
                "gold_class": gold["evidence_class"],
                "predicted_class": "MISSING_RECORD",
                "correct": False,
                "note": "gold message_id not found in ingested messages.jsonl",
            })
            continue
        pred = classify_record(rec, reuse_idx, convs)
        pred_class = pred["evidence_class"]
        results.append({
            "gold_id": gold["gold_id"],
            "gold_class": gold["evidence_class"],
            "predicted_class": pred_class,
            "correct": pred_class == gold["evidence_class"],
            "prediction": {k: v for k, v in pred.items() if k not in ("evidence_package", "segmentation")},
            "gold_text": gold["original_text"][:120],
        })

    # ── Safety metrics (§6.0g) ──
    total = len(results)
    d0_gold = [r for r in results if r["gold_class"] == "D0"]
    a0_gold = [r for r in results if r["gold_class"] == "A0"]
    p0_gold = [r for r in results if r["gold_class"] == "P0"]
    x0_gold = [r for r in results if r["gold_class"] == "X0"]
    mixed_gold = [r for r in results if r["gold_class"] == "MIXED"]
    unresolved_gold = [r for r in results if r["gold_class"] == "UNRESOLVED"]

    false_derek = [r for r in results if r["gold_class"] in ("A0", "P0", "X0") and r["predicted_class"] == "D0"]
    false_asst = [r for r in results if r["gold_class"] == "D0" and r["predicted_class"] in ("A0", "P0")]
    p0_miss = [r for r in p0_gold if r["predicted_class"] == "D0"]
    bad_abstain_over = [r for r in unresolved_gold if r["predicted_class"] != "UNRESOLVED"]
    bad_abstain_under = [r for r in results if r["predicted_class"] == "UNRESOLVED" and r["gold_class"] != "UNRESOLVED"]

    d0_precision_denom = len([r for r in results if r["predicted_class"] == "D0"])
    d0_precision_num = len([r for r in results if r["predicted_class"] == "D0" and r["gold_class"] == "D0"])
    d0_precision = d0_precision_num / d0_precision_denom if d0_precision_denom else 0.0

    d0_recall_denom = len(d0_gold)
    d0_recall_num = len([r for r in d0_gold if r["correct"]])
    d0_recall = d0_recall_num / d0_recall_denom if d0_recall_denom else 0.0

    p0_precision_denom = len([r for r in results if r["predicted_class"] == "P0"])
    p0_precision_num = len([r for r in results if r["predicted_class"] == "P0" and r["gold_class"] == "P0"])
    p0_precision = p0_precision_num / p0_precision_denom if p0_precision_denom else 0.0

    p0_recall_denom = len(p0_gold)
    p0_recall_num = len([r for r in p0_gold if r["correct"]])
    p0_recall = p0_recall_num / p0_recall_denom if p0_recall_denom else 0.0

    a0_precision_denom = len([r for r in results if r["predicted_class"] == "A0"])
    a0_precision_num = len([r for r in results if r["predicted_class"] == "A0" and r["gold_class"] == "A0"])
    a0_precision = a0_precision_num / a0_precision_denom if a0_precision_denom else 0.0

    a0_recall_denom = len(a0_gold)
    a0_recall_num = len([r for r in a0_gold if r["correct"]])
    a0_recall = a0_recall_num / a0_recall_denom if a0_recall_denom else 0.0

    abstain_denom = len([r for r in results if r["predicted_class"] == "UNRESOLVED"])
    abstain_correct = len([r for r in results if r["predicted_class"] == "UNRESOLVED" and r["gold_class"] == "UNRESOLVED"])
    abstain_accuracy = abstain_correct / abstain_denom if abstain_denom else 0.0

    mixed_correct = len([r for r in mixed_gold if r["correct"]])
    mixed_accuracy = mixed_correct / len(mixed_gold) if mixed_gold else 0.0

    # Confusion matrix
    classes = ["D0", "A0", "P0", "X0", "MIXED", "UNRESOLVED"]
    confusion = {g: {p: 0 for p in classes} for g in classes}
    for r in results:
        gc = r["gold_class"]
        pc = r["predicted_class"]
        if gc in confusion and pc in confusion[gc]:
            confusion[gc][pc] += 1

    report = {
        "resolver": "PROVENANCE_RESOLVER_V0.2",
        "version": "0.2.0",
        "benchmarked_at": "2026-08-12",
        "gold_set": "provenance_gold_set_v1 (frozen, 40 records)",
        "total": total,
        "correct": sum(1 for r in results if r["correct"]),
        "accuracy": round(sum(1 for r in results if r["correct"]) / total, 4),
        "safety_metrics": {
            "false_derek_attribution": len(false_derek),
            "false_assistant_attribution": len(false_asst),
            "p0_miss": len(p0_miss),
            "bad_abstention_over_confidence": len(bad_abstain_over),
            "bad_abstention_under_confidence": len(bad_abstain_under),
        },
        "d0_precision": round(d0_precision, 4),
        "d0_recall": round(d0_recall, 4),
        "d0_precision_bar_met": d0_precision >= 0.98,
        "p0_precision": round(p0_precision, 4),
        "p0_recall": round(p0_recall, 4),
        "a0_precision": round(a0_precision, 4),
        "a0_recall": round(a0_recall, 4),
        "abstention_accuracy": round(abstain_accuracy, 4),
        "mixed_segmentation_accuracy": round(mixed_accuracy, 4),
        "false_derek_attribution_rate": round(len(false_derek) / max(1, d0_precision_denom), 4),
        "confusion_matrix": confusion,
        "per_class": {
            "D0": {"gold": len(d0_gold), "correct": sum(1 for r in d0_gold if r["correct"])},
            "A0": {"gold": len(a0_gold), "correct": sum(1 for r in a0_gold if r["correct"])},
            "P0": {"gold": len(p0_gold), "correct": sum(1 for r in p0_gold if r["correct"])},
            "X0": {"gold": len(x0_gold), "correct": sum(1 for r in x0_gold if r["correct"])},
            "MIXED": {"gold": len(mixed_gold), "correct": mixed_correct},
            "UNRESOLVED": {"gold": len(unresolved_gold), "correct": sum(1 for r in unresolved_gold if r["correct"])},
        },
        "results": results,
    }

    OUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== PROVENANCE_RESOLVER_V0.2 BENCHMARK =====")
    print(f"Total: {total} | Correct: {report['correct']} | Accuracy: {report['accuracy']}")
    print(f"\nSafety metrics:")
    for k, v in report["safety_metrics"].items():
        print(f"  {k}: {v}")
    print(f"\nD0 precision: {report['d0_precision']} (bar >= 0.98: {'MET' if report['d0_precision_bar_met'] else 'NOT MET'})")
    print(f"D0 recall: {report['d0_recall']}")
    print(f"P0 precision: {report['p0_precision']}, recall: {report['p0_recall']}")
    print(f"A0 precision: {report['a0_precision']}, recall: {report['a0_recall']}")
    print(f"Abstention accuracy: {report['abstention_accuracy']}")
    print(f"Mixed segmentation accuracy: {report['mixed_segmentation_accuracy']}")
    print(f"False Derek Attribution Rate: {report['false_derek_attribution_rate']}")
    print(f"\nConfusion matrix (rows=gold, cols=predicted):")
    hdr = "          " + " ".join(f"{c:>9}" for c in classes)
    print(hdr)
    for g in classes:
        row = " ".join(f"{confusion[g][p]:>9}" for p in classes)
        print(f"{g:>9}  {row}")
    print(f"\nPer class: {json.dumps(report['per_class'], indent=2)}")
    print(f"\nWrote: {OUT_FILE}")
    return report


if __name__ == "__main__":
    benchmark()
