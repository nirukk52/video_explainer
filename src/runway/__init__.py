"""Runway AI video generation module.

This module provides integration with Runway's API for generating AI videos
from images and text prompts. Used to create dynamic backgrounds for video shorts.
"""

from .generator import RunwayGenerator, RunwayResult, RunwayConfig

__all__ = ["RunwayGenerator", "RunwayResult", "RunwayConfig"]
