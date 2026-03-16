import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "spec" / "schemas" / "ocbc-v0.1.json"


def _minimal_catalog():
    return {
        "project": "Open Controls Baseline Catalog (OCBC)",
        "project_version": "0.1.0",
        "generated_at_utc": "2026-03-06T06:00:00Z",
        "framework": "NIST SP 800-53 Rev. 5",
        "reference": {},
        "rules": {},
        "count": 1,
        "controls": [
            {
                "control_id": "AC-1",
                "control_name": "Policy and Procedures",
                "family": "AC",
                "control_text": "...",
                "discussion": None,
                "related_controls": None,
                "parent_control_id": None,
                "baseline_membership": {
                    "low": True,
                    "moderate": True,
                    "high": True,
                    "privacy": False,
                },
                "fedramp_membership": {
                    "li_saas": False,
                    "low": True,
                    "moderate": True,
                    "high": True,
                },
                "severity": "MEDIUM",
                "non_negotiable": True,
            }
        ],
    }


def test_schema_file_exists():
    assert SCHEMA_PATH.exists(), f"Schema not found at {SCHEMA_PATH}"


def test_valid_catalog_passes_schema():
    schema = json.loads(SCHEMA_PATH.read_text())
    catalog = _minimal_catalog()
    # Should not raise
    jsonschema.validate(instance=catalog, schema=schema)


def test_missing_required_field_fails():
    schema = json.loads(SCHEMA_PATH.read_text())
    catalog = _minimal_catalog()
    del catalog["controls"][0]["severity"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=catalog, schema=schema)


def test_invalid_severity_value_fails():
    schema = json.loads(SCHEMA_PATH.read_text())
    catalog = _minimal_catalog()
    catalog["controls"][0]["severity"] = "EXTREME"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=catalog, schema=schema)


def test_extra_field_on_control_fails():
    schema = json.loads(SCHEMA_PATH.read_text())
    catalog = _minimal_catalog()
    catalog["controls"][0]["unexpected_field"] = "oops"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=catalog, schema=schema)
