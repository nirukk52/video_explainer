"""Allow running CLI as: python -m src.cli"""

import sys
from pathlib import Path

# Load .env file from workspace root before anything else
from dotenv import load_dotenv

# Find .env relative to this file (src/cli/__main__.py -> project root)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from .main import main

sys.exit(main())
