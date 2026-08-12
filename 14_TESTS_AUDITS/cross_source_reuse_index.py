"""
Cross-source reuse index — generalizes find_reused_passages.py (ChatGPT-only)
and check_copilot_overlap.py (ChatGPT<->Copilot one-off) into a single,
source-agnostic pass over the now-unified 01_INGEST/messages.jsonl.

Every assistant-role message from EVERY source (chatgpt, copilot-csv,
other-ai-export-fragments) is indexed as a candidate origin. Every
user-role message from EVERY source is checked against that combined
index. This is what "integrate Copilot into the same cross-source
origin/reuse index as ChatGPT" means concretely: one index, not one per
source, because provenance doesn't respect platform boundaries - already
proven by the 38 ChatGPT<->Copilot matches found during Copilot's
pre-import analysis.
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
    return re.findall(r"[a-z0-9']+", text.lower())


def shingles(words: list[str], size: int = SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


def main() -> None:
    messages = []
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            messages.append(json.loads(line))

    print(f"total messages across all sources: {len(messages)}")
    source_counts = defaultdict(int)
    for m in messages:
        source_counts[m.get("source_format", m.get("source_file", "unknown"))] += 1
    print("by source:", dict(source_counts))

    # Index every assistant-role message from every source.
    origin_index: dict[str, tuple[str, str, str]] = {}  # shingle -> (message_id, conversation_id, source_format)
    for m in messages:
        if m.get("role") != "assistant":
            continue
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        words = normalize_words(text)
        for sh in shingles(words):
            if sh not in origin_index:
                origin_index[sh] = (
                    m["message_id"],
                    m["conversation_id"],
                    m.get("source_format", m.get("source_file", "unknown")),
                )
    print(f"cross-source assistant shingle index size: {len(origin_index)}")

    hits = []
    for m in messages:
        if m.get("role") != "user":
            continue
        text = m.get("text") or ""
        if len(text) < 100:
            continue
        words = normalize_words(text)
        matches: dict[tuple, int] = defaultdict(int)
        for sh in shingles(words):
            origin = origin_index.get(sh)
            if origin:
                matches[origin] += 1
        if not matches:
            continue
        best_origin, count = max(matches.items(), key=lambda kv: kv[1])
        if count < 5:
            continue
        origin_msg_id, origin_conv_id, origin_source = best_origin
        this_source = m.get("source_format", m.get("source_file", "unknown"))
        hits.append(
            {
                "message_id": m["message_id"],
                "conversation_id": m["conversation_id"],
                "conversation_title": m.get("conversation_title"),
                "source": this_source,
                "matching_shingle_count": count,
                "origin_message_id": origin_msg_id,
                "origin_conversation_id": origin_conv_id,
                "origin_source": origin_source,
                "cross_source": origin_source != this_source,
                "same_conversation": origin_conv_id == m["conversation_id"],
                "text_preview": text[:200],
            }
        )

    hits.sort(key=lambda h: -h["matching_shingle_count"])
    cross_source_hits = [h for h in hits if h["cross_source"]]
    print(f"total reuse hits: {len(hits)}")
    print(f"cross-SOURCE reuse hits (different platform than origin): {len(cross_source_hits)}")

    by_source_pair = defaultdict(int)
    for h in cross_source_hits:
        by_source_pair[f"{h['origin_source']} -> {h['source']}"] += 1
    print("cross-source pairs:", dict(by_source_pair))

    out_path = OUT_DIR / "cross_source_reuse_index.json"
    out_path.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path} ({len(hits)} total hits)")


if __name__ == "__main__":
    main()
