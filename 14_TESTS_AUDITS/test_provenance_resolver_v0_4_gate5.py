from provenance_resolver_v0_4_gate5 import (
    segment_spans,
    resolve_adoption,
    classify_gate5,
)


def _case(text, evidence=None, aid="r1"):
    return {
        "adversarial_id": aid,
        "text_excerpt": text,
        "evidence": evidence or {},
    }


# ---------------------------------------------------------------- Gate 4

def test_transcript_wrapper_is_mixed_with_segments():
    text = "Summarize the transcript of a YouTube video in 10 bullet points. The video is by X. The entire transcript is given below.\nactual transcript text here is long"
    spans = segment_spans(text, {})
    assert spans is not None
    assert spans[0].evidence_class == "D0" and spans[0].authored_by == "derek"
    assert spans[1].evidence_class == "P0" and spans[1].authored_by == "external"


def test_carrier_lead_does_not_make_body_d0():
    text = ("Can you create a follow-up email from the email below in Dan Ferrari style\n\n"
            "Subject: Welcome back\nHey LEADFIRSTNAME, welcome back to the world of endless "
            "possibilities! I hope this message finds you in good spirits and ready for a "
            "journey into the realm of financial growth and personal transformation. This is "
            "a long pasted email body that continues well beyond two hundred and fifty "
            "characters so the transformation rule threshold is satisfied and the imported "
            "material can be classified separately from the Derek lead instruction.")
    spans = segment_spans(text, {
        "reuse": {"origin_message_id": "o1", "matched_frac": 0.85},
    })
    assert spans is not None
    assert spans[0].evidence_class == "D0"          # Derek lead
    assert spans[1].evidence_class == "P0"          # imported body NOT D0
    res = classify_gate5(_case(text, {
        "reuse": {"origin_message_id": "o1", "matched_frac": 0.85},
    }))
    assert res.evidence_class == "MIXED"
    assert res.authored_by == "mixed"


def test_her_reply_label_wrapper():
    text = "Her reply.\n\nI write a lot about my feelings and reflect on things mostly. This is a long quoted message from another person that continues well beyond two hundred characters of content so the wrapper gets detected."
    spans = segment_spans(text, {})
    assert spans is not None
    assert spans[0].evidence_class == "D0"
    assert spans[1].evidence_class == "P0"


def test_v03_mixed_overfire_is_demoted_without_span_evidence():
    text = "Can we add this in when you're finished with the above\n\n# 🚀 DOMINANT REVENUE ENGINE - COMPLETE PRODUCTION SYSTEM\nI'll provide you with the complete production-ready system"
    res = classify_gate5(_case(text, {
        "reuse": {"origin_message_id": "o1", "matched_frac": 0.92},
    }))
    assert res.evidence_class in ("P0", "UNRESOLVED")  # demoted, not MIXED, not D0


# ---------------------------------------------------------------- Gate 5

def test_rejection_overrides_adoption():
    by, status, _ = resolve_adoption("No, don't do that", "assistant")
    assert status == "AD0"


def test_yes_but_is_ad4_modification():
    by, status, _ = resolve_adoption("Yes but add live events", "assistant")
    assert status == "AD4"


def test_transformation_directive_is_ad4_with_evidence():
    by, status, _ = resolve_adoption(
        "Recreate this with 760 characters", None, transformation_evidence=True)
    assert status == "AD4"


def test_explicit_add_this_is_ad3():
    by, status, _ = resolve_adoption("Add this to the system", "assistant")
    assert status == "AD3"


def test_continuation_is_not_adoption():
    by, status, _ = resolve_adoption("What if we added robotics too?", "assistant")
    assert status == "AD1"


def test_plain_discussion_is_ad0():
    by, status, _ = resolve_adoption("Can you explain that more", "assistant")
    assert status == "AD0"


def test_adoption_does_not_change_authorship():
    text = ("Can you create a follow-up email from the email below\n\n"
            "Subject: Welcome back\nbody body body body body body body body body body body body body")
    res = classify_gate5(_case(text, {
        "reuse": {"origin_message_id": "o1", "matched_frac": 0.85},
    }))
    assert res.authored_by in ("mixed", "assistant")
    assert res.adoption_status in ("AD0", "AD1", "AD2", "AD3", "AD4")


def test_frozen_d0_core_untouched_by_adoption():
    res = classify_gate5(_case("Yes", {"reuse": {}}), preceding_role="assistant")
    assert res.evidence_class == "D0"
