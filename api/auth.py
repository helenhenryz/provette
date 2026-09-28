"""The judge password: the one credential the product has (the hackathon rules allow one).

The run page sends it as the `X-Judge-Password` header; anything that writes on behalf of a
person (a live run, a failed-run record, a role word) checks it here. Without a password set on
the deployment, those writes are off and the reads still work.

    POST /api/judge     the unlock dialog's check: 204 if the header holds the password, else
                        401 (wrong) or 503 (none set), so a wrong password is said at once
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Request, Response

from api.settings import Settings

router = APIRouter(prefix="/api", tags=["judge"])


def require_judge_password(request: Request, what: str = "this") -> None:
    cfg: Settings = request.app.state.settings
    if not cfg.judge_password:
        raise HTTPException(
            503, f"{what.capitalize()} needs the judge password, and this deployment has none set."
        )
    given = request.headers.get("x-judge-password", "")
    if not secrets.compare_digest(given, cfg.judge_password):
        raise HTTPException(401, "The judge password is missing or wrong.")


@router.post("/judge", status_code=204)
def check_judge_password(request: Request) -> Response:
    require_judge_password(request, "unlocking")
    return Response(status_code=204)
