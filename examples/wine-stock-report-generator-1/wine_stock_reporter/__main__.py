"""Module entry point: ``python3 -m wine_stock_reporter CSV_PATH [options]``.

Delegates to :func:`wine_stock_reporter.cli.main`. Argparse's ``SystemExit``
(``--help`` -> 0, usage error -> 2) propagates untouched; other exit codes are
returned and turned into the process status by ``sys.exit``.
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
