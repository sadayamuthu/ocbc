"""Download the pre-built OCBC catalog from openastra.org."""

from __future__ import annotations

import argparse
import json

import requests

OCBC_CATALOG_URL = "https://openastra.org/ocbc/catalog/v0.1/latest.json"


def main(args: argparse.Namespace) -> None:
    print(f"Fetching catalog from {OCBC_CATALOG_URL} ...")
    r = requests.get(OCBC_CATALOG_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Wrote {data.get('count', '?')} controls to {args.out}")
