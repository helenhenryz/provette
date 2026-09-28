"""Teaching Provette a word: what the product calls when someone places an unplaced liquid.

    from provette.rules import roles_edit
    roles_edit.lists()                      # {"sample": [...], "reagent": [...], ...}
    roles_edit.add_word("reagent", "lysozyme")
    roles_edit.added()                      # the words this deployment added, by list
    roles_edit.remove_word("reagent", "lysozyme")   # only a word this deployment added

`add_word` appends one line to `roles.yaml` under the list named, keeping every comment and
every other line as it is (a line-based edit, not a YAML round trip, because a round trip
drops our comments), then reloads the lists so the running process uses the word
at once. It refuses a list that does not exist, an empty word, a word already in that list
and a word the file could not hold on one line. A bad pattern (an entry between slashes that
is not a regular expression) is refused before the file is touched.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from provette.rules import roles
from provette.rules.roles import LIST_NAMES


class RolesEditError(ValueError):
    """The word cannot be added; the message says why, in plain words."""


def lists() -> dict[str, list[str]]:
    """The seven lists in use, by name; every entry as the file spells it."""
    return roles.lists()


def add_word(list_name: str, word: str) -> None:
    """Append `word` to the list `list_name` in `roles.ROLES_FILE`, and reload the lists."""
    path = roles.ROLES_FILE
    word = _clean(list_name, word)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    at = _end_of_list(lines, list_name, path)
    lines.insert(at, _item_line(word))
    text = "".join(lines)
    _check(text, list_name, word, path)  # the file it would become parses, and holds the word
    path.write_text(text, encoding="utf-8")
    roles.reload()


def _clean(list_name: str, word: str) -> str:
    if list_name not in LIST_NAMES:
        raise RolesEditError(
            f"there is no list called {list_name!r}; the lists are {', '.join(LIST_NAMES)}"
        )
    word = word.strip()
    if not word:
        raise RolesEditError("the word is empty")
    if "\n" in word or "\r" in word:
        raise RolesEditError("a word is one line")
    if word.startswith("#"):
        raise RolesEditError("a word cannot start with '#': that is how a comment starts")
    if len(word) > 2 and word.startswith("/") and word.endswith("/"):
        try:
            re.compile(word[1:-1])
        except re.error as error:
            raise RolesEditError(f"{word} is not a pattern: {error}") from error
    existing = [entry.lower() for entry in roles.lists().get(list_name, [])]
    if word.lower() in existing:
        raise RolesEditError(f"{word!r} is already in the {list_name} list")
    return word


def _end_of_list(lines: list[str], list_name: str, path: Path) -> int:
    """The index at which a new item of `list_name` goes: after its last item line."""
    start = next(
        (i for i, line in enumerate(lines) if re.fullmatch(rf"{list_name}:\s*", line.rstrip("\n"))),
        None,
    )
    if start is None:
        raise RolesEditError(f"{path} has no list called {list_name}")
    end = start + 1
    for i in range(start + 1, len(lines)):
        line = lines[i]
        if re.match(r"\s+-\s", line):
            end = i + 1  # an item of this list
        elif line.strip() == "" or line.lstrip().startswith("#"):
            continue  # a blank line or a comment: the list may go on after it
        else:
            break  # the next list
    return end


def _item_line(word: str) -> str:
    """`  - word`, quoted the way YAML needs when the word has a character YAML would misread."""
    dumped = yaml.safe_dump([word], default_flow_style=False, allow_unicode=True, width=10_000)
    item = dumped.rstrip("\n").splitlines()[0]
    return f"  {item}\n"


def _check(text: str, list_name: str, word: str, path: Path) -> None:
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise RolesEditError(f"adding {word!r} would make {path} unreadable: {error}") from error
    entries = loaded.get(list_name) if isinstance(loaded, dict) else None
    if not isinstance(entries, list) or word not in entries:
        raise RolesEditError(f"could not add {word!r} to the {list_name} list in {path}")


# The lists as they ship with the package. On a deployment the live file is a copy on the volume
# (PROVETTE_ROLES_FILE); a word in the live file and not in this one was added there, and only
# such a word may be taken out from a page: a shipped word ("master mix") switches a check on.
SHIPPED_FILE = Path(roles.__file__).with_name("roles.yaml")


def added() -> dict[str, list[str]]:
    """The words the live file holds that the shipped one does not, by list (empty locally,
    where the live file is the shipped one)."""
    if roles.ROLES_FILE.resolve() == SHIPPED_FILE.resolve():
        return {name: [] for name in LIST_NAMES}
    shipped = yaml.safe_load(SHIPPED_FILE.read_text(encoding="utf-8")) or {}
    live = roles.lists()
    out: dict[str, list[str]] = {}
    for name in LIST_NAMES:
        known = {str(w).lower() for w in shipped.get(name) or []}
        out[name] = [w for w in live.get(name, []) if str(w).lower() not in known]
    return out


def remove_word(list_name: str, word: str) -> None:
    """Take `word` out of the list `list_name` in the live file, and reload the lists. Refused
    for a word the package ships with, or one the list does not hold."""
    if list_name not in LIST_NAMES:
        raise RolesEditError(
            f"there is no list called {list_name!r}; the lists are {', '.join(LIST_NAMES)}"
        )
    word = word.strip()
    if word not in added().get(list_name, []):
        if word.lower() in (w.lower() for w in roles.lists().get(list_name, [])):
            raise RolesEditError(
                f"{word!r} ships with Provette: it changes only through the repository"
            )
        raise RolesEditError(f"{word!r} is not in the {list_name} list")
    path = roles.ROLES_FILE
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    start = next(
        (i for i, line in enumerate(lines) if re.fullmatch(rf"{list_name}:\s*", line.rstrip("\n"))),
        None,
    )
    end = _end_of_list(lines, list_name, path)
    target = _item_line(word)
    at = next(
        (i for i in range(start + 1 if start is not None else 0, end) if lines[i] == target), None
    )
    if at is None:
        raise RolesEditError(f"could not find {word!r} in the {list_name} list in {path}")
    del lines[at]
    text = "".join(lines)
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict) or word in (loaded.get(list_name) or []):
        raise RolesEditError(f"could not remove {word!r} from the {list_name} list in {path}")
    path.write_text(text, encoding="utf-8")
    roles.reload()
