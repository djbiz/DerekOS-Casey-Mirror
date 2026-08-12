"""Score sealed provenance predictions against the frozen blind labels."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = {row["adversarial_id"]: row for row in read_jsonl(args.cases)}
    labels = {row["adversarial_id"]: row for row in read_jsonl(args.labels)}
    prediction_doc = json.loads(args.predictions.read_text(encoding="utf-8-sig"))
    predictions = prediction_doc["predictions"]

    expected = set(cases)
    if set(labels) != expected or set(predictions) != expected:
        raise SystemExit("case, label, and prediction ID sets must match exactly")

    confusion: dict[str, Counter] = defaultdict(Counter)
    category_totals: Counter = Counter()
    category_false_derek: Counter = Counter()
    false_derek_ids: list[str] = []
    predicted_d0 = 0
    true_d0 = 0
    correct_d0 = 0
    exact = Counter()

    for case_id in sorted(expected):
        truth = labels[case_id]
        prediction = predictions[case_id]
        true_class = truth["evidence_class"]
        predicted_class = prediction["evidence_class"]
        confusion[true_class][predicted_class] += 1
        is_false_derek = predicted_class == "D0" and true_class != "D0"
        if is_false_derek:
            false_derek_ids.append(case_id)
        predicted_d0 += predicted_class == "D0"
        true_d0 += true_class == "D0"
        correct_d0 += predicted_class == "D0" and true_class == "D0"
        exact["evidence_class"] += predicted_class == true_class
        exact["adoption_status"] += prediction["adoption_status"] == truth["adoption_status"]
        exact["provenance_certainty"] += (
            prediction["provenance_certainty"] == truth["provenance_certainty"]
        )
        exact["requires_review"] += prediction["requires_review"] == truth["requires_review"]
        for category in cases[case_id]["categories"]:
            category_totals[category] += 1
            category_false_derek[category] += is_false_derek

    total = len(expected)
    result = {
        "benchmark": "PROVENANCE_ADVERSARIAL_SET_V1",
        "records": total,
        "primary_gate": {
            "name": "False Derek Attribution",
            "required": 0,
            "observed": len(false_derek_ids),
            "passed": not false_derek_ids,
            "case_ids": false_derek_ids,
        },
        "d0": {
            "predicted": predicted_d0,
            "adjudicated": true_d0,
            "correct": correct_d0,
            "precision": correct_d0 / predicted_d0 if predicted_d0 else None,
            "recall": correct_d0 / true_d0 if true_d0 else None,
        },
        "exact_accuracy": {key: value / total for key, value in sorted(exact.items())},
        "confusion_matrix": {
            truth: dict(sorted(counts.items())) for truth, counts in sorted(confusion.items())
        },
        "category_false_derek": {
            category: {
                "records": category_totals[category],
                "false_derek": category_false_derek[category],
            }
            for category in sorted(category_totals)
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["primary_gate"], indent=2))
    print(json.dumps(result["d0"], indent=2))
    return 0 if result["primary_gate"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
