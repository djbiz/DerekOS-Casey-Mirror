#!/usr/bin/env python3
"""Seal PROVENANCE_RESOLVER_V0.6 predictions for PROVENANCE_OUT_OF_SAMPLE_SET_V1.

Runs the frozen V0.6 resolver over the out-of-sample cases and writes a sealed
predictions file. This MUST run before adjudication labels are frozen so that
adjudication stays blind to resolver output.

Input threading matches the adversarial flow exactly: each case carries the
full `evidence` block (reuse, external fingerprint, markers, structure) from
the OOS SET file, plus `text_excerpt`. The bundle is used for target/context.

NOTE: predictions were initially sealed with evidence omitted (harness defect:
resolver saw no reuse evidence and abstained on everything). The frozen blind
adjudication had already been written from the bundles (evidence only) before
re-sealing, so blindness is preserved. This revision fixes input threading and
re-seals; the frozen labels are unchanged.
"""
from __future__ import annotations

import importlib.util as _ilu
import json
from pathlib import Path

AUDITS = Path(__file__).resolve().parent
SET = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1.jsonl"
BUNDLES = AUDITS / "out_of_sample_bundles"
OUT = AUDITS / "PROVENANCE_OUT_OF_SAMPLE_SET_V1_predictions.json"

_spec = _ilu.spec_from_file_location("resolver_v06", AUDITS / "provenance_resolver_v0_6.py")
_resolver = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_resolver)


def load_oos_bundles(directory: Path) -> dict[str, dict]:
    rows = {}
    for path in sorted(directory.glob("batch_*.jsonl")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["oos_id"]] = row
    return rows


def main() -> None:
    bundles = load_oos_bundles(BUNDLES)
    cases = {}
    for line in SET.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            cases[r["oos_id"]] = r
    print(f"set cases: {len(cases)} | bundles: {len(bundles)}")

    predictions = {}
    for oid in sorted(cases):
        case = {
            "adversarial_id": oid,
            "oos_id": oid,
            "text_excerpt": cases[oid].get("text_excerpt", ""),
            "evidence": cases[oid].get("evidence", {}),
        }
        predictions[oid] = _resolver.resolve_case(case, bundles.get(oid))
    OUT.write_text(
        json.dumps(
            {
                "resolver": "PROVENANCE_RESOLVER_V0.6",
                "sealed": "after frozen adjudication (adjudication blind); input threading corrected to include evidence block",
                "count": len(predictions),
                "predictions": predictions,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"sealed {len(predictions)} predictions -> {OUT.name}")


if __name__ == "__main__":
    main()
