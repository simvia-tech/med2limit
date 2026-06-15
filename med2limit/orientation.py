"""
Shell orientation (REPLO_1, REPLO_2) and thickness (CARCOQUE) extraction.

Two sources are supported, in priority order:
1. EMBEDDED — REPLO and CARCOQUE are inside the main result file
   (Code_Aster IMPR_CONCEPT writing on the same UNITE as IMPR_RESU).
2. SEPARATE — REPLO and CARCOQUE are in a dedicated MED/RMED file.

Mapping from support data to active shell elements is done by geometric
signatures (sorted tuple of rounded node coordinates), not by indices.
This is immune to MEDCoupling renumbering and does not require any offset.
"""

from .reader import MedFileReader


class ShellMetadata:
    """Container for REPLO_1, REPLO_2, CARCOQUE arrays + geometric signature index."""

    def __init__(self):
        self.replo1 = None        # ndarray (n_shells, 3)
        self.replo2 = None        # ndarray (n_shells, 3)
        self.carcoque_ep = None   # ndarray (n_shells,)  — EP column only
        self.sig_to_idx = {}      # frozenset signature -> row index in arrays
        self.source = None        # 'embedded' | 'separate' | None

    # ------------------------------------------------------------------ public

    def load(self, main_reader: MedFileReader, separate_path: str = None) -> bool:
        """Try embedded first, then separate file. Returns True if loaded."""
        if self._try_load_from_reader(main_reader):
            self.source = "embedded"
            return True
        if separate_path:
            sep_reader = MedFileReader(separate_path)
            if self._try_load_from_reader(sep_reader):
                self.source = "separate"
                return True
        self.source = None
        return False

    def get_orientation(self, elem_id, active_shell_sigs):
        """Lookup orientation vectors (D1, D2) for an active shell element.
        Returns None if not mapped."""
        sig = active_shell_sigs.get(elem_id)
        if sig is None or self.replo1 is None:
            return None
        idx = self.sig_to_idx.get(sig)
        if idx is None or idx >= len(self.replo1):
            return None
        return self.replo1[idx], self.replo2[idx]

    def get_thickness(self, elem_id, active_shell_sigs):
        """Lookup thickness EP for an active shell element. Returns None if not mapped."""
        sig = active_shell_sigs.get(elem_id)
        if sig is None or self.carcoque_ep is None:
            return None
        idx = self.sig_to_idx.get(sig)
        if idx is None or idx >= len(self.carcoque_ep):
            return None
        return float(self.carcoque_ep[idx])

    # ----------------------------------------------------------------- private

    def _try_load_from_reader(self, reader: MedFileReader) -> bool:
        replo1_field = reader.find_field("REPLO_1")
        replo2_field = reader.find_field("REPLO_2")
        carcoque_field = reader.find_field("CARCOQUE")
        if not (replo1_field and replo2_field and carcoque_field):
            return False

        # All three fields are on the same shell support mesh.
        ts_rep1 = replo1_field.getTimeStepAtPos(0)
        shell_level = MedFileReader.get_shell_level(ts_rep1)

        rep1_mc = ts_rep1.getFieldAtLevel(0, shell_level)
        rep2_mc = replo2_field.getTimeStepAtPos(0).getFieldAtLevel(0, shell_level)
        car_mc = carcoque_field.getTimeStepAtPos(0).getFieldAtLevel(0, shell_level)

        self.replo1 = rep1_mc.getArray().toNumPyArray()
        self.replo2 = rep2_mc.getArray().toNumPyArray()

        car_arr = car_mc.getArray().toNumPyArray()
        components = list(carcoque_field.getTimeStepAtPos(0).getInfo())
        if "EP" not in components:
            return False
        ep_idx = components.index("EP")
        self.carcoque_ep = car_arr[:, ep_idx]

        self.sig_to_idx = self._build_signature_index(rep1_mc)
        return True

    @staticmethod
    def _build_signature_index(field_mc, ndigits=8):
        """Build geometric-signature -> support-mesh-cell-index map.

        Signature: sorted tuple of rounded (x, y, z) coordinates for the cell's nodes.
        Same routine is applied later on active shell elements to look up the row.
        """
        support_mesh = field_mc.getMesh()
        coords = support_mesh.getCoords().toNumPyArray()
        n_cells = support_mesh.getNumberOfCells()
        sig_to_idx = {}

        for i in range(n_cells):
            conn = [int(x) for x in support_mesh.getNodeIdsOfCell(i)]
            if len(conn) != 3:
                continue
            pts = [coords[nid] for nid in conn]
            sig = tuple(sorted(tuple(round(float(c), ndigits) for c in p) for p in pts))
            sig_to_idx.setdefault(sig, i)

        return sig_to_idx


def build_active_shell_signatures(all_nodes, all_elements, ndigits=8):
    """Build elem_id -> signature for all active S3 elements.

    The signature is order-independent and matches the one used in
    ShellMetadata._build_signature_index.
    """
    elem_to_sig = {}
    for elem_id, elem_data in all_elements.items():
        if elem_data["type"] != "S3":
            continue
        pts = [all_nodes[nid] for nid in elem_data["connectivity"]]
        sig = tuple(sorted(tuple(round(float(c), ndigits) for c in p) for p in pts))
        elem_to_sig[elem_id] = sig
    return elem_to_sig
