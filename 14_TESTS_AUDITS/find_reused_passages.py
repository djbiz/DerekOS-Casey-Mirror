"""
Finds user-role messages that verbatim-reuse assistant-authored text from
elsewhere in the corpus - the mechanical half of the Business Character
Method discovery (search for a match; a human still verifies every hit).

Method: build a shingle (12-word rolling window) index of every assistant
message, keyed by shingle -> list of (message_id, conversation_id). For
every user message, shingle it the same way and look for any hit. A hit
means: this exact 12-word sequence appears in some assistant message,
somewhere in the corpus (any conversation). Report the best (longest
run of matching shingles) candidates.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

INGEST_DIR = Path(__file__).resolve().parent.parent / "01_INGEST"
OUT_DIR = Path(__file__).resolve().parent

SHINGLE_SIZE = 12


def normalize_words(text: str) -> list[str]:
    text = re.sub(r"\*\*|__|##+|[-*]\s", " ", text)
    words = re.findall(r"[a-z0-9']+", text.lower())
    return words


def shingles(words: list[str], size: int = SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


def main() -> None:
    messages = []
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            messages.append(json.loads(line))

    assistant_index: dict[str, tuple[str, str]] = {}
    for m in messages:
        if m["role"] != "assistant" or len(m["text"]) < 100:
            continue
        words = normalize_words(m["text"])
        for sh in shingles(words):
            # first-seen wins - earliest occurrence is what matters for origin tracing
            if sh not in assistant_index:
                assistant_index[sh] = (m["message_id"], m["conversation_id"])

    print(f"assistant shingle index size: {len(assistant_index)}")

    hits = []
    for m in messages:
        if m["role"] != "user" or len(m["text"]) < 150:
            continue
        words = normalize_words(m["text"])
        matched_origins: dict[tuple[str, str], int] = defaultdict(int)
        for sh in shingles(words):
            origin = assistant_index.get(sh)
            if origin:
                matched_origins[origin] += 1
        if matched_origins:
            best_origin, match_count = max(matched_origins.items(), key=lambda kv: kv[1])
            # Only care about substantial overlap, not a coincidental short phrase
            if match_count >= 5:
                hits.append(
                    {
                        "reuse_message_id": m["message_id"],
                        "reuse_conversation_id": m["conversation_id"],
                        "reuse_source_file": m["source_file"],
                        "reuse_conversation_title": m["conversation_title"],
                        "origin_message_id": best_origin[0],
                        "origin_conversation_id": best_origin[1],
                        "same_conversation": m["conversation_id"] == best_origin[1],
                        "matching_shingle_count": match_count,
                        "reuse_text_preview": m["text"][:200],
                    }
                )

    hits.sort(key=lambda h: -h["matching_shingle_count"])
    print(f"total reuse hits: {len(hits)}")
    cross_conv = [h for h in hits if not h["same_conversation"]]
    print(f"cross-conversation reuse hits: {len(cross_conv)}")

    (OUT_DIR / "reused_passages_candidates.json").write_text(
        json.dumps(hits[:200], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("wrote reused_passages_candidates.json (top 200 by match strength)")


if __name__ == "__main__":
    main()
