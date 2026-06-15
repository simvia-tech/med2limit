"""
Top-level orchestrator. Public step methods allow debugging in a notebook.

Typical use:
    converter = MEDToLimitConverter("model.rmed", "out.linp", "out.lui",
                                    active_groups=["Shell1", "Shell2"])
    converter.convert()

Step-by-step debug:
    converter.step_1_load()
    converter.step_2_extract_mesh()
    print(converter.mesh.all_nodes)   # inspect
    converter.step_3_extract_fields()
    ...
"""

from .reader import MedFileReader
from .mesh import MeshExtractor
from .fields import FieldExtractor
from .orientation import ShellMetadata
from .filter import ActiveFilter
from .writer import LinpWriter, LuiWriter


class MEDToLimitConverter:
    """Orchestrate the MED → LIMIT conversion pipeline."""

    def __init__(self, med_filename, linp_filename, lui_filename,
                 orientation_med_filename=None,
                 active_groups=None, active_nsets=None):
        self.med_filename = med_filename
        self.linp_filename = linp_filename
        self.lui_filename = lui_filename
        self.orientation_med_filename = orientation_med_filename
        self.active_groups = list(active_groups or [])
        self.active_nsets = list(active_nsets or [])

        # Filled at runtime
        self.reader = None
        self.mesh = None
        self.fields = None
        self.shell_meta = None
        self.filter = None

    # --------------------------------------------------------------- steps

    def step_1_load(self):
        """Open the main MED/RMED file."""
        print(f"Loading MED file: {self.med_filename}")
        self.reader = MedFileReader(self.med_filename)
        print(f"  Found {len(self.reader.meshes)} mesh(es)")
        print(f"  Found {len(self.reader.fields)} field(s)")
        for f in self.reader.fields:
            print(f"    - {f.getName()}")

    def step_2_extract_mesh(self):
        """Extract nodes, elements, element groups and node groups."""
        print("\nExtracting mesh...")
        self.mesh = MeshExtractor(
            self.reader.meshes, self.active_groups, self.active_nsets
        )
        self.mesh.extract_all()
        print(f"  Total nodes: {len(self.mesh.all_nodes)}")
        print(f"  Total elements: {len(self.mesh.all_elements)}")
        print(f"  Element sets: {list(self.mesh.element_sets.keys())}")
        print(f"  Node sets: {list(self.mesh.node_sets.keys())}")

    def step_3_extract_fields(self):
        """Extract DEPL and SIEF fields for all time steps."""
        print("\nExtracting fields...")
        self.fields = FieldExtractor(self.reader)
        self.fields.extract()
        print(f"  Stress mode: {self.fields.stress_mode}")
        print(f"  Time steps:  {self.fields.n_timesteps}")

    def step_4_load_shell_metadata(self):
        """Load REPLO/CARCOQUE: embedded first, then separate file as fallback."""
        print("\nLoading shell metadata (REPLO, CARCOQUE)...")
        self.shell_meta = ShellMetadata()
        loaded = self.shell_meta.load(self.reader, self.orientation_med_filename)
        if loaded:
            print(f"  Loaded from: {self.shell_meta.source}")
            if self.shell_meta.replo1 is not None:
                print(f"  REPLO_1: {len(self.shell_meta.replo1)} entries")
            if self.shell_meta.carcoque_ep is not None:
                uniq = sorted({round(float(v), 3) for v in self.shell_meta.carcoque_ep})
                print(f"  CARCOQUE EP unique values: {uniq}")
        else:
            print("  No shell metadata available (using defaults)")

    def step_5_filter(self):
        """Reduce model to active groups and map shell metadata."""
        print("\nFiltering active data...")
        self.filter = ActiveFilter(
            self.mesh, self.shell_meta,
            requested_groups=self.active_groups,
            requested_nsets=self.active_nsets,
        )
        self.filter.apply()
        print(f"  Active elements: {len(self.filter.active_elem_ids)}")
        print(f"  Active nodes:    {len(self.filter.active_node_ids)}")

    def step_6_write(self):
        """Write the .linp and .lui output files."""
        LinpWriter(self.mesh, self.filter, self.med_filename).write(self.linp_filename)
        LuiWriter(self.mesh, self.filter, self.fields, self.med_filename).write(self.lui_filename)

    # --------------------------------------------------------------- full

    def convert(self):
        """Run the complete pipeline."""
        try:
            self.step_1_load()
            self.step_2_extract_mesh()
            self.step_3_extract_fields()
            self.step_4_load_shell_metadata()
            self.step_5_filter()
            self.step_6_write()
            print("\n" + "=" * 60)
            print("Translation complete")
            print("=" * 60)
            return True
        except Exception as e:
            import traceback
            print(f"\nERROR: Conversion failed: {e}")
            print(traceback.format_exc())
            return False
