"""Build the v0.5 curriculum from committed blind labels and v0.4 output."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def p0_fn_family(text):
    if re.search(r"(?im)^from (?:codex|claude|hermes|opencode|gemini)|^codeone:", text):
        return "explicit_agent_source_label"
    if re.search(r"(?im)^(?:ps [a-z]:|traceback|listed directory|created \d+_|docker ps|memory updated)", text):
        return "terminal_or_tool_artifact"
    if re.search(r"(?im)(1st degree connection|sent the following message|view .+ profile|her reply)", text):
        return "third_party_communication"
    if re.search(r"(?im)(https?://|webinar|screen-reader|the entire transcript|\d+:\d{2} )", text):
        return "external_web_or_transcript"
    return "untraceable_imported_artifact"


def main():
    labels = {row["adversarial_id"]: row for row in read_jsonl(ROOT / "blind_adjudication" / "PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl")}
    cases = {row["adversarial_id"]: row for row in read_jsonl(ROOT / "PROVENANCE_ADVERSARIAL_SET_V1.jsonl")}
    predictions = json.loads((ROOT / "PROVENANCE_RESOLVER_V0_4_predictions.json").read_text(encoding="utf-8"))["predictions"]
    families = defaultdict(list)
    for case_id, truth in labels.items():
        predicted = predictions[case_id]
        text = cases[case_id]["text_excerpt"]
        if predicted["evidence_class"] == "P0" and truth["evidence_class"] != "P0":
            family = "p0_fp_correction_or_quotation" if re.match(r"(?i)^i didn.t say", text) else "p0_fp_carrier_collapsed"
            families[family].append(case_id)
        if truth["evidence_class"] == "P0" and predicted["evidence_class"] != "P0":
            families["p0_fn_" + p0_fn_family(text)].append(case_id)
        if predicted["evidence_class"] == "MIXED" and truth["evidence_class"] != "MIXED":
            if "transcript" in text.lower():
                family = "mixed_fp_transcript_label_tension"
            elif re.search(r"(?i)^can you rewrite|^summarize|^recreate", text):
                family = "mixed_fp_carrier_metadata_vs_semantic_span"
            else:
                family = "mixed_fp_ambiguous_structural_boundary"
            families[family].append(case_id)
        if truth["evidence_class"] == "MIXED" and predicted["evidence_class"] != "MIXED":
            families["mixed_fn_traceable_body_boundary"].append(case_id)
        if truth["adoption_status"] in {"AD3", "AD4"} and predicted["adoption_status"] != truth["adoption_status"]:
            families["adoption_fn_material_transformation"].append(case_id)
    result = {
        "source_labels": "blind_adjudication/PROVENANCE_ADVERSARIAL_LABELS_V1.jsonl",
        "source_predictions": "PROVENANCE_RESOLVER_V0_4_predictions.json",
        "families": dict(sorted(families.items())),
        "counts": {key: len(value) for key, value in sorted(families.items())},
    }
    (ROOT / "PROVENANCE_V0_5_ERROR_INVENTORY.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
