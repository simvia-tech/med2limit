"""
Active filter: select element groups to export and trim everything else.

Also applies shell metadata (orientations and thickness) to the active
shell elements by geometric signature lookup.
"""

from .element_types import is_shell, is_solid
from .orientation import build_active_shell_signatures


class ActiveFilter:
    """Reduce the model to a chosen subset of element groups.

    After `apply()`:
    - mesh.all_elements / all_nodes / element_sets / node_sets are filtered in place
    - active_elem_ids:    set[int]
    - active_node_ids:    set[int]
    - shell_orientations: {elem_id: (D1, D2)}  (only mapped shells)
    - shell_thickness:    {elem_id: float}     (only mapped shells)
    - has_shell_elements / has_solid_elements: bool
    """

    def __init__(self, mesh, shell_metadata, requested_groups=None, requested_nsets=None):
        self.mesh = mesh
        self.shell_metadata = shell_metadata
        self.requested_groups = set(requested_groups or [])
        self.requested_nsets = set(requested_nsets or [])

        self.active_elem_ids = set()
        self.active_node_ids = set()
        self.shell_orientations = {}
        self.shell_thickness = {}
        self.has_shell_elements = False
        self.has_solid_elements = False

    # ------------------------------------------------------------------ public

    def apply(self):
        selected = self._select_group_names()
        self._trim_elements_and_nodes(selected)
        self._trim_node_sets()
        self._compute_capability_flags()
        self._map_shell_metadata()

    # ----------------------------------------------------------------- private

    def _select_group_names(self):
        """Pick the set of element-group names to keep.

        Priority:
        1. Explicit requested_groups (if any names match)
        2. User-defined GROUP_MA names extracted by the mesh
        3. All solid-only sets if the model contains solids
        4. Otherwise all shell sets
        """
        es = self.mesh.element_sets

        if self.requested_groups:
            selected = {name for name in es if name in self.requested_groups}
            if selected:
                return selected
            print("  WARNING: requested active groups not found — falling back to auto selection")

        if self.mesh.user_element_group_names:
            return set(self.mesh.user_element_group_names)

        all_types = {e["type"] for e in self.mesh.all_elements.values()}
        if any(is_solid(t) for t in all_types):
            return {name for name, d in es.items() if is_solid(d["type"])}
        return {name for name, d in es.items() if is_shell(d["type"])}

    def _trim_elements_and_nodes(self, selected_names):
        active_elem_ids = set()
        kept_sets = {}
        for name, data in self.mesh.element_sets.items():
            if name not in selected_names:
                continue
            ids = [eid for eid in data["elements"] if eid in self.mesh.all_elements]
            if not ids:
                continue
            kept_sets[name] = {"type": data["type"], "elements": ids}
            active_elem_ids.update(ids)

        if not active_elem_ids:
            raise RuntimeError(
                "No active elements selected. Check element group names or model contents."
            )

        self.mesh.element_sets = kept_sets
        self.mesh.all_elements = {
            eid: d for eid, d in self.mesh.all_elements.items() if eid in active_elem_ids
        }

        active_node_ids = set()
        for elem in self.mesh.all_elements.values():
            active_node_ids.update(elem["connectivity"])
        self.mesh.all_nodes = {
            nid: c for nid, c in self.mesh.all_nodes.items() if nid in active_node_ids
        }

        self.active_elem_ids = active_elem_ids
        self.active_node_ids = active_node_ids

    def _trim_node_sets(self):
        if self.requested_nsets:
            self.mesh.node_sets = {
                name: ids for name, ids in self.mesh.node_sets.items()
                if name in self.requested_nsets
            }
        else:
            # Keep only nodes that survived the element filter
            self.mesh.node_sets = {
                name: [nid for nid in ids if nid in self.active_node_ids]
                for name, ids in self.mesh.node_sets.items()
            }
            self.mesh.node_sets = {n: ids for n, ids in self.mesh.node_sets.items() if ids}

    def _compute_capability_flags(self):
        types = {d["type"] for d in self.mesh.all_elements.values()}
        self.has_shell_elements = any(is_shell(t) for t in types)
        self.has_solid_elements = any(is_solid(t) for t in types)

    def _map_shell_metadata(self):
        if not self.has_shell_elements or self.shell_metadata is None:
            return

        sigs = build_active_shell_signatures(self.mesh.all_nodes, self.mesh.all_elements)
        if not sigs:
            return

        n_orient = 0
        n_thick = 0
        for elem_id, _sig in sigs.items():
            ori = self.shell_metadata.get_orientation(elem_id, sigs)
            if ori is not None:
                self.shell_orientations[elem_id] = ori
                n_orient += 1
            thick = self.shell_metadata.get_thickness(elem_id, sigs)
            if thick is not None:
                self.shell_thickness[elem_id] = thick
                n_thick += 1

        print(f"  Mapped {n_orient} shell orientations and {n_thick} shell thicknesses")
