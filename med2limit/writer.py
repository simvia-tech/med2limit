"""
LIMIT file writers: .linp (geometry) and .lui (geometry + results).

Both writers share the geometry-writing helpers; .lui writes additional
STEP / INCREMENT / STRESS / DISPLACEMENT blocks per time step.
"""

import os

from .element_types import (
    is_shell,
    is_solid,
    is_beam_or_truss,
    reorder_connectivity,
    get_reorder_indices,
    select_section_elsets,
)
from .result_mapper import representative_shell_thickness


# ============================================================================
# Shared geometry block (used by both .linp and .lui)
# ============================================================================

def _write_header(f, source_filename):
    f.write("*Heading\n")
    f.write(f"** Converted from MED file: {os.path.basename(source_filename)}\n")
    f.write("** Conversion tool: MED to LIMIT converter\n")
    f.write("**\n")


def _write_nodes(f, all_nodes):
    f.write("*Node\n")
    for node_id in sorted(all_nodes):
        x, y, z = all_nodes[node_id]
        f.write(f"{node_id}, {x:.6e}, {y:.6e}, {z:.6e}\n")


def _group_elements_by_type(all_elements):
    grouped = {}
    for eid, data in all_elements.items():
        grouped.setdefault(data["type"], []).append((eid, data))
    return grouped


def _write_elements(f, all_elements):
    grouped = _group_elements_by_type(all_elements)
    for elem_type in sorted(grouped):
        f.write(f"*Element, type={elem_type}\n")
        for eid, data in sorted(grouped[elem_type]):
            conn = data["connectivity"]
            if is_solid(elem_type):
                conn = reorder_connectivity(elem_type, conn)
            f.write(f"{eid}, {', '.join(map(str, conn))}\n")


def _write_element_sets(f, element_sets):
    f.write("**\n** Element Sets\n")
    for name in sorted(element_sets):
        f.write(f"*Elset, elset={name}\n")
        ids = element_sets[name]["elements"]
        for i in range(0, len(ids), 16):
            f.write(", ".join(map(str, ids[i:i + 16])) + "\n")


def _write_node_sets(f, node_sets):
    if not node_sets:
        return
    f.write("**\n** Node Sets\n")
    for name in sorted(node_sets):
        f.write(f"*Nset, nset={name}\n")
        ids = node_sets[name]
        for i in range(0, len(ids), 16):
            f.write(", ".join(map(str, ids[i:i + 16])) + "\n")


def _write_sections(f, element_sets, shell_thickness, property_prefixes=None):
    f.write("**\n** Section Definitions\n")
    section_names = select_section_elsets(element_sets.keys(), property_prefixes)
    _report_excluded_sections(element_sets.keys(), section_names)
    for name, data in sorted(element_sets.items()):
        if name not in section_names:
            continue
        elem_type = data["type"]
        if is_solid(elem_type):
            f.write(f"*Solid Section, elset={name}, material=MAT1\n,\n")
        elif is_shell(elem_type):
            thickness = representative_shell_thickness(name, data, shell_thickness)
            f.write(f"*Shell Section, elset={name}, material=MAT1\n")
            f.write(f"{thickness}, 5\n")
        elif is_beam_or_truss(elem_type):
            f.write(f"** Beam/Truss section for {name} - define as needed\n")


def _report_excluded_sections(all_names, section_names):
    """Say out loud which elsets were left without a Section.

    An excluded elset reaches LIMIT as a plain Elset: no material, no
    thickness. That is the intent for construction/BC/weld-line groups,
    but it silently loses a group that did need a property and just
    doesn't follow the naming convention (see select_section_elsets).
    Without this line the only way to catch it is to import the file into
    LIMIT and count the Property Sets against a reference model by hand.
    """
    excluded = sorted(set(all_names) - set(section_names))
    if not excluded:
        return
    print(f"  WARNING: {len(excluded)} of {len(set(all_names))} elsets got no Section "
          f"(no material/thickness in LIMIT) — they do not match the property-set "
          f"naming convention:")
    print(f"           {', '.join(excluded)}")


def _write_geometry_block(f, source_filename, all_nodes, all_elements,
                         element_sets, node_sets, shell_thickness,
                         property_prefixes=None):
    _write_header(f, source_filename)
    _write_nodes(f, all_nodes)
    _write_elements(f, all_elements)
    _write_element_sets(f, element_sets)
    _write_node_sets(f, node_sets)
    _write_sections(f, element_sets, shell_thickness, property_prefixes)
    f.write("**\n** End of geometry definition\n")


# ============================================================================
# .linp writer
# ============================================================================

class LinpWriter:
    def __init__(self, mesh, filter_, source_filename, property_prefixes=None):
        self.mesh = mesh
        self.filter = filter_
        self.source_filename = source_filename
        self.property_prefixes = property_prefixes

    def write(self, path):
        print(f"\nWriting .linp file: {path}")
        with open(path, "w") as f:
            _write_geometry_block(
                f,
                self.source_filename,
                self.mesh.all_nodes,
                self.mesh.all_elements,
                self.mesh.element_sets,
                self.mesh.node_sets,
                self.filter.shell_thickness,
                self.property_prefixes,
            )
        print(f"  Wrote {len(self.mesh.all_nodes)} nodes, "
              f"{len(self.mesh.all_elements)} elements, "
              f"{len(self.mesh.element_sets)} elsets, "
              f"{len(self.mesh.node_sets)} nsets")


# ============================================================================
# .lui writer
# ============================================================================

class LuiWriter:
    def __init__(self, mesh, filter_, fields, source_filename, property_prefixes=None):
        self.mesh = mesh
        self.filter = filter_
        self.fields = fields
        self.source_filename = source_filename
        self.property_prefixes = property_prefixes

    def write(self, path):
        from .result_mapper import ResultMapper

        print(f"\nWriting .lui file: {path}")
        with open(path, "w") as f:
            _write_geometry_block(
                f,
                self.source_filename,
                self.mesh.all_nodes,
                self.mesh.all_elements,
                self.mesh.element_sets,
                self.mesh.node_sets,
                self.filter.shell_thickness,
                self.property_prefixes,
            )

            n_ts = self.fields.n_timesteps
            if n_ts <= 0:
                print("  WARNING: No timesteps detected. No results written.")
                f.write("**\n** End of stress/displacement definition\n")
                return

            mapper = ResultMapper(
                self.mesh.all_elements,
                self.filter.active_node_ids,
                self.filter.active_elem_ids,
                self.fields,
            )

            for it in range(n_ts):
                step_no = it + 1
                mapper.map_timestep(it)
                f.write(f"*STEP = {step_no}\n*INCREMENT = 1\n*STRESS\n")
                n_shells, n_solids = self._write_stress_block(f, mapper)
                print(f"  STEP={step_no}/{n_ts}: {n_shells} shells, {n_solids} solids")

                f.write("*DISPLACEMENT\n")
                self._write_displacement_block(f, mapper)
                print(f"  STEP={step_no}/{n_ts}: {len(mapper.disp_data)} displacement nodes")

            f.write("**\n** End of stress/displacement definition\n")

    def _write_stress_block(self, f, mapper):
        n_shells = 0
        n_solids = 0
        for elem_id in sorted(self.mesh.all_elements):
            elem_type = self.mesh.all_elements[elem_id]["type"]
            conn = self.mesh.all_elements[elem_id]["connectivity"]

            if is_shell(elem_type):
                if elem_id not in mapper.stress_top or elem_id not in mapper.stress_bottom:
                    continue
                self._write_shell_stress(f, elem_id, conn, mapper)
                n_shells += 1
            elif is_solid(elem_type):
                if elem_id not in mapper.stress_by_element:
                    continue
                if self._write_solid_stress(f, elem_id, elem_type, conn, mapper):
                    n_solids += 1
        return n_shells, n_solids

    def _write_shell_stress(self, f, elem_id, conn, mapper):
        D1D2 = self.filter.shell_orientations.get(elem_id)
        if D1D2 is None:
            d1 = (1.0, 0.0, 0.0)
            d2 = (0.0, 0.0, 1.0)
        else:
            d1 = tuple(D1D2[0][:3])
            d2 = tuple(D1D2[1][:3])

        f.write(f"{elem_id}\n*TOP\n")
        for node_id in conn:
            s = mapper.stress_top[elem_id].get(node_id)
            if s is not None:
                f.write(self._fmt_shell_line(node_id, s, d1, d2))
        f.write("*BOTTOM\n")
        for node_id in conn:
            s = mapper.stress_bottom[elem_id].get(node_id)
            if s is not None:
                f.write(self._fmt_shell_line(node_id, s, d1, d2))

    def _write_solid_stress(self, f, elem_id, elem_type, conn, mapper):
        stress_tuples = mapper.stress_by_element[elem_id]
        if len(stress_tuples) != len(conn):
            print(f"  WARNING: solid {elem_id} connectivity/stress mismatch")
            return False
        reordered_conn = reorder_connectivity(elem_type, conn)
        order = get_reorder_indices(elem_type, len(conn))
        reordered_stress = [stress_tuples[i] for i in order]

        f.write(f"{elem_id}\n")
        for node_id, s in zip(reordered_conn, reordered_stress):
            f.write(f"{node_id}, {s[0]:.6e}, {s[1]:.6e}, {s[2]:.6e}, "
                    f"{s[3]:.6e}, {s[4]:.6e}, {s[5]:.6e}, "
                    f"1.0, 0.0, 0.0, 0.0, 1.0, 0.0\n")
        return True

    def _write_displacement_block(self, f, mapper):
        for node_id in sorted(mapper.disp_data):
            d = mapper.disp_data[node_id]
            f.write(f"{node_id}, {d[0]:.6e}, {d[1]:.6e}, {d[2]:.6e}\n")

    @staticmethod
    def _fmt_shell_line(node_id, s, d1, d2):
        return (f"{node_id}, {s[0]:.6e}, {s[1]:.6e}, {s[2]:.6e}, "
                f"{s[3]:.6e}, {s[4]:.6e}, {s[5]:.6e}, "
                f"{d1[0]:.6f}, {d1[1]:.6f}, {d1[2]:.6f}, "
                f"{d2[0]:.6f}, {d2[1]:.6f}, {d2[2]:.6f}\n")
