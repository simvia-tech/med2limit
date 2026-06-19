# Changelog


## [0.0.2] - 2026-06-19

### Added
- CI/CD release pipeline

## [0.0.1] - 2026-06-17

### Added
- Initial public release of `med2limit`.
- Conversion of Code_Aster MED/RMED files to LIMIT_CAE `.linp` and `.lui` formats.
- Shell workflow with DKT elements (S3, S4, STRI65, S8R).
- Linear solid workflow with validated LIMIT node ordering for C3D8 and C3D6.
- Multi-step / multi-increment displacement and stress transfer.
- Embedded REPLO/CARCOQUE detection from `IMPR_CONCEPT` in the main result file.
- Optional separate orientation file (legacy workflow).
- Dynamic shell support level detection — works for shell-only and mixed
  hexa + shell models without manual configuration.
- Mixed stress mode: SUP/INF for shells and generic SIEF_ELNO for solids
  in the same conversion.
- Geometric signature matching for shell metadata mapping (no hardcoded
  element ID offsets).
- Automatic node set derivation from element groups when needed.
- Command-line interface (`med2limit ...`) and Python API
  (`from med2limit import MEDToLimitConverter`).
- Unit tests for type classification and shell signature mapping.
- Bundled example with full Code_Aster source files (`.comm`, `.export`)
  and test mesh.