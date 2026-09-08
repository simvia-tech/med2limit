"""Tests for the CLI argument surface — no MED file required."""

from med2limit.cli import _from_cli


def test_from_cli_parses_the_prefix_options(monkeypatch):
    """Both naming conventions med2limit relies on are study-specific, so
    they belong on the command line next to --groups/--nsets rather than
    hard-coded in element_types.py.
    """
    monkeypatch.setattr(
        "sys.argv",
        [
            "med2limit", "model.rmed", "out.linp", "out.lui",
            "--limit-prefixes", "PROF_,SW_",
            "--property-prefixes", "solset, surfset",
        ],
    )
    config = _from_cli()

    assert config.limit_prefixes == ["PROF_", "SW_"]
    assert config.property_prefixes == ["solset", "surfset"]


def test_from_cli_leaves_prefixes_empty_when_not_given(monkeypatch):
    """Omitting the options must mean "use the built-in conventions", not
    "no prefix is significant" — an empty list would silently re-break the
    PROF_/SW_ classification.
    """
    monkeypatch.setattr("sys.argv", ["med2limit", "model.rmed"])
    config = _from_cli()

    assert config.limit_prefixes == []
    assert config.property_prefixes == []
