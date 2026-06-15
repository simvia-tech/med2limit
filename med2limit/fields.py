"""
Field extraction: displacement (DEPL) and stress (SIEF).

Two stress modes are detected automatically:
- 'shell_top_bottom' — SIEF_INF + SIEF_SUP (shell top/bottom faces)
- 'generic'          — SIEF_ELNO (solid or generic ELNO stress)

All time steps are extracted at once. Per-step mapping to per-element data
happens later in writer.py / filter.py.
"""


class FieldExtractor:
    """Extract raw displacement and stress arrays for every time step.

    Outputs after `extract()`:
    - n_timesteps:           int
    - stress_mode:           'shell_top_bottom' | 'generic' | None
    - disp_raw_ts:           list of ndarray  (one per timestep)
    - stress_inf_raw_ts:     list of ndarray | None  (only if shell mode)
    - stress_sup_raw_ts:     list of ndarray | None  (only if shell mode)
    - stress_generic_raw_ts: list of ndarray | None  (only if generic mode)
    """

    def __init__(self, reader):
        self.reader = reader
        self.n_timesteps = 0
        self.stress_mode = None
        self.disp_raw_ts = []
        self.stress_inf_raw_ts = []
        self.stress_sup_raw_ts = []
        self.stress_generic_raw_ts = []

    def extract(self):
        disp_field = self._find_displacement_field()
        if disp_field is None:
            raise RuntimeError("No displacement field found (DEPL). Cannot proceed.")

        stress_inf_field = self.reader.find_field("SIEF_INFSIEF_ELNO")
        stress_sup_field = self.reader.find_field("SIEF_SUPSIEF_ELNO")
        stress_generic_field = self.reader.find_field(
            "SIEF_ELNO", exclude=("INF", "SUP")
        )

        if stress_generic_field is not None:
            self.stress_mode = "generic"
        elif stress_inf_field is not None and stress_sup_field is not None:
            self.stress_mode = "shell_top_bottom"
        else:
            self.stress_mode = None

        self.n_timesteps = disp_field.getNumberOfTS()
        self.disp_raw_ts = [None] * self.n_timesteps
        self.stress_inf_raw_ts = [None] * self.n_timesteps
        self.stress_sup_raw_ts = [None] * self.n_timesteps
        self.stress_generic_raw_ts = [None] * self.n_timesteps

        for it in range(self.n_timesteps):
            self._extract_one_step(
                it, disp_field, stress_inf_field, stress_sup_field, stress_generic_field
            )

    def _find_displacement_field(self):
        """Find a field whose name contains DEPL (e.g., RESU____DEPL)."""
        for field in self.reader.fields:
            if "DEPL" in field.getName():
                return field
        return None

    def _extract_one_step(self, it, disp_field, inf_field, sup_field, gen_field):
        # Displacement
        try:
            self.disp_raw_ts[it] = (
                disp_field.getTimeStepAtPos(it).getUndergroundDataArray().toNumPyArray()
            )
        except Exception as e:
            print(f"  WARNING: TS={it}: could not extract displacement: {e}")

        # Stress
        if self.stress_mode == "generic" and gen_field is not None:
            try:
                self.stress_generic_raw_ts[it] = (
                    gen_field.getTimeStepAtPos(it).getUndergroundDataArray().toNumPyArray()
                )
            except Exception as e:
                print(f"  WARNING: TS={it}: could not extract generic stress: {e}")
        elif self.stress_mode == "shell_top_bottom":
            try:
                self.stress_inf_raw_ts[it] = (
                    inf_field.getTimeStepAtPos(it).getUndergroundDataArray().toNumPyArray()
                )
            except Exception as e:
                print(f"  WARNING: TS={it}: could not extract stress_inf: {e}")
            try:
                self.stress_sup_raw_ts[it] = (
                    sup_field.getTimeStepAtPos(it).getUndergroundDataArray().toNumPyArray()
                )
            except Exception as e:
                print(f"  WARNING: TS={it}: could not extract stress_sup: {e}")
