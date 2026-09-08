"""
Command-line entry point.

Two modes:
- in-script configuration: edit the constants below for Salome / IDE direct runs
- CLI: standard argparse mode

This module does NOT call sys.exit() so it stays Salome-safe.
"""

import argparse
import os
from dataclasses import dataclass, field
from typing import List, Optional

from .converter import MEDToLimitConverter


VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# In-script configuration (edit for Salome / direct IDE execution)
# ---------------------------------------------------------------------------

INPUT_MED = ""
OUTPUT_LINP = ""
OUTPUT_LUI = ""
ORIENTATION_MED = None
ACTIVE_GROUPS = []
ACTIVE_NSETS = []
# Leave empty to use the built-in conventions (element_types.py):
# PROF_/SW_ for the LIMIT set prefixes, solset/surfset for the property sets.
LIMIT_PREFIXES = []
PROPERTY_PREFIXES = []

USE_IN_SCRIPT_CONFIGURATION = False


@dataclass
class RunConfig:
    """One conversion run's inputs, whatever mode they came from."""

    input_med: str
    output_linp: str
    output_lui: str
    orientation_med: Optional[str] = None
    groups: List[str] = field(default_factory=list)
    nsets: List[str] = field(default_factory=list)
    # Empty means "keep the built-in naming conventions", which is not the
    # same as "no prefix is significant" — an empty tuple passed down would
    # silently re-break the PROF_/SW_ classification.
    limit_prefixes: List[str] = field(default_factory=list)
    property_prefixes: List[str] = field(default_factory=list)


def _parse_name_list(text_value: str):
    if not text_value:
        return []
    return [item.strip() for item in text_value.split(",") if item.strip()]


def _from_in_script_config():
    return RunConfig(
        input_med=INPUT_MED,
        output_linp=OUTPUT_LINP or os.path.splitext(INPUT_MED)[0] + ".linp",
        output_lui=OUTPUT_LUI or os.path.splitext(INPUT_MED)[0] + ".lui",
        orientation_med=ORIENTATION_MED,
        groups=list(ACTIVE_GROUPS),
        nsets=list(ACTIVE_NSETS),
        limit_prefixes=list(LIMIT_PREFIXES),
        property_prefixes=list(PROPERTY_PREFIXES),
    )


def _from_cli():
    parser = argparse.ArgumentParser(
        description=f"MED/RMED to LIMIT converter ({VERSION})"
    )
    parser.add_argument("input_med")
    parser.add_argument("output_linp", nargs="?")
    parser.add_argument("output_lui", nargs="?")
    parser.add_argument("orientation_med", nargs="?", default=None)
    parser.add_argument("--groups", default="")
    parser.add_argument("--nsets", default="")
    parser.add_argument(
        "--limit-prefixes", default="",
        help="Comma-separated literal prefixes LIMIT uses to auto-classify sets, "
             "kept with their underscore (default: PROF_,SW_)",
    )
    parser.add_argument(
        "--property-prefixes", default="",
        help="Comma-separated prefixes marking the elsets that carry a material/"
             "thickness, i.e. LIMIT Property Sets, matched case-insensitively "
             "(default: solset,surfset)",
    )
    args, _unknown = parser.parse_known_args()

    return RunConfig(
        input_med=args.input_med,
        output_linp=args.output_linp or os.path.splitext(args.input_med)[0] + ".linp",
        output_lui=args.output_lui or os.path.splitext(args.input_med)[0] + ".lui",
        orientation_med=args.orientation_med,
        groups=_parse_name_list(args.groups),
        nsets=_parse_name_list(args.nsets),
        limit_prefixes=_parse_name_list(args.limit_prefixes),
        property_prefixes=_parse_name_list(args.property_prefixes),
    )


def main():
    if USE_IN_SCRIPT_CONFIGURATION and INPUT_MED:
        config = _from_in_script_config()
        print("Running in in-script configuration mode")
    else:
        config = _from_cli()

    print(f"  input             : {config.input_med}")
    print(f"  output_linp       : {config.output_linp}")
    print(f"  output_lui        : {config.output_lui}")
    print(f"  orientation_med   : {config.orientation_med}")
    print(f"  groups            : {config.groups}")
    print(f"  nsets             : {config.nsets}")
    print(f"  limit_prefixes    : {config.limit_prefixes or 'default'}")
    print(f"  property_prefixes : {config.property_prefixes or 'default'}")

    if not os.path.exists(config.input_med):
        print(f"ERROR: Input file not found: {config.input_med}")
        return 1
    if config.orientation_med and not os.path.exists(config.orientation_med):
        print(f"ERROR: Orientation file not found: {config.orientation_med}")
        return 1

    converter = MEDToLimitConverter(
        med_filename=config.input_med,
        linp_filename=config.output_linp,
        lui_filename=config.output_lui,
        orientation_med_filename=config.orientation_med,
        active_groups=config.groups,
        active_nsets=config.nsets,
        limit_prefixes=config.limit_prefixes or None,
        property_prefixes=config.property_prefixes or None,
    )
    return 0 if converter.convert() else 1


if __name__ == "__main__":
    main()
