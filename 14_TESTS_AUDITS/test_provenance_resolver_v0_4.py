import json
from pathlib import Path

from provenance_resolver_v0_4 import load_bundles, resolve_case


AUDITS = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def test_transcript_carrier_is_segmented_without_transferring_authorship():
    case = {"adversarial_id": "x", "text_excerpt": "Summarize the transcript.\nbody", "evidence": {}}
    bundle = {
        "target": {"text": "Summarize the transcript. The entire transcript is given below.\nexternal body with enough source content to segment safely"},
        "context": {"prev": {"role": "assistant"}},
    }
    result = resolve_case(case, bundle)
    assert result["evidence_class"] == "MIXED"
    assert [span["authored_by"] for span in result["spans"]] == ["derek", "external"]


def test_import_markers_without_traceable_origin_stay_unresolved():
    case = {"adversarial_id": "x", "text_excerpt": "From Codex: completed the implementation", "evidence": {}}
    bundle = {"target": {"text": case["text_excerpt"]}, "context": {}}
    result = resolve_case(case, bundle)
    assert result["evidence_class"] == "UNRESOLVED"
    assert result["p0_status"] == "P0-PROBABLE"


def test_frozen_d0_set_and_safety_remain_unchanged():
    cases = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    labels = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    v3 = json.loads((AUDITS / "PROVENANCE_RESOLVER_V0_3_predictions.json").read_text(encoding="utf-8"))["predictions"]
    bundles = load_bundles(AUDITS / "adjudication_bundles")
    v4 = {case_id: resolve_case(case, bundles.get(case_id)) for case_id, case in cases.items()}
    v3_d0 = {case_id for case_id, result in v3.items() if result["evidence_class"] == "D0"}
    v4_d0 = {case_id for case_id, result in v4.items() if result["evidence_class"] == "D0"}
    assert v4_d0 == v3_d0
    assert all(labels[case_id]["evidence_class"] == "D0" for case_id in v4_d0)


def test_span_segmentation_improves_without_claiming_gate_completion():
    cases = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    labels = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    bundles = load_bundles(AUDITS / "adjudication_bundles")
    predictions = {case_id: resolve_case(case, bundles.get(case_id)) for case_id, case in cases.items()}
    true_mixed = {case_id for case_id, row in labels.items() if row["evidence_class"] == "MIXED"}
    predicted_mixed = {case_id for case_id, row in predictions.items() if row["evidence_class"] == "MIXED"}
    assert len(true_mixed & predicted_mixed) / len(true_mixed) >= 0.70
    assert predicted_mixed  # non-vacuous
