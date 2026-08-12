"""
PROVENANCE_RESOLVER_V0.1 - Stage 2: candidate segmentation.

Coarse, deliberately conservative heuristic - flagged in the spec (S12.7)
and by the Board as likely "one of the hardest parts of the entire
system." This stage does NOT try to be precise; it proposes a split point
only when Stage 1 evidence gives a real reason to (reuse match found, or
strong external paste markers), and always leaves the full, unsplit text
available to Stage 3 as a fallback - segmentation is a hint, not a
binding decision.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

INGEST_DIR = Path(__file__).resolve().parents[2] / "01_INGEST"


def find_split_point(text: str) -> int | None:
    """Heuristic: Derek's own lead-in commentary, if present, is usually
    a short sentence or two before a blank-line break into a much longer
    pasted block. Look for the first double-newline after a short
    (<300 char) leading segment. Returns a character offset, or None if
    no plausible split point is found (message stays unsegmented)."""
    first_break = text.find("\n\n")
    if first_break == -1:
        first_break = text.find("\n")
    if first_break == -1:
        return None
    if 10 <= first_break <= 300:
        return first_break
    return None


def segment(message_text: str, evidence: dict) -> dict:
    reuse = evidence["reuse_evidence"]
    markers = evidence["paste_markers"]
    has_reuse_signal = reuse.get("reuse_match_found") and reuse.get("matching_shingle_count", 0) >= 5
    has_paste_signal = markers["has_unsubscribe"] or markers["has_physical_address"] or markers["has_signature_line"]

    if not (has_reuse_signal or has_paste_signal):
        return {
            "segmentation_proposed": False,
            "reason": "no reuse or external-paste evidence from Stage 1",
            "spans": [{"span_type": "unsegmented", "text": message_text}],
        }

    split = find_split_point(message_text)
    if split is None:
        return {
            "segmentation_proposed": False,
            "reason": "reuse/paste evidence present but no plausible lead-in/paste boundary found - message may be entirely pasted, or the boundary heuristic failed. Stage 3 should treat the whole message as a segmentation candidate.",
            "spans": [{"span_type": "unsegmented", "text": message_text}],
        }

    lead_in = message_text[:split].strip()
    rest = message_text[split:].strip()
    return {
        "segmentation_proposed": True,
        "reason": (
            "reuse match against an earlier assistant message"
            if has_reuse_signal
            else "external paste markers (unsubscribe/address/signature) found"
        ),
        "spans": [
            {"span_type": "candidate_commentary", "text": lead_in},
            {"span_type": "candidate_pasted_content", "text": rest},
        ],
    }


def main():
    resolver_dir = Path(__file__).resolve().parent
    evidence_path = resolver_dir / "stage1_evidence_packages.jsonl"
    messages = {}
    with (INGEST_DIR / "messages.jsonl").open(encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            messages[m["message_id"]] = m["text"]

    out = []
    with evidence_path.open(encoding="utf-8") as f:
        for line in f:
            ev = json.loads(line)
            text = messages[ev["message_id"]]
            seg = segment(text, ev)
            out.append({"message_id": ev["message_id"], **seg})

    out_path = resolver_dir / "stage2_segments.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")

    proposed = sum(1 for o in out if o["segmentation_proposed"])
    print(f"segmentation proposed for {proposed}/{len(out)} messages")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
