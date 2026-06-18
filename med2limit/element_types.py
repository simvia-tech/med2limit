"""
MED ↔ LIMIT element type mapping and classification helpers.

This module is pure: no I/O, no MEDCoupling reads. Only mapping tables and
small functions. Easy to test in isolation.
"""

import medcoupling as mc


# Mapping from MEDCoupling geometric type codes to LIMIT/Abaqus element type names.
MED_TO_LIMIT = {
    # Solids
    mc.NORM_HEXA8: "C3D8",
    mc.NORM_HEXA20: "C3D20",
    mc.NORM_TETRA4: "C3D4",
    mc.NORM_TETRA10: "C3D10",
    mc.NORM_PENTA6: "C3D6",
    mc.NORM_PENTA15: "C3D15",
    # Shells / 2D
    mc.NORM_TRI3: "S3",
    mc.NORM_QUAD4: "S4",
    mc.NORM_TRI6: "STRI65",
    mc.NORM_QUAD8: "S8R",
    # Beams / 1D
    mc.NORM_SEG2: "T3D2",
    mc.NORM_SEG3: "B32",
}


# Validated MED → LIMIT local-node permutations for linear 3D solids.
# Identified by direct LIMIT_CAE geometry tests.
NODE_REORDER = {
    "C3D8": [0, 3, 2, 1, 4, 7, 6, 5],
    "C3D6": [0, 2, 1, 3, 5, 4],
}


def med_to_limit(geo_type):
    """Return the LIMIT name for a MEDCoupling geometric type, or a placeholder."""
    return MED_TO_LIMIT.get(geo_type, f"UNKNOWN_{geo_type}")


def is_shell(elem_type: str) -> bool:
    """True for shell-like element types handled by this tool."""
    return elem_type.startswith("S") or elem_type.startswith("M")


def is_solid(elem_type: str) -> bool:
    """True for 3D solid element types."""
    return elem_type.startswith("C3D")


def is_beam_or_truss(elem_type: str) -> bool:
    """True for 1D beam/truss element types."""
    return elem_type.startswith("T3D") or elem_type.startswith("B")


def is_result_carrying(elem_type: str) -> bool:
    """True for element types that carry stress/displacement results in LIMIT."""
    return is_shell(elem_type) or is_solid(elem_type)


def get_reorder_indices(elem_type: str, n_nodes: int):
    """Return the validated MED→LIMIT local-node permutation, or identity."""
    perm = NODE_REORDER.get(elem_type)
    if perm is None or len(perm) != n_nodes:
        return list(range(n_nodes))
    return perm


def reorder_connectivity(elem_type: str, connectivity):
    """Reorder a connectivity list with the validated MED→LIMIT permutation."""
    order = get_reorder_indices(elem_type, len(connectivity))
    return [connectivity[i] for i in order]


def clean_name(name) -> str:
    """Normalize a group name by removing underscores (LIMIT naming convention)."""
    return str(name).replace("_", "")
