"""
Mesh extraction: nodes, elements, element groups (GROUP_MA) and node groups (GROUP_NO).

The output of this module is plain Python dictionaries that downstream modules
can consume without touching MEDCoupling directly.
"""

from .element_types import med_to_limit, clean_name


class MeshExtractor:
    """Extract a flat geometry representation from one or more MED meshes.

    Outputs after `extract_all()`:
    - all_nodes:    {global_node_id: (x, y, z)}
    - all_elements: {global_elem_id: {'type': str, 'level': int,
                                      'connectivity': [int], 'elset': str}}
    - element_sets: {set_name: {'type': str, 'elements': [int]}}
    - node_sets:    {set_name: [int]}
    - user_element_group_names: set[str]  (names that came from GROUP_MA)
    """

    def __init__(self, meshes, active_groups=None, active_nsets=None):
        self.meshes = meshes
        self.active_groups = set(active_groups or [])
        self.active_nsets = set(active_nsets or [])

        self.all_nodes = {}
        self.all_elements = {}
        self.element_sets = {}
        self.node_sets = {}
        self.user_element_group_names = set()

    # ---------------------------------------------------------------- public

    def extract_all(self):
        """Run all extraction steps in the right order."""
        self._extract_nodes()
        self._extract_elements()
        self._extract_groups()
        self._derive_node_sets_from_element_groups()

    # ----------------------------------------------------------- private

    def _extract_nodes(self):
        node_id = 1
        for mesh in self.meshes:
            coords = mesh.getCoords()
            n_nodes = coords.getNumberOfTuples()
            for i in range(n_nodes):
                coord = coords.getTuple(i)
                # Pad to 3D if input is 1D or 2D
                if len(coord) == 2:
                    coord = (coord[0], coord[1], 0.0)
                elif len(coord) == 1:
                    coord = (coord[0], 0.0, 0.0)
                self.all_nodes[node_id] = coord
                node_id += 1

    def _extract_elements(self):
        element_id = 1
        node_offset = 0

        for mesh in self.meshes:
            mesh_name = mesh.getName()
            n_nodes = mesh.getCoords().getNumberOfTuples()
            levels = mesh.getNonEmptyLevels()

            for level in levels:
                mesh_at_level = mesh.getMeshAtLevel(level)
                geo_types = mesh_at_level.getAllGeoTypes()

                for geo_type in geo_types:
                    cell_ids = mesh_at_level.giveCellsWithType(geo_type)
                    if len(cell_ids) == 0:
                        continue

                    elem_type_name = med_to_limit(geo_type)
                    elset_name = f"{mesh_name}{elem_type_name}"
                    self.element_sets.setdefault(
                        elset_name,
                        {"type": elem_type_name, "elements": []},
                    )

                    for cell_id in cell_ids:
                        connectivity = mesh_at_level.getNodeIdsOfCell(int(cell_id))
                        adjusted = [int(n) + node_offset + 1 for n in connectivity]
                        self.all_elements[element_id] = {
                            "type": elem_type_name,
                            "level": level,
                            "connectivity": adjusted,
                            "elset": elset_name,
                        }
                        self.element_sets[elset_name]["elements"].append(element_id)
                        element_id += 1

            node_offset += n_nodes

    def _extract_groups(self):
        node_offset = 0

        for mesh in self.meshes:
            n_nodes = mesh.getCoords().getNumberOfTuples()

            # ---- node groups (GROUP_NO, level 1) ----
            try:
                node_group_names = mesh.getGroupsOnSpecifiedLev(1)
                for gname in node_group_names:
                    arr = mesh.getGroupArr(1, gname).toNumPyArray()
                    cname = clean_name(gname)
                    adjusted = [int(n) + node_offset + 1 for n in arr]
                    self.node_sets.setdefault(cname, []).extend(adjusted)
            except Exception:
                pass

            # ---- element groups (GROUP_MA, levels 0, -1, -2, -3) ----
            level_offset = {}
            offset = 0
            for level in (0, -1, -2, -3):
                level_offset[level] = offset
                try:
                    offset += mesh.getMeshAtLevel(level).getNumberOfCells()
                except Exception:
                    pass

            for level in (0, -1, -2, -3):
                try:
                    elem_group_names = mesh.getGroupsOnSpecifiedLev(level)
                except Exception:
                    continue
                for gname in elem_group_names:
                    if self.active_groups and clean_name(gname) not in self.active_groups \
                            and gname not in self.active_groups:
                        # If an explicit active_groups filter is set, skip non-matching names
                        # We compare both raw and cleaned form for convenience.
                        continue

                    local_ids = mesh.getGroupArr(level, gname).toNumPyArray()
                    global_ids = [int(l) + level_offset[level] + 1 for l in local_ids]
                    cname = clean_name(gname)

                    elem_type = None
                    for eid in global_ids:
                        if eid in self.all_elements:
                            elem_type = self.all_elements[eid]["type"]
                            break

                    self.element_sets[cname] = {
                        "type": elem_type,
                        "elements": global_ids,
                    }
                    self.user_element_group_names.add(cname)

            node_offset += n_nodes

    def _derive_node_sets_from_element_groups(self):
        """If an active_nset name matches an element group instead of a node group,
        synthesize a node set from the connectivity of those elements.

        This covers the common case where GROUP_MA='Weld' is used in Code_Aster
        without an explicit CREA_GROUP_NO/DEFI_GROUP step.
        """
        if not self.active_nsets:
            return

        node_offset = 0
        for mesh in self.meshes:
            n_nodes = mesh.getCoords().getNumberOfTuples()

            level_offset = {}
            offset = 0
            for level in (0, -1, -2, -3):
                level_offset[level] = offset
                try:
                    offset += mesh.getMeshAtLevel(level).getNumberOfCells()
                except Exception:
                    pass

            for level in (0, -1, -2, -3):
                try:
                    elem_group_names = mesh.getGroupsOnSpecifiedLev(level)
                except Exception:
                    continue
                for gname in elem_group_names:
                    cname = clean_name(gname)
                    # Only treat as nset if requested AND not already a real node set
                    if cname not in self.active_nsets:
                        continue
                    if cname in self.node_sets and self.node_sets[cname]:
                        continue

                    local_ids = mesh.getGroupArr(level, gname).toNumPyArray()
                    global_ids = [int(l) + level_offset[level] + 1 for l in local_ids]

                    nodes = set()
                    for eid in global_ids:
                        if eid in self.all_elements:
                            nodes.update(self.all_elements[eid]["connectivity"])
                    if nodes:
                        self.node_sets[cname] = sorted(nodes)

            node_offset += n_nodes
