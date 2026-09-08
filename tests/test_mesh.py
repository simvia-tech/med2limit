"""Tests for MeshExtractor's name normalization — no MED file required."""

from med2limit.mesh import MeshExtractor


def test_mesh_extractor_normalizes_names_with_the_configured_prefixes():
    """Group names are cleaned during mesh extraction, so a CLI-provided
    prefix list has to reach MeshExtractor — otherwise the elsets are
    already de-underscored by the time the writer sees them.
    """
    extractor = MeshExtractor([], limit_prefixes=("WELD_",))
    assert extractor._clean("WELD_POA_1a") == "WELD_POA1a"
    assert extractor._clean("PROF_POA") == "PROFPOA"


def test_mesh_extractor_defaults_to_the_limit_prefixes():
    extractor = MeshExtractor([])
    assert extractor._clean("PROF_POA_COR_1a") == "PROF_POACOR1a"
    assert extractor._clean("SW_POA") == "SW_POA"
