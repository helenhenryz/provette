"""The public Opentrons protocol library: fetch it at the pinned commit and read its folders.

Nothing here runs a protocol. The library has no license (DECISIONS.md D-05), so the checkout
lives under `.cache/`, which is gitignored, and never anywhere else in this repository.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LIBRARY_URL = "https://github.com/Opentrons/Protocols"
LIBRARY_COMMIT = "2f447c936b49720d68154054e94d58e1d33ccba5"

REPO_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = REPO_ROOT / ".cache"
DEFAULT_CHECKOUT = CACHE_DIR / "opentrons-protocols"

# The only two top-level folders we read: the protocols, and the library's own build tool,
# whose `get_values` logic `prepare` mirrors. Leaving out `protoBuilds/` halves the checkout.
_SPARSE_PATHS = ("protocols", "protolib")


# ---------------------------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------------------------


def _git(checkout: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(checkout), *args], capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def _head(checkout: Path) -> str | None:
    if not (checkout / ".git").is_dir():
        return None
    try:
        return _git(checkout, "rev-parse", "HEAD")
    except RuntimeError:
        return None


def fetch(cache_dir: Path = DEFAULT_CHECKOUT) -> Path:
    """Check the library out at exactly `LIBRARY_COMMIT` and return the checkout path.

    Idempotent: a checkout already at the pinned commit is left alone and the network is not
    touched. Otherwise one shallow, blobless, sparse fetch of that single commit (measured
    GitHub serves the sha directly; about 7 s and 61 MB on disk).
    """
    if _head(cache_dir) != LIBRARY_COMMIT:
        cache_dir.mkdir(parents=True, exist_ok=True)
        if not (cache_dir / ".git").is_dir():
            _git(cache_dir, "init", "--quiet")
            _git(cache_dir, "remote", "add", "origin", LIBRARY_URL)
        _git(cache_dir, "sparse-checkout", "set", *_SPARSE_PATHS)
        _git(
            cache_dir,
            "fetch",
            "--quiet",
            "--depth",
            "1",
            "--filter=blob:none",
            "origin",
            LIBRARY_COMMIT,
        )
        _git(
            cache_dir,
            "-c",
            "advice.detachedHead=false",
            "checkout",
            "--quiet",
            "--force",
            LIBRARY_COMMIT,
        )
    head = _head(cache_dir)
    if head != LIBRARY_COMMIT:
        raise RuntimeError(f"{cache_dir} is at {head}, not the pinned commit {LIBRARY_COMMIT}")
    return cache_dir


# ---------------------------------------------------------------------------------------------
# Discover
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class LibraryProtocol:
    """One folder under `protocols/` in the library."""

    slug: str
    source: Path  # the protocol's .py
    fields_json: Path | None
    labware_dir: Path | None  # `labware/` or `custom_labware/`, holding custom definitions
    api_level: str | None  # as written in the source's metadata or requirements
    categories: list[str]  # top-level README categories, normalised
    subcategories: list[str]  # the indented bullets under them, normalised
    raw_categories: list[str]  # every bullet of the README section exactly as written
    hidden: bool  # carries `.hide-from-search`
    ignored: bool  # carries `.ignore`


_API_LEVEL = re.compile(r"""['"]apiLevel['"]\s*:\s*['"]([\d.]+)['"]""")


def parse_api_level(source_text: str) -> str | None:
    match = _API_LEVEL.search(source_text)
    return match.group(1) if match else None


def discover(checkout: Path) -> list[LibraryProtocol]:
    """One entry per folder under `protocols/` that holds a .py file, sorted by slug."""
    found = []
    for folder in sorted(p for p in (checkout / "protocols").iterdir() if p.is_dir()):
        sources = sorted(folder.glob("*.py"))
        if not sources:
            continue
        source = sources[0]  # measured: every one of the 833 folders has exactly one
        fields_json = folder / "fields.json"
        labware_dirs = [d for d in (folder / "labware", folder / "custom_labware") if d.is_dir()]
        readme = folder / "README.md"
        readme_text = (
            readme.read_text(encoding="utf-8", errors="replace") if readme.is_file() else ""
        )
        raw, top, sub = parse_categories(readme_text)
        found.append(
            LibraryProtocol(
                slug=folder.name,
                source=source,
                fields_json=fields_json if fields_json.is_file() else None,
                labware_dir=labware_dirs[0] if labware_dirs else None,
                api_level=parse_api_level(source.read_text(encoding="utf-8", errors="replace")),
                categories=top,
                subcategories=sub,
                raw_categories=raw,
                hidden=(folder / ".hide-from-search").exists(),
                ignored=(folder / ".ignore").exists(),
            )
        )
    return found


# ---------------------------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------------------------

# The spellings we settle on, matched without regard to case or spacing.
_CANONICAL = [
    "NGS Library Prep",
    "Sample Prep",
    "PCR",
    "PCR Prep",
    "qPCR Setup",
    "qPCR Prep",
    "Nucleic Acid Extraction & Purification",
    "Proteins & Proteomics",
    "DNA/RNA",
    "ELISA",
    "Cherrypicking",
    "Cleanup",
]
# Variants found in the library at the pinned commit that mean one of the above.
_ALIASES = {
    "nucleic acid purification & extraction": "Nucleic Acid Extraction & Purification",
    "nucleic acid purification": "Nucleic Acid Extraction & Purification",
    "nucleic acid extraction": "Nucleic Acid Extraction & Purification",
    "proteins & proteiomics": "Proteins & Proteomics",
    "proteins": "Proteins & Proteomics",
    "library prep": "NGS Library Prep",
    "ngs": "NGS Library Prep",
    "cherry picking": "Cherrypicking",
    "clean up": "Cleanup",
}
_BY_KEY = {**{name.casefold(): name for name in _CANONICAL}, **_ALIASES}

_HEADING = re.compile(r"^#+\s*categor\w*\s*$", re.IGNORECASE)
_BULLET = re.compile(r"^(\s*)[*-]\s+(.*\S)\s*$")


def normalise_category(raw: str) -> str:
    """Strip, collapse spaces, settle known variants, and capitalise all-lowercase words."""
    text = " ".join(raw.split())
    known = _BY_KEY.get(text.casefold())
    if known:
        return known
    return " ".join(w.capitalize() if w.islower() else w for w in text.split(" "))


def parse_categories(readme_text: str) -> tuple[list[str], list[str], list[str]]:
    """The README's "## Categories" bullets as (raw, top-level normalised, indented normalised).

    The section ends at the next heading, or at the first line that is not a bullet: one
    README runs straight on into its parameter notes without a heading.
    """
    raw: list[str] = []
    top: list[str] = []
    sub: list[str] = []
    in_section = False
    for line in readme_text.splitlines():
        if not in_section:
            in_section = bool(_HEADING.match(line))
            continue
        if not line.strip():
            continue
        bullet = _BULLET.match(line)
        if not bullet:
            break
        raw.append(bullet.group(2))
        bucket = sub if bullet.group(1) else top
        name = normalise_category(bullet.group(2))
        if name not in bucket:
            bucket.append(name)
    return raw, top, sub


# ---------------------------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldInfo:
    """One user-facing parameter from `fields.json`."""

    name: str
    label: str
    type: str  # dropDown, int, float, str, string, textFile
    default: Any  # what the library's build tool would pass: see `default_value`
    options: list[dict[str, Any]]  # dropDown only: [{"label": ..., "value": ...}]


def default_value(field: dict[str, Any]) -> Any:
    """The value the library's own build tool gives a parameter when it simulates.

    Mirrors `get_default_field_value` in the library's `protolib/parse/parseOT2v2.py`: the first
    option of a dropDown, otherwise `default` (for a textFile that is the CSV text itself).
    """
    if field["type"] == "dropDown":
        return field["options"][0]["value"]
    return field["default"]


def read_fields(protocol: LibraryProtocol) -> list[FieldInfo]:
    if protocol.fields_json is None:
        return []
    fields = json.loads(protocol.fields_json.read_text(encoding="utf-8"))
    return [
        FieldInfo(
            name=f["name"],
            label=str(f.get("label", "")),
            type=f["type"],
            default=default_value(f),
            options=list(f.get("options", [])),
        )
        for f in fields
    ]


# A parameter is about tip reuse when it mentions tips and one of these ideas...
_TIP_REUSE = re.compile(
    r"reus|park|strateg|scheme|chang|same|new[ _]tip|tip[ _]use|return[ _]tips|fresh|replace"
)
# ...and is not about one of these: tracking tips across runs, which rack, touch-tip, and so on.
_NOT_TIP_REUSE = re.compile(r"track|rack|touch|start|filter|replenish")


def tip_reuse_parameters(protocol: LibraryProtocol) -> list[FieldInfo]:
    """The parameters that let the user choose whether tips are reused, parked or changed."""
    found = []
    for info in read_fields(protocol):
        text = f"{info.name} {info.label}".lower()
        if "tip" in text and _TIP_REUSE.search(text) and not _NOT_TIP_REUSE.search(text):
            found.append(info)
    return found
