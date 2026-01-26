"""
Data models for Company Researcher results.

Defines structured output types for company research data
gathered from various sources via Exa.ai searches.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class CompanyInfo:
    """
    Core company information extracted from website content.
    
    Contains structured data about what the company does,
    their products, pricing, and key facts.
    """
    
    name: str
    url: str
    description: str = ""
    main_product: str = ""
    target_users: str = ""
    pricing: str = ""
    strengths: list[str] = field(default_factory=list)
    key_points: dict[str, str] = field(default_factory=dict)  # heading -> text


@dataclass
class FundingInfo:
    """
    Company funding and valuation information.
    
    Aggregated from Crunchbase, PitchBook, Tracxn, and news sources.
    """
    
    total_raised: str = ""
    valuation: str = ""
    latest_round: str = ""
    latest_round_amount: str = ""
    latest_round_date: str = ""
    investors: list[str] = field(default_factory=list)
    source_url: str = ""
    summary: str = ""  # Raw funding summary from Exa


@dataclass
class FounderInfo:
    """
    Information about a company founder.
    
    Includes LinkedIn profile data and background.
    """
    
    name: str
    title: str = ""
    linkedin_url: str = ""
    background: str = ""
    previous_companies: list[str] = field(default_factory=list)


@dataclass
class CompetitorInfo:
    """
    Information about a competitor company.
    
    Brief overview for competitive analysis.
    """
    
    name: str
    url: str
    description: str = ""
    similarity_reason: str = ""


@dataclass
class NewsArticle:
    """
    A news article about the company.
    
    Contains article metadata and summary.
    """
    
    title: str
    url: str
    source: str = ""
    published_date: str = ""
    summary: str = ""


@dataclass
class SocialProfile:
    """
    A social media profile for the company.
    
    Can represent Twitter, YouTube, TikTok, GitHub, etc.
    """
    
    platform: str  # twitter, youtube, tiktok, github, reddit
    url: str
    handle: str = ""
    followers: str = ""
    description: str = ""
    recent_activity: list[str] = field(default_factory=list)


@dataclass
class WikipediaInfo:
    """
    Wikipedia information about the company.
    
    Extracted from the company's Wikipedia page if available.
    """
    
    url: str
    summary: str = ""
    founded: str = ""
    headquarters: str = ""
    industry: str = ""
    key_people: list[str] = field(default_factory=list)
