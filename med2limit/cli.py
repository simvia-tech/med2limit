"""
Command-line entry point.

Two modes:
- in-script configuration: edit the constants below for Salome / IDE direct runs
- CLI: standard argparse mode

This module does NOT call sys.exit() so it stays Salome-safe.
"""

import argparse
import os

from .converter import MEDToLimitConverter


VERSION = "0.10.0"


# ---------------------------------------------------------------------------
# In-script configuration (edit for Salome / direct IDE execution)
# ---------------------------------------------------------------------------

INPUT_MED = ""
OUTPUT_LINP = ""
OUTPUT_LUI = ""
ORIENTATION_MED = None
ACTIVE_GROUPS = []
ACTIVE_NSETS = []

USE_IN_SCRIPT_CONFIGURATION = False


def _parse_name_list(text_value: str):
    if not text_value:
        return []
    return [item.strip() for item in text_value.split(",") if item.strip()]


def _from_in_script_config():
    return (
        INPUT_MED,
        OUTPUT_LINP or os.path.splitext(INPUT_MED)[0] + ".linp",
        OUTPUT_LUI or os.path.splitext(INPUT_MED)[0] + ".lui",
        ORIENTATION_MED,
        list(ACTIVE_GROUPS),
        list(ACTIVE_NSETS),
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
    args, _unknown = parser.parse_known_args()

    return (
        args.input_med,
        args.output_linp or os.path.splitext(args.input_med)[0] + ".linp",
        args.output_lui or os.path.splitext(args.input_med)[0] + ".lui",
        args.orientation_med,
        _parse_name_list(args.groups),
        _parse_name_list(args.nsets),
    )


def main():
    if USE_IN_SCRIPT_CONFIGURATION and INPUT_MED:
        (input_file, out_linp, out_lui, orient, groups, nsets) = _from_in_script_config()
        print("Running in in-script configuration mode")
    else:
        (input_file, out_linp, out_lui, orient, groups, nsets) = _from_cli()

    print(f"  input          : {input_file}")
    print(f"  output_linp    : {out_linp}")
    print(f"  output_lui     : {out_lui}")
    print(f"  orientation_med: {orient}")
    print(f"  groups         : {groups}")
    print(f"  nsets          : {nsets}")

    if not os.path.exists(input_file):
        print(f"ERROR: Input file not found: {input_file}")
        return 1
    if orient and not os.path.exists(orient):
        print(f"ERROR: Orientation file not found: {orient}")
        return 1

    converter = MEDToLimitConverter(
        med_filename=input_file,
        linp_filename=out_linp,
        lui_filename=out_lui,
        orientation_med_filename=orient,
        active_groups=groups,
        active_nsets=nsets,
    )
    return 0 if converter.convert() else 1


if __name__ == "__main__":
    main()
