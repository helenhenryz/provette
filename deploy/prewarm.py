"""Analyse every gallery episode once on a deployment, so no visitor waits for a first analysis.

    python3 deploy/prewarm.py https://provette.fly.dev

No model is called: each analysis is the simulator and the checks, kept on the volume after the
first time (api/analysis.py), so this costs nothing and a second pass only reads the files. Two
at a time, the deployment's own bound. Prints each episode's time and verdict; exits 0 either way,
since a slow episode is told to try again, not lost. deploy/fly-up.sh runs it after the smoke test.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def analyse(url: str, episode: str) -> str:
    started = time.time()
    try:
        with urllib.request.urlopen(f"{url}/api/episodes/{episode}/analysis", timeout=420) as r:
            passed = (json.load(r).get("simulator") or {}).get("passed")
        verdict = "passed" if passed else "rejected (the episode's own verdict)"
    except urllib.error.HTTPError as error:
        verdict = f"HTTP {error.code}: try this one again later"
    except OSError as error:
        verdict = f"no answer: {error}"
    return f"{time.time() - started:6.1f}s  {verdict:40.40}  {episode}"


def main(argv: list[str]) -> int:
    url = (argv[1] if len(argv) > 1 else "https://provette.fly.dev").rstrip("/")
    with urllib.request.urlopen(f"{url}/api/episodes", timeout=60) as r:
        episodes = [e["id"] for e in json.load(r)["episodes"]]
    print(f"analysing {len(episodes)} gallery episodes on {url}, two at a time", flush=True)
    with ThreadPoolExecutor(2) as pool:
        for line in pool.map(lambda e: analyse(url, e), episodes):
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
