"""CLI dispatcher for the ocbc command."""

from __future__ import annotations

import argparse

from . import __version__
from .fetch import main as fetch_main
from .generate import _generate_parser
from .generate import main as generate_main


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ocbc",
        description="Open Controls Baseline Catalog (OCBC) CLI",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # fetch subcommand
    fetch_p = subparsers.add_parser(
        "fetch",
        help="Download the pre-built catalog from openastra.org (fast)",
    )
    fetch_p.add_argument(
        "--out",
        default="ocbc_full_catalog_enriched.json",
        help="Output file path (default: ocbc_full_catalog_enriched.json)",
    )

    # generate subcommand — inherits all flags from _generate_parser
    subparsers.add_parser(
        "generate",
        help="Generate the catalog from scratch from NIST/FedRAMP OSCAL sources",
        parents=[_generate_parser(add_help=False)],
    )

    args = parser.parse_args()
    if args.command == "fetch":
        fetch_main(args)
    else:
        generate_main(args)
