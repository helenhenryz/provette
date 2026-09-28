"""What kind of thing a declared liquid is, from its name: the table behind carry-over severity.

Carry-over of water into a tube of drug that the water is about to dilute is harmless; the
same tip carrying sample 3 into the shared master mix ruins the plate. The contamination rules
know that something was carried; this table says what it was, so that severity can follow.

Three roles, decided from the name the protocol gives in `define_liquid` (and its description):

* **carrier**: water, buffers, saline, media, solvents, ethanol. Inert. A trace of it anywhere
  changes nothing that matters.
* **sample**: anything that is one of many and must not meet the others: samples, DNA, cDNA,
  libraries, colonies, serum, standards of a curve, compounds, plasmids.
* **reagent**: the shared active ingredients: master mix, enzymes, primers, dyes, beads,
  antibodies, substrates.

None when the name says nothing we recognise, and then severity is left as the structural rule
set it. This is deterministic and deliberately small; **the word lists are data, in
`roles.yaml` next to this file, and we own that file** (docs/rulebook.md;
docs/rule-sources.md, "Carry-over: what may be carried into what"). A word list is not
intelligence, and it is not meant to be: a name we cannot place is reported as such
(`unplaced`, below), never guessed.

A second, smaller question is the *order of addition* (ENZYME-BEFORE-DILUENT): which liquids
go into a reaction last (enzymes, polymerases, master mixes: shipped in glycerol, meant to meet
a well that is already at the right dilution) and which go in first (water, buffer: the bulk
that makes the dilution). Two more lists, `order_of` below; and two for the controls
(NO-NEGATIVE-CONTROL): the words that name a PCR mix and the reverse transcriptase.

How a list becomes a pattern: a plain entry is a whole word or phrase, matched with word
boundaries on both sides, in lower case ("te" never matches inside "template"); an entry
between slashes is a regular expression used as written. The file is read once, when this
module is imported; `reload()` reads it again (the product calls it after adding a word).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml

if TYPE_CHECKING:
    from provette.model import Trace

Role = Literal["carrier", "sample", "reagent"]
Order = Literal["last", "first"]

# The file the lists are read from. `PROVETTE_ROLES_FILE` moves it (the deployment keeps it on its
# volume, so a taught word survives a redeploy; a test teaches words to a copy); read here at
# import so every subprocess (`provette verify`, `api.worker`) sees the same file as the API.
ROLES_FILE = Path(os.environ.get("PROVETTE_ROLES_FILE") or Path(__file__).with_name("roles.yaml"))

# The lists the file must hold, in the order the file shows them.
LIST_NAMES = ("sample", "reagent", "carrier", "add_last", "add_first", "mix", "rt")

# The words a student is asked to choose between, in the order the file lists them.
PLACES = "a sample, a reagent, a carrier, an enzyme to add last, or a diluent to add first"


class RolesFileError(ValueError):
    """`roles.yaml` is not a file of the seven lists of words."""


def load_lists(path: Path | None = None) -> dict[str, list[str]]:
    """The seven lists as the file holds them: every entry a string, in file order."""
    where = path or ROLES_FILE
    loaded: Any = yaml.safe_load(where.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RolesFileError(f"{where} must hold the lists {', '.join(LIST_NAMES)}")
    lists: dict[str, list[str]] = {}
    for name in LIST_NAMES:
        entries = loaded.get(name)
        if entries is None:
            entries = []
        if not isinstance(entries, list) or not all(isinstance(e, str) for e in entries):
            raise RolesFileError(f"{where}: `{name}` must be a list of words")
        lists[name] = [entry.strip() for entry in entries if entry.strip()]
    unknown = sorted(set(loaded) - set(LIST_NAMES))
    if unknown:
        raise RolesFileError(f"{where}: unknown list(s) {', '.join(unknown)}")
    return lists


def entry_pattern(entry: str) -> str:
    """One entry of a list as a regular expression fragment.

    "master mix" becomes `\\bmaster\\ mix\\b`; "/\\bcells?\\b/" is used as written, without
    the slashes.
    """
    if len(entry) > 2 and entry.startswith("/") and entry.endswith("/"):
        return entry[1:-1]
    return r"\b" + re.escape(entry.lower()) + r"\b"


def compile_list(entries: list[str]) -> str:
    """The alternation of every entry; a list with no entry matches nothing."""
    return "|".join(entry_pattern(entry) for entry in entries) or r"(?!x)x"


_LISTS: dict[str, list[str]] = {}
_PATTERNS: dict[str, str] = {}
_SAMPLE = _REAGENT = _CARRIER = _ADD_LAST = _ADD_FIRST = _MIX = _RT = ""


def reload(path: Path | None = None) -> None:
    """Read the lists from the file (`ROLES_FILE` unless a path is given) and use them from now."""
    global _SAMPLE, _REAGENT, _CARRIER, _ADD_LAST, _ADD_FIRST, _MIX, _RT
    lists = load_lists(path)
    patterns = {name: compile_list(entries) for name, entries in lists.items()}
    for pattern in patterns.values():
        re.compile(pattern)  # a bad entry is refused before any list is replaced
    _LISTS.clear()
    _LISTS.update(lists)
    _PATTERNS.clear()
    _PATTERNS.update(patterns)
    _SAMPLE, _REAGENT, _CARRIER = patterns["sample"], patterns["reagent"], patterns["carrier"]
    _ADD_LAST, _ADD_FIRST = patterns["add_last"], patterns["add_first"]
    _MIX, _RT = patterns["mix"], patterns["rt"]


def lists() -> dict[str, list[str]]:
    """A copy of the seven lists in use, by name, every entry as the file spells it."""
    return {name: list(entries) for name, entries in _LISTS.items()}


reload()


def role_of(name: str | None, description: str | None = None) -> Role | None:
    """The role of a declared liquid, from its name first and its description second."""
    for text in (name, description):
        if not text:
            continue
        lowered = text.lower()
        if re.search(_SAMPLE, lowered):
            return "sample"
        if re.search(_REAGENT, lowered):
            return "reagent"
        if re.search(_CARRIER, lowered):
            return "carrier"
    return None


def order_of(name: str | None, description: str | None = None) -> Order | None:
    """Where in the order of addition a declared liquid belongs: "last" for an enzyme or a
    master mix, "first" for the water or buffer that makes the dilution, None otherwise.

    The name is read first and the description second, as in `role_of`. A sample is never the
    diluent: "DNA in TE buffer" is a sample, not add-first, whatever the words after it say.
    """
    for text in (name, description):
        if not text:
            continue
        lowered = text.lower()
        if re.search(_ADD_LAST, lowered):
            return "last"
        if re.search(_ADD_FIRST, lowered) and role_of(name, description) != "sample":
            return "first"
    return None


def _matches(pattern: str, name: str | None, description: str | None) -> bool:
    return any(re.search(pattern, text.lower()) for text in (name, description) if text)


def is_mix_word(name: str | None, description: str | None = None) -> bool:
    """Does the name (or the description) call this liquid a PCR or qPCR mix?

    "SYBR master mix", "Taq polymerase", "qPCR mix" and "PCR mastermix" are; "premix" and
    "loading dye" are not. Whether it is a reagent at all is `role_of`'s question.
    """
    return _matches(_MIX, name, description)


def is_rt_word(name: str | None, description: str | None = None) -> bool:
    """Does the name (or the description) say this liquid is the reverse transcriptase?

    "RT", "RTase", "reverse transcriptase" and "RT enzyme mix" are; "start" and "template" are
    not, because the words are bounded.
    """
    return _matches(_RT, name, description)


def is_placed(name: str | None, description: str | None = None) -> bool:
    """Does any of the seven lists know this liquid, by its name or its description?"""
    return any(_matches(pattern, name, description) for pattern in _PATTERNS.values())


# ---------------------------------------------------------------------------------------------
# Unplaced liquids: declared, and in no list
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Unplaced:
    """A declared liquid no list knows. The product asks the student what it is."""

    name: str
    description: str | None
    wells: tuple[str, ...]  # "A1 in slot 2", one per well it is declared in, in file order
    line: int | None  # the first load_liquid line that declares it

    @property
    def sentence(self) -> str:
        where = f" (declared at line {self.line})" if self.line is not None else ""
        return (
            f"I do not know what '{self.name}' is{where}: tell me whether it is {PLACES}, and "
            "the checks that grade by what was carried will use it."
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "wells": list(self.wells),
            "line": self.line,
            "sentence": self.sentence,
        }


def unplaced(trace: Trace) -> list[Unplaced]:
    """The declared liquids that match no list, one per name, in the order they are declared.

    `load_empty` (an empty name) is not a liquid. A name is placed when any of the seven lists
    matches it or its description; a liquid declared in several wells is one entry with every
    well.
    """
    slots = {labware.labware_id: labware.slot for labware in trace.deck.labware}
    found: dict[str, Unplaced] = {}
    for load in trace.deck.liquid_loads:
        name = load.liquid_name.strip()
        if not name or is_placed(name, load.description):
            continue
        well = f"{load.well.well} in slot {slots.get(load.well.labware_id, '?')}"
        if name in found:
            earlier = found[name]
            wells = earlier.wells if well in earlier.wells else (*earlier.wells, well)
            line = earlier.line if earlier.line is not None else load.line
            found[name] = Unplaced(name, earlier.description or load.description, wells, line)
        else:
            found[name] = Unplaced(name, load.description, (well,), load.line)
    return list(found.values())
