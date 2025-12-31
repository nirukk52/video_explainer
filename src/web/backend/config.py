"""Configuration for the web backend."""

from pathlib import Path
from pydantic import BaseModel


class WebConfig(BaseModel):
    """Web server configuration."""

    host: str = "127.0.0.1"
    port: int = 8000
    projects_dir: Path = Path("projects")
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    job_timeout: int = 600  # 10 minutes

    class Config:
        """Pydantic config."""

        arbitrary_types_allowed = True
