"""The word lists over a declared liquid's name: what it is, and where in the order it goes."""

from __future__ import annotations

import pytest

from provette.rules.roles import order_of, role_of


@pytest.mark.parametrize(
    ("name", "description", "role"),
    [
        ("nuclease-free water", None, "carrier"),
        ("10x buffer", "10x restriction buffer", "carrier"),
        ("BsaI enzyme", None, "reagent"),
        ("Q5 polymerase", None, "reagent"),
        ("plasmid 3", None, "sample"),
        ("DNA in TE buffer", None, "sample"),
        ("liquid A", None, None),
        ("A", "PCR master mix", "reagent"),
    ],
)
def test_role_of(name: str, description: str | None, role: str | None) -> None:
    assert role_of(name, description) == role


@pytest.mark.parametrize(
    ("name", "description", "order"),
    [
        ("BsaI enzyme", "restriction enzyme in 50% glycerol", "last"),
        ("Q5 polymerase", None, "last"),
        ("Taq", None, "last"),
        ("T4 DNA ligase", None, "last"),  # a sample word in the name does not stop add-last
        ("EcoRI", "restriction endonuclease", "last"),
        ("RT", "reverse transcriptase", "last"),
        ("reverse transcription mix", None, "last"),
        ("PCR master mix", None, "last"),
        ("mastermix", None, "last"),
        ("nuclease-free water", None, "first"),
        ("H2O", None, "first"),
        ("10x buffer", "10x restriction buffer", "first"),
        ("diluent", None, "first"),
        ("TE", None, "first"),
        ("Tris", "10 mM Tris pH 8", "first"),
        ("growth medium", None, "first"),
        ("enzyme", "in storage buffer", "last"),  # the name is read first
        ("liquid A", "restriction enzyme", "last"),  # then the description
        ("DNA in TE buffer", None, None),  # a sample is never the diluent
        ("template", None, None),  # "te" does not match inside "template"
        ("start mix", None, None),  # "mix" alone is not add-last, and "rt" is not in "start"
        ("starter culture", None, None),
        ("forward primer", None, None),
        ("plasmid 3", None, None),
        (None, None, None),
    ],
)
def test_order_of(name: str | None, description: str | None, order: str | None) -> None:
    assert order_of(name, description) == order
