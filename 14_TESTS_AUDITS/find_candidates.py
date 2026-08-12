"""
Candidate search for the 50-record Provenance Gold Set.

This does NOT classify anything - it only narrows 68,761 messages down to
a shortlist per target category so a human (Claude) can actually read and
verify genuine examples. Every candidate must still be manually read
against 00_RAW_ARCHIVE/ before being accepted into the Gold Set - this
script's job is recall (don't miss plausible examples), not precision.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

INGEST_DIR = Path(__file__).resolve().parent.parent / "01_INGEST"
OUT_DIR = Path(__file__).resolve().parent


def load_messages():
    messages = []
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            messages.append(json.loads(line))
    return messages


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

PASTE_INDICATOR_PATTERNS = re.compile(
    r"(add this to|what do you think of this|here'?s (the|my|a) (text|bio|profile|"
    r"article|draft|resume|cv)|can you (improve|fix|enhance|edit) this|"
    r"linkedin|resume|cv:|bio:)",
    re.IGNORECASE,
)

MODIFICATION_PATTERNS = re.compile(
    r"(yes,? but|love it,? (but|change|except)|keep .+ but (rename|change|call)|"
    r"let'?s do this,? except|i want to (call|rename|name) (it|this)|"
    r"change .+ to |instead of .+ let'?s|good,? but)",
    re.IGNORECASE,
)

WEAK_AMBIGUOUS_PATTERNS = re.compile(
    r"^\s*(ok\.?|okay\.?|sure\.?|maybe\.?|hmm\.?|i guess\.?|not sure\.?|"
    r"could be\.?|possibly\.?)\s*$",
    re.IGNORECASE,
)


def has_markdown_structure(text: str) -> bool:
    return bool(re.search(r"(^#{1,4}\s|\*\*[^*]+\*\*|^\d+\.\s.+\n.+\n\d+\.\s)", text, re.MULTILINE))


def main() -> None:
    messages = load_messages()
    by_conv_seq: dict[tuple[str, int], dict] = {}
    for m in messages:
        if m["branch"] == "main" and m["sequence_index"] is not None:
            by_conv_seq[(m["conversation_id"], m["sequence_index"])] = m

    candidates = {
        "d0_clear": [],
        "a0_clear": [],
        "p0_paste_indicator": [],
        "ad3_approval": [],
        "ad4_modification": [],
        "x0_rejection": [],
        "mixed_long_with_comment": [],
        "ambiguous_weak": [],
    }

    for m in messages:
        if m["branch"] != "main" or m["sequence_index"] is None:
            continue
        text = m["text"].strip()
        if not text:
            continue

        if m["role"] == "user":
            if APPROVAL_PATTERNS.match(text) and len(text) < 200:
                # Check there IS a preceding assistant proposal to approve
                prev = by_conv_seq.get((m["conversation_id"], m["sequence_index"] - 1))
                if prev and prev["role"] == "assistant" and len(prev["text"]) > 200:
                    candidates["ad3_approval"].append(m)

            if MODIFICATION_PATTERNS.search(text) and 20 < len(text) < 500:
                prev = by_conv_seq.get((m["conversation_id"], m["sequence_index"] - 1))
                if prev and prev["role"] == "assistant" and len(prev["text"]) > 200:
                    candidates["ad4_modification"].append(m)

            if REJECTION_PATTERNS.match(text) and len(text) < 300:
                prev = by_conv_seq.get((m["conversation_id"], m["sequence_index"] - 1))
                if prev and prev["role"] == "assistant":
                    candidates["x0_rejection"].append(m)

            if PASTE_INDICATOR_PATTERNS.search(text) and len(text) > 100:
                candidates["p0_paste_indicator"].append(m)

            if len(text) > 800 and has_markdown_structure(text):
                candidates["mixed_long_with_comment"].append(m)

            if WEAK_AMBIGUOUS_PATTERNS.match(text):
                prev = by_conv_seq.get((m["conversation_id"], m["sequence_index"] - 1))
                if prev and prev["role"] == "assistant" and len(prev["text"]) > 300:
                    candidates["ambiguous_weak"].append(m)

            if (
                20 < len(text) < 300
                and not has_markdown_structure(text)
                and "™" not in text
                and not text.lower().startswith(("should something", "what do you think"))
            ):
                candidates["d0_clear"].append(m)

        elif m["role"] == "assistant":
            if 300 < len(text) < 3000:
                candidates["a0_clear"].append(m)

    report = {k: len(v) for k, v in candidates.items()}
    print(json.dumps(report, indent=2))

    (OUT_DIR / "candidates_raw.json").write_text(
        json.dumps(
            {k: v[:150] for k, v in candidates.items()},  # cap per-bucket for file size
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("wrote candidates_raw.json (capped at 150 per bucket)")


if __name__ == "__main__":
    main()
