"""The `provette` command. Subcommands register themselves here as their modules land."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provette", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    # Each module that owns a subcommand exposes `register(sub)` and is added to this list.
    for module_name in (
        "provette.trace.cli",
        "provette.corpus.cli",
        "provette.check",
        "provette.intent.cli",
        "provette.view.cli",
        "provette.planner.cli",
    ):
        try:
            module = __import__(module_name, fromlist=["register"])
        except ModuleNotFoundError as error:
            # A missing optional dependency loses one subcommand, and says so, not silently.
            print(
                f"provette: the {module_name} subcommand is unavailable ({error})", file=sys.stderr
            )
            continue
        module.register(sub)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
