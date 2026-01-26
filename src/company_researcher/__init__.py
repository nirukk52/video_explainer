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

Based on: https://github.com/exa-labs/company-researcher
"""

from .researcher import CompanyResearcher, CompanyReport
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
    "CompanyInfo",
    "FundingInfo",
    "FounderInfo",
    "CompetitorInfo",
    "NewsArticle",
    "SocialProfile",
]
