import json
from pathlib import Path

from provenance_resolver_v0_3 import classify_adversarial_case


AUDITS = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def preceding_roles():
    roles = {}
    for path in sorted((AUDITS / "adjudication_bundles").glob("batch_*.jsonl")):
        for row in read_jsonl(path):
            previous = row.get("context", {}).get("prev") or {}
            roles[row["adversarial_id"]] = previous.get("role")
    return roles


def test_frozen_safety_and_precision_gates():
    cases = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    labels = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    roles = preceding_roles()

    assert len(cases) == len(labels) == 230
    predictions = {
        case_id: classify_adversarial_case(case, roles.get(case_id))
        for case_id, case in cases.items()
    }
    predicted_d0 = [case_id for case_id, result in predictions.items() if result.evidence_class == "D0"]
    false_derek = [case_id for case_id in predicted_d0 if labels[case_id]["evidence_class"] != "D0"]
    correct_d0 = [case_id for case_id in predicted_d0 if labels[case_id]["evidence_class"] == "D0"]

    assert false_derek == []
    assert predicted_d0  # precision must not pass vacuously
    assert len(correct_d0) / len(predicted_d0) >= 0.98


def test_coverage_is_measured_without_weakening_safety():
    cases = read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")
    roles = preceding_roles()
    results = [classify_adversarial_case(case, roles.get(case["adversarial_id"])) for case in cases]
    unresolved = sum(result.evidence_class == "UNRESOLVED" for result in results)
    assert unresolved == 149
