"""
Example 01 — Minimal shell conversion.

Uses the LIMIT1.rmed test file bundled in examples/data/.
Run from anywhere with: python examples/01_shell_basic.py
"""

from pathlib import Path

from med2limit import MEDToLimitConverter


# Locate examples/data/ relative to this script — works regardless of cwd
HERE = Path(__file__).parent
DATA = HERE / "data"

INPUT_MED = DATA / "01_exemple.rmed"
OUTPUT_LINP = DATA / "01_exemple.linp"
OUTPUT_LUI = DATA / "01_exemple.lui"

ACTIVE_GROUPS = ["Shell1", "Shell2"]
ACTIVE_NSETS = ["WeldNo"]


if __name__ == "__main__":
    converter = MEDToLimitConverter(
        med_filename=str(INPUT_MED),
        linp_filename=str(OUTPUT_LINP),
        lui_filename=str(OUTPUT_LUI),
        active_groups=ACTIVE_GROUPS,
        active_nsets=ACTIVE_NSETS,
    )
    converter.convert()