"""Tests for ocbc.generate — integration and unit."""

import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from ocbc.generate import (
    Rules,
    _collect_prose,
    _generate_parser,
    _related_controls,
    download_json,
    family_of,
    log_orphan_baselines,
    main,
    membership_flags,
    non_negotiable_from_membership,
    parent_of,
    parse_oscal_catalog,
    parse_oscal_profile,
    severity_from_membership,
)

# ---------------------------------------------------------------------------
# Fake OSCAL structures
# ---------------------------------------------------------------------------

FAKE_CATALOG = {
    "catalog": {
        "uuid": "test-uuid",
        "metadata": {
            "title": "Test",
            "version": "5.2.0",
            "oscal-version": "1.1.3",
            "last-modified": "2025-01-01T00:00:00Z",
        },
        "groups": [
            {
                "id": "ac",
                "class": "family",
                "title": "Access Control",
                "controls": [
                    {
                        "id": "ac-1",
                        "title": "Policy and Procedures",
                        "links": [
                            {"href": "#ac-2", "rel": "related"},
                        ],
                        "parts": [
                            {
                                "id": "ac-1_smt",
                                "name": "statement",
                                "prose": "Develop an access control policy.",
                            },
                            {
                                "id": "ac-1_gdn",
                                "name": "guidance",
                                "prose": "None.",
                            },
                        ],
                    },
                    {
                        "id": "ac-2",
                        "title": "Account Management",
                        "links": [
                            {"href": "#ac-3", "rel": "related"},
                            {"href": "#ac-5", "rel": "related"},
                        ],
                        "parts": [
                            {
                                "id": "ac-2_smt",
                                "name": "statement",
                                "prose": "Define and manage system accounts.",
                            },
                            {
                                "id": "ac-2_gdn",
                                "name": "guidance",
                                "prose": "None.",
                            },
                        ],
                        "controls": [
                            {
                                "id": "ac-2.1",
                                "title": "Automated System Account Management",
                                "links": [
                                    {"href": "#ac-2", "rel": "related"},
                                ],
                                "parts": [
                                    {
                                        "id": "ac-2.1_smt",
                                        "name": "statement",
                                        "prose": "Support management of system accounts using automated mechanisms.",
                                    },
                                    {
                                        "id": "ac-2.1_gdn",
                                        "name": "guidance",
                                        "prose": "None.",
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "id": "sc",
                "class": "family",
                "title": "System and Communications Protection",
                "controls": [
                    {
                        "id": "sc-7",
                        "title": "Boundary Protection",
                        "links": [
                            {"href": "#ac-4", "rel": "related"},
                            {"href": "#sc-8", "rel": "related"},
                        ],
                        "parts": [
                            {
                                "id": "sc-7_smt",
                                "name": "statement",
                                "prose": "Monitor and control communications at the boundary.",
                            },
                            {
                                "id": "sc-7_gdn",
                                "name": "guidance",
                                "prose": "None.",
                            },
                        ],
                    },
                ],
            },
        ],
    }
}


def _profile(ids: list[str]) -> dict:
    return {
        "profile": {
            "uuid": "test-uuid",
            "metadata": {
                "title": "Test Profile",
                "version": "5.2.0",
                "oscal-version": "1.1.3",
                "last-modified": "2025-01-01T00:00:00Z",
            },
            "imports": [
                {"include-controls": [{"with-ids": ids}]},
            ],
        }
    }


FAKE_LOW = _profile(["ac-1", "ac-2"])
FAKE_MODERATE = _profile(["ac-1", "ac-2", "ac-2.1", "sc-7"])
FAKE_HIGH = _profile(["ac-1", "ac-2", "ac-2.1", "sc-7"])
FAKE_PRIVACY = _profile(["ac-1"])

FAKE_FEDRAMP_LI_SAAS = _profile(["ac-1"])
FAKE_FEDRAMP_LOW = _profile(["ac-1", "ac-2"])
FAKE_FEDRAMP_MODERATE = _profile(["ac-1", "ac-2", "sc-7"])
FAKE_FEDRAMP_HIGH = _profile(["ac-1", "ac-2", "ac-2.1", "sc-7"])


def _mock_download_json(url: str) -> dict:
    lower = url.lower()
    if "catalog" in lower:
        return FAKE_CATALOG
    if "fedramp" in lower:
        if "li-saas" in lower:
            return FAKE_FEDRAMP_LI_SAAS
        if "low" in lower:
            return FAKE_FEDRAMP_LOW
        if "moderate" in lower:
            return FAKE_FEDRAMP_MODERATE
        if "high" in lower:
            return FAKE_FEDRAMP_HIGH
    if "low" in lower:
        return FAKE_LOW
    if "moderate" in lower:
        return FAKE_MODERATE
    if "high" in lower:
        return FAKE_HIGH
    if "privacy" in lower:
        return FAKE_PRIVACY
    raise ValueError(f"Unexpected URL in test: {url}")


@patch("ocbc.generate.download_json", side_effect=_mock_download_json)
def test_main_produces_valid_json(mock_dl):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "output.json")
        with patch("sys.argv", ["ocbc-generate", "--out", out_path]):
            main()

        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)

    assert data["project"] == "Open Controls Baseline Catalog (OCBC)"
    assert "project_version" in data
    assert "generated_at_utc" in data
    assert data["framework"] == "NIST SP 800-53 Rev. 5"
    assert "reference" in data
    assert "rules" in data
    assert isinstance(data["controls"], list)
    assert data["count"] == len(data["controls"])

    ids = [c["control_id"] for c in data["controls"]]
    assert ids == sorted(ids), "controls should be sorted by control_id"

    required_keys = {
        "control_id",
        "control_name",
        "family",
        "control_text",
        "discussion",
        "related_controls",
        "parent_control_id",
        "baseline_membership",
        "fedramp_membership",
        "severity",
        "non_negotiable",
    }
    for ctrl in data["controls"]:
        assert required_keys.issubset(ctrl.keys())
        bm = ctrl["baseline_membership"]
        assert set(bm.keys()) == {"low", "moderate", "high", "privacy"}
        assert all(isinstance(v, bool) for v in bm.values())
        fm = ctrl["fedramp_membership"]
        assert set(fm.keys()) == {"li_saas", "low", "moderate", "high"}
        assert all(isinstance(v, bool) for v in fm.values())
        assert ctrl["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert isinstance(ctrl["non_negotiable"], bool)


@patch("ocbc.generate.download_json", side_effect=_mock_download_json)
def test_baseline_membership_accuracy(mock_dl):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "output.json")
        with patch("sys.argv", ["ocbc-generate", "--out", out_path]):
            main()

        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)

    by_id = {c["control_id"]: c for c in data["controls"]}

    ac1 = by_id["AC-1"]
    assert ac1["baseline_membership"] == {"low": True, "moderate": True, "high": True, "privacy": True}
    assert ac1["fedramp_membership"] == {"li_saas": True, "low": True, "moderate": True, "high": True}
    assert ac1["severity"] == "MEDIUM"
    assert ac1["non_negotiable"] is True

    sc7 = by_id["SC-7"]
    assert sc7["baseline_membership"] == {"low": False, "moderate": True, "high": True, "privacy": False}
    assert sc7["fedramp_membership"] == {"li_saas": False, "low": False, "moderate": True, "high": True}
    assert sc7["severity"] == "HIGH"
    assert sc7["non_negotiable"] is True


@patch("ocbc.generate.download_json", side_effect=_mock_download_json)
def test_enhancement_parent_linkage(mock_dl):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "output.json")
        with patch("sys.argv", ["ocbc-generate", "--out", out_path]):
            main()

        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)

    by_id = {c["control_id"]: c for c in data["controls"]}

    assert by_id["AC-2"]["parent_control_id"] is None
    assert by_id["AC-2(1)"]["parent_control_id"] == "AC-2"
    assert by_id["AC-2(1)"]["family"] == "AC"


@patch("ocbc.generate.download_json", side_effect=_mock_download_json)
def test_non_negotiable_high_only(mock_dl):
    """When --non_negotiable_min_baseline=high, only high-baseline controls are non-negotiable."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = str(Path(tmpdir) / "output.json")
        with patch("sys.argv", ["ocbc-generate", "--out", out_path, "--non_negotiable_min_baseline", "high"]):
            main()

        with open(out_path, encoding="utf-8") as f:
            data = json.load(f)

    for ctrl in data["controls"]:
        if ctrl["baseline_membership"]["high"]:
            assert ctrl["non_negotiable"] is True
        else:
            assert ctrl["non_negotiable"] is False


def test_log_orphan_baselines_warns(caplog):
    catalog_ids = {"AC-1", "AC-2"}
    with caplog.at_level(logging.WARNING):
        log_orphan_baselines(
            catalog_ids,
            low={"AC-1", "AC-2"},
            moderate={"AC-1", "AC-2", "AC-99"},
            high={"AC-1"},
            privacy={"PM-1"},
        )
    assert "1 moderate-baseline" in caplog.text
    assert "AC-99" in caplog.text
    assert "1 privacy-baseline" in caplog.text
    assert "PM-1" in caplog.text
    assert "low-baseline" not in caplog.text
    assert "high-baseline" not in caplog.text


def test_log_orphan_baselines_silent_when_no_orphans(caplog):
    catalog_ids = {"AC-1", "AC-2"}
    with caplog.at_level(logging.WARNING):
        log_orphan_baselines(
            catalog_ids,
            low={"AC-1"},
            moderate={"AC-1", "AC-2"},
            high={"AC-2"},
            privacy=set(),
        )
    assert caplog.text == ""


# ---------------------------------------------------------------------------
# Unit tests for individual functions
# ---------------------------------------------------------------------------


def test_download_json():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"catalog": {}}
    with patch("ocbc.generate.requests.get", return_value=mock_resp) as mock_get:
        result = download_json("https://example.com/data.json")
    mock_get.assert_called_once_with("https://example.com/data.json", timeout=120)
    mock_resp.raise_for_status.assert_called_once()
    assert result == {"catalog": {}}


def test_collect_prose_with_sub_parts():
    """Cover the branch where a matching part has nested sub-parts with prose."""
    parts = [
        {
            "name": "statement",
            "prose": "Top-level statement.",
            "parts": [
                {"prose": "Sub-part A."},
                {"prose": "Sub-part B."},
            ],
        },
    ]
    assert _collect_prose(parts, "statement") == "Top-level statement.\nSub-part A.\nSub-part B."


def test_collect_prose_nested_under_non_matching_parent():
    """Cover the elif branch: statement buried inside a wrapper with a different name."""
    parts = [
        {
            "name": "assessment-objective",
            "parts": [
                {"name": "statement", "prose": "Nested statement."},
            ],
        },
    ]
    assert _collect_prose(parts, "statement") == "Nested statement."


def test_collect_prose_returns_none_when_empty():
    assert _collect_prose([], "statement") is None


def test_related_controls_ignores_non_related_links():
    links = [
        {"href": "#ac-1", "rel": "related"},
        {"href": "https://example.com", "rel": "reference"},
        {"href": "#ac-2", "rel": "related"},
    ]
    assert _related_controls(links) == "AC-1, AC-2"


def test_related_controls_returns_none_when_empty():
    assert _related_controls([]) is None


def test_severity_high_only():
    rules = Rules()
    m = {"low": False, "moderate": False, "high": True, "privacy": False}
    assert severity_from_membership(m, rules) == "CRITICAL"


def test_severity_privacy_only():
    rules = Rules()
    m = {"low": False, "moderate": False, "high": False, "privacy": True}
    assert severity_from_membership(m, rules) == "MEDIUM"


def test_severity_no_baseline():
    rules = Rules()
    m = {"low": False, "moderate": False, "high": False, "privacy": False}
    assert severity_from_membership(m, rules) == "LOW"


def test_parent_of_base_control():
    assert parent_of("AC-2") is None


def test_parent_of_enhancement():
    assert parent_of("AC-2(1)") == "AC-2"


def test_family_of_base():
    assert family_of("SC-7") == "SC"


def test_family_of_enhancement():
    assert family_of("AC-2(1)") == "AC"


def test_membership_flags():
    flags = membership_flags("AC-1", low={"AC-1"}, moderate={"AC-1"}, high=set(), privacy=set())
    assert flags == {"low": True, "moderate": True, "high": False, "privacy": False}


def test_non_negotiable_moderate_default():
    rules = Rules()
    assert non_negotiable_from_membership({"moderate": True, "high": False}, rules) is True
    assert non_negotiable_from_membership({"moderate": False, "high": False}, rules) is False


def test_parse_oscal_catalog_empty():
    assert parse_oscal_catalog({}) == {}
    assert parse_oscal_catalog({"catalog": {}}) == {}


def test_parse_oscal_profile_empty():
    assert parse_oscal_profile({}) == set()
    assert parse_oscal_profile({"profile": {}}) == set()


def test_main_module_importable():
    import ocbc.__main__  # noqa: F401


def test_version_is_string():
    from ocbc import __version__

    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_generate_parser_returns_parser():
    import argparse as _argparse

    p = _generate_parser()
    assert isinstance(p, _argparse.ArgumentParser)
    # spot-check key arguments are registered
    arg_dests = {a.dest for a in p._actions}
    assert "out" in arg_dests
    assert "non_negotiable_min_baseline" in arg_dests
    assert "catalog_url" in arg_dests


def test_generate_parser_add_help_false():
    p = _generate_parser(add_help=False)
    # When add_help=False, --help should not be registered
    actions = {a.option_strings[0] for a in p._actions if a.option_strings}
    assert "--help" not in actions


@patch("ocbc.generate.download_json", side_effect=_mock_download_json)
def test_main_accepts_prebuilt_args(mock_dl, tmp_path):
    """main() should accept a pre-parsed Namespace and not call parse_args."""
    import argparse

    out_path = str(tmp_path / "output.json")
    args = argparse.Namespace(
        out=out_path,
        non_negotiable_min_baseline="moderate",
        catalog_url="https://fake/catalog",
        baseline_low_url="https://fake/low",
        baseline_moderate_url="https://fake/moderate",
        baseline_high_url="https://fake/high",
        baseline_privacy_url="https://fake/privacy",
        fedramp_lisaas_url="https://fake/fedramp/li-saas",
        fedramp_low_url="https://fake/fedramp/low",
        fedramp_moderate_url="https://fake/fedramp/moderate",
        fedramp_high_url="https://fake/fedramp/high",
    )
    main(args)
    assert Path(out_path).exists()
