"""Unit tests for PROVENANCE_RESOLVER_V0.6's substantive-meaning MIXED gate."""

import json
from pathlib import Path

from provenance_resolver_v0_4_baseline import load_bundles
from provenance_resolver_v0_6 import (
    _pure_derek_directive,
    _demote_to_p0,
    SUBSTANTIVE_DEREK_SPAN,
    CONVERSATION_THREAD,
    TRANSCRIPT_TEMPLATE,
    STYLE_TRANSFORM_CARRIER,
    resolve_case,
)


AUDITS = Path(__file__).resolve().parent


def _bundles():
    return load_bundles(AUDITS / "adjudication_bundles")


def _case(aid: str) -> dict:
    with open(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl", encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row["adversarial_id"] == aid:
                return row
    raise KeyError(aid)


def test_real_genuine_mixed_kept():
    # adv_021989: substantive governance requirement + imported list.
    r = resolve_case(_case("adv_021989"), _bundles().get("adv_021989"))
    assert r["evidence_class"] == "MIXED"


def test_real_conversation_thread_mixed_kept():
    # adv_003597: Derek's own chat statements + Rob Walker's message.
    r = resolve_case(_case("adv_003597"), _bundles().get("adv_003597"))
    assert r["evidence_class"] == "MIXED"


def test_real_transcript_template_demoted_to_p0():
    # adv_000346: 'Summarize the transcript...' carrier -> P0 + AD3.
    r = resolve_case(_case("adv_000346"), _bundles().get("adv_000346"))
    assert r["evidence_class"] == "P0"
    assert r["adoption_status"] == "AD3"


def test_real_style_carrier_demoted_to_p0_ad4():
    # adv_001324: rewrite-in-style carrier -> P0 + AD4.
    r = resolve_case(_case("adv_001324"), _bundles().get("adv_001324"))
    assert r["evidence_class"] == "P0"
    assert r["adoption_status"] == "AD4"


def test_real_pure_derek_directive_unresolved():
    # adv_017999: pure Derek requirement, no imported body -> UNRESOLVED.
    r = resolve_case(_case("adv_017999"), _bundles().get("adv_017999"))
    assert r["evidence_class"] == "UNRESOLVED"


def test_real_label_quote_demoted_to_p0():
    # adv_014438: 'Her reply.' label + imported quote -> P0.
    r = resolve_case(_case("adv_014438"), _bundles().get("adv_014438"))
    assert r["evidence_class"] == "P0"


def test_pure_derek_directive_detection():
    assert _pure_derek_directive("Can you make the system self learning and connect the python codes")
    assert _pure_derek_directive("Please add this to the system")
    assert not _pure_derek_directive("Can you rewrite this\n\nHere is a long pasted email body" * 3)
    assert not _pure_derek_directive("Can you fix this https://example.com thing")


def test_substantive_derek_spans_detected():
    assert SUBSTANTIVE_DEREK_SPAN.search("Can't we put a limit on how much or a plan that allows the system flexibility.")
    assert SUBSTANTIVE_DEREK_SPAN.search("I want DerekOS controlling capital allocation")
    assert SUBSTANTIVE_DEREK_SPAN.search("make the system self learning")
    assert not SUBSTANTIVE_DEREK_SPAN.search("Can you create a follow-up email in a Dan Ferrari writing style")


def test_conversation_thread_detected():
    assert CONVERSATION_THREAD.search("Derek Jamieson (He/Him) 10:01 AM\nGreat I'm looking for closer and setters")
    assert not CONVERSATION_THREAD.search("This is a post I like to leave a thoughtful message https://link")


def test_transcript_template_detected():
    assert TRANSCRIPT_TEMPLATE.search(
        "Summarize the transcript of a YouTube video in 10 bullet points. "
        "The video is by Dan Koe and is titled Stop Trying. "
        "The entire transcript is given below."
    )


def test_style_carrier_detected():
    assert STYLE_TRANSFORM_CARRIER.search("Can you rewrite this Live Answer Script in a Kevin James writing style")
    assert STYLE_TRANSFORM_CARRIER.search("Recreate this with 760 characters")
    assert STYLE_TRANSFORM_CARRIER.search("create a prompt for DALE:")
    assert STYLE_TRANSFORM_CARRIER.search("Is this inside the system.")
    assert STYLE_TRANSFORM_CARRIER.search("Her reply.")


def test_demote_to_p0_assigns_adoption():
    result = {
        "evidence_class": "MIXED",
        "adoption_status": "AD0",
        "spans": [],
        "requires_review": True,
        "reason": "x",
    }
    bundle = {"origin_candidate": {"message_id": "m1", "matched_frac": 0.9}}
    demoted = _demote_to_p0(
        result,
        bundle,
        "Recreate this with 760 characters\n\nShifting consumer preferences demand adaptability.",
    )
    assert demoted["evidence_class"] == "P0"
    assert demoted["adoption_status"] == "AD4"


def test_resolve_case_pure_derek_directive_unresolved():
    result = resolve_case(
        {"adversarial_id": "adv_017999", "text_excerpt": "x"},
        {
            "target": {
                "text": "Can you make the system self learning and make sure this system can connect to other python codes and other python codes can connect to the system",
            },
            "context": {"prev": {"role": "assistant"}, "next": {"role": "assistant"}},
            "origin_candidate": {},
            "evidence_flags": {},
        },
    )
    assert result["evidence_class"] in {"UNRESOLVED", "P0"}
