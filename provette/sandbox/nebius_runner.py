"""`NebiusRunner`: the checks in a Nebius Token Factory Sandbox ("Contree").

    runner = NebiusRunner()                     # needs PROVETTE_API_KEY (a Token Factory key)
    result = runner.run_checks(text, platemap)  # the dict of provette/agent/runner.py

It talks to the REST API (https://api.tokenfactory.nebius.com/sandboxes/v1) with the standard
library only, so the project takes on no new dependency; the paths and request shapes are the
ones the official `contree-sdk` 0.3.6 sends, read from its source. `provette/sandbox/README.md`
says what was measured.

Authentication. Every call carries `Authorization: Bearer <key>` and a `Project: <id>` header.
The key is the project's Token Factory key (PROVETTE_API_KEY). The project id is not in the key and
not in our config: it is asked from Nebius IAM (`GET https://api.nebius.cloud/iam/v1/profiles`
with the same key), whose answer names the service account's parent project. Set
PROVETTE_SANDBOX_PROJECT to skip that call.

The image. On first use the runner looks for a sandbox image tagged `provette-checks:<hash>`,
where the hash is of the package source it would install. If there is none, it imports
python:3.10-slim from Docker Hub (a public image the service pulls itself: nothing of ours is
published anywhere), uploads a tarball of the package source, `pip install`s it inside a
non-disposable run, and tags the result. The tag pins the image against garbage collection and
is recorded in ~/.config/provette/sandbox-image.txt, never in the repository.

Each run_checks call is one disposable instance: protocol.py and platemap.json are uploaded
as files, the entrypoint prints the result JSON to stdout, and nothing is kept.
"""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import io
import json
import os
import tarfile
import time
from base64 import b64decode
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from provette.sandbox.entrypoint import PLATEMAP, PROTOCOL

SANDBOX_URL = "https://api.tokenfactory.nebius.com/sandboxes/v1"
IAM_PROFILES_URL = "https://api.nebius.cloud/iam/v1/profiles"
BASE_IMAGE = "python:3.10-slim"
BASE_IMAGE_URL = "docker://docker.io/library/python:3.10-slim"
IMAGE_TAG_PREFIX = "provette-checks"
IMAGE_RECORD = Path("~/.config/provette/sandbox-image.txt").expanduser()
# Cloudflare in front of api.nebius.cloud answers 403 (error 1010) to Python's default agent.
USER_AGENT = "provette-sandbox/0.1"
RUN_TIMEOUT_S = 300
BUILD_TIMEOUT_S = 900
OUTPUT_CAP = 10 * 1024 * 1024  # the API's documented maximum for one stream
FINAL = frozenset({"SUCCESS", "FAILED", "CANCELLED"})

# What goes into the sandbox image: the same files docker/Dockerfile copies.
PACKAGE_FILES = ("pyproject.toml", "uv.lock", "README.md", "LICENSE")
PACKAGE_DIR = "provette"


class SandboxError(RuntimeError):
    """The sandbox itself failed: not the protocol, the thing meant to run it."""


class SandboxPermissionError(SandboxError):
    """The key authenticates but holds no sandbox grant (spawn, import, list...)."""


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def package_tarball(root: Path | None = None) -> tuple[bytes, str]:
    """The package source as a deterministic tar.gz, and a short hash that names it.

    Deterministic (fixed mtimes and owners, sorted paths) so the same source gives the same
    hash and therefore the same image tag; a change to any file changes the tag.
    """
    root = root or repo_root()
    paths: list[Path] = [root / name for name in PACKAGE_FILES]
    paths += sorted(
        p
        for p in (root / PACKAGE_DIR).rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    )
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as tar:
        for path in paths:
            data = path.read_bytes()
            info = tarfile.TarInfo(f"src/{path.relative_to(root).as_posix()}")
            info.size = len(data)
            info.mtime = 0
            info.uid = info.gid = 0
            info.uname = info.gname = "root"
            tar.addfile(info, io.BytesIO(data))
    # gzip writes the time into its header unless told not to: mtime=0 keeps the bytes the same.
    packed = gzip.compress(buffer.getvalue(), compresslevel=6, mtime=0)
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return packed, digest.hexdigest()[:12]


class SandboxApi:
    """The few REST calls the runner needs. Never logs or stores the key beyond the header."""

    def __init__(self, key: str, project: str, base_url: str = SANDBOX_URL) -> None:
        self._headers = {
            "Authorization": f"Bearer {key}",
            "Project": project,
            "User-Agent": USER_AGENT,
        }
        self.base_url = base_url.rstrip("/")

    def _call(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        data: bytes | None = None,
        timeout_s: float = 60,
    ) -> Any:
        url = self.base_url + path
        if query:
            url += "?" + parse.urlencode(query)
        headers = dict(self._headers)
        payload: bytes | None = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            payload = data
            headers["Content-Type"] = "application/octet-stream"
        req = request.Request(url, data=payload, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=timeout_s) as resp:
                text = resp.read().decode("utf-8", errors="replace")
        except error.HTTPError as http_error:
            detail = http_error.read().decode("utf-8", errors="replace")[:500]
            if http_error.code == 403:
                raise SandboxPermissionError(
                    f"{method} {path}: HTTP 403 {detail}. The Token Factory key has no sandbox "
                    "grant for this project; see provette/sandbox/README.md, 'Access'."
                ) from http_error
            if http_error.code == 404:
                raise LookupError(f"{method} {path}: HTTP 404 {detail}") from http_error
            raise SandboxError(f"{method} {path}: HTTP {http_error.code} {detail}") from http_error
        except error.URLError as url_error:
            raise SandboxError(f"{method} {path}: {url_error.reason}") from url_error
        return json.loads(text) if text else None

    def whoami(self) -> dict[str, Any]:
        result: dict[str, Any] = self._call("GET", "/whoami")
        return result

    def image_by_tag(self, tag: str) -> dict[str, Any] | None:
        try:
            result: dict[str, Any] = self._call("GET", "/inspect/", query={"tag": tag})
        except LookupError:
            return None
        return result

    def upload(self, data: bytes) -> str:
        """The uuid of `data` on the server, uploading it only if it is not there already."""
        sha = hashlib.sha256(data).hexdigest()
        try:
            found: dict[str, Any] = self._call("GET", f"/files/{sha}")
            return str(found["uuid"])
        except LookupError:
            pass
        uploaded: dict[str, Any] = self._call("POST", "/files", data=data, timeout_s=300)
        return str(uploaded["uuid"])

    def start_import(self, url: str, tag: str, timeout_s: int) -> str:
        body = {"registry": {"url": url}, "tag": tag, "timeout": timeout_s}
        result: dict[str, Any] = self._call("POST", "/images/import", body=body)
        return str(result["uuid"])

    def start_instance(self, body: dict[str, Any]) -> str:
        result: dict[str, Any] = self._call("POST", "/instances", body=body)
        return str(result["uuid"])

    def operation(self, operation_uuid: str) -> dict[str, Any]:
        result: dict[str, Any] = self._call("GET", f"/operations/{operation_uuid}")
        return result

    def cancel(self, operation_uuid: str) -> None:
        with contextlib.suppress(SandboxError, LookupError):
            self._call("DELETE", f"/operations/{operation_uuid}")

    def tag(self, image_uuid: str, tag: str) -> None:
        self._call("PATCH", f"/images/{image_uuid}/tag", body={"tag": tag})

    def wait(self, operation_uuid: str, timeout_s: float) -> dict[str, Any]:
        """Poll until the operation is final, backing off from 0.5 s to 5 s as the SDK does."""
        started = time.monotonic()
        interval = 0.5
        while True:
            op = self.operation(operation_uuid)
            if op.get("status") in FINAL:
                if op["status"] != "SUCCESS":
                    raise SandboxError(
                        f"operation {operation_uuid} ended {op['status']}: {op.get('error')}"
                    )
                return op
            if time.monotonic() - started > timeout_s:
                self.cancel(operation_uuid)
                raise SandboxError(f"operation {operation_uuid} did not finish in {timeout_s} s")
            time.sleep(interval)
            interval = min(interval * 1.5, 5.0)


def decode_stream(stream: dict[str, Any] | None) -> str:
    if not stream:
        return ""
    value = str(stream.get("value", ""))
    if stream.get("encoding", "base64") == "base64":
        return b64decode(value).decode("utf-8", errors="replace")
    return value


def discover_project(key: str) -> str:
    """The project the key belongs to, from Nebius IAM: the service account's parent."""
    headers = {"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
    req = request.Request(IAM_PROFILES_URL, headers=headers)
    try:
        with request.urlopen(req, timeout=30) as resp:
            profile = json.loads(resp.read())
    except (error.URLError, json.JSONDecodeError) as fail:
        raise SandboxError(
            f"cannot ask Nebius IAM which project the key belongs to: {fail}"
        ) from fail
    try:
        return str(profile["serviceAccountProfile"]["info"]["metadata"]["parentId"])
    except (KeyError, TypeError) as fail:
        raise SandboxError(
            "the IAM profile has no serviceAccountProfile.info.metadata.parentId; set "
            "PROVETTE_SANDBOX_PROJECT by hand"
        ) from fail


class NebiusRunner:
    name = "nebius"

    def __init__(
        self,
        *,
        key: str | None = None,
        project: str | None = None,
        timeout_s: int = RUN_TIMEOUT_S,
        record: Path = IMAGE_RECORD,
    ) -> None:
        key = key or os.environ.get("PROVETTE_API_KEY")
        if not key:
            raise SandboxError(
                "PROVETTE_API_KEY is not set (see ~/.config/provette/token-factory.env)"
            )
        project = project or os.environ.get("PROVETTE_SANDBOX_PROJECT") or discover_project(key)
        self.project = project
        self.api = SandboxApi(key, project)
        self.timeout_s = timeout_s
        self.record = record
        self.image: str | None = None  # the uuid of the image with provette installed
        self.image_tag: str | None = None
        self.last: dict[str, Any] = {}  # metrics of the last run, for the README's numbers

    # --- access -------------------------------------------------------------------------------

    def check_access(self) -> dict[str, Any]:
        """`whoami`: permissions and limits. Raises if the key cannot spawn."""
        who = self.api.whoami()
        permissions = who.get("permissions", {})
        if not (permissions.get("spawn_disposable") or permissions.get("spawn")):
            raise SandboxPermissionError(
                "the key authenticates to the sandbox API but every permission is false "
                f"(project {self.project}): {permissions}. Sandbox access has to be granted to "
                "the project; see provette/sandbox/README.md, 'Access'."
            )
        return who

    # --- the image ----------------------------------------------------------------------------

    def ensure_image(self) -> str:
        """The uuid of an image with this package installed, building it once if needed."""
        if self.image:
            return self.image
        self.check_access()
        tarball, digest = package_tarball()
        tag = f"{IMAGE_TAG_PREFIX}:{digest}"
        found = self.api.image_by_tag(tag)
        if found:
            self.image, self.image_tag = str(found["uuid"]), tag
            return self.image
        started = time.monotonic()
        if self.api.image_by_tag(BASE_IMAGE) is None:
            op = self.api.start_import(BASE_IMAGE_URL, BASE_IMAGE, BUILD_TIMEOUT_S)
            self.api.wait(op, BUILD_TIMEOUT_S)
        self.last["import_seconds"] = round(time.monotonic() - started, 1)
        tar_uuid = self.api.upload(tarball)
        body = {
            "image": f"tag:{BASE_IMAGE}",
            "command": (
                "set -e; mkdir -p /opt/provette && cd /opt/provette"
                " && tar xzf /opt/provette/src.tgz"
                " && pip install --no-cache-dir 'opentrons==8.8.2' 'pyyaml==6.0.3'"
                " && pip install --no-cache-dir"
                " --no-deps ./src && python -c 'import opentrons, provette;"
                ' assert opentrons.__version__ == "8.8.2"\' && rm -rf /opt/provette/src'
                " /opt/provette/src.tgz /root/.cache && mkdir -p /work /tmp/ot"
            ),
            "shell": True,
            "hostname": "provette",
            "cwd": "/",
            "disposable": False,
            "timeout": BUILD_TIMEOUT_S,
            "truncate_output_at": OUTPUT_CAP,
            "stdin": {"value": "", "encoding": "ascii"},
            "files": {
                "/opt/provette/src.tgz": {"uuid": tar_uuid, "mode": "0644", "uid": 0, "gid": 0}
            },
            "env": {"PIP_DISABLE_PIP_VERSION_CHECK": "1"},
        }
        op = self.api.start_instance(body)
        done = self.api.wait(op, BUILD_TIMEOUT_S)
        run = (done.get("metadata") or {}).get("result") or {}
        exit_code = (run.get("state") or {}).get("exit_code")
        if exit_code != 0 or not (done.get("result") or {}).get("image"):
            raise SandboxError(
                f"building the sandbox image failed (exit {exit_code}):\n"
                + decode_stream(run.get("stderr"))[-3000:]
            )
        image = str(done["result"]["image"])
        self.api.tag(image, tag)
        self.image, self.image_tag = image, tag
        self.last["build_seconds"] = round(time.monotonic() - started, 1)
        self.last["build_cost"] = (run.get("resources") or {}).get("cost")
        self._record(image, tag)
        return image

    def _record(self, image: str, tag: str) -> None:
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        line = f"{stamp} {tag} {image} project={self.project}\n"
        try:
            self.record.parent.mkdir(parents=True, exist_ok=True)
            with self.record.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            pass  # the tag on the server is the record that matters

    # --- one run ------------------------------------------------------------------------------

    def run_checks(self, protocol_text: str, platemap_json: dict[str, Any]) -> dict[str, Any]:
        image = self.ensure_image()
        started = time.monotonic()
        protocol_uuid = self.api.upload(protocol_text.encode("utf-8"))
        platemap_uuid = self.api.upload(json.dumps(platemap_json).encode("utf-8"))
        body = {
            "image": image,
            "command": "python -m provette.sandbox.entrypoint --work /work --print",
            "shell": True,
            "hostname": "provette",
            "cwd": "/work",
            "disposable": True,
            "timeout": self.timeout_s,
            "truncate_output_at": OUTPUT_CAP,
            "stdin": {"value": "", "encoding": "ascii"},
            "files": {
                f"/work/{PROTOCOL}": {"uuid": protocol_uuid, "mode": "0644", "uid": 0, "gid": 0},
                f"/work/{PLATEMAP}": {"uuid": platemap_uuid, "mode": "0644", "uid": 0, "gid": 0},
            },
            "env": {"OT_API_CONFIG_DIR": "/tmp/ot"},
        }
        op = self.api.start_instance(body)
        done = self.api.wait(op, self.timeout_s + 60)
        run = (done.get("metadata") or {}).get("result") or {}
        state = run.get("state") or {}
        stdout = decode_stream(run.get("stdout"))
        if state.get("timed_out"):
            raise SandboxError(f"the sandbox run hit its {self.timeout_s} s limit")
        if state.get("exit_code") != 0:
            raise SandboxError(
                f"the entrypoint exited with {state.get('exit_code')}:\n"
                + decode_stream(run.get("stderr"))[-3000:]
            )
        try:
            result: dict[str, Any] = json.loads(stdout.strip().splitlines()[-1])
        except (json.JSONDecodeError, IndexError) as fail:
            raise SandboxError(
                f"the entrypoint printed no result JSON: {stdout[-500:]!r}"
            ) from fail
        resources = run.get("resources") or {}
        self.last = {
            "round_trip_seconds": round(time.monotonic() - started, 1),
            "sandbox_seconds": resources.get("elapsed_time"),
            "cost": resources.get("cost"),
            "max_rss_bytes": resources.get("max_rss"),
            "operation": op,
        }
        return result

    def close(self) -> None:
        """Nothing is held: every run is disposable and the image is a tagged server object."""
