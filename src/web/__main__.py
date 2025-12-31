"""Entry point for the web server.

Usage:
    python -m src.web [--port PORT] [--host HOST] [--projects-dir DIR]
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Run the web server."""
    parser = argparse.ArgumentParser(
        description="Video Explainer Web Interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to run the server on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to",
    )
    parser.add_argument(
        "--projects-dir",
        type=Path,
        default=Path("projects"),
        help="Directory containing projects",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    args = parser.parse_args()

    # Import here to avoid loading FastAPI before parsing args
    import uvicorn
    from .backend.config import WebConfig
    from .backend.dependencies import get_config

    # Update config with CLI args
    config = get_config()
    config.host = args.host
    config.port = args.port
    config.projects_dir = args.projects_dir

    print(f"Starting Video Explainer Web Interface...")
    print(f"  Host: {args.host}")
    print(f"  Port: {args.port}")
    print(f"  Projects: {args.projects_dir.absolute()}")
    print(f"  URL: http://{args.host}:{args.port}")
    print()

    uvicorn.run(
        "src.web.backend.app:create_app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        factory=True,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
