"""The gallery's episodes: the pre-run results under `eval/agent/results/`, read as they are.

An episode is one directory the agent loop wrote (`provette/agent/README.md`, "On disk"):
`done.json`, `transcript.jsonl`, `NN-draft.py` and `NN-checks.json`. Its id in the product is
`<set>/<condition>/<request id>`, for example `super-tools/plain/pcr-01`. Nothing is copied or
re-judged here: the verdict is `done.json`'s, the checks are the files the loop wrote, and the
replay is `provette view`'s export of the final draft, computed once and cached (`api/analysis.py`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from api.analysis import analyse
from api.prices import Prices, model_label
from api.settings import Settings
from api.steps import checks_sentence, steps_from_transcript

_DRAFT = re.compile(r"^(\d\d)-draft\.py$")

RUNNER_LABELS = {
    "local": "on the server",
    "docker": "in a local Docker container",
    "nebius": "in a Nebius Token Factory Sandbox",
    "scripted": "by a scripted runner (a test)",
}


def runner_label(name: str | None) -> str:
    """Where the checks ran, in words: done.json's `runner`."""
    return RUNNER_LABELS.get(str(name), f"by the {name} runner") if name else "on the server"


CONDITION_LABELS = {
    "plain": "the request as written",
    "short-on-tips": "the request, plus “use as few tips as possible”",
}


@dataclass(frozen=True)
class EpisodeRef:
    set_name: str
    condition: str
    request_id: str
    path: Path

    @property
    def id(self) -> str:
        return f"{self.set_name}/{self.condition}/{self.request_id}"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def verified(done: dict[str, Any]) -> bool:
    """`eval/agent/tabulate.py`'s definition: the last checked draft passed everything."""
    loop = done.get("loop") or {}
    return bool(
        loop.get("simulator") == "passed"
        and loop.get("verify_exit") == 0
        and loop.get("check_exit") == 0
    )


class Gallery:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.prices = Prices(settings.prices_file)
        self.requests: dict[str, dict[str, Any]] = {}
        for requests_file, _ in settings.request_sets:
            self.requests.update(self._load_requests(requests_file))
        self.refs = self._scan()
        self._summaries: dict[str, dict[str, Any]] = {}

    # -- reading ---------------------------------------------------------------------------

    @staticmethod
    def _load_requests(path: Path) -> dict[str, dict[str, Any]]:
        if not path.is_file():
            return {}
        return {row["id"]: row for row in _read_jsonl(path)}

    def _scan(self) -> dict[str, EpisodeRef]:
        refs: dict[str, EpisodeRef] = {}
        for set_name in self.settings.gallery_sets:
            root = self.settings.episodes_dir / set_name
            if not root.is_dir():
                continue
            for done in sorted(root.glob("*/*/done.json")):
                ref = EpisodeRef(set_name, done.parent.parent.name, done.parent.name, done.parent)
                refs[ref.id] = ref
        return refs

    def ref(self, episode_id: str) -> EpisodeRef | None:
        return self.refs.get(episode_id)

    @staticmethod
    def done(ref: EpisodeRef) -> dict[str, Any]:
        path = ref.path / "done.json"
        row: dict[str, Any] = _read_json(path) if path.is_file() else {}
        return row

    def files_dir(self, ref: EpisodeRef) -> Path:
        """Where the transcript and the drafts are: the episode's own directory, or the chosen
        candidate's when the request was run best-of-N (`eval/agent/run.py --candidates`)."""
        chosen = self.done(ref).get("chosen")
        if (
            isinstance(chosen, str)
            and chosen
            and "/" not in chosen
            and (ref.path / chosen).is_dir()
        ):
            return ref.path / chosen
        return ref.path

    def platemap(self, request_id: str) -> dict[str, Any] | None:
        if not all(c.isalnum() or c in "-_" for c in request_id):
            return None
        for _, folder in self.settings.request_sets:
            path = folder / f"{request_id}.json"
            if path.is_file():
                row: dict[str, Any] = _read_json(path)
                return row
        return None

    def platemap_for(self, ref: EpisodeRef) -> dict[str, Any] | None:
        """The map the episode was run against: its own platemap.json (a live run), else eval's."""
        own = ref.path / "platemap.json"
        return _read_json(own) if own.is_file() else self.platemap(ref.request_id)

    def request_of(self, ref: EpisodeRef) -> dict[str, Any]:
        """The request: the episode's own request.json (a live run), else eval/requests."""
        own = ref.path / "request.json"
        if own.is_file():
            row: dict[str, Any] = _read_json(own)
            return row
        return self.requests.get(ref.request_id) or {}

    @staticmethod
    def summary_label(model: str) -> str:
        return model_label(model)

    @staticmethod
    def run_label(set_name: str) -> str:
        """'nano-best3' -> 'best of 3'; 'super' -> 'one try'."""
        best = re.search(r"-best(\d+)(?:-|$)", set_name)
        return f"best of {best.group(1)}" if best else "one try"

    def drafts(self, ref: EpisodeRef) -> list[dict[str, Any]]:
        rows = []
        folder = self.files_dir(ref)
        for path in sorted(folder.iterdir()):
            m = _DRAFT.match(path.name)
            if not m:
                continue
            n = int(m.group(1))
            checks_path = folder / f"{n:02d}-checks.json"
            checks = _read_json(checks_path) if checks_path.is_file() else None
            row: dict[str, Any] = {
                "n": n,
                "lines": sum(1 for _ in path.open(encoding="utf-8")),
                "checked": checks is not None,
                "repaired": (folder / f"{n:02d}-draft.as-written.py").is_file(),
                "summary": None,
            }
            if checks is not None:
                title, detail, status = checks_sentence({**checks, "draft": n})
                row["summary"] = {"title": title, "detail": detail, "status": status}
                row["simulator"] = checks.get("simulator")
                row["verify_exit"] = checks.get("verify_exit")
                row["check_exit"] = checks.get("check_exit")
                row["findings"] = checks.get("findings") or []
                intent = (
                    ((checks.get("verify") or {}).get("intent") or {})
                    if isinstance(checks.get("verify"), dict)
                    else {}
                )
                row["wells_ok"] = intent.get("wells_ok")
                row["wells_total"] = intent.get("wells_total")
                row["simulator_error"] = checks.get("simulator_error") or None
                row["report"] = "\n\n".join(
                    str(t) for t in (checks.get("verify_text"), checks.get("check_text")) if t
                )[:6000]
            rows.append(row)
        return rows

    def draft(self, ref: EpisodeRef, n: int) -> dict[str, Any] | None:
        folder = self.files_dir(ref)
        path = folder / f"{n:02d}-draft.py"
        if not path.is_file():
            return None
        checks_path = folder / f"{n:02d}-checks.json"
        as_written = folder / f"{n:02d}-draft.as-written.py"  # before prelint's repairs, if any
        return {
            "n": n,
            "text": path.read_text(encoding="utf-8"),
            "as_written": as_written.read_text(encoding="utf-8") if as_written.is_file() else None,
            "checks": _read_json(checks_path) if checks_path.is_file() else None,
        }

    def final_draft(self, ref: EpisodeRef) -> dict[str, Any] | None:
        done = self.done(ref)
        n = (done.get("loop") or {}).get("draft")
        if n is None:
            drafts = self.drafts(ref)
            n = drafts[-1]["n"] if drafts else None
        return self.draft(ref, int(n)) if n is not None else None

    # -- the contract ----------------------------------------------------------------------

    def summary(self, ref: EpisodeRef) -> dict[str, Any]:
        """The card: what the list endpoint returns for one episode."""
        if ref.id in self._summaries:
            return self._summaries[ref.id]
        done = _read_json(ref.path / "done.json")
        request = self.request_of(ref)
        model = str(done.get("model") or "")
        row = {
            "id": ref.id,
            "set": ref.set_name,
            "run_label": self.run_label(ref.set_name),
            "condition": ref.condition,
            "condition_label": CONDITION_LABELS.get(ref.condition, ref.condition),
            "request_id": ref.request_id,
            "technique": request.get("technique"),
            "request": request.get("request") or done.get("request") or "",
            "model": model,
            "model_label": model_label(model),
            "runner": done.get("runner"),
            "runner_label": runner_label(done.get("runner")),
            "candidates": candidates(done),
            "verified": verified(done),
            "outcome": outcome(done),
            "drafts": done.get("drafts"),
            "tool_calls": done.get("tool_calls"),
            "tokens_in": done.get("tokens_in"),
            "tokens_out": done.get("tokens_out"),
            "cost_usd": self.prices.cost_usd(
                model, int(done.get("tokens_in") or 0), int(done.get("tokens_out") or 0)
            ),
            "seconds": done.get("seconds"),
            "stop_reason": done.get("stop_reason"),
        }
        self._summaries[ref.id] = row
        return row

    def list(self) -> list[dict[str, Any]]:
        return [self.summary(ref) for ref in self.refs.values()]

    def detail(self, ref: EpisodeRef) -> dict[str, Any]:
        """The story: the card, the plate map, the steps, the draft rows and the verdict."""
        done = self.done(ref)
        transcript_path = self.files_dir(ref) / "transcript.jsonl"
        turns = _read_jsonl(transcript_path) if transcript_path.is_file() else []
        return {
            **self.summary(ref),
            "done": done,
            "platemap": self.platemap_for(ref),
            "steps": steps_from_transcript(list(turns)),
            "draft_rows": self.drafts(ref),
            "final_draft": (done.get("loop") or {}).get("draft"),
            "prices_read_on": self.prices.read_on,
        }

    def analysis(self, ref: EpisodeRef) -> dict[str, Any] | None:
        """`api.worker`'s analysis of the final draft against the plate map."""
        final = self.final_draft(ref)
        if final is None:
            return None
        return analyse(
            final["text"],
            self.platemap_for(ref),
            self.settings.cache_dir,
            roles_file=self.settings.roles_file,
            sources_file=self.settings.sources_file,
        )


def candidates(done: dict[str, Any]) -> dict[str, Any] | None:
    """Best-of-N: how many candidates ran, how many verified, which was chosen. None otherwise."""
    rows = done.get("candidates")
    if not isinstance(rows, list) or not rows:
        return None
    return {
        "n": len(rows),
        "verified": sum(bool(r.get("verified")) for r in rows),
        "chosen": done.get("chosen"),
        "rows": [
            {k: r.get(k) for k in ("dir", "verified", "stop_reason", "tokens_in", "tokens_out")}
            for r in rows
        ],
    }


def outcome(done: dict[str, Any]) -> dict[str, Any]:
    """One plain sentence on how the episode ended, and the fields it rests on."""
    loop = done.get("loop") or {}
    draft = loop.get("draft")
    findings = list(loop.get("findings") or [])
    ok = verified(done)
    stop = str(done.get("stop_reason") or "")
    drafts = done.get("drafts")
    best = candidates(done)
    if ok:
        sentence = (
            f"Verified: draft {draft} passed the simulator, holds what the plate map says in "
            f"every well, and has no biology problems."
        )
        if best:
            sentence += (
                f" {best['n']} candidates ran at once and the checks chose this one"
                f" ({best['verified']} of {best['n']} verified)."
            )
        if not done.get("submitted"):
            sentence += " The model ran out of budget before submitting, so the harness checked it."
    elif loop.get("simulator") == "timeout":
        sentence = (
            f"Not verified: the checks on draft {draft} did not finish in time; the server was "
            "too slow, so nothing in the draft was judged."
        )
    elif loop.get("simulator") == "rejected":
        sentence = (
            f"Not verified: after {drafts} drafts the simulator still rejected the file ({stop})."
        )
    elif loop.get("verify_exit") == 3:
        sentence = (
            f"Not verified: the plate map could not be checked against draft {draft} ({stop})."
        )
    elif loop.get("verify_exit") not in (0, None):
        sentence = f"Not verified: draft {draft} does not deliver the plate map ({stop})."
    elif findings:
        n = len(findings)
        sentence = (
            f"Not verified: draft {draft} delivers the plate map but has {n} biology "
            f"problem{'s' if n != 1 else ''} the model did not clear ({stop})."
        )
    else:
        sentence = f"Not verified ({stop})."
    return {
        "verified": ok,
        "sentence": sentence,
        "stop_reason": stop,
        "submitted": bool(done.get("submitted")),
        "final_draft": draft,
        "findings": findings,
    }
