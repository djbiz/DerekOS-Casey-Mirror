"""PROVENANCE_RESOLVER_V0.3: positive-evidence authorship resolution.

`role=user` establishes submission only. User-submitted content defaults to
UNRESOLVED unless independent evidence positively establishes authorship.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal

EvidenceClass = Literal["D0", "A0", "P0", "MIXED", "UNRESOLVED"]
AuthoredBy = Literal["derek", "assistant", "external", "mixed", "unknown"]

SHORT_CONTROL_ACT = re.compile(
    r"^\s*(?:yes|yep|yeah|ok(?:ay)?|no|wrong|perfect|good|great|"
    r"let(?:'|’)s\s+(?:do|go)|i\s+(?:agree|approve)|"
    r"that(?:'|’)s\s+(?:not|right|correct)|i\s+(?:didn(?:'|’)t|don(?:'|’)t))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PositiveEvidence:
    code: Literal["DAE-0", "DAE-1", "DAE-2", "DAE-3", "DAE-4"]
    kind: str
    source_reference: str | None
    description: str


@dataclass(frozen=True)
class AttributionInput:
    record_id: str
    role: str
    text: str
    preceding_role: str | None = None
    traceable_assistant_origin: str | None = None
    traceable_external_origin: str | None = None
    traceable_derek_origin: str | None = None
    substantial_assistant_reuse: bool = False
    substantial_external_reuse: bool = False
    mixed_content_evidence: bool = False
    derek_supplied_facts_before_formulation: tuple[str, ...] = ()
    derek_correction_turns: tuple[str, ...] = ()


@dataclass(frozen=True)
class AttributionResult:
    record_id: str
    evidence_class: EvidenceClass
    submitted_by: str
    authored_by: AuthoredBy
    adopted_by: str | None
    adoption_status: str
    derek_attribution_evidence: str
    positive_evidence: tuple[PositiveEvidence, ...] = field(default_factory=tuple)
    requires_review: bool = True
    reason: str = ""

    def to_dict(self) -> dict:
        result = asdict(self)
        result["provenance_certainty"] = {
            "DAE-0": "PC0",
            "DAE-1": "PC1",
            "DAE-2": "PC2",
            "DAE-3": "PC3",
            "DAE-4": "PC4",
        }[self.derek_attribution_evidence]
        return result


def _submitted_by(role: str) -> str:
    return "derek" if role == "user" else role


def _adoption(text: str, preceding_role: str | None) -> tuple[str | None, str]:
    stripped = text.strip()
    if preceding_role == "assistant" and re.match(r"^(?:yes|good|great).{0,100}\bbut\b", stripped, re.I):
        return "derek", "AD4"
    if preceding_role == "assistant" and re.match(r"^(?:yes|yep|yeah|perfect|approved?)\b", stripped, re.I):
        return "derek", "AD3"
    return None, "AD0"


def resolve_authorship(record: AttributionInput) -> AttributionResult:
    """Resolve authorship with an UNRESOLVED fail-closed default."""
    submitted_by = _submitted_by(record.role)

    if record.role == "assistant":
        evidence = PositiveEvidence("DAE-4", "platform_author_record", record.record_id, "Assistant-authored source record.")
        return AttributionResult(
            record.record_id, "A0", submitted_by, "assistant", None, "AD0", "DAE-4",
            (evidence,), False, "Traceable assistant author record.",
        )

    if record.mixed_content_evidence:
        evidence = PositiveEvidence("DAE-3", "mixed_segment_evidence", None, "Independent evidence identifies multiple authorship segments.")
        return AttributionResult(
            record.record_id, "MIXED", submitted_by, "mixed", None, "AD0", "DAE-3",
            (evidence,), True, "Message requires claim-level segmentation.",
        )

    if record.traceable_assistant_origin or record.substantial_assistant_reuse:
        evidence = PositiveEvidence(
            "DAE-4" if record.traceable_assistant_origin else "DAE-3",
            "assistant_origin", record.traceable_assistant_origin,
            "Assistant origin or substantial assistant reuse is positively established.",
        )
        adopted_by, status = _adoption(record.text, record.preceding_role)
        return AttributionResult(
            record.record_id, "P0", submitted_by, "assistant", adopted_by, status,
            evidence.code, (evidence,), not bool(record.traceable_assistant_origin),
            "Submission is not authorship; assistant provenance controls.",
        )

    if record.traceable_external_origin or record.substantial_external_reuse:
        evidence = PositiveEvidence(
            "DAE-4" if record.traceable_external_origin else "DAE-3",
            "external_origin", record.traceable_external_origin,
            "External origin or substantial external reuse is positively established.",
        )
        return AttributionResult(
            record.record_id, "P0", submitted_by, "external", None, "AD0",
            evidence.code, (evidence,), not bool(record.traceable_external_origin),
            "Submission is not authorship; external provenance controls.",
        )

    positive: list[PositiveEvidence] = []
    if record.traceable_derek_origin:
        positive.append(PositiveEvidence("DAE-4", "traceable_derek_origin", record.traceable_derek_origin, "Earlier Derek-authored version is traceable."))
    if record.derek_supplied_facts_before_formulation:
        positive.append(PositiveEvidence("DAE-3", "prior_derek_facts", record.derek_supplied_facts_before_formulation[0], "Derek supplied the underlying facts before formulation."))
    if record.derek_correction_turns:
        positive.append(PositiveEvidence("DAE-3", "derek_correction_sequence", record.derek_correction_turns[0], "Derek developed or corrected the proposition across turns."))

    # A brief conversational control act is authorship evidence for that act,
    # not evidence that Derek originated the preceding proposition.
    stripped = record.text.strip()
    if (
        record.role == "user"
        and record.preceding_role == "assistant"
        and len(stripped) <= 180
        and SHORT_CONTROL_ACT.match(stripped)
        and "\n\n" not in stripped
    ):
        positive.append(PositiveEvidence("DAE-3", "direct_control_act", record.record_id, "Brief direct response to an immediately preceding assistant turn."))

    strongest = max((int(item.code[-1]) for item in positive), default=0)
    if strongest >= 3:
        adopted_by, status = _adoption(record.text, record.preceding_role)
        return AttributionResult(
            record.record_id, "D0", submitted_by, "derek", adopted_by, status,
            f"DAE-{strongest}", tuple(positive), False,
            "Derek authorship is supported by positive, traceable evidence.",
        )

    return AttributionResult(
        record.record_id, "UNRESOLVED", submitted_by, "unknown", None, "AD0",
        "DAE-0", tuple(positive), True,
        "No positive authorship evidence; absence of a located origin is not authorship evidence.",
    )


def classify_adversarial_case(case: dict, preceding_role: str | None = None) -> AttributionResult:
    evidence = case.get("evidence", {})
    reuse = evidence.get("reuse", {}) or {}
    matched_fraction = float(reuse.get("matched_frac") or 0.0)
    origin_id = reuse.get("origin_message_id")
    substantial_reuse = bool(origin_id and matched_fraction >= 0.15)
    text = case.get("text_excerpt", "")
    external = evidence.get("external_fingerprint")
    mixed = bool(
        substantial_reuse
        and len(text) > 80
        and re.match(r"^.{1,160}(?:add this|use this|what can|can you|with this)", text, re.I | re.S)
    )
    return resolve_authorship(AttributionInput(
        record_id=case["adversarial_id"],
        role="user",
        text=text,
        preceding_role=preceding_role,
        traceable_assistant_origin=origin_id if substantial_reuse else None,
        traceable_external_origin=external,
        substantial_assistant_reuse=substantial_reuse,
        substantial_external_reuse=bool(external),
        mixed_content_evidence=mixed,
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundles", type=Path)
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    preceding_roles: dict[str, str | None] = {}
    if args.bundles:
        for bundle in sorted(args.bundles.glob("batch_*.jsonl")):
            for line in bundle.read_text(encoding="utf-8-sig").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                previous = row.get("context", {}).get("prev") or {}
                preceding_roles[row["adversarial_id"]] = previous.get("role")
    results = {
        case["adversarial_id"]: classify_adversarial_case(
            case, preceding_roles.get(case["adversarial_id"])
        ).to_dict()
        for case in cases
    }
    args.output.write_text(json.dumps({"resolver": "PROVENANCE_RESOLVER_V0.3", "count": len(results), "predictions": results}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
