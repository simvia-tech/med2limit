"""
Per-timestep result mapping.

Converts raw arrays from FieldExtractor into per-element / per-node containers
ready to be written into the .lui file.
"""

import collections

from .element_types import (
    is_shell,
    is_solid,
    is_result_carrying,
    get_reorder_indices,
)


class ResultMapper:
    """Map one MED time step into LIMIT-ready result containers.

    Containers reset on each `map_timestep(it)` call:
    - disp_data:         {node_id: (dx, dy, dz)}
    - stress_top:        {elem_id: {node_id: (sxx, syy, szz, sxy, sxz, syz)}}
    - stress_bottom:     {elem_id: {node_id: (sxx, syy, szz, sxy, sxz, syz)}}
    - stress_by_element: {elem_id: [stress_tuple_for_each_local_node]}
    """

    def __init__(self, all_elements, active_node_ids, active_elem_ids,
                 field_extractor):
        self.all_elements = all_elements
        self.active_node_ids = active_node_ids
        self.active_elem_ids = active_elem_ids
        self.fields = field_extractor

        self.disp_data = {}
        self.stress_top = {}
        self.stress_bottom = {}
        self.stress_by_element = {}

    def map_timestep(self, it: int):
        """Map one time step. Containers are reset before filling."""
        self.disp_data = {}
        self.stress_top = {}
        self.stress_bottom = {}
        self.stress_by_element = {}

        self._map_displacement(it)
        if self.fields.stress_mode == "generic":
            self._map_generic_stress(it)
        elif self.fields.stress_mode == "shell_top_bottom":
            self._map_shell_stress(it)

    def _map_displacement(self, it):
        raw = self.fields.disp_raw_ts[it]
        if raw is None:
            return
        sorted_nodes = sorted(self.active_node_ids)
        if len(sorted_nodes) != len(raw):
            print(f"  WARNING: TS={it}: displacement count mismatch "
                  f"({len(raw)} vs {len(sorted_nodes)} nodes)")
            return
        for i, node_id in enumerate(sorted_nodes):
            self.disp_data[node_id] = raw[i][:3]

    def _map_generic_stress(self, it):
        raw = self.fields.stress_generic_raw_ts[it]
        if raw is None:
            return
        idx = 0
        for elem_id in sorted(self.active_elem_ids):
            elem_type = self.all_elements[elem_id]["type"]
            conn = self.all_elements[elem_id]["connectivity"]
            if not is_result_carrying(elem_type):
                continue
            n = len(conn)
            end = idx + n
            if end <= len(raw):
                # Keep MED/local node order — LIMIT expects element-local ordering for solids
                self.stress_by_element[elem_id] = [raw[j][:6] for j in range(idx, end)]
            else:
                print(f"  WARNING: TS={it}: not enough generic stress tuples for elem {elem_id}")
                self.stress_by_element[elem_id] = []
            idx = end

    def _map_shell_stress(self, it):
        raw_inf = self.fields.stress_inf_raw_ts[it]
        raw_sup = self.fields.stress_sup_raw_ts[it]
        if raw_inf is None or raw_sup is None:
            return
        idx = 0
        for elem_id in sorted(self.active_elem_ids):
            elem_type = self.all_elements[elem_id]["type"]
            conn = self.all_elements[elem_id]["connectivity"]
            if not is_shell(elem_type):
                continue
            self.stress_bottom.setdefault(elem_id, {})
            self.stress_top.setdefault(elem_id, {})
            for node_id in conn:
                if idx < len(raw_inf):
                    self.stress_bottom[elem_id][node_id] = raw_inf[idx][:6]
                if idx < len(raw_sup):
                    self.stress_top[elem_id][node_id] = raw_sup[idx][:6]
                idx += 1


def representative_shell_thickness(elset_name, elset_data, shell_thickness):
    """Pick the dominant thickness for a shell elset.

    A shell elset may mix several thicknesses; LIMIT *Shell Section accepts one
    value per elset, so we use the most frequent and emit a warning if mixed.
    """
    values = [
        round(float(shell_thickness[eid]), 6)
        for eid in elset_data["elements"]
        if eid in shell_thickness
    ]
    if not values:
        print(f"  WARNING: no shell thickness mapped for elset '{elset_name}'. Using 1.0")
        return 1.0
    counts = collections.Counter(values)
    if len(counts) > 1:
        most = counts.most_common(1)[0][0]
        print(f"  WARNING: elset '{elset_name}' has mixed thicknesses {sorted(counts.keys())}."
              f" Using {most}")
    return counts.most_common(1)[0][0]


__all__ = ["ResultMapper", "representative_shell_thickness", "get_reorder_indices", "is_solid"]
