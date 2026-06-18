"""
MED/RMED file reader — encapsulates MEDCoupling I/O calls.

All fragile MEDCoupling operations (getFieldAtLevel, getNonEmptyLevels, etc.)
are isolated here. Other modules in the package only see Python-friendly data.
"""

import medcoupling as mc


class MedFileReader:
    """Open a MED/RMED file and provide convenient access to its meshes and fields."""

    def __init__(self, path: str):
        self.path = path
        self._data = mc.MEDFileData(path)
        self.meshes = self._collect_meshes()
        self.fields = self._collect_fields()

    def _collect_meshes(self):
        md = self._data.getMeshes()
        return [md.getMeshAtPos(i) for i in range(md.getNumberOfMeshes())]

    def _collect_fields(self):
        fd = self._data.getFields()
        return [fd.getFieldAtPos(i) for i in range(fd.getNumberOfFields())]

    def find_field(self, *required, exclude=()):
        """Return the first field whose name contains all `required` substrings
        and none of the `exclude` substrings. Returns None if not found."""
        for f in self.fields:
            name = f.getName()
            if all(k in name for k in required) and not any(e in name for e in exclude):
                return f
        return None

    def field_names(self):
        """Return the list of field names — handy for diagnostics."""
        return [f.getName() for f in self.fields]

    @staticmethod
    def get_shell_level(field_ts) -> int:
        """Compute the relative MED level on which shell support data is stored.

        MEDCoupling stores fields by relative level (0 = max dim, -1 = max dim - 1, ...).
        For shell-related fields (dim 2), the relative level depends on the
        maximum element dimension present in the model:
        - 100% shell model → dim_max = 2 → shell_level = 0
        - hexa + shell     → dim_max = 3 → shell_level = -1
        """
        dim_max = field_ts.getNonEmptyLevels()[0]
        return 2 - dim_max
