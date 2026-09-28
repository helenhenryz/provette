"""The arithmetic of a protocol, done by code and never by the model.

Three calculations a scientist does on paper before writing a protocol, each pure and typed so
it can be tested and handed to a model as a tool:

* `dilution_series`: what to put in each well of a serial dilution, and what it then holds;
* `normalise`: how much of each sample and of diluent brings every sample to one concentration;
* `master_mix`: how much of each component to pool for so many reactions, with overage.

The plate maps in `eval/platemaps/build.py` are written from these same functions, so the
model's arithmetic and the check's expectations come from one place.
"""

from __future__ import annotations

from provette.calc.dilution import DilutionPoint, dilution_series
from provette.calc.master_mix import MasterMix, master_mix
from provette.calc.normalise import Normalised, normalise

__all__ = [
    "DilutionPoint",
    "MasterMix",
    "Normalised",
    "dilution_series",
    "master_mix",
    "normalise",
]
