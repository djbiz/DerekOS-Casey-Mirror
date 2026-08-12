"""PROVENANCE_RESOLVER_V0.4-GATE5 — parallel variant focused on Gates 4 + 5.

This is a complementary implementation to the committed `provenance_resolver_v0_4.py`
(which carries span provenance + P0 tiers). This variant shares the same frozen
v0.3 D0 safety boundary and adds:

  Gate 4 — deterministic span-level MIXED detection (transcript wrapper,
           "Her reply." label, transformation directive on reused text) and
           demotion of v0.3's over-broad mixed flag.
  Gate 5 — hardened AD0-AD4 adoption, independent of authorship, with the
           Board's rules (discussion != adoption, continuation != adoption,
           reuse != adoption, explicit adoption -> AD3, modification -> AD4,
           rejection overrides).

v0.3 D0/A0 outputs pass through unchanged; only P0/UNRESOLVED results may be
refined. Never creates a new D0 from a P0/UNRESOLVED/MIXED input.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from provenance_resolver_v0_3 import (
    AttributionInput,
    AttributionResult,
    PositiveEvidence,
    resolve_authorship as _v03_resolve,
)

# ------------------------------------------------------------------ Gate 4

TRANSCRIPT_WRAP = re.compile(r"the entire transcript is given below", re.I)
HER_REPLY_LABEL = re.compile(r"^\s*her reply\.?\s*$", re.I | re.MULTILINE)
# Direct transformation directives. Permission questions ("can I / can we")
# are carrier/discussion, NOT transformation ownership -> excluded.
TRANSFORM_LEAD = re.compile(
    r"^\s*(?:can\s+you\s+(?:create|rewrite|recreate|write|make|build|summarize)\b|"
    r"(?:please\s+)?(?:create|rewrite|recreate|write|make it|summarize)\b)",
    re.I,
)


@dataclass(frozen=True)
class Span:
    kind: str                      # "lead" | "body"
    evidence_class: Literal["D0", "P0", "UNRESOLVED"]
    authored_by: str
    reason: str
    start: int
    end: int


def segment_spans(text: str, evidence: dict | None = None) -> list[Span] | None:
    """Return spans when the message contains a Derek lead + imported body,
    else None (no span split justified)."""
    if not text:
        return None
    t = text.strip()
    evidence = evidence or {}
    reuse = evidence.get("reuse") or {}
    frac = float(reuse.get("matched_frac") or 0.0)
    origin = bool(reuse.get("origin_message_id"))
    first_line = t.split("\n", 1)[0] if "\n" in t else t
    flen = len(first_line.strip())

    # 1) transcript wrapper: Derek instruction + pasted transcript body
    m = TRANSCRIPT_WRAP.search(t)
    if m:
        return [
            Span("lead", "D0", "derek", "Derek instruction wraps a supplied transcript", 0, m.start()),
            Span("body", "P0", "external", "Pasted transcript is imported source material", m.start(), len(t)),
        ]

    # 2) "Her reply." label + quoted body
    if HER_REPLY_LABEL.match(t) and len(t) > 200:
        return [
            Span("lead", "D0", "derek", "Derek labels the quoted message", 0, len(first_line)),
            Span("body", "P0", "external", "Quoted third-party message", len(first_line), len(t)),
        ]

    # 3) transformation directive on substantially reused assistant text
    if origin and frac >= 0.8 and flen <= 160 and TRANSFORM_LEAD.match(first_line) and len(t) > 250:
        return [
            Span("lead", "D0", "derek", "Derek transformation instruction (AD4-eligible)", 0, len(first_line)),
            Span("body", "P0", "assistant", f"Substantially reused assistant text (frac {frac:.2f})", len(first_line), len(t)),
        ]

    return None


# ------------------------------------------------------------------ Gate 5

REJECT_PREFIX = re.compile(
    r"^\s*(?:no|nope|wrong|that(?:'|’)s\s+(?:not|wrong)|don(?:'|’)t\s+(?:do|use|add)|"
    r"never\s+(?:do|use|add)|remove\s+(?:that|it|the))\b", re.I,
)
EXPLICIT_ADOPT = re.compile(
    r"^\s*(?:yes|yep|yeah|perfect|approved?|exactly|that(?:'|’)s\s+it)\b|"
    r"\b(add this|use this|build this|put this in|integrate this|"
    r"make this part of|include this)\b", re.I,
)
CONTINUATION = re.compile(
    r"^\s*(?:what if|how about|can we also|can you also|and then|also,?)\b", re.I,
)
TRANSFORM_ADOPT = re.compile(
    r"^\s*(?:can\s+you\s+)?(?:create|rewrite|recreate|write|make it|build)\b|"
    r"\bbut\s+", re.I,
)


def resolve_adoption(text: str, preceding_role: str | None = None, *, transformation_evidence: bool = False) -> tuple[str | None, str, str]:
    """Resolve AD0-AD4 independently of authorship.

    Rules (Board directive):
      - rejection/correction overrides inferred adoption
      - discussion != adoption (AD0)
      - continuation != adoption (AD1)
      - reuse != adoption (AD0 for the body itself)
      - explicit 'add this/use this/build this' -> AD3 when scope is identifiable
      - modification ('yes but ...', transformation directive) -> AD4

    `transformation_evidence` is set when span analysis positively identified
    a Derek transformation directive wrapping imported material; it carries
    AD4 even when the immediate preceding role is unknown (cross-conversation
    reuse), because the modification is evidenced by the directive itself.
    """
    stripped = text.strip()
    if REJECT_PREFIX.match(stripped):
        return "derek", "AD0", "rejection/correction overrides inferred adoption"
    if preceding_role == "assistant" and len(stripped) <= 180 and re.match(r"^(?:yes|good|great).{0,100}\bbut\b", stripped, re.I):
        return "derek", "AD4", "yes-but: explicit modification of the preceding proposition"
    if (transformation_evidence or preceding_role == "assistant") and TRANSFORM_ADOPT.match(stripped) and len(stripped) <= 400:
        return "derek", "AD4", "transformation directive: Derek modifies/re-owns the material"
    if preceding_role == "assistant" and EXPLICIT_ADOPT.search(stripped):
        return "derek", "AD3", "explicit adoption with identifiable proposition scope"
    if preceding_role == "assistant" and CONTINUATION.match(stripped):
        return "derek", "AD1", "continuation/engagement is not adoption"
    return None, "AD0", "no adoption evidence (discussion != adoption)"


# ------------------------------------------------------------------ classify

def _v03_input(case: dict, mixed: bool, preceding_role: str | None) -> AttributionInput:
    """Build the v0.3 AttributionInput for a case (frozen core logic)."""
    evidence = case.get("evidence", {})
    reuse = evidence.get("reuse", {}) or {}
    matched_fraction = float(reuse.get("matched_frac") or 0.0)
    origin_id = reuse.get("origin_message_id")
    substantial_reuse = bool(origin_id and matched_fraction >= 0.15)
    external = evidence.get("external_fingerprint")
    return AttributionInput(
        record_id=case["adversarial_id"],
        role="user",
        text=case.get("text_excerpt", ""),
        preceding_role=preceding_role,
        traceable_assistant_origin=origin_id if substantial_reuse else None,
        traceable_external_origin=external,
        substantial_assistant_reuse=substantial_reuse,
        substantial_external_reuse=bool(external),
        mixed_content_evidence=mixed,
    )


def classify_gate5(case: dict, preceding_role: str | None = None) -> AttributionResult:
    """V0.4-GATE5 classification: frozen v0.3 core + span/adoption refinement."""
    evidence = case.get("evidence", {})
    reuse = evidence.get("reuse", {}) or {}
    matched_fraction = float(reuse.get("matched_frac") or 0.0)
    origin_id = reuse.get("origin_message_id")
    substantial_reuse = bool(origin_id and matched_fraction >= 0.15)
    text = case.get("text_excerpt", "")
    v03_mixed = bool(
        substantial_reuse
        and len(text) > 80
        and re.match(r"^.{1,160}(?:add this|use this|what can|can you|with this)", text, re.I | re.S)
    )
    base = _v03_resolve(_v03_input(case, mixed=v03_mixed, preceding_role=preceding_role))

    # Frozen: never touch D0 or A0.
    if base.evidence_class in ("D0", "A0"):
        return base

    spans = segment_spans(text, evidence)

    if spans:
        # Adoption is resolved on Derek's own lead span, not the pasted body.
        lead_text = text[spans[0].start:spans[0].end]
        is_transform = bool(TRANSFORM_ADOPT.match(lead_text.strip()))
        adopted_by, status, why = resolve_adoption(
            lead_text, preceding_role, transformation_evidence=is_transform)
        return AttributionResult(
            record_id=base.record_id,
            evidence_class="MIXED",
            submitted_by=base.submitted_by,
            authored_by="mixed",
            adopted_by=adopted_by,
            adoption_status=status,
            derek_attribution_evidence="DAE-3",
            positive_evidence=(
                PositiveEvidence("DAE-3", "span_segmentation", None,
                                 "Derek lead + imported body detected by span analysis."),
            ),
            requires_review=True,
            reason="MIXED: " + why,
        )

    # v0.3's mixed flag fired but no lead/body split: demote to the underlying
    # class (computed with mixed flag OFF). Removes v0.3 false-MIXED over-fire.
    if base.evidence_class == "MIXED":
        base = _v03_resolve(_v03_input(case, mixed=False, preceding_role=preceding_role))

    # No span split justified: keep the frozen base class, but harden adoption.
    if base.evidence_class in ("P0", "UNRESOLVED"):
        adopted_by, status, why = resolve_adoption(text, preceding_role)
        base = AttributionResult(
            record_id=base.record_id,
            evidence_class=base.evidence_class,
            submitted_by=base.submitted_by,
            authored_by=base.authored_by,
            adopted_by=adopted_by,
            adoption_status=status,
            derek_attribution_evidence=base.derek_attribution_evidence,
            positive_evidence=base.positive_evidence,
            requires_review=base.requires_review,
            reason=base.reason + f" | adoption: {why}",
        )
    return base


# ------------------------------------------------------------------ CLI

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundles", type=Path)
    args = parser.parse_args()

    cases = [json.loads(l) for l in args.cases.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    preceding_roles: dict[str, str | None] = {}
    if args.bundles:
        for bundle in sorted(args.bundles.glob("batch_*.jsonl")):
            for line in bundle.read_text(encoding="utf-8-sig").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                prev = (row.get("context") or {}).get("prev") or {}
                preceding_roles[row["adversarial_id"]] = prev.get("role")

    results = {
        case["adversarial_id"]: classify_gate5(case, preceding_roles.get(case["adversarial_id"])).to_dict()
        for case in cases
    }
    args.output.write_text(
        json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.4-GATE5", "count": len(results), "predictions": results}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
