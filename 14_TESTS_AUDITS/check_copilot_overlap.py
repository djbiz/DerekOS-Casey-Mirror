"""
Cross-corpus overlap check for the newly-added Copilot CSV export against
the existing ChatGPT canonical corpus (01_INGEST/messages.jsonl).

Reuses the same 12-word shingle-matching method proven out in
provenance_resolver_v0_1/find_reused_passages.py - checks BOTH directions
(Copilot Human messages vs ChatGPT assistant messages, and Copilot AI
messages vs ChatGPT assistant messages, since either could reveal
Derek copy-pasting between platforms).
"""

import csv
import json
import re
from pathlib import Path

INGEST_DIR = Path(__file__).resolve().parent.parent / "01_INGEST"
COPILOT_CSV = (
    Path(__file__).resolve().parent.parent
    / "00_RAW_ARCHIVE"
    / "copilot"
    / "copilot-2026-08-12T11_59_49.315Z.csv"
)
SHINGLE_SIZE = 12


def normalize_words(text):
    text = re.sub(r"\*\*|__|##+|[-*]\s", " ", text)
    return re.findall(r"[a-z0-9']+", text.lower())


def shingles(words, size=SHINGLE_SIZE):
    for i in range(len(words) - size + 1):
        yield " ".join(words[i : i + size])


def main():
    print("building ChatGPT assistant shingle index...")
    chatgpt_index = {}
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m["role"] != "assistant" or len(m["text"]) < 100:
                continue
            words = normalize_words(m["text"])
            for sh in shingles(words):
                if sh not in chatgpt_index:
                    chatgpt_index[sh] = (m["message_id"], m["conversation_id"])
    print(f"ChatGPT assistant shingle index: {len(chatgpt_index)}")

    with COPILOT_CSV.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    hits = []
    for i, row in enumerate(rows):
        text = row["Message"]
        if len(text) < 100:
            continue
        words = normalize_words(text)
        matches = {}
        for sh in shingles(words):
            origin = chatgpt_index.get(sh)
            if origin:
                matches[origin] = matches.get(origin, 0) + 1
        if matches:
            best_origin, count = max(matches.items(), key=lambda kv: kv[1])
            if count >= 5:
                hits.append(
                    {
                        "copilot_row_index": i,
                        "conversation": row["Conversation"],
                        "author": row["Author"],
                        "time": row["Time"],
                        "matching_shingle_count": count,
                        "chatgpt_origin_message_id": best_origin[0],
                        "chatgpt_origin_conversation_id": best_origin[1],
                        "text_preview": text[:200],
                    }
                )

    print(f"total Copilot rows with >=100 chars checked: {sum(1 for r in rows if len(r['Message']) >= 100)}")
    print(f"cross-corpus matches found (ChatGPT <-> Copilot): {len(hits)}")

    out_path = Path(__file__).resolve().parent / "copilot_chatgpt_overlap.json"
    out_path.write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")

    # within-Copilot near-duplicate check (same file, different rows)
    print()
    print("checking within-Copilot near-duplicates...")
    copilot_index = {}
    dup_hits = []
    for i, row in enumerate(rows):
        text = row["Message"]
        if len(text) < 100:
            continue
        words = normalize_words(text)
        row_matches = {}
        for sh in shingles(words):
            origin = copilot_index.get(sh)
            if origin is not None and origin != i:
                row_matches[origin] = row_matches.get(origin, 0) + 1
            if sh not in copilot_index:
                copilot_index[sh] = i
        if row_matches:
            best_row, count = max(row_matches.items(), key=lambda kv: kv[1])
            if count >= 15:
                dup_hits.append((i, best_row, count))
    print(f"within-Copilot near-duplicate row pairs (>=15 matching shingles): {len(dup_hits)}")
    for a, b, c in dup_hits[:10]:
        print(f"  row {a} ~ row {b} ({c} matching shingles)")


if __name__ == "__main__":
    main()
