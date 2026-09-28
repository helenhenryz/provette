"""Plant one bug in a protocol with a small, generic change to its syntax tree.

    from mutate import mutants
    for m in mutants(source): m.operator, m.description, m.source

Five operators, none of which knows anything about a particular protocol:

  a  volume     halve, double or raise by 10% one number that feeds the volume of an aspirate,
                dispense, transfer, distribute or consolidate (a literal in the call, a constant the
                volume is computed from, or one entry of a list of numbers it is computed from)
  b  drop-last  drop the last item of a list, or shrink a slice `[:n]` or a `range(n)` by one
  c  reorder    reverse, or rotate by one, the first list of a `zip(...)` (the sources of a
                "for source, destination in zip(...)" loop) or the source list of a transfer
  d  wrong-src  make one aspirate or transfer draw from the well of a different declared liquid
  e  to-trash   make one execution (the first, or the second) of a dispense or transfer go
                into the trash instead of its destination

A mutant is only a candidate: the caller keeps it if the simulator still passes it.
"""

from __future__ import annotations

import ast
import copy
import random
from collections.abc import Callable, Iterator
from dataclasses import dataclass

VOLUME_CALLS = ("aspirate", "dispense", "transfer", "distribute", "consolidate")
SOURCE_ARG = {"aspirate": ("location", 1), "transfer": ("source", 1),
              "distribute": ("source", 1), "consolidate": ("source", 1)}  # fmt: skip
DEST_ARG = {"dispense": ("location", 1), "transfer": ("dest", 2)}

HELPER = """
_PROVETTE_MUTANT_CALLS = {"n": 0}


def _provette_nth(k):
    _PROVETTE_MUTANT_CALLS["n"] += 1
    return _PROVETTE_MUTANT_CALLS["n"] == k


def _provette_reorder(items, how):
    items = list(items)
    return items[::-1] if how == "reverse" else items[1:] + items[:1]
"""


@dataclass(frozen=True)
class Mutant:
    operator: str  # "a".."e"
    line: int  # line in the ORIGINAL source
    description: str
    source: str


def _is_number(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
        and node.value > 0
    )


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _arg(call: ast.Call, keyword: str, position: int) -> ast.expr | None:
    for kw in call.keywords:
        if kw.arg == keyword:
            return kw.value
    return call.args[position] if len(call.args) > position else None


def _names(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _literals_outside_subscripts(node: ast.AST) -> list[ast.Constant]:
    found: list[ast.Constant] = []

    def visit(n: ast.AST) -> None:
        if isinstance(n, ast.Subscript):
            visit(n.value)
            return
        if _is_number(n):
            found.append(n)  # type: ignore[arg-type]
        for child in ast.iter_child_nodes(n):
            visit(child)

    visit(node)
    return found


# ---------------------------------------------------------------------------------------------
# Finding the places to mutate. Each finder yields (node, description, edit), where `edit`
# changes the node IN A COPY of the tree, found again by its position in a walk.
# ---------------------------------------------------------------------------------------------

Edit = Callable[[ast.AST], None]


def _volume_sites(tree: ast.AST) -> Iterator[tuple[ast.AST, str, Edit]]:
    volume_exprs = [
        v for n in ast.walk(tree)
        if _call_name(n) in VOLUME_CALLS and (v := _arg(n, "volume", 0)) is not None  # type: ignore[arg-type]
    ]  # fmt: skip
    feeding: set[str] = set().union(*(_names(v) for v in volume_exprs)) if volume_exprs else set()
    assigned: dict[str, list[ast.expr]] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            assigned.setdefault(n.targets[0].id, []).append(n.value)
        elif isinstance(n, (ast.For, ast.comprehension)):
            for target in _names(n.target):
                assigned.setdefault(target, []).append(n.iter)
    frontier = set(feeding)
    while frontier:
        name = frontier.pop()
        for value in assigned.get(name, []):
            new = _names(value) - feeding
            feeding |= new
            frontier |= new

    sites: list[ast.Constant] = []
    for v in volume_exprs:
        sites += _literals_outside_subscripts(v)
    for name in sorted(feeding):
        for value in assigned.get(name, []):
            if _is_number(value):
                sites.append(value)  # type: ignore[arg-type]
            elif (
                isinstance(value, (ast.List, ast.Tuple))
                and value.elts
                and all(_is_number(e) for e in value.elts)
            ):
                sites.append(value.elts[len(value.elts) // 2])  # type: ignore[arg-type]
    seen: set[int] = set()
    for site in sites:
        if id(site) in seen:
            continue
        seen.add(id(site))
        for word, factor in (("halve", 0.5), ("double", 2.0), ("raise by 10%", 1.1)):

            def edit(node: ast.AST, factor: float = factor) -> None:
                assert isinstance(node, ast.Constant)
                value = round(node.value * factor, 4)
                node.value = int(value) if float(value).is_integer() and factor > 1 else value

            yield site, f"{word} the number {site.value}", edit


def _drop_last_sites(tree: ast.AST) -> Iterator[tuple[ast.AST, str, Edit]]:
    def minus_one(expr: ast.expr) -> ast.expr:
        if _is_number(expr):
            return ast.Constant(expr.value - 1)  # type: ignore[attr-defined]
        return ast.BinOp(expr, ast.Sub(), ast.Constant(1))

    for n in ast.walk(tree):
        if (
            isinstance(n, (ast.List, ast.Tuple))
            and len(n.elts) >= 3
            and isinstance(getattr(n, "ctx", None), ast.Load)
            and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in n.elts)
        ):

            def edit_list(node: ast.AST) -> None:
                node.elts.pop()  # type: ignore[attr-defined]

            yield n, f"drop the last of {len(n.elts)} items of a list", edit_list
        elif (
            isinstance(n, ast.Subscript)
            and isinstance(n.slice, ast.Slice)
            and n.slice.upper is not None
            and n.slice.step is None
        ):

            def edit_slice(node: ast.AST) -> None:
                node.slice.upper = minus_one(node.slice.upper)  # type: ignore[attr-defined]

            yield n, f"shrink the slice [{ast.unparse(n.slice)}] by one", edit_slice
        elif (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "range"
            and 1 <= len(n.args) <= 2
        ):

            def edit_range(node: ast.AST) -> None:
                node.args[-1] = minus_one(node.args[-1])  # type: ignore[attr-defined]

            yield n, f"shrink {ast.unparse(n)} by one", edit_range


def _reorder_sites(tree: ast.AST) -> Iterator[tuple[ast.AST, str, Edit]]:
    for n in ast.walk(tree):
        is_zip = isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "zip"
        is_transfer = _call_name(n) in ("transfer", "distribute", "consolidate")
        if not (is_zip and n.args) and not (is_transfer and len(n.args) > 1):  # type: ignore[attr-defined]
            continue
        position = 0 if is_zip else 1
        for how in ("reverse", "rotate"):

            def edit(node: ast.AST, how: str = how, position: int = position) -> None:
                args = node.args  # type: ignore[attr-defined]
                args[position] = ast.Call(
                    ast.Name("_provette_reorder", ast.Load()),
                    [args[position], ast.Constant(how)],
                    [],
                )

            what = ast.unparse(n.args[position])  # type: ignore[attr-defined]
            yield n, f"{how} the list {what}", edit


def _fixed_wells(tree: ast.AST) -> list[ast.expr]:
    """Expressions that mean one fixed source well anywhere in `run`: the `X` of every
    `X.load_liquid(...)`, and the source of every aspirate or transfer, when `X` is a plain
    name or `labware["A1"]` and not a loop variable."""
    loop_names: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.For, ast.comprehension)):
            loop_names |= _names(n.target)
        if isinstance(n, ast.FunctionDef) and n.name != "run":
            loop_names |= {a.arg for a in n.args.args}
    wells: list[ast.expr] = []
    for n in ast.walk(tree):
        name = _call_name(n)
        target: ast.expr | None = None
        if name == "load_liquid":
            target = n.func.value  # type: ignore[attr-defined]
        elif name in SOURCE_ARG:
            target = _arg(n, *SOURCE_ARG[name])  # type: ignore[arg-type]
            if _call_name(target) in ("bottom", "top", "center"):  # type: ignore[arg-type]
                target = target.func.value  # type: ignore[union-attr]
        simple = isinstance(target, ast.Name) or (
            isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant)
        )
        known = target is None or ast.dump(target) in [ast.dump(w) for w in wells]
        if target is not None and simple and not known and not (_names(target) & loop_names):
            wells.append(target)
    return wells


def _wrong_source_sites(tree: ast.AST) -> Iterator[tuple[ast.AST, str, Edit]]:
    wells = _fixed_wells(tree)
    dumps = [ast.dump(w) for w in wells]
    if len(wells) < 2:
        return
    for n in ast.walk(tree):
        name = _call_name(n)
        if name not in SOURCE_ARG:
            continue
        source = _arg(n, *SOURCE_ARG[name])  # type: ignore[arg-type]
        if source is None:
            continue
        for inner in ast.walk(source):
            if ast.dump(inner) in dumps:
                other = wells[(dumps.index(ast.dump(inner)) + 1) % len(wells)]
                inner_dump = ast.dump(inner)

                def edit(
                    node: ast.AST,
                    inner_dump: str = inner_dump,
                    other: ast.expr = other,
                    name: str = name,
                ) -> None:  # type: ignore[assignment]
                    class Swap(ast.NodeTransformer):
                        def generic_visit(self, sub: ast.AST) -> ast.AST:
                            if ast.dump(sub) == inner_dump:
                                return copy.deepcopy(other)
                            return super().generic_visit(sub)

                    keyword, position = SOURCE_ARG[name]
                    for kw in node.keywords:  # type: ignore[attr-defined]
                        if kw.arg == keyword:
                            kw.value = Swap().visit(kw.value)
                            return
                    node.args[position] = Swap().visit(node.args[position])  # type: ignore[attr-defined]

                yield (
                    n,
                    f"{name} draws from {ast.unparse(other)} instead of {ast.unparse(inner)}",
                    edit,
                )
                break


def _to_trash_sites(tree: ast.AST) -> Iterator[tuple[ast.AST, str, Edit]]:
    run = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "run"), None
    )
    if run is None or not run.args.args:
        return
    context = run.args.args[0].arg
    for n in ast.walk(tree):
        name = _call_name(n)
        if name not in DEST_ARG or _arg(n, *DEST_ARG[name]) is None:  # type: ignore[arg-type]
            continue

        for nth, word in ((1, "first"), (2, "second")):

            def edit(node: ast.AST, name: str = name, nth: int = nth) -> None:  # type: ignore[assignment]
                keyword, position = DEST_ARG[name]
                trash = ast.Attribute(ast.Name(context, ast.Load()), "fixed_trash", ast.Load())
                once = ast.Call(ast.Name("_provette_nth", ast.Load()), [ast.Constant(nth)], [])
                for kw in node.keywords:  # type: ignore[attr-defined]
                    if kw.arg == keyword:
                        kw.value = ast.IfExp(once, trash, kw.value)
                        return
                args = node.args  # type: ignore[attr-defined]
                args[position] = ast.IfExp(once, trash, args[position])

            yield n, f"the {word} time this {name} runs, it goes into the trash", edit


FINDERS = {"a": _volume_sites, "b": _drop_last_sites, "c": _reorder_sites,
           "d": _wrong_source_sites, "e": _to_trash_sites}  # fmt: skip


def mutants(source: str, per_operator: int = 9, seed: int = 20260921) -> list[Mutant]:
    """At most `per_operator` mutants of each kind, drawn at random (fixed seed) from the
    places found."""
    tree = ast.parse(source)
    order = {id(node): i for i, node in enumerate(ast.walk(tree))}
    out: list[Mutant] = []
    for operator, finder in FINDERS.items():
        sites = list(finder(tree))
        if len(sites) > per_operator:
            chosen = sorted(random.Random(seed).sample(range(len(sites)), per_operator))
            sites = [sites[i] for i in chosen]
        for node, description, edit in sites:
            clone = copy.deepcopy(tree)
            twin = next(n for i, n in enumerate(ast.walk(clone)) if i == order[id(node)])
            edit(twin)
            ast.fix_missing_locations(clone)
            body = ast.unparse(clone)
            # the helpers go after the imports, so `from __future__` stays first
            lines = body.split("\n")
            last_import = max(
                (i for i, line in enumerate(lines) if line.startswith(("import ", "from "))),
                default=-1,
            )
            mutated = (
                "\n".join(lines[: last_import + 1])
                + "\n"
                + HELPER
                + "\n".join(lines[last_import + 1 :])
            )
            out.append(Mutant(operator, getattr(node, "lineno", 0), description, mutated + "\n"))
    return out
