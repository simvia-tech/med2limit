# Roadmap

This roadmap is a statement of intent, not a contractual commitment. It is
updated at least at every major or minor version bump.

## Short term — Next release (v0.2.0)

### Features in development

- **Quadratic element support** — extend the validated LIMIT node-ordering
  to:
  - `C3D10` (10-node tetrahedron)
  - `C3D15` (15-node pentahedron)
  - `C3D20` (20-node hexahedron)
  - `STRI65` (6-node triangular shell))

- **Salome integration** — provide a documented and tested workflow to run
  `med2limit` from inside the Salome_Meca embedded Python interpreter:
  - Standalone launcher script template
  - Detection of Salome's embedded MEDCoupling vs. the pip-installed version
  - Salome-safe execution (no `sys.exit`, no `argparse` collision with
    host application arguments)
  - Step-by-step example inside Salome's Python console

### Quality improvements

- Integration tests using the bundled `.rmed` example files

## Medium / long term — Vision

- Broader element type coverage (axisymmetric, plane stress / plane strain
  if relevant for fatigue post-processing)
- Improved handling of T-junctions and non-conforming meshes between
  shell-shell or shell-solid interfaces

## Help wanted

- Test cases from real industrial models (mixed shell + solid,
  multiple thicknesses, complex weld configurations)
- LIMIT_CAE expertise on edge cases not yet handled by the converter
- Documentation improvements (more annotated examples, troubleshooting
  guide based on user feedback)

---

> [!NOTE]
> This roadmap is updated at every major or minor release.
> Issues tagged `enhancement` or `help wanted` on GitHub track the
> day-to-day progress between roadmap updates.