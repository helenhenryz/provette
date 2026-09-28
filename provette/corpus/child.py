"""The process one protocol runs in: `python -m provette.corpus.child <worker> <result file>`.

Reads the prepared protocol as JSON on stdin, calls the worker, and writes the outcome to the
result file. A file, not stdout, because protocols print whatever they like.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from provette.corpus.runner import first_line, load_worker


def main(worker: str, result_file: Path) -> None:
    prepared = json.load(sys.stdin)
    try:
        result = {"status": "ok", "payload": load_worker(worker)(prepared)}
        text = json.dumps(result)
    except BaseException as error:  # a protocol may raise SystemExit or anything else
        text = json.dumps(
            {
                "status": "error",
                "error_class": type(error).__name__,
                "error_message": first_line(str(error)),
            }
        )
    result_file.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1], Path(sys.argv[2]))
