import json
from pathlib import Path

from provenance_resolver_v0_5 import load_bundles, resolve_case


AUDITS = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def benchmark():
    cases = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    labels = {row["adversarial_id"]: row for row in read_jsonl(AUDITS / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    bundles = load_bundles(AUDITS / "adjudication_bundles")
    predictions = {case_id: resolve_case(case, bundles.get(case_id)) for case_id, case in cases.items()}
    return labels, predictions


def precision_recall(labels, predictions, target):
    predicted = {case_id for case_id, row in predictions.items() if row["evidence_class"] == target}
    actual = {case_id for case_id, row in labels.items() if row["evidence_class"] == target}
    correct = predicted & actual
    return len(correct) / len(predicted), len(correct) / len(actual)


def test_d0_set_is_identical_to_v04_and_remains_safe():
    labels, v5 = benchmark()
    v4 = json.loads((AUDITS / "PROVENANCE_RESOLVER_V0_4_predictions.json").read_text(encoding="utf-8"))["predictions"]
    v4_d0 = {case_id for case_id, row in v4.items() if row["evidence_class"] == "D0"}
    v5_d0 = {case_id for case_id, row in v5.items() if row["evidence_class"] == "D0"}
    assert v5_d0 == v4_d0
    assert all(labels[case_id]["evidence_class"] == "D0" for case_id in v5_d0)


def test_p0_precision_gate_passes_nonvacuously():
    labels, predictions = benchmark()
    precision, _ = precision_recall(labels, predictions, "P0")
    assert precision >= 0.95


def test_mixed_recall_passes_but_precision_limitation_is_preserved():
    labels, predictions = benchmark()
    precision, recall = precision_recall(labels, predictions, "MIXED")
    assert recall >= 0.85
    assert precision < 0.90  # honest blocked gate; do not hide label/structure tension


def test_ad3_ad4_accuracy_gate_passes():
    labels, predictions = benchmark()
    actual = [case_id for case_id, row in labels.items() if row["adoption_status"] in {"AD3", "AD4"}]
    correct = sum(predictions[case_id]["adoption_status"] == labels[case_id]["adoption_status"] for case_id in actual)
    assert correct / len(actual) >= 0.97
