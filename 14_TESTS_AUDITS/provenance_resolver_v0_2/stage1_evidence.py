"""
PROVENANCE_RESOLVER_V0.2 - Stage 1: deterministic evidence.

Produces facts, not conclusions. Every field here is either a direct
lookup (timestamps, topology) or a mechanically-verifiable match
(shingle overlap against the assistant-message index, regex hits for
known paste markers). Nothing in this module makes a D0/A0/P0 decision -
that's Stage 3's job, and it only happens after Stage 1+2 have run.

v0.2 change from v0.1 (see MASTER_BRAIN_BUILD_SPEC.md S6.0a revision,
2026-08-12): adds `matched_span_mostly_quoted` - a v0.1 benchmark case
(gold_010) had a spurious ~53% shingle-coverage match purely because
Derek was quoting his own recurring article title back to the assistant
in two different conversations. A genuine reuse case (the LinkedIn
headline correction, gold_019 in v1.1) had nearly identical raw
coverage (~53%) but was unquoted prose - coverage percentage alone
cannot separate these two real cases; whether the match falls inside
quotation marks can.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

INGEST_DIR = Path(__file__).resolve().parents[2] / "01_INGEST"
SHINGLE_SIZE = 12

URL_PATTERN = re.compile(r"https?://\S+")
UNSUBSCRIBE_PATTERN = re.compile(r"\bunsubscribe\b", re.IGNORECASE)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,6}\s+[A-Za-z0-9.\s]+(Road|Rd|Street|St|Ave|Avenue|Suite|Blvd|Drive|Dr)\b",
)
SIGNATURE_PATTERN = re.compile(r"\bBest,\s*[A-Z][a-z]+\b|\bRegards,\s*[A-Z][a-z]+\b")
THIRD_PARTY_QUOTE_PATTERN = re.compile(
    r'"[^"]{10,}"\s*[-—]\s*[A-Z][a-z]+ [A-Z][a-z]+'  # "quote" - Some Person
)
QUOTE_PATTERN = re.compile(r'["“]([^"”]{5,})["”]')


def normalize_words(text: str) -> list[str]:
    text = re.sub(r"\*\*|__|##+|[-*]\s", " ", text)
    return re.findall(r"[a-z0-9']+", text.lower())


def shingles(words: list[str], size: int = SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


class CorpusIndex:
    """Loaded once, reused across many evidence-package builds."""

    def __init__(self):
        self.messages: dict[str, dict] = {}
        self.by_conv: dict[str, list[dict]] = {}
        self.assistant_shingle_index: dict[str, tuple[str, str]] = {}
        self._load()

    def _load(self):
        with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
            for line in f:
                m = json.loads(line)
                self.messages[m["message_id"]] = m
                self.by_conv.setdefault(m["conversation_id"], []).append(m)

        for m in self.messages.values():
            if m["role"] != "assistant" or len(m["text"]) < 100:
                continue
            words = normalize_words(m["text"])
            for sh in shingles(words):
                if sh not in self.assistant_shingle_index:
                    self.assistant_shingle_index[sh] = (
                        m["message_id"],
                        m["conversation_id"],
                    )

    def preceding_message(self, message_id: str) -> dict | None:
        m = self.messages[message_id]
        if m["sequence_index"] is None:
            return None
        candidates = [
            x
            for x in self.by_conv[m["conversation_id"]]
            if x["branch"] == "main" and x["sequence_index"] == m["sequence_index"] - 1
        ]
        return candidates[0] if candidates else None

    def reuse_evidence(self, text: str) -> dict:
        words = normalize_words(text)
        matches: dict[tuple[str, str], int] = {}
        matching_shingle_texts: dict[tuple[str, str], list[str]] = {}
        for sh in shingles(words):
            origin = self.assistant_shingle_index.get(sh)
            if origin:
                matches[origin] = matches.get(origin, 0) + 1
                matching_shingle_texts.setdefault(origin, []).append(sh)
        if not matches:
            return {"reuse_match_found": False}
        best_origin, count = max(matches.items(), key=lambda kv: kv[1])

        # v0.2: is the matched span confined to a quoted title/label in THIS
        # message? (S6.0a revision - a quoted match is weak/referential
        # evidence, not proof of reuse; a Derek-verified real case,
        # gold_010, had ~53% shingle coverage purely because he was
        # quoting his own recurring article title back to the assistant.)
        quoted_shingles = set()
        for quoted_span in QUOTE_PATTERN.findall(text):
            quoted_shingles.update(shingles(normalize_words(quoted_span)))
        best_match_shingles = set(matching_shingle_texts[best_origin])
        matched_in_quotes = (
            len(best_match_shingles & quoted_shingles) / len(best_match_shingles)
            if best_match_shingles
            else 0.0
        )

        return {
            "matched_span_mostly_quoted": matched_in_quotes >= 0.7,
            "reuse_match_found": True,
            "matching_shingle_count": count,
            "candidate_origin_message_id": best_origin[0],
            "candidate_origin_conversation_id": best_origin[1],
        }


def build_evidence(index: CorpusIndex, message_id: str) -> dict:
    m = index.messages[message_id]
    text = m["text"]

    prev = index.preceding_message(message_id)
    reuse = index.reuse_evidence(text) if m["role"] == "user" else {"reuse_match_found": False}

    evidence = {
        "message_id": message_id,
        "conversation_id": m["conversation_id"],
        "role": m["role"],
        "sequence_index": m["sequence_index"],
        "is_conversation_opener": m["sequence_index"] in (0, 1),
        "char_length": len(text),
        "preceding_message": (
            {
                "message_id": prev["message_id"],
                "role": prev["role"],
                "char_length": len(prev["text"]),
                "text_preview": prev["text"][:600],
            }
            if prev
            else None
        ),
        "reuse_evidence": reuse,
        "paste_markers": {
            "has_url": bool(URL_PATTERN.search(text)),
            "has_unsubscribe": bool(UNSUBSCRIBE_PATTERN.search(text)),
            "has_physical_address": bool(ADDRESS_PATTERN.search(text)),
            "has_signature_line": bool(SIGNATURE_PATTERN.search(text)),
            "has_attributed_quote": bool(THIRD_PARTY_QUOTE_PATTERN.search(text)),
        },
        "stylistic_signals": {
            "has_markdown_headers": bool(re.search(r"^#{1,4}\s", text, re.MULTILINE)),
            "has_bold_markdown": "**" in text,
            "has_trademark_symbol": "™" in text,
            "numbered_list_structure": bool(
                re.search(r"^\d+\.\s.+\n.+\n\d+\.\s", text, re.MULTILINE)
            ),
        },
    }
    return evidence


def main():
    import sys

    gold_path = (
        Path(__file__).resolve().parents[1] / "provenance_gold_set_v1.jsonl"
    )
    message_ids = []
    with gold_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            message_ids.append(rec["message_id"])

    print(f"loading corpus index...", file=sys.stderr)
    index = CorpusIndex()
    print(f"assistant shingle index: {len(index.assistant_shingle_index)}", file=sys.stderr)

    packages = [build_evidence(index, mid) for mid in message_ids]

    out_path = Path(__file__).resolve().parent / "stage1_evidence_packages.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for p in packages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"wrote {len(packages)} evidence packages to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
