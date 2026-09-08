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



# Literal, underscore-including prefixes LIMIT matches to auto-classify
# element sets (see the LIMIT training material):
#   "PROF_" -> Profile Sets, consumed by "Generate Weld Sets by Properties
#              (incl. 'PROF_' sets)" to build the shell weld sets.
#   "SW_"   -> Solid Weld Generation Elsets, required by the Solid Weld
#              Manager to pair up the plates on either side of a weld.
# These prefixes must keep their underscore, or LIMIT can no longer match
# them and files the set under "Other Nsets"/"Other Elsets" instead.
LIMIT_SIGNIFICANT_PREFIXES = ("PROF_", "SW_")


def clean_name(name, prefixes=None) -> str:
    """Normalize a group name by removing underscores (LIMIT naming convention).

    Underscores are cosmetic noise almost everywhere, but a handful of
    literal prefixes are meaningful to LIMIT and must be preserved as-is
    (see LIMIT_SIGNIFICANT_PREFIXES).

    `prefixes` overrides that default list for studies using another
    convention; it replaces the defaults rather than extending them.
    """
    name = str(name)
    if prefixes is None:
        prefixes = LIMIT_SIGNIFICANT_PREFIXES
    for prefix in prefixes:
        if name.startswith(prefix):
            return prefix + name[len(prefix):].replace("_", "")
    return name.replace("_", "")


# Aster naming convention some models use to mark the element sets that
# actually carry a material/thickness assignment (see the formation email:
# "les sets de propriété sont ceux commencent par 'surfset' et 'solset'").
# Checked after clean_name() has already stripped the underscore, so the
# prefixes here are written without it.
PROPERTY_SET_PREFIXES = ("surfset", "solset")


def select_section_elsets(names, prefixes=None):
    """Pick which (already clean_name'd) elset names should get a LIMIT
    Section (i.e. count as a Property Set rather than a plain Elset).

    If any name follows the surfset/solset convention, only those are
    selected — every other GROUP_MA (weld lines, control/BC groups, raw
    geometry import groups) has no material/thickness of its own and
    should stay a plain Elset/Nset (LIMIT files it under "Other Elsets"/
    "Other Nsets"), matching how the reference Abaqus model classifies
    them (11 real Sections there vs. one per active elset before this
    fix — see the Aster/Abaqus LIMIT tree comparison).

    Falls back to selecting every name when the convention isn't used at
    all, so models without surfset_/solset_ groups (e.g. the bundled
    Shell1/Shell2 example) keep the original "one Section per elset"
    behaviour.

    `prefixes` overrides PROPERTY_SET_PREFIXES for studies naming their
    property groups differently. Matching ignores case on both sides:
    the same convention shows up as solset/SolSet/SOLSET depending on
    who built the mesh.

    Careful: the rule is global to the model. As soon as one name matches,
    every other elset loses its Section — including one that legitimately
    carries a material or a thickness under an unprefixed name. Callers
    are expected to report the exclusions (see writer._write_sections).
    """
    names = list(names)
    if prefixes is None:
        prefixes = PROPERTY_SET_PREFIXES
    prefixes = tuple(p.lower() for p in prefixes)
    property_names = {n for n in names if n.lower().startswith(prefixes)}
    return property_names or set(names)
