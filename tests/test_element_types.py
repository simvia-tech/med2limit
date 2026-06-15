"""Tests for the pure element_types module — no MED file required."""

from med2limit.element_types import (
    is_shell,
    is_solid,
    is_beam_or_truss,
    is_result_carrying,
    reorder_connectivity,
    get_reorder_indices,
    clean_name,
)


def test_classification_shells():
    assert is_shell("S3")
    assert is_shell("S4")
    assert is_shell("STRI65")
    assert not is_shell("C3D8")
    assert not is_shell("T3D2")


def test_classification_solids():
    assert is_solid("C3D8")
    assert is_solid("C3D6")
    assert is_solid("C3D10")
    assert not is_solid("S3")


def test_classification_beams():
    assert is_beam_or_truss("T3D2")
    assert is_beam_or_truss("B32")
    assert not is_beam_or_truss("S3")


def test_result_carrying():
    assert is_result_carrying("S3")
    assert is_result_carrying("C3D8")
    assert not is_result_carrying("T3D2")


def test_reorder_c3d8():
    conn = [10, 20, 30, 40, 50, 60, 70, 80]
    reordered = reorder_connectivity("C3D8", conn)
    # Permutation: [0, 3, 2, 1, 4, 7, 6, 5]
    assert reordered == [10, 40, 30, 20, 50, 80, 70, 60]


def test_reorder_c3d6():
    conn = [1, 2, 3, 4, 5, 6]
    reordered = reorder_connectivity("C3D6", conn)
    # Permutation: [0, 2, 1, 3, 5, 4]
    assert reordered == [1, 3, 2, 4, 6, 5]


def test_reorder_identity_for_shells():
    conn = [1, 2, 3]
    assert reorder_connectivity("S3", conn) == [1, 2, 3]


def test_reorder_indices_identity_fallback():
    assert get_reorder_indices("S3", 3) == [0, 1, 2]


def test_clean_name():
    assert clean_name("Shell_1") == "Shell1"
    assert clean_name("My_Group_Name") == "MyGroupName"
    assert clean_name("NoUnderscore") == "NoUnderscore"
