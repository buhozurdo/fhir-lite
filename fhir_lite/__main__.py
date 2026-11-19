"""Executable entrypoint for `python -m fhir_lite`.
"""

import sys
from .cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
