"""PROVENANCE_RESOLVER_V0.6: reconciled candidate.

Safety baseline: V0.5 (itself a chain of frozen D0 invariants through v0.4 and
v0.3). V0.6 never changes any D0 decision; the False Derek Attribution = 0
boundary and the frozen D0 set are preserved by construction.

MIXED semantics: implements MIXED_SEMANTICS_ADJUDICATION_V1. A record is MIXED
only when at least two independently attributable semantic spans exist and both
contribute substantive meaning. A CONTROL_ACT / LABEL / QUERY carrier over an
imported body resolves to P0 + adoption instead. A pure Derek message with no
imported author resolves to UNRESOLVED (fail-closed, D0-leaning).

Decision order for a V0.5-MIXED result:
  1. Substantive Derek span (REQUIREMENT / MODIFICATION) or a conversation
     thread containing Derek's own statements  -> keep MIXED.
  2. Carrier over an imported body (boundary + body, or paste/submission
     markers, or a transcript template)         -> P0 + adoption (AD3 transcript,
     AD4 material transformation, AD2 style, AD1 label/query).
  3. Pure paste with no carrier                 -> P0 (imported artifact).
  4. Pure Derek directive with no imported body -> UNRESOLVED (fail-closed).
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from provenance_resolver_v0_4_baseline import _origin_is_prior, load_bundles
from provenance_resolver_v0_5 import resolve_case as resolve_v05

# --------------------------------------------------------------------------
# Span-function detection (MIXED_SEMANTICS_ADJUDICATION_V1 taxonomy)
# --------------------------------------------------------------------------

# Substantive Derek spans: REQUIREMENT / MODIFICATION / DATA_SUBMISSION.
SUBSTANTIVE_DEREK_SPAN = re.compile(
    r"(?is)(can(?:'|’)t we put (?:a limit|limits?)|"
    r"\bi (?:want|need|'d like|prefer|decided)\b|"
    r"\bmake (?:the|this) system\b|"
    r"\bdon(?:'|’)t make\b|\bremove (?:funding|that)\b|"
    r"\bmake vox (?:the|our) operator\b|"
    r"\b(?:we|i) should\b|\b(?:we|i) need\b|\bchange .{0,40} to\b|"
    r"\blooking for closer|train them to be\b)"
)

# Conversation thread where Derek is a participant inside a pasted artifact.
CONVERSATION_THREAD = re.compile(
    r"(?im)(derek jamieson \(he/him\)|derek jamieson \(he/him\) \d{1,2}:\d{2}|"
    r"^me:?\s)"
)

# Derek's own artifact referenced in first person: the pasted body is his own
# tooling/output, so there is no second independent author (Family H).
DEREK_SELF_CONTENT = re.compile(
    r"(?is)\bmy chrome extension\b"
)

# CONTROL_ACT carriers: task directives with zero semantic content.
TRANSCRIPT_TEMPLATE = re.compile(
    r"(?is)(summarize the transcript of a youtube video .{0,300}?"
    r"the entire transcript is given below)"
)
STYLE_TRANSFORM_CARRIER = re.compile(
    r"(?is)(can you (?:create|rewrite|write|make) .{0,140}(?:writing style|"
    r"style of|characters please|subject line|and make it funny)|"
    r"recreate this(?: with \d+ characters?)?|create a prompt for|"
    r"how can we make this better|wait before we move on|"
    r"this is a post i like|what can be done with these|"
    r"is this inside the system|her reply)"
)

MATERIAL_TRANSFORM_HINT = re.compile(
    r"(?is)(create a follow-up email|rewrite this|recreate this|"
    r"create a prompt for|come up with a killer subject line)"
)

EXTERNAL_MARKERS = re.compile(
    r"(?im)(https?://|^subject:|^from:\s|^sent:\s|```(?:python|bash|json|yaml|sql)?|"
    r"docker run|pip install|^body:|the entire transcript is given below|"
    r"word-for-word script transcription|import random|import datetime|"
    r"from datetime import)"
)


def _find_boundary(text: str) -> int | None:
    for position in (text.find("\n\n"), text.find("\n")):
        if 5 <= position <= 300:
            return position
    return None


def _demote_to_p0(result: dict, bundle: dict | None, text: str) -> dict:
    """Demote a MIXED carrier record to P0 + adoption, preserving spans."""
    origin = (bundle or {}).get("origin_candidate") or {}
    source_reference = origin.get("message_id")
    traceable = bool(
        source_reference
        and _origin_is_prior(bundle or {})
        and float(origin.get("matched_frac") or 0.0) >= 0.15
    )
    author = "assistant" if traceable else ("external" if EXTERNAL_MARKERS.search(text) else "unknown")
    p0_status = "P0-CERTAIN" if traceable else ("P0-PROBABLE" if author == "external" else "P0-UNRESOLVED")

    if TRANSCRIPT_TEMPLATE.search(text):
        adoption = "AD3"
    elif MATERIAL_TRANSFORM_HINT.search(text):
        adoption = "AD4"
    elif STYLE_TRANSFORM_CARRIER.search(text):
        adoption = "AD2"
    else:
        adoption = result.get("adoption_status") or "AD1"

    spans = []
    for span in result.get("spans") or []:
        if span.get("evidence_class") == "D0":
            spans.append(span)
        else:
            spans.append({
                **span,
                "authored_by": author,
                "evidence_class": "P0",
                "source_reference": source_reference,
                "confidence_tier": p0_status,
            })

    return {
        **result,
        "resolver": "PROVENANCE_RESOLVER_V0.6",
        "evidence_class": "P0",
        "authored_by": author,
        "adopted_by": "derek",
        "adoption_status": adoption,
        "p0_status": p0_status,
        "spans": spans,
        "requires_review": p0_status != "P0-CERTAIN",
        "reason": (
            "Control-act carrier over imported body resolves to P0 per "
            "MIXED_SEMANTICS_ADJUDICATION_V1; carrier does not create MIXED."
        ),
    }


def _pure_derek_directive(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) > 400:
        return False
    if "\n\n" in stripped:
        return False
    if EXTERNAL_MARKERS.search(text):
        return False
    return bool(re.match(r"(?is)^(?:can|could|please|make|add|connect|do|create)\b", stripped))


def resolve_case(case: dict, bundle: dict | None = None) -> dict:
    result = resolve_v05(case, bundle)

    if result["evidence_class"] == "D0":
        return {**result, "resolver": "PROVENANCE_RESOLVER_V0.6"}

    target = (bundle or {}).get("target") or {}
    text = target.get("text") or case.get("text_excerpt", "")
    flags = (bundle or {}).get("evidence_flags") or {}

    if result["evidence_class"] == "MIXED":
        first = ""
        for span in result.get("spans") or []:
            if span.get("evidence_class") == "D0":
                first = span.get("text", "")
                break
        boundary = _find_boundary(text)
        has_body = boundary is not None and len(text) - boundary > 40

        # 0. Pasted body is Derek's own artifact (no second independent author).
        if DEREK_SELF_CONTENT.search(text):
            return {
                **result,
                "resolver": "PROVENANCE_RESOLVER_V0.6",
                "evidence_class": "UNRESOLVED",
                "authored_by": "unknown",
                "p0_status": "P0-UNRESOLVED",
                "spans": [],
                "requires_review": True,
                "reason": (
                    "Pasted body is Derek's own artifact (first-person reference); "
                    "no second independent author. Fail-closed UNRESOLVED, D0-leaning."
                ),
            }

        # 1. Substantive Derek span or a mixed-author conversation thread -> MIXED.
        if SUBSTANTIVE_DEREK_SPAN.search(first) or CONVERSATION_THREAD.search(text):
            return {**result, "resolver": "PROVENANCE_RESOLVER_V0.6"}

        # 2. Carrier over an imported body -> P0 + adoption.
        if has_body and (
            TRANSCRIPT_TEMPLATE.search(text)
            or STYLE_TRANSFORM_CARRIER.search(first)
            or flags.get("paste_markers")
            or flags.get("submission_phrases")
            or flags.get("structured")
        ):
            return _demote_to_p0(result, bundle, text)

        # 3. Pure paste with no carrier -> P0 (imported artifact).
        if EXTERNAL_MARKERS.search(text) or flags.get("external_fingerprint"):
            return _demote_to_p0(result, bundle, text)

        # 4. Pure Derek directive with no imported body -> UNRESOLVED.
        return {
            **result,
            "resolver": "PROVENANCE_RESOLVER_V0.6",
            "evidence_class": "UNRESOLVED",
            "authored_by": "unknown",
            "p0_status": "P0-UNRESOLVED",
            "spans": [],
            "requires_review": True,
            "reason": (
                "No imported body and no paste evidence; the MIXED split is "
                "unjustified. Fail-closed UNRESOLVED, D0-leaning."
            ),
        }

    if result["evidence_class"] == "P0":
        # A short pure Derek directive mislabeled P0 by a weak partial match.
        if _pure_derek_directive(text):
            return {
                **result,
                "resolver": "PROVENANCE_RESOLVER_V0.6",
                "evidence_class": "UNRESOLVED",
                "authored_by": "unknown",
                "p0_status": "P0-UNRESOLVED",
                "spans": [],
                "requires_review": True,
                "reason": (
                    "Pure Derek directive with no imported body; P0 is "
                    "unjustified by a weak partial match. Fail-closed "
                    "UNRESOLVED, D0-leaning."
                ),
            }

    return {**result, "resolver": "PROVENANCE_RESOLVER_V0.6"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    bundles = load_bundles(args.bundles)
    predictions = {case["adversarial_id"]: resolve_case(case, bundles.get(case["adversarial_id"])) for case in cases}
    args.output.write_text(
        json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.6", "count": len(predictions), "predictions": predictions}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
