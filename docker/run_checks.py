"""The image's entrypoint: `provette verify` and `provette check` on /work, result in
/work/result.json.

The work is done by `provette.sandbox.entrypoint`, which is inside the installed package so the
same code runs here, in a Nebius sandbox, and in-process in the tests.
"""

import sys

from provette.sandbox.entrypoint import main

if __name__ == "__main__":
    sys.exit(main())
