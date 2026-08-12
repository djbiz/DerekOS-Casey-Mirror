from provenance_resolver_v0_3 import AttributionInput, resolve_authorship


def make(**changes):
    base = dict(record_id="r1", role="user", text="A polished first-person business framework")
    base.update(changes)
    return AttributionInput(**base)


def test_user_role_alone_is_not_authorship():
    result = resolve_authorship(make())
    assert result.submitted_by == "derek"
    assert result.authored_by == "unknown"
    assert result.evidence_class == "UNRESOLVED"
    assert result.derek_attribution_evidence == "DAE-0"


def test_style_first_person_and_repetition_do_not_establish_d0():
    result = resolve_authorship(make(text="I built this framework and it matches all my later ideas."))
    assert result.evidence_class == "UNRESOLVED"


def test_traceable_assistant_origin_separates_submission_authorship_adoption():
    result = resolve_authorship(make(
        text="Yes, use this framework",
        preceding_role="assistant",
        traceable_assistant_origin="assistant-message-1",
    ))
    assert result.submitted_by == "derek"
    assert result.authored_by == "assistant"
    assert result.adopted_by == "derek"
    assert result.adoption_status == "AD3"
    assert result.evidence_class == "P0"


def test_short_direct_control_act_is_only_d0_for_the_act():
    result = resolve_authorship(make(text="Yes", preceding_role="assistant"))
    assert result.evidence_class == "D0"
    assert result.derek_attribution_evidence == "DAE-3"
    assert result.adoption_status == "AD3"


def test_yes_but_is_material_adoption_not_simple_approval():
    result = resolve_authorship(make(text="Yes but add live events", preceding_role="assistant"))
    assert result.evidence_class == "D0"
    assert result.adoption_status == "AD4"


def test_short_text_without_preceding_assistant_stays_unresolved():
    assert resolve_authorship(make(text="Yes")).evidence_class == "UNRESOLVED"


def test_traceable_derek_origin_allows_d0():
    result = resolve_authorship(make(traceable_derek_origin="derek-message-0"))
    assert result.evidence_class == "D0"
    assert result.authored_by == "derek"
    assert result.derek_attribution_evidence == "DAE-4"


def test_prior_derek_facts_allow_d0_with_direct_evidence():
    result = resolve_authorship(make(derek_supplied_facts_before_formulation=("derek-fact-turn",)))
    assert result.evidence_class == "D0"
    assert result.derek_attribution_evidence == "DAE-3"


def test_mixed_content_wins_over_d0_signals():
    result = resolve_authorship(make(
        text="Yes\n\nHere is the pasted framework",
        preceding_role="assistant",
        mixed_content_evidence=True,
    ))
    assert result.evidence_class == "MIXED"
    assert result.authored_by == "mixed"


def test_assistant_role_is_traceable_a0():
    result = resolve_authorship(make(role="assistant"))
    assert result.evidence_class == "A0"
    assert result.authored_by == "assistant"


def test_external_origin_is_p0_not_d0():
    result = resolve_authorship(make(traceable_external_origin="external-source"))
    assert result.evidence_class == "P0"
    assert result.authored_by == "external"
