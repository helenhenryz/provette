"""The replay's working records: wells and tips it can change in place, and how they are frozen.

The public `WellState` and `TipState` are frozen values. The replay works on the records here and
freezes a well after every event that changed it, and the tips at the end.

Why it is built this way. On a deck where one set of tips works through six plates of 384
samples, every tip and well ends up carrying all 2,300 of them, nearly all as traces, and the
run has millions of arrivals. Three things made that take minutes and gigabytes, and each has
its answer here:

* Touching every atom on every action. Each record keeps, beside its atoms, the sets the replay
  asks questions of (which atoms are certain, which are bulk, which have a volume), and a
  version number per set that changes when the set does, so that "is this set inside that one?"
  is answered once per pair of versions (`_Replay._within`). An action that brings nothing new
  then costs a few lookups, however many atoms there are.
* Hashing `WellKey`, a Python-level hash, hundreds of millions of times. Atoms are numbered, and
  the records work on the numbers; `names` turns a number back into the `WellKey`.
* Copying a well's atoms for the history after every event. A well instead keeps a log of every
  change to its atoms, and a frozen `WellState` holds a position in that log (`AtomsView`). The
  atoms as they were are rebuilt from the log when someone looks.
"""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import Iterator, Mapping
from typing import Literal

from provette.model import WellKey
from provette.state.types import Layer, Presence, Residue, TipState, WellState

Amounts = dict[int, "float | None"]  # atom number -> volume

versions = itertools.count(1)


class Names:
    """Atom numbers. Shared by everything in one replay."""

    def __init__(self) -> None:
        self.keys: list[WellKey] = []
        self.numbers: dict[WellKey, int] = {}
        self.looked_at: deque[AtomsView] = deque(maxlen=256)

    def number(self, key: WellKey) -> int:
        number = self.numbers.get(key)
        if number is None:
            number = self.numbers[key] = len(self.keys)
            self.keys.append(key)
        return number


class AtomsView(Mapping[WellKey, Presence]):
    """The atoms of a well as they were when its log was `cut` entries long.

    Behaves as the `dict[WellKey, Presence]` it stands for, in the order the atoms arrived. The
    dict is built when first asked for; only the 256 views looked at most recently keep theirs.
    """

    __slots__ = ("_log", "_names", "_cut", "_built")

    def __init__(self, log: tuple[list[int], list[Presence]], names: Names, cut: int) -> None:
        self._log = log  # only the log: the rest of the working record goes when the replay ends
        self._names = names
        self._cut = cut
        self._built: dict[WellKey, Presence] | None = None

    def _atoms(self) -> dict[WellKey, Presence]:
        if self._built is None:
            atoms, presences = self._log
            keys = self._names.keys
            # A later entry for the same atom replaces the value and keeps the place.
            latest = dict(zip(atoms[: self._cut], presences[: self._cut], strict=True))
            self._built = {keys[number]: presence for number, presence in latest.items()}
            looked_at = self._names.looked_at
            if len(looked_at) == looked_at.maxlen:
                looked_at[0]._built = None
            looked_at.append(self)
        return self._built

    def __getitem__(self, key: WellKey) -> Presence:
        return self._atoms()[key]

    def __iter__(self) -> Iterator[WellKey]:
        return iter(self._atoms())

    def __len__(self) -> int:
        return len(self._atoms())

    def __contains__(self, key: object) -> bool:
        return key in self._atoms()

    def __repr__(self) -> str:
        return repr(self._atoms())


class Well:
    __slots__ = (
        "key", "names", "volume", "min_volume", "received", "atoms", "place", "sure", "bulk",
        "bulk_sure", "sized", "v_all", "v_sure", "v_bulk_sure", "dirty", "lowest",
        "log_atoms", "log_presences", "grew", "_zeros", "_zeros_v", "_sources", "_sources_v",
    )  # fmt: skip

    def __init__(self, key: WellKey, names: Names, volume: float | None, min_volume: float) -> None:
        self.key = key
        self.names = names
        self.volume = volume
        self.min_volume = min_volume
        self.received = False
        self.atoms: dict[int, Presence] = {}
        self.place: dict[int, int] = {}  # atom -> its place in the order of arrival
        self.sure: set[int] = set()  # atoms whose presence is certain
        self.bulk: set[int] = set()
        self.bulk_sure: set[int] = set()
        self.sized: set[int] = set()  # atoms whose volume is not exactly 0.0
        self.v_all = self.v_sure = self.v_bulk_sure = next(versions)
        self.dirty = False
        self.lowest = min_volume
        self.grew = 0  # which sets `put_new` has added to since `renumber`
        self.log_atoms: list[int] = []
        self.log_presences: list[Presence] = []
        self._zeros: Amounts = {}
        self._zeros_v = 0
        self._sources: dict[int, WellKey] = {}
        self._sources_v = 0

    def put(self, atom: int, presence: Presence) -> None:
        if atom not in self.atoms:
            self.place[atom] = len(self.place)
            self.v_all = next(versions)
        self.atoms[atom] = presence
        self.log_atoms.append(atom)
        self.log_presences.append(presence)
        if presence.certain and atom not in self.sure:
            self.sure.add(atom)
            self.v_sure = next(versions)
        if presence.mode == "bulk":
            self.bulk.add(atom)
            if presence.certain and atom not in self.bulk_sure:
                self.bulk_sure.add(atom)
                self.v_bulk_sure = next(versions)
        if presence.volume_ul != 0:
            self.sized.add(atom)
        else:
            self.sized.discard(atom)
        self.dirty = True

    def put_new(self, atom: int, presence: Presence) -> None:
        """`put`, for an atom the well does not hold yet, without the version numbers: the caller
        adds many at once and then calls `renumber`."""
        self.place[atom] = len(self.place)
        self.atoms[atom] = presence
        self.log_atoms.append(atom)
        self.log_presences.append(presence)
        self.grew |= 1
        if presence.certain:
            self.sure.add(atom)
            self.grew |= 2
        if presence.mode == "bulk":
            self.bulk.add(atom)
            if presence.certain:
                self.bulk_sure.add(atom)
                self.grew |= 4
        if presence.volume_ul != 0:
            self.sized.add(atom)

    def renumber(self) -> None:
        """New version numbers for the sets that `put_new` has added to."""
        if self.grew & 1:
            self.v_all = next(versions)
            self.dirty = True
        if self.grew & 2:
            self.v_sure = next(versions)
        if self.grew & 4:
            self.v_bulk_sure = next(versions)
        self.grew = 0

    def zeros(self) -> Amounts:
        """Every atom of the well at volume 0.0, in the well's order. A fresh copy."""
        if self._zeros_v != self.v_all:
            self._zeros = dict.fromkeys(self.atoms, 0.0)
            self._zeros_v = self.v_all
        return self._zeros.copy()

    def sure_sources(self) -> dict[int, WellKey]:
        """certain atom -> this well. Shared: not to be changed."""
        if self._sources_v != self.v_sure:
            self._sources = dict.fromkeys(self.sure, self.key)
            self._sources_v = self.v_sure
        return self._sources

    def frozen(self) -> WellState:
        log = (self.log_atoms, self.log_presences)
        view = AtomsView(log, self.names, len(self.log_atoms))
        return WellState(self.key, self.volume, self.min_volume, view, self.received)


class TipLayer:
    __slots__ = ("volume", "atoms", "sized", "v_keys", "place")

    def __init__(
        self,
        volume: float,
        atoms: Amounts | None,
        sized: set[int],
        v_keys: int,
        place: dict[int, int] | None,
    ) -> None:
        self.volume = volume
        self.atoms = atoms  # None is air
        self.sized = sized  # the atoms whose amount may be other than 0.0
        self.v_keys = v_keys  # the version of the set of atoms
        self.place = place  # the order of the atoms, when it is that of the well they came from


class Tip:
    __slots__ = (
        "key", "status", "layers", "source", "since", "place", "sure", "v_all", "v_sure",
        "picked_up",
    )  # fmt: skip

    def __init__(self, key: WellKey, picked_up: int) -> None:
        self.key = key
        self.status: Literal["in_use", "parked", "dropped"] = "in_use"
        self.layers: list[TipLayer] = []
        self.source: dict[int, WellKey] = {}  # the residue, in the order met: atom -> source well
        self.since: dict[int, int] = {}
        self.place: dict[int, int] = {}
        self.sure: set[int] = set()
        self.v_all = self.v_sure = next(versions)
        self.picked_up = picked_up

    def held(self) -> tuple[float, float]:
        liquid = sum(layer.volume for layer in self.layers if layer.atoms is not None)
        air = sum(layer.volume for layer in self.layers if layer.atoms is None)
        return liquid, air

    def frozen(self, names: Names) -> TipState:
        keys = names.keys
        layers = tuple(
            Layer(
                layer.volume,
                None if layer.atoms is None else {keys[a]: v for a, v in layer.atoms.items()},
            )
            for layer in self.layers
        )
        residue = {
            keys[atom]: Residue(well, self.since[atom], atom in self.sure)
            for atom, well in self.source.items()
        }
        return TipState(self.key, self.status, layers, residue, self.picked_up)
