"""
Base agent interface for the video production pipeline.

Defines the contract that all agents must follow: receive project state,
enrich it with their output, and return the updated state. This ensures
consistent agent-to-agent communication via models throughout the pipeline.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import VideoProject


class BaseAgent(ABC):
    """
    Abstract base class for all pipeline agents.

    All agents in the relay receive the shared VideoProject state, perform their
    specialized task, and return the enriched state for the next agent.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for logging and debugging."""
        pass

    @abstractmethod
    async def run(self, project: "VideoProject") -> "VideoProject":
        """
        Execute the agent's task and enrich the project state.

        Args:
            project: The current project state from previous agents.

        Returns:
            The enriched project state with this agent's contributions.
        """
        pass

    def log(self, message: str) -> None:
        """Standardized logging with agent name prefix."""
        print(f"[{self.name}] {message}")
