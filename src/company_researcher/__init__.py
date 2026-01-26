"""
Company Researcher Agent - Research companies using Exa.ai.

Provides comprehensive company intelligence gathering including:
- Website content & subpages
- LinkedIn profiles (company + founders)
- Funding information (Crunchbase, PitchBook, Tracxn)
- News coverage
- Competitor analysis
- Social media presence (Twitter, YouTube, TikTok, Reddit, GitHub)
- Wikipedia information

Also provides research summarization for ad-ready insights:
- Hook angles for video ads
- Testimonial themes
- Unique value propositions
- Target audience details

Based on: https://github.com/exa-labs/company-researcher
"""

from .researcher import CompanyResearcher, CompanyReport
from .summarizer import ResearchSummarizer, ResearchDisplay
from .models import (
    CompanyInfo,
    FundingInfo,
    FounderInfo,
    CompetitorInfo,
    NewsArticle,
    SocialProfile,
)

__all__ = [
    "CompanyResearcher",
    "CompanyReport",
    "ResearchSummarizer",
    "ResearchDisplay",
    "CompanyInfo",
    "FundingInfo",
    "FounderInfo",
    "CompetitorInfo",
    "NewsArticle",
    "SocialProfile",
]
