#!/usr/bin/env python3
"""
CLI: Generate an enriched NIST SP 800-53 Rev.5 catalog JSON
with NIST SP 800-53B baseline membership + derived severity/non-negotiable.

Data is sourced from the official OSCAL JSON published by NIST at
https://github.com/usnistgov/oscal-content
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

from . import __version__
from .urls import (
    BASELINE_HIGH_URL,
    BASELINE_LOW_URL,
    BASELINE_MODERATE_URL,
    BASELINE_PRIVACY_URL,
    CATALOG_URL,
    FEDRAMP_HIGH_URL,
    FEDRAMP_LI_SAAS_URL,
    FEDRAMP_LOW_URL,
    FEDRAMP_MODERATE_URL,
)

logger = logging.getLogger(__name__)

CONTROL_ID_RE = re.compile(r"^[A-Z]{2,3}-\d{1,3}$")
ENHANCEMENT_RE = re.compile(r"^([A-Z]{2,3}-\d{1,3})\((\d+)\)$")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download_json(url: str) -> dict[str, Any]:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------------------
# OSCAL ID helpers
# ---------------------------------------------------------------------------


def oscal_id_to_control_id(oscal_id: str) -> str:
    """Convert an OSCAL-style ID to the canonical display form.

    ``"ac-2"``   -> ``"AC-2"``
    ``"ac-2.1"`` -> ``"AC-2(1)"``
    """
    parts = oscal_id.split(".")
    base = parts[0].upper()
    if len(parts) == 2:
        return f"{base}({int(parts[1])})"
    return base


def parent_of(control_id: str) -> str | None:
    m = ENHANCEMENT_RE.match(control_id)
    return m.group(1) if m else None


def family_of(control_id: str) -> str:
    base = parent_of(control_id) or control_id
    return base.split("-")[0]


# ---------------------------------------------------------------------------
# OSCAL catalog parsing
# ---------------------------------------------------------------------------


def _collect_prose(parts: list[dict[str, Any]], target_name: str) -> str | None:
    """Recursively collect ``prose`` from *parts* whose ``name`` equals *target_name*."""
    fragments: list[str] = []
    for part in parts:
        if part.get("name") == target_name:
            if prose := part.get("prose"):
                fragments.append(prose)
            for sub in part.get("parts", []):
                if sub_prose := sub.get("prose"):
                    fragments.append(sub_prose)
        elif part.get("parts"):
            nested = _collect_prose(part["parts"], target_name)
            if nested:
                fragments.append(nested)
    return "\n".join(fragments) if fragments else None


def _related_controls(links: list[dict[str, Any]]) -> str | None:
    ids: list[str] = []
    for link in links:
        if link.get("rel") == "related":
            href = link.get("href", "")
            if href.startswith("#"):
                ids.append(oscal_id_to_control_id(href[1:]))
    return ", ".join(ids) if ids else None


def _parse_control(ctrl: dict[str, Any], parent_id: str | None) -> dict[str, Any]:
    cid = oscal_id_to_control_id(ctrl["id"])
    parts = ctrl.get("parts", [])
    return {
        "control_id": cid,
        "control_name": ctrl.get("title"),
        "family": family_of(cid),
        "control_text": _collect_prose(parts, "statement"),
        "discussion": _collect_prose(parts, "guidance"),
        "related_controls": _related_controls(ctrl.get("links", [])),
        "parent_control_id": parent_id,
    }


def parse_oscal_catalog(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return ``{control_id: record}`` from an OSCAL catalog JSON."""
    out: dict[str, dict[str, Any]] = {}
    for group in data.get("catalog", {}).get("groups", []):
        for ctrl in group.get("controls", []):
            rec = _parse_control(ctrl, parent_id=None)
            out[rec["control_id"]] = rec
            for enh in ctrl.get("controls", []):
                enh_rec = _parse_control(enh, parent_id=rec["control_id"])
                out[enh_rec["control_id"]] = enh_rec
    return out


# ---------------------------------------------------------------------------
# OSCAL profile parsing
# ---------------------------------------------------------------------------


def parse_oscal_profile(data: dict[str, Any]) -> set[str]:
    """Return the set of canonical control IDs selected by an OSCAL profile."""
    ids: set[str] = set()
    for imp in data.get("profile", {}).get("imports", []):
        for ic in imp.get("include-controls", []):
            for wid in ic.get("with-ids", []):
                ids.add(oscal_id_to_control_id(wid))
    return ids


# ---------------------------------------------------------------------------
# Enrichment (unchanged from CSV era)
# ---------------------------------------------------------------------------


@dataclass
class Rules:
    non_negotiable_min_baseline: str = "moderate"  # "moderate" or "high"
    severity_low: str = "MEDIUM"
    severity_moderate: str = "HIGH"
    severity_high: str = "CRITICAL"
    severity_privacy_only: str = "MEDIUM"
    severity_none: str = "LOW"


def membership_flags(cid: str, low: set[str], moderate: set[str], high: set[str], privacy: set[str]) -> dict[str, bool]:
    return {
        "low": cid in low,
        "moderate": cid in moderate,
        "high": cid in high,
        "privacy": cid in privacy,
    }


def severity_from_membership(m: dict[str, bool], rules: Rules) -> str:
    if m["low"]:
        return rules.severity_low
    if m["moderate"]:
        return rules.severity_moderate
    if m["high"]:
        return rules.severity_high
    if m["privacy"] and not (m["low"] or m["moderate"] or m["high"]):
        return rules.severity_privacy_only
    return rules.severity_none


def non_negotiable_from_membership(m: dict[str, bool], rules: Rules) -> bool:
    if rules.non_negotiable_min_baseline.lower() == "high":
        return bool(m["high"])
    return bool(m["moderate"] or m["high"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _generate_parser(add_help: bool = True) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ocbc-generate",
        description="Generate Open Controls Baseline Catalog JSON",
        add_help=add_help,
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    p.add_argument("--catalog_url", default=CATALOG_URL)
    p.add_argument("--baseline_low_url", default=BASELINE_LOW_URL)
    p.add_argument("--baseline_moderate_url", default=BASELINE_MODERATE_URL)
    p.add_argument("--baseline_high_url", default=BASELINE_HIGH_URL)
    p.add_argument("--baseline_privacy_url", default=BASELINE_PRIVACY_URL)

    p.add_argument("--fedramp_lisaas_url", default=FEDRAMP_LI_SAAS_URL)
    p.add_argument("--fedramp_low_url", default=FEDRAMP_LOW_URL)
    p.add_argument("--fedramp_moderate_url", default=FEDRAMP_MODERATE_URL)
    p.add_argument("--fedramp_high_url", default=FEDRAMP_HIGH_URL)

    p.add_argument("--non_negotiable_min_baseline", choices=["moderate", "high"], default="moderate")
    p.add_argument("--out", default="ocbc_full_catalog_enriched.json")

    return p


def log_orphan_baselines(
    catalog_ids: set[str],
    *,
    low: set[str],
    moderate: set[str],
    high: set[str],
    privacy: set[str],
) -> None:
    """Warn about baseline control IDs that don't appear in the catalog."""
    baselines = {"low": low, "moderate": moderate, "high": high, "privacy": privacy}
    for name, id_set in baselines.items():
        orphans = sorted(id_set - catalog_ids)
        if orphans:
            logger.warning(
                "%d %s-baseline control(s) not found in catalog: %s",
                len(orphans),
                name,
                ", ".join(orphans),
            )


def main(args: argparse.Namespace | None = None) -> None:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.WARNING)
    if args is None:
        args = _generate_parser().parse_args()
    rules = Rules(non_negotiable_min_baseline=args.non_negotiable_min_baseline)

    catalog_data = download_json(args.catalog_url)
    low_data = download_json(args.baseline_low_url)
    mod_data = download_json(args.baseline_moderate_url)
    high_data = download_json(args.baseline_high_url)
    priv_data = download_json(args.baseline_privacy_url)

    fed_li_data = download_json(args.fedramp_lisaas_url)
    fed_low_data = download_json(args.fedramp_low_url)
    fed_mod_data = download_json(args.fedramp_moderate_url)
    fed_high_data = download_json(args.fedramp_high_url)

    controls = parse_oscal_catalog(catalog_data)
    low = parse_oscal_profile(low_data)
    moderate = parse_oscal_profile(mod_data)
    high = parse_oscal_profile(high_data)
    privacy = parse_oscal_profile(priv_data)

    fed_lisaas = parse_oscal_profile(fed_li_data)
    fed_low = parse_oscal_profile(fed_low_data)
    fed_moderate = parse_oscal_profile(fed_mod_data)
    fed_high = parse_oscal_profile(fed_high_data)

    log_orphan_baselines(
        set(controls.keys()),
        low=low,
        moderate=moderate,
        high=high,
        privacy=privacy,
    )

    enriched = []
    for cid, rec in sorted(controls.items(), key=lambda x: x[0]):
        m = membership_flags(cid, low, moderate, high, privacy)
        rec_out = dict(rec)
        rec_out["baseline_membership"] = m
        rec_out["fedramp_membership"] = {
            "li_saas": cid in fed_lisaas,
            "low": cid in fed_low,
            "moderate": cid in fed_moderate,
            "high": cid in fed_high,
        }
        rec_out["severity"] = severity_from_membership(m, rules)
        rec_out["non_negotiable"] = non_negotiable_from_membership(m, rules)
        enriched.append(rec_out)

    out_obj = {
        "project": "Open Controls Baseline Catalog (OCBC)",
        "project_version": __version__,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "framework": "NIST SP 800-53 Rev. 5",
        "reference": {
            "publication": "https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final",
            "oscal_content": "https://github.com/usnistgov/oscal-content",
        },
        "rules": {
            "severity_definition": {
                "if_in_low": rules.severity_low,
                "elif_in_moderate": rules.severity_moderate,
                "elif_in_high": rules.severity_high,
                "elif_privacy_only": rules.severity_privacy_only,
                "else": rules.severity_none,
            },
            "non_negotiable_min_baseline": rules.non_negotiable_min_baseline,
        },
        "count": len(enriched),
        "controls": enriched,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out_obj, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(enriched)} controls to {args.out}")


if __name__ == "__main__":
    main()
