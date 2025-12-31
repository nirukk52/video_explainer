"""API routers for the web backend."""

from .projects import router as projects_router
from .narrations import router as narrations_router
from .voiceovers import router as voiceovers_router
from .render import router as render_router
from .feedback import router as feedback_router
from .sound import router as sound_router
from .files import router as files_router
from .jobs import router as jobs_router
from .storyboard import router as storyboard_router

__all__ = [
    "projects_router",
    "narrations_router",
    "voiceovers_router",
    "render_router",
    "feedback_router",
    "sound_router",
    "files_router",
    "jobs_router",
    "storyboard_router",
]
