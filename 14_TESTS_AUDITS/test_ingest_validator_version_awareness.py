"""Focused regression tests for explicit ingest schema dispatch."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import jsonschema

from .verify_phase1_reconciliation import (
    INGEST,
    load_schemas,
    record_profile,
    validate_versioned_record,
)


class VersionAwareValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schemas = load_schemas()
        cls.examples = {}
        wanted = set(cls.schemas)
        with (INGEST / "messages.jsonl").open("rb") as source:
            for raw_line in source:
                record = json.loads(raw_line)
                profile = record_profile(record)
                cls.examples.setdefault(profile, record)
                if set(cls.examples) == wanted:
                    break

    def test_each_supported_profile_validates_against_its_own_schema(self) -> None:
        self.assertEqual(set(self.examples), set(self.schemas))
        for profile, record in self.examples.items():
            self.assertEqual(validate_versioned_record(record, self.schemas), profile)

    def test_unknown_version_fails_closed(self) -> None:
        record = dict(self.examples[("1.1.0", "chatgpt-json")], ingest_version="9.9.9")
        with self.assertRaisesRegex(ValueError, "unsupported ingest profile"):
            validate_versioned_record(record, self.schemas)

    def test_source_format_cannot_select_another_versions_contract(self) -> None:
        record = dict(self.examples[("2.0.0", "other-ai-export-fragments")])
        record["source_format"] = "copilot-csv"
        with self.assertRaisesRegex(ValueError, "unsupported ingest profile"):
            validate_versioned_record(record, self.schemas)

    def test_extra_properties_remain_rejected(self) -> None:
        record = dict(self.examples[("1.0.0", "copilot-csv")], unauthorized_field=True)
        with self.assertRaises(jsonschema.ValidationError):
            validate_versioned_record(record, self.schemas)


if __name__ == "__main__":
    unittest.main()
