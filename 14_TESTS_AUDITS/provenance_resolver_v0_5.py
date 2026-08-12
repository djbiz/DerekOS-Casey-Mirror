"""PROVENANCE_RESOLVER_V0.5: error-family refinements over frozen v0.4."""

from __future__ import annotations

import argparse
import difflib
import json
import re
from dataclasses import asdict
from pathlib import Path

from provenance_resolver_v0_4_baseline import (
    ProvenanceSpan,
    _origin_is_prior,
    load_bundles,
    resolve_case as resolve_v04,
)


TRACEABLE_CARRIER = re.compile(
    r"(?is)^\s*(?:"
    r"can you create .{0,180}\b(?:email|script|prompt)\b.{0,100}\bbelow\b|"
    r"create a (?:prompt|video hook)\b|"
    r"can(?:'|’)t we put (?:a limit|limits?)\b"
    r")"
)

CORRECTION_OF_SUPPLIED_TEXT = re.compile(
    r"(?is)^\s*(?:i (?:didn(?:'|’)t|did not) say|those are not my words|"
    r"you attributed .{0,80} to me incorrectly)\b"
)

MATERIAL_TRANSFORMATION = re.compile(
    r"(?is)^\s*(?:can you create .{0,180}\bfrom (?:the|this) .{0,40}\bbelow\b|"
    r"create a prompt for\b|recreate this with \d+ characters?\b)"
)


def _carrier_boundary(text: str) -> int | None:
    candidates = [position for position in (text.find("\n\n"), text.find("  "), text.find(":")) if position >= 5]
    return min(candidates) if candidates else None


def _alignment_spans(text: str, origin_text: str, source_reference: str) -> list[ProvenanceSpan]:
    """Locate the strongest contiguous reused token span with source offsets."""
    target_tokens = list(re.finditer(r"[A-Za-z0-9']+", text))
    origin_tokens = list(re.finditer(r"[A-Za-z0-9']+", origin_text))
    if not target_tokens or not origin_tokens:
        return []
    target_words = [match.group(0).lower() for match in target_tokens]
    origin_words = [match.group(0).lower() for match in origin_tokens]
    block = difflib.SequenceMatcher(None, target_words, origin_words, autojunk=False).find_longest_match()
    if block.size < 5 or block.size / len(target_words) < 0.15:
        return []
    start = target_tokens[block.a].start()
    end = target_tokens[block.a + block.size - 1].end()
    spans = []
    if start:
        spans.append(ProvenanceSpan(0, start, text[:start], "derek", "D0", None, "DAE-3"))
    spans.append(ProvenanceSpan(start, end, text[start:end], "assistant", "P0", source_reference, "P0-CERTAIN"))
    if end < len(text):
        spans.append(ProvenanceSpan(end, len(text), text[end:], "derek", "D0", None, "DAE-3"))
    return spans if len(spans) > 1 else []


def resolve_case(case: dict, bundle: dict | None = None) -> dict:
    result = resolve_v04(case, bundle)

    # Immutable safety invariant: all v0.4 D0 decisions pass through exactly.
    if result["evidence_class"] == "D0":
        return {**result, "resolver": "PROVENANCE_RESOLVER_V0.5"}

    target = (bundle or {}).get("target") or {}
    text = target.get("text") or case.get("text_excerpt", "")
    origin = (bundle or {}).get("origin_candidate") or {}
    match_fraction = float(origin.get("matched_frac") or 0.0)
    traceable_prior = bool(origin.get("message_id") and _origin_is_prior(bundle or {}) and match_fraction >= 0.15)

    # A correction is Derek's control act around supplied text, but v0.5 is not
    # authorized to expand D0. It therefore abstains instead of calling the
    # complete message P0.
    if CORRECTION_OF_SUPPLIED_TEXT.match(text):
        return {
            **result,
            "resolver": "PROVENANCE_RESOLVER_V0.5",
            "evidence_class": "UNRESOLVED",
            "authored_by": "unknown",
            "p0_status": "P0-UNRESOLVED",
            "spans": [],
            "requires_review": True,
            "reason": "Correction and quoted supplied text require review; whole-message P0 is unsafe.",
        }

    if traceable_prior and TRACEABLE_CARRIER.match(text):
        boundary = _carrier_boundary(text)
        spans = []
        if boundary and boundary <= 300 and len(text) - boundary > 30:
            spans = [
                ProvenanceSpan(0, boundary, text[:boundary], "derek", "D0", None, "DAE-3"),
                ProvenanceSpan(boundary, len(text), text[boundary:], "assistant", "P0", origin["message_id"], "P0-CERTAIN"),
            ]
        else:
            spans = _alignment_spans(text, origin.get("text", ""), origin["message_id"])
        if spans:
            adoption_status = "AD4" if MATERIAL_TRANSFORMATION.match(text) else result["adoption_status"]
            adopted_by = "derek" if adoption_status == "AD4" else result.get("adopted_by")
            return {
                **result,
                "resolver": "PROVENANCE_RESOLVER_V0.5",
                "evidence_class": "MIXED",
                "authored_by": "mixed",
                "adopted_by": adopted_by,
                "adoption_status": adoption_status,
                "p0_status": "P0-CERTAIN",
                "spans": [asdict(span) for span in spans],
                "requires_review": True,
                "reason": "Traceable imported body separated from a structurally bounded carrier instruction.",
            }

    if MATERIAL_TRANSFORMATION.match(text):
        return {
            **result,
            "resolver": "PROVENANCE_RESOLVER_V0.5",
            "adopted_by": "derek",
            "adoption_status": "AD4",
            "reason": result["reason"] + " Material transformation request establishes AD4.",
        }

    return {**result, "resolver": "PROVENANCE_RESOLVER_V0.5"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    bundles = load_bundles(args.bundles)
    predictions = {case["adversarial_id"]: resolve_case(case, bundles.get(case["adversarial_id"])) for case in cases}
    args.output.write_text(json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.5", "count": len(predictions), "predictions": predictions}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
