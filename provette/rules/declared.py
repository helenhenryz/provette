"""Declared rules: a rule written as a small YAML file, one per file, in `declared/`.

In words. A biologist who cannot program can still say what a rule is: "a tip that has been in
a sample must not go into a well holding a reagent", "a well nine tenths full must not be
mixed", "the enzyme goes in after the water". Each of those is one of three *shapes*, and a
shape with its numbers filled in is a rule. The file says the rule in the fields below; this
module reads every file in the directory when `provette.rules` is imported, checks each one,
and turns it into a `Rule` that runs beside the rules written in Python. A file with a
mistake in it stops the import with the file name and the field, so a bad rule never runs
half-way.

The fields every file has:

    id            the rule's name, capitals and dashes, and the file's name
    shape         no_carry_over | full_well_not_mixed | add_after
    title         what the finding is called, in a few words
    severity      error | warning | note
    why           one paragraph a first-year student can read: what goes wrong and why it
                  matters. The finding's explanation is the facts (the line, the wells, what
                  moved) followed by this paragraph.
    fix           what would fix it; `{line}`, `{wells}` and `{liquids}` are filled in
    sources       keys of `sources.yaml` (the rows of docs/rule-sources.md)
    proposed_by   who wrote the rule
    status        proposed | adopted
    adopted_on    the date it was adopted, or null while it is proposed
    family        optional: the rule family number; each shape has its default

The shapes and their own fields:

    no_carry_over         carried_role: sample | reagent | carrier | any
                          into_role: stock | sample_well | reagent_well | any
                          A tip carrying a liquid of the carried role enters a well of the
                          into role. The carry-over facts are CONTAM-STOCK's and CONTAM-WELL's
                          (`Facts.roots`): a tip that has been in real liquid leaves a film of
                          it in the next well it touches, and the protocol never puts that
                          liquid there on purpose.
    full_well_not_mixed   share: 0..1 of what the well holds (the rim when the labware
                          definition gives one, else the maker's stated maximum)
                          stroke_share: 0..1, the smallest mixing stroke that counts
                          A mixing stroke in a well at least that full.
    add_after             first: add_first | carrier | sample | reagent
                          last: add_last | carrier | sample | reagent
                          half_clause: true | false
                          share: optional, 0..1, default 0.5 (the half of `half_clause`)
                          A well receives a `last` liquid straight from its stock, and a
                          `first` liquid comes afterwards. With `half_clause` the rule is
                          silent when the well already held `share` of its final `first`
                          liquid, and when the `last` liquid is itself the bulk of the
                          reaction (a 2x master mix followed by the sample). `add_first` and
                          `add_last` are the word lists in `roles.py`; the roles are `role_of`.

The status rule. A rule with status `proposed` runs like any other, but every finding it
makes is a **note** titled "(proposed) ...". `provette check` exits 1 only on an error or a
warning, and the agent's `ready_to_submit` and `verify` read that exit code, so a proposed
rule can never block a submission: we see what it would say, on real drafts,
before anyone adopts it. Adopting it is changing `status` and writing `adopted_on`.

For the product's rule form: `validate(data, name)` says whether a rule is well formed and
returns it, `save(data)` writes the file, `preview(rule, protocol)` runs one rule (a file's
data or a `Rule`) on one protocol.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Literal

import yaml

from provette.model import Trace, WellKey
from provette.rules import sources as _sources
from provette.rules.common import (
    ALIKE_NOTE,
    Facts,
    facts_of,
    group_by_line,
    is_real,
    liquid,
    listing,
    natural,
    place,
    stack_key,
    times,
    well_listing,
)
from provette.rules.finding import Downstream, Finding, Severity, Source, Tier, WellRef, lower
from provette.rules.roles import Role, order_of, role_of
from provette.rules.rule import Check, Rule, Status
from provette.rules.well_capacity import Capacity
from provette.state import Arrival, Run, WellState

# The directory the rules are loaded from at import. `PROVETTE_DECLARED_DIR` moves it (the
# deployment keeps it on its volume, seeded from the files shipped here, so a rule saved from
# the form survives a redeploy); read at import so `provette check` in a subprocess loads the
# same rules as the API that saved them.
DECLARED_DIR = Path(os.environ.get("PROVETTE_DECLARED_DIR") or Path(__file__).parent / "declared")

Shape = Literal["no_carry_over", "full_well_not_mixed", "add_after"]
SHAPES: tuple[str, ...] = ("no_carry_over", "full_well_not_mixed", "add_after")
SEVERITIES: tuple[str, ...] = ("error", "warning", "note")
STATUSES: tuple[str, ...] = ("proposed", "adopted")
ROLES: tuple[str, ...] = ("sample", "reagent", "carrier", "any")
INTO: tuple[str, ...] = ("stock", "sample_well", "reagent_well", "any")
SELECTORS: tuple[str, ...] = ("add_first", "add_last", "carrier", "sample", "reagent")
FAMILY_OF_SHAPE: dict[str, int] = {"no_carry_over": 1, "full_well_not_mixed": 9, "add_after": 7}
PROPOSED_PREFIX = "(proposed) "
TOL = 1e-6  # microlitres: a 2x mix that is half the well to the last floating-point bit is half
RECEIVING_OPS = ("dispense", "blow_out")

# The registry: every source in sources.yaml, by its key (`provette.rules.sources.SOURCES`, the
# same dict, so a source added while the process runs is known here at once). A file cites
# these keys.
SOURCES: dict[str, Source] = _sources.SOURCES


class DeclaredRuleError(ValueError):
    """A declared rule file that cannot be loaded. The message names the file and the field."""


@dataclass(frozen=True)
class DeclaredRule:
    """One file, read and checked. `params` holds the shape's own fields."""

    id: str
    shape: Shape
    title: str
    severity: Severity
    why: str
    fix: str
    source_keys: tuple[str, ...]
    proposed_by: str
    status: Status
    adopted_on: dt.date | None
    family: int
    params: Mapping[str, Any]

    @property
    def sources(self) -> tuple[Source, ...]:
        return tuple(SOURCES[key] for key in self.source_keys)

    @property
    def tier(self) -> Tier:
        return "role" if _needs_roles(self.shape, self.params) else "structural"

    def to_data(self) -> dict[str, Any]:
        """The file's fields, in the order the file writes them."""
        data: dict[str, Any] = {
            "id": self.id,
            "shape": self.shape,
            "title": self.title,
            "severity": self.severity,
        }
        data.update(self.params)
        data.update(
            {
                "why": self.why,
                "fix": self.fix,
                "sources": list(self.source_keys),
                "proposed_by": self.proposed_by,
                "status": self.status,
                "adopted_on": self.adopted_on,
            }
        )
        if self.family != FAMILY_OF_SHAPE[self.shape]:
            data["family"] = self.family
        return data


# -- validation: a JSON-schema-like check in plain Python ------------------------------------

Checker = Callable[[Any], str | None]  # None when the value is fine, else what is wrong


def _text(value: Any) -> str | None:
    return None if isinstance(value, str) and value.strip() else "must be a non-empty string"


def _choice(*allowed: str) -> Checker:
    def check(value: Any) -> str | None:
        return None if value in allowed else f"must be one of {', '.join(allowed)}"

    return check


def _share(value: Any) -> str | None:
    ok = isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1
    return None if ok else "must be a number between 0 and 1"


def _flag(value: Any) -> str | None:
    return None if isinstance(value, bool) else "must be true or false"


def _family(value: Any) -> str | None:
    ok = isinstance(value, int) and not isinstance(value, bool) and value > 0
    return None if ok else "must be a whole number above 0"


def _rule_id(value: Any) -> str | None:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z0-9]+(-[A-Z0-9]+)*", value):
        return "must be capitals, digits and dashes, like NO-SAMPLE-INTO-REAGENT-WELL"
    return None


def _source_keys(value: Any) -> str | None:
    if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
        return "must be a list of at least one source name; a rule without a source does not load"
    unknown = [key for key in value if key not in SOURCES]
    if unknown:
        return f"{', '.join(unknown)}: not a name in provette/rules/sources.yaml"
    return None


def _date_or_null(value: Any) -> str | None:
    if value is None or isinstance(value, dt.date):
        return None
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            dt.date.fromisoformat(value)
        except ValueError:
            return "must be a real date, YYYY-MM-DD, or null"
        return None
    return "must be a date, YYYY-MM-DD, or null"


COMMON_FIELDS: dict[str, tuple[Checker, bool]] = {  # name -> (checker, required)
    "id": (_rule_id, True),
    "shape": (_choice(*SHAPES), True),
    "title": (_text, True),
    "severity": (_choice(*SEVERITIES), True),
    "why": (_text, True),
    "fix": (_text, True),
    "sources": (_source_keys, True),
    "proposed_by": (_text, True),
    "status": (_choice(*STATUSES), True),
    "adopted_on": (_date_or_null, True),
    "family": (_family, False),
}
SHAPE_FIELDS: dict[str, dict[str, tuple[Checker, bool]]] = {
    "no_carry_over": {"carried_role": (_choice(*ROLES), True), "into_role": (_choice(*INTO), True)},
    "full_well_not_mixed": {"share": (_share, True), "stroke_share": (_share, True)},
    "add_after": {
        "first": (_choice(*SELECTORS), True),
        "last": (_choice(*SELECTORS), True),
        "half_clause": (_flag, True),
        "share": (_share, False),
    },
}
SHAPE_DEFAULTS: dict[str, dict[str, Any]] = {"add_after": {"share": 0.5}}


def validate(data: Mapping[str, Any], name: str = "<rule>") -> DeclaredRule:
    """Check a rule's fields and return it; `DeclaredRuleError` names the file and the field."""

    def fail(field: str, what: str) -> DeclaredRuleError:
        return DeclaredRuleError(f"{name}: field '{field}': {what}")

    if not isinstance(data, Mapping):
        raise DeclaredRuleError(f"{name}: the file must be a mapping of fields, not a list")
    for field, (checker, required) in COMMON_FIELDS.items():
        if field not in data:
            if required:
                raise fail(field, "missing")
            continue
        problem = checker(data[field])
        if problem:
            raise fail(field, problem)
    shape = data["shape"]
    own = SHAPE_FIELDS[shape]
    params: dict[str, Any] = dict(SHAPE_DEFAULTS.get(shape, {}))
    for field, (checker, required) in own.items():
        if field not in data:
            if required:
                raise fail(field, f"missing (a {shape} rule needs it)")
            continue
        problem = checker(data[field])
        if problem:
            raise fail(field, problem)
        params[field] = data[field]
    for field in data:
        if field not in COMMON_FIELDS and field not in own:
            raise fail(field, f"not a field of a {shape} rule")
    if shape == "add_after" and data["first"] == data["last"]:
        raise fail("last", "must differ from 'first'")
    adopted_on = data["adopted_on"]
    if isinstance(adopted_on, str):
        adopted_on = dt.date.fromisoformat(adopted_on)
    if data["status"] == "adopted" and adopted_on is None:
        raise fail("adopted_on", "an adopted rule says when it was adopted")
    if data["status"] == "proposed" and adopted_on is not None:
        raise fail("adopted_on", "a proposed rule has no adoption date yet: write null")
    return DeclaredRule(
        id=data["id"],
        shape=shape,
        title=data["title"].strip(),
        severity=data["severity"],
        why=" ".join(data["why"].split()),
        fix=" ".join(data["fix"].split()),
        source_keys=tuple(data["sources"]),
        proposed_by=data["proposed_by"].strip(),
        status=data["status"],
        adopted_on=adopted_on,
        family=data.get("family", FAMILY_OF_SHAPE[shape]),
        params=params,
    )


def load_file(path: Path) -> DeclaredRule:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise DeclaredRuleError(f"{path.name}: not valid YAML: {error}") from error
    rule = validate(data, path.name)
    if rule.id != path.stem:
        raise DeclaredRuleError(f"{path.name}: field 'id': must be the file's name, {path.stem}")
    return rule


def load_rules(directory: Path = DECLARED_DIR, taken: Iterable[str] = ()) -> list[Rule]:
    """Every `*.yaml` in the directory as a `Rule`, in file-name order. A bad file raises."""
    seen = set(taken)
    rules = []
    for path in sorted(directory.glob("*.yaml")):
        declared = load_file(path)
        if declared.id in seen:
            raise DeclaredRuleError(f"{path.name}: field 'id': {declared.id} is already a rule")
        seen.add(declared.id)
        rules.append(build(declared))
    return rules


def save(data: Mapping[str, Any], directory: Path = DECLARED_DIR) -> Path:
    """Validate a rule and write it as `<id>.yaml` in the directory; the path is returned."""
    rule = validate(data, f"{data.get('id', '<rule>')}.yaml")
    path = directory / f"{rule.id}.yaml"
    path.write_text(
        yaml.safe_dump(rule.to_data(), sort_keys=False, allow_unicode=True, width=96),
        encoding="utf-8",
    )
    return path


def preview(
    rule: Rule | Mapping[str, Any], protocol: Path, labware_dirs: Sequence[Path] = ()
) -> list[Finding]:
    """Run one rule (a `Rule`, or a file's data not yet saved) on one protocol.

    Raises `provette.trace.TraceError` if the simulator rejects the protocol.
    """
    from provette.rules.finding import fingerprint
    from provette.state import replay
    from provette.trace import trace_protocol

    if not isinstance(rule, Rule):
        rule = build(validate(rule, "<preview>"))
    trace = trace_protocol(protocol, labware_dirs=labware_dirs)
    run = replay(trace)
    lines = tuple(protocol.read_text(encoding="utf-8", errors="replace").splitlines())
    return [replace(f, fingerprint=fingerprint(f, lines)) for f in rule.check(trace, run)]


# -- building a Rule ----------------------------------------------------------------------------


def build(declared: DeclaredRule) -> Rule:
    """The `Rule` a file describes: the shape's check, guarded by the status rule."""
    builders: dict[str, Callable[[DeclaredRule], Check]] = {
        "no_carry_over": _no_carry_over,
        "full_well_not_mixed": _full_well_not_mixed,
        "add_after": _add_after,
    }
    inner = builders[declared.shape](declared)

    def check(trace: Trace, run: Run) -> list[Finding]:
        found = inner(trace, run)
        if declared.status == "proposed":
            found = [replace(f, severity="note", title=PROPOSED_PREFIX + f.title) for f in found]
        return found

    return Rule(
        rule_id=declared.id,
        family=declared.family,
        tier=declared.tier,
        title=declared.title,
        description=describe(declared),
        sources=declared.sources,
        check=check,
        status=declared.status,
        proposed_by=declared.proposed_by,
    )


ROLE_WORDS: dict[str, str] = {
    "sample": "a sample",
    "reagent": "a reagent",
    "carrier": "a carrier (water, buffer, medium)",
    "any": "any liquid",
    "add_first": "water or buffer",
    "add_last": "an enzyme, polymerase or master mix",
}
INTO_WORDS: dict[str, str] = {
    "stock": "a stock (a well that held liquid from the start and that the protocol draws from)",
    "sample_well": "a well holding a sample",
    "reagent_well": "a well holding a reagent",
    "any": "any well",
}


def describe(declared: DeclaredRule) -> str:
    """The rule in one plain sentence, for the README table and `--json`."""
    p = declared.params
    severity = declared.severity.capitalize()
    if declared.shape == "no_carry_over":
        words = (
            f"A tip that has been in {ROLE_WORDS[p['carried_role']]} touches the liquid of "
            f"{INTO_WORDS[p['into_role']]} into which the protocol never transfers that liquid "
            f"on purpose. {severity}."
        )
    elif declared.shape == "full_well_not_mixed":
        words = (
            f"A mixing stroke of at least {p['stroke_share']:.0%} of the well, in a well "
            f"{p['share']:.0%} full or more (of the rim when the labware definition gives one, "
            f"else of the maker's stated maximum). {severity}. Waste, trash and sinks are exempt."
        )
    else:
        half = (
            f", when the well held less than {p['share']:.0%} of its final "
            f"{ROLE_WORDS[p['first']]} at the time"
            if p["half_clause"]
            else ""
        )
        words = (
            f"A well receives {ROLE_WORDS[p['last']]} straight from its stock, and "
            f"{ROLE_WORDS[p['first']]} comes afterwards{half}. {severity}. Silent when no "
            "liquids are declared"
            + (
                ", when the liquid arrives inside a mix made in another tube, or when the mix "
                "is itself the bulk of the reaction."
                if p["half_clause"]
                else " or when the liquid arrives inside a mix made in another tube."
            )
        )
    if declared.status == "proposed":
        words += f" Proposed by {declared.proposed_by}: reported as a note until adopted."
    return words


class _Words(dict[str, str]):
    """`str.format_map` with the placeholders a fix may use; an unknown one is left as typed."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _fill(text: str, **words: str) -> str:
    return text.format_map(_Words(words))


def _needs_roles(shape: str, params: Mapping[str, Any]) -> bool:
    if shape == "no_carry_over":
        by_contents = params["into_role"] in ("sample_well", "reagent_well")
        return bool(params["carried_role"] != "any" or by_contents)
    return shape == "add_after"


def _selects(selector: str, name: str | None, description: str | None) -> bool:
    """Does a declared liquid belong to the word list or role the selector names?"""
    if selector == "add_first":
        return order_of(name, description) == "first"
    if selector == "add_last":
        return order_of(name, description) == "last"
    return role_of(name, description) == selector


def _atoms_selected(run: Run, selector: str) -> set[WellKey]:
    return {
        atom
        for atom, origin in run.origins.items()
        if origin.loads
        and _selects(selector, origin.loads[0].liquid_name, origin.loads[0].description)
    }


def _finding(
    declared: DeclaredRule,
    facts: Facts,
    *,
    severity: Severity,
    certain: bool,
    roles_basis: Literal["none", "declared", "inferred"],
    title: str,
    explanation: str,
    root_index: int,
    indices: Iterable[int],
    wells: tuple[WellRef, ...],
    liquids: str,
    downstream: tuple[WellRef, ...] = (),
) -> Finding:
    root = facts.event(root_index)
    return Finding(
        rule_id=declared.id,
        family=declared.family,
        tier=declared.tier,
        severity=severity,
        certain=certain,
        roles_basis=roles_basis,
        title=title,
        explanation=explanation,
        fix=_fill(declared.fix, line=str(root.line), wells=well_listing(wells), liquids=liquids),
        line=root.line,
        stack=tuple(root.stack),
        occurrences=facts.occurrences(indices),
        wells=wells,
        downstream=Downstream(len(downstream), downstream),
        sources=declared.sources,
    )


# -- shape: no_carry_over ---------------------------------------------------------------------


def _roles_held(facts: Facts, well: WellKey, event_index: int) -> set[Role]:
    """The roles of the real liquids a well holds just before an event."""
    state = facts.run.well_before(well, event_index)
    held: set[Role] = set()
    for atom, presence in state.atoms.items():
        role = facts.role(atom) if is_real(presence) else None
        if role is not None:
            held.add(role)
    return held


def _no_carry_over(declared: DeclaredRule) -> Check:
    carried_role: str = declared.params["carried_role"]
    into_role: str = declared.params["into_role"]

    def carried_ok(facts: Facts, arrival: Arrival) -> bool:
        return carried_role == "any" or facts.role(arrival.atom) == carried_role

    def into_ok(facts: Facts, arrival: Arrival) -> bool:
        if into_role == "any":
            return True
        if into_role == "stock":
            return facts.is_stock(arrival.well)
        wanted: Role = "sample" if into_role == "sample_well" else "reagent"
        return wanted in _roles_held(facts, arrival.well, arrival.event_index)

    def check(trace: Trace, run: Run) -> list[Finding]:
        facts = facts_of(trace, run)
        if declared.tier == "role" and not any(o.kind == "declared" for o in run.origins.values()):
            return []  # nothing declared: the names cannot say what is a sample or a reagent
        roots = [
            a
            for a in facts.roots
            if a.atom != a.well
            and not facts.deliberate(a.well, a.atom)
            and carried_ok(facts, a)
            and into_ok(facts, a)
        ]
        findings = []
        for group in group_by_line(facts, roots):
            first = facts.event(group[0].event_index)
            wells = facts.refs(a.well for a in group)
            carried = facts.refs(a.atom for a in group)
            touched = {a.well for a in group}
            reached = facts.refs(w for w in facts.consequences(group) if w not in touched)
            certain = any(a.certain for a in group)
            roles_known = any(facts.role(a.atom) is not None for a in group)
            severity: Severity = declared.severity
            if not certain:
                severity = lower(severity)
            alike = all(facts.treated_alike(a) for a in group)
            if alike:
                severity = "note"
            count = len({a.event_index for a in group})
            liquids = listing([liquid(c) for c in carried])
            explanation = (
                f"At line {first.line} the tip touched the liquid in {well_listing(wells)} while "
                f"it still carried {liquids} from an earlier step"
                f"{'' if count == 1 else f' (this line did it {times(count)})'}. "
                "A tip that has touched one liquid leaves a little of it in the next liquid it "
                "touches, and the protocol never transfers that liquid into "
                f"{'this well' if len(wells) == 1 else 'these wells'} on purpose. {declared.why}"
            )
            if reached:
                explanation += (
                    f" Liquid was later taken out of the affected wells, and the unwanted "
                    f"material went along into {len(reached)} other "
                    f"well{'s' if len(reached) > 1 else ''}: {well_listing(reached)}."
                )
            if alike:
                explanation += ALIKE_NOTE
            if not certain:
                explanation += (
                    " Provette could not tell for sure that the tip touched the liquid here "
                    "(it does not know how full the well was), so this is reported one level "
                    "lower."
                )
            findings.append(
                _finding(
                    declared,
                    facts,
                    severity=severity,
                    certain=certain,
                    roles_basis="inferred" if roles_known else "none",
                    title=declared.title,
                    explanation=explanation,
                    root_index=group[0].event_index,
                    indices=(a.event_index for a in group),
                    wells=wells,
                    liquids=liquids,
                    downstream=reached,
                )
            )
        return findings

    return check


# -- shape: full_well_not_mixed ----------------------------------------------------------------


def _full_well_not_mixed(declared: DeclaredRule) -> Check:
    share, stroke_share = declared.params["share"], declared.params["stroke_share"]

    def check(trace: Trace, run: Run) -> list[Finding]:
        facts = facts_of(trace, run)
        capacity = Capacity(facts)
        seen: set[WellKey] = set()
        groups: dict[tuple[str, ...], list[tuple[int, WellKey, float, float]]] = {}
        for move in facts.moves:
            if (
                move not in facts.strokes
                or move.is_aspirate
                or move.well in seen
                or capacity.exempt(move.well)
            ):
                continue
            limit = capacity.holds(move.well)
            if limit is None or move.liquid_ul < stroke_share * limit:
                continue
            volume = run.well_before(move.well, move.event_index + 1).volume_ul
            if volume is None or volume < share * limit:
                continue
            seen.add(move.well)
            groups.setdefault(stack_key(facts.event(move.event_index)), []).append(
                (move.event_index, move.well, volume, limit)
            )
        findings = []
        for mixed in groups.values():
            first_index, _, volume, limit = mixed[0]
            first = facts.event(first_index)
            wells = facts.refs(w for _, w, _, _ in mixed)
            explanation = (
                f"At line {first.line} the tip mixes {well_listing(wells)} holding {volume:g} ul "
                f"of the {limit:g} ul the well can take"
                f"{'' if len(mixed) == 1 else f' (this line did it {times(len(mixed))})'}. "
                f"{declared.why}"
            )
            findings.append(
                _finding(
                    declared,
                    facts,
                    severity=declared.severity,
                    certain=True,
                    roles_basis="none",
                    title=declared.title,
                    explanation=explanation,
                    root_index=first_index,
                    indices=(i for i, _, _, _ in mixed),
                    wells=wells,
                    liquids="the liquid in the well",
                )
            )
        return findings

    return check


# -- shape: add_after (ENZYME-BEFORE-DILUENT's shape) -----------------------------------------


@dataclass(frozen=True)
class _Early:
    """One well that got its `last` liquid too soon."""

    event_index: int  # the dispense of the `last` liquid
    well: WellKey
    late: WellKey  # the stock it came from
    held_ul: float  # what the well held at that moment
    first_ul: float  # ... of which `first` liquid
    held: tuple[WellKey, ...]  # the `first` stocks whose liquid was already there
    final_first_ul: float  # the `first` liquid the well ends up with
    came: tuple[WellKey, ...]  # the `first` stocks whose liquid came afterwards
    came_event: int  # the first dispense that brought one


def _add_after(declared: DeclaredRule) -> Check:
    p = declared.params
    first_sel, last_sel, half_clause, share = p["first"], p["last"], p["half_clause"], p["share"]
    first_word = ROLE_WORDS[first_sel]

    def check(trace: Trace, run: Run) -> list[Finding]:
        facts = facts_of(trace, run)
        if not any(origin.kind == "declared" for origin in run.origins.values()):
            return []  # nothing declared: the names cannot say what goes in first or last
        last_atoms = _atoms_selected(run, last_sel)
        first_atoms = _atoms_selected(run, first_sel)
        if not last_atoms or not first_atoms:
            return []
        groups: dict[tuple[str, ...], list[_Early]] = {}
        for step in run.steps:
            if step.op not in RECEIVING_OPS:
                continue
            for arrival in step.arrivals:
                if (
                    arrival.mode != "bulk"
                    or arrival.atom not in last_atoms
                    or arrival.source_well != arrival.atom  # came out of a mix, not the stock
                    or (arrival.volume_ul is not None and arrival.volume_ul <= 0)  # a trace
                ):
                    continue
                early = _early(facts, arrival, first_atoms, half_clause, share)
                if early is not None:
                    groups.setdefault(stack_key(facts.event(early.event_index)), []).append(early)

        findings = []
        for group in groups.values():
            first = group[0]
            root = facts.event(first.event_index)
            wells = facts.refs(e.well for e in group)
            late = listing(sorted({facts.liquid_name(e.late) or "the liquid" for e in group}))
            came = listing(
                sorted({facts.liquid_name(d) or first_word for e in group for d in e.came})
            )
            count = len({e.event_index for e in group})
            example = facts.ref(first.well)
            already = listing(sorted({facts.liquid_name(a) or first_word for a in first.held}))
            if first.held_ul <= 0:
                held = "was dry"
            elif first.first_ul >= first.held_ul - TOL:
                held = f"held only {first.held_ul:g} ul, all of it neat {already}"
            else:
                held = f"held {first.held_ul:g} ul, only {first.first_ul:g} ul of it {first_word}"
            explanation = (
                f"At line {root.line} the robot put {late} into {well_listing(wells)}"
                f"{'' if count == 1 else f' (this line did it {times(count)})'}. "
                f"Take {place(example)}: at that moment it {held}, and the {came} came "
                f"afterwards, at line {facts.event(first.came_event).line}, to make the "
                f"{first.final_first_ul:g} ul of {first_word} the reaction is built on. "
                f"{declared.why}"
            )
            findings.append(
                _finding(
                    declared,
                    facts,
                    severity=declared.severity,
                    certain=True,
                    roles_basis="declared",
                    title=f"{declared.title}: {late}",
                    explanation=explanation,
                    root_index=first.event_index,
                    indices=(e.event_index for e in group),
                    wells=wells,
                    liquids=late,
                )
            )
        return findings

    return check


def _early(
    facts: Facts, arrival: Arrival, first_atoms: set[WellKey], half_clause: bool, share: float
) -> _Early | None:
    """Did this `last` liquid go into its well before the `first` liquid? None if not, or if
    the volumes needed to say so are unknown."""
    run = facts.run
    well, i = arrival.well, arrival.event_index
    final = _built(facts, well, i)
    before = run.well_before(well, i)
    if final.volume_ul is None or before.volume_ul is None:
        return None
    final_first = _amount(final, first_atoms)
    first_before = _amount(before, first_atoms)
    if final_first is None or first_before is None:
        return None
    if half_clause:
        if first_before >= share * final_first - TOL:
            return None  # the water was there first (or there is no water at all)
        late_final = _one(final, arrival.atom)
        if late_final is None or late_final >= share * final.volume_ul - TOL:
            return None  # a master mix that is the bulk of the reaction is the diluent, not this
    came = tuple(
        atom
        for atom in sorted(first_atoms, key=natural)
        if (_one(final, atom) or 0.0) - (_one(before, atom) or 0.0) > TOL
    )
    held = tuple(a for a in sorted(first_atoms, key=natural) if (_one(before, a) or 0.0) > TOL)
    later = _first_dispense_of(facts, well, i, first_atoms)
    if not came or later is None:
        return None
    return _Early(
        i, well, arrival.atom, before.volume_ul, first_before, held, final_first, came, later
    )


def _built(facts: Facts, well: WellKey, after: int) -> WellState:
    """The well as it was built up: just before the first draw out of it after `after`, or at
    the end of the run if nothing is drawn. A master mix tube is nearly empty when the run ends;
    what it held when the mix was complete is what the enzyme was diluted into."""
    draws = [index for index in facts.draws.get(well, []) if index > after]
    return facts.run.well_before(well, draws[0]) if draws else facts.run.wells[well]


def _one(state: WellState, atom: WellKey) -> float | None:
    presence = state.atoms.get(atom)
    return presence.volume_ul if presence is not None and is_real(presence) else 0.0


def _amount(state: WellState, atoms: set[WellKey]) -> float | None:
    """How much of these stocks' liquid the well holds; None if any amount is unknown."""
    total = 0.0
    for atom in atoms:
        amount = _one(state, atom)
        if amount is None:
            return None
        total += amount
    return total


def _first_dispense_of(facts: Facts, well: WellKey, after: int, atoms: set[WellKey]) -> int | None:
    """The first dispense into `well` after event `after` that brought liquid of these stocks."""
    for move in facts.moves:
        if move.is_aspirate or move.well != well or move.event_index <= after:
            continue
        was = facts.run.well_before(well, move.event_index)
        now = facts.run.well_before(well, move.event_index + 1)
        for atom in atoms:
            had, has = _one(was, atom), _one(now, atom)
            if has is None or (had is not None and has - had > 1e-9):
                return move.event_index
    return None
