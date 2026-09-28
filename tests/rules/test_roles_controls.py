"""The mix and RT word lists behind NO-NEGATIVE-CONTROL: bounded words, name then description."""

from __future__ import annotations

import pytest

from provette.rules.roles import is_mix_word, is_rt_word, role_of


@pytest.mark.parametrize(
    "name",
    ["SYBR master mix", "PCR mastermix", "qPCR mix", "Taq polymerase", "pcr mix", "2x Taq"],
)
def test_mix_words_name_the_reaction_mix(name: str) -> None:
    assert is_mix_word(name)
    assert role_of(name) == "reagent"


@pytest.mark.parametrize("name", ["premix", "water", "cDNA sample 1", "loading dye", "primer"])
def test_mix_words_are_bounded(name: str) -> None:
    assert not is_mix_word(name)


def test_mix_word_in_the_description_counts() -> None:
    assert is_mix_word("reagent A", "qPCR master mix with ROX")
    assert not is_mix_word("reagent A", "the dye")
    assert not is_mix_word(None, None)


@pytest.mark.parametrize(
    "name", ["RT", "RTase", "reverse transcriptase", "Reverse Transcription mix", "RT-qPCR mix"]
)
def test_rt_words_name_the_reverse_transcriptase(name: str) -> None:
    assert is_rt_word(name)


@pytest.mark.parametrize("name", ["start buffer", "template", "cDNA sample 1", "SYBR master mix"])
def test_rt_words_are_bounded(name: str) -> None:
    assert not is_rt_word(name)


def test_rt_word_in_the_description_counts() -> None:
    assert is_rt_word("enzyme", "the RT for the first strand")
    assert not is_rt_word("enzyme", "restriction enzyme")
