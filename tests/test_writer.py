"""Tests for the writer module's Section selection — no MED file required."""

import io
from types import SimpleNamespace

from med2limit.element_types import select_section_elsets
from med2limit.writer import LinpWriter, _write_sections


def test_select_section_elsets_uses_surfset_solset_convention_when_present():
    """The customer's Aster property groups are prefixed 'surfset'/'solset'
    (see formation email: "les sets de propriété sont ceux commencent par
    'surfset' et 'solset'"). When any such group is present, only those
    should get a LIMIT Section (Property Set) — everything else (weld
    lines, control/BC groups, raw geometry import groups) stays a plain
    Elset/Nset, matching how the reference Abaqus model classifies them
    (11 Property Sets there vs the 35 med2limit was producing before this
    fix, because it used to write a Section for every active elset).
    """
    names = ["CTPOA1a", "cordon", "solsetPOAep10", "surfsetPOAep10", "ep10"]
    assert select_section_elsets(names) == {"solsetPOAep10", "surfsetPOAep10"}


def test_select_section_elsets_falls_back_to_all_when_no_convention():
    """Models that don't use the surfset_/solset_ convention (e.g. the
    bundled Shell1/Shell2 example) keep the original behaviour: every
    active elset gets a Section, so basic usage isn't broken by this
    customer-specific naming convention.
    """
    names = ["Shell1", "Shell2"]
    assert select_section_elsets(names) == {"Shell1", "Shell2"}


def test_select_section_elsets_honours_custom_property_prefixes():
    """The surfset/solset convention is this customer's, not a LIMIT rule.
    A study naming its property groups otherwise must be able to pass its
    own prefixes instead of falling back to "a Section for every elset".
    """
    names = ["matPlate", "cordon", "solsetPOAep10"]
    assert select_section_elsets(names, prefixes=("mat",)) == {"matPlate"}


def test_select_section_elsets_drops_property_elsets_outside_the_convention():
    """Locks in the known blind spot of the prefix heuristic: the rule is
    global to the model, so as soon as ONE name matches the convention,
    every other elset loses its Section — including one that legitimately
    carries a material/thickness under a different name. Such a model ends
    up in LIMIT with no property assigned to that part, which is why
    _write_sections has to report the exclusions out loud.
    """
    names = ["solsetPOAep10", "PlateWithItsOwnThickness"]
    assert select_section_elsets(names) == {"solsetPOAep10"}


def test_write_sections_reports_the_elsets_it_left_without_a_section(capsys):
    """An elset excluded from the Section set reaches LIMIT with no material
    and no thickness. Before this warning the only way to notice was to
    import the file into LIMIT and count the Property Sets by hand against
    a reference model — so the writer has to say which elsets it dropped.
    """
    element_sets = {
        "solsetPOAep10": {"type": "C3D8", "elements": [1]},
        "cordon": {"type": "C3D8", "elements": [2]},
        "CTPOA1a": {"type": "C3D8", "elements": [3]},
    }
    _write_sections(io.StringIO(), element_sets, {})

    out = capsys.readouterr().out
    assert "2 of 3" in out
    assert "CTPOA1a" in out and "cordon" in out
    assert "solsetPOAep10" not in out


def test_write_sections_stays_quiet_when_every_elset_gets_a_section(capsys):
    """No exclusion, nothing to warn about — the fallback path (models that
    don't use the convention at all) must not print spurious warnings.
    """
    element_sets = {
        "Plate1": {"type": "C3D8", "elements": [1]},
        "Plate2": {"type": "C3D8", "elements": [2]},
    }
    _write_sections(io.StringIO(), element_sets, {})

    assert capsys.readouterr().out == ""


def _fake_model(element_sets):
    mesh = SimpleNamespace(
        all_nodes={1: (0.0, 0.0, 0.0)},
        all_elements={1: {"type": "C3D8", "connectivity": [1] * 8}},
        element_sets=element_sets,
        node_sets={},
    )
    return mesh, SimpleNamespace(shell_thickness={})


def test_linp_writer_applies_the_configured_property_prefixes(tmp_path):
    """The prefixes have to reach the file that LIMIT actually reads, not
    just the helper — this covers the plumbing from the writer down to the
    *Solid Section lines.
    """
    mesh, filter_ = _fake_model({
        "matPlate": {"type": "C3D8", "elements": [1]},
        "solsetPOAep10": {"type": "C3D8", "elements": [1]},
    })
    out = tmp_path / "out.linp"
    LinpWriter(mesh, filter_, "model.rmed", property_prefixes=("mat",)).write(str(out))

    text = out.read_text()
    assert "*Solid Section, elset=matPlate" in text
    assert "*Solid Section, elset=solsetPOAep10" not in text


def test_select_section_elsets_matches_property_prefixes_case_insensitively():
    """Aster studies write the same convention as solset/SolSet/SOLSET
    depending on who built the mesh, so the property prefixes are matched
    without regard to case — including the ones passed in by the caller.
    """
    assert select_section_elsets(["SolSet-POA"], prefixes=("solset",)) == {"SolSet-POA"}
    assert select_section_elsets(["solsetPOA"], prefixes=("SolSet",)) == {"solsetPOA"}
