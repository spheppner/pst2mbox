"""
Allow direct execution via `python -m pst2mbox`.
"""

import sys
from pst2mbox.cli import main

if __name__ == "__main__":
    sys.exit(main())
