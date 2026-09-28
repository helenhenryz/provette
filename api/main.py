"""The FastAPI application. `uvicorn api.main:app` serves it; `create_app` builds one for tests.

Routes live in one module each (`api/gallery.py`, `api/rules.py`, ...); this file only wires
them and serves the built pages. `/health` is what the platform polls.
"""

from __future__ import annotations

import importlib.metadata
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api import (
    auth,
    checks,
    coverage,
    declared,
    docs,
    evidence,
    gallery,
    live,
    outcomes,
    rules,
    run_settings,
)
from api.episodes import Gallery
from api.settings import Settings, settings_from_env

FOOTER = "Provette checks the logic of a protocol, not the physics."


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or settings_from_env()
    if cfg.roles_file is not None:
        from provette.rules import roles as roles_module

        roles_module.ROLES_FILE = cfg.roles_file  # the tests teach words to a copy
        roles_module.reload(cfg.roles_file)
    if cfg.sources_file is not None:
        from provette.rules import sources as sources_module

        sources_module.SOURCES_FILE = cfg.sources_file  # the tests add sources to a copy
        sources_module.reload(cfg.sources_file)
    # The route documentation page is a developer's tool: on for the dev server
    # (PROVETTE_API_DOCS=1), off as deployed, where it would list every route to anyone.
    app = FastAPI(
        title="Provette",
        docs_url="/api/docs" if cfg.api_docs else None,
        openapi_url="/api/openapi.json" if cfg.api_docs else None,
    )
    app.state.settings = cfg
    app.state.gallery = Gallery(cfg)
    app.state.live = live.Live(cfg, app.state.gallery)
    app.state.run_settings = app.state.live.run_settings
    app.include_router(auth.router)
    app.include_router(gallery.router)
    app.include_router(rules.router)
    app.include_router(checks.router)
    app.include_router(live.router)
    app.include_router(run_settings.router)
    app.include_router(evidence.router)
    app.include_router(docs.router)
    app.include_router(outcomes.router)
    app.include_router(coverage.router)
    app.include_router(declared.router)

    @app.get("/health")
    def health() -> dict[str, Any]:
        """Green when the process is up and the simulator is importable; Fly polls this."""
        import opentrons

        return {
            "ok": True,
            "opentrons": opentrons.__version__,
            "provette": importlib.metadata.version("provette"),
            "episodes": len(app.state.gallery.refs),
            "live": cfg.live_enabled,
            "spent_today_usd": app.state.live.ledger.spent_today(),
            "footer": FOOTER,
        }

    if cfg.web_dir is not None and cfg.web_dir.is_dir():
        # The built pages. Any path that is not an API route falls back to index.html so the
        # client-side router can open a deep link (an episode's URL) directly.
        web_dir = cfg.web_dir.resolve()
        app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")
        index = web_dir / "index.html"

        @app.get("/{path:path}", include_in_schema=False)
        def page(path: str) -> FileResponse:
            if path.startswith("api/"):
                # An API route that does not exist is a 404, never the page as JSON.
                raise HTTPException(404, "there is no such API route")
            # Only a file under the built pages is served: `Path(web_dir) / "/etc/passwd"` is
            # `/etc/passwd`, so the resolved path must stay inside web_dir.
            candidate = (web_dir / path.lstrip("/")).resolve()
            if path and candidate.is_relative_to(web_dir) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(index)

    return app


app = create_app()
