"""
Company Researcher - Core research logic using Exa.ai.

Orchestrates multiple Exa.ai searches to build comprehensive
company intelligence reports. Mirrors the functionality of
https://github.com/exa-labs/company-researcher but in Python.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

from exa_py import Exa

from .models import (
    CompanyInfo,
    CompetitorInfo,
    FounderInfo,
    FundingInfo,
    NewsArticle,
    SocialProfile,
    WikipediaInfo,
)


@dataclass
class CompanyReport:
    """
    Complete research report for a company.
    
    Aggregates all research data from multiple sources into
    a single comprehensive report. Used as input for video
    script generation.
    """
    
    company: CompanyInfo
    funding: Optional[FundingInfo] = None
    founders: list[FounderInfo] = field(default_factory=list)
    competitors: list[CompetitorInfo] = field(default_factory=list)
    news: list[NewsArticle] = field(default_factory=list)
    social_profiles: list[SocialProfile] = field(default_factory=list)
    wikipedia: Optional[WikipediaInfo] = None
    linkedin_url: str = ""
    crunchbase_url: str = ""
    pitchbook_url: str = ""
    tracxn_url: str = ""
    
    def to_dict(self) -> dict:
        """Convert report to JSON-serializable dictionary."""
        return {
            "company": {
                "name": self.company.name,
                "url": self.company.url,
                "description": self.company.description,
                "main_product": self.company.main_product,
                "target_users": self.company.target_users,
                "pricing": self.company.pricing,
                "strengths": self.company.strengths,
                "key_points": self.company.key_points,
            },
            "funding": {
                "total_raised": self.funding.total_raised if self.funding else "",
                "valuation": self.funding.valuation if self.funding else "",
                "latest_round": self.funding.latest_round if self.funding else "",
                "investors": self.funding.investors if self.funding else [],
                "summary": self.funding.summary if self.funding else "",
            } if self.funding else None,
            "founders": [
                {
                    "name": f.name,
                    "title": f.title,
                    "linkedin_url": f.linkedin_url,
                    "background": f.background,
                }
                for f in self.founders
            ],
            "competitors": [
                {
                    "name": c.name,
                    "url": c.url,
                    "description": c.description,
                }
                for c in self.competitors
            ],
            "news": [
                {
                    "title": n.title,
                    "url": n.url,
                    "source": n.source,
                    "summary": n.summary,
                }
                for n in self.news
            ],
            "social_profiles": [
                {
                    "platform": s.platform,
                    "url": s.url,
                    "handle": s.handle,
                }
                for s in self.social_profiles
            ],
            "wikipedia": {
                "url": self.wikipedia.url,
                "summary": self.wikipedia.summary,
            } if self.wikipedia else None,
            "profile_urls": {
                "linkedin": self.linkedin_url,
                "crunchbase": self.crunchbase_url,
                "pitchbook": self.pitchbook_url,
                "tracxn": self.tracxn_url,
            },
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize report to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class CompanyResearcher:
    """
    Researches companies using Exa.ai semantic search.
    
    Provides methods to gather comprehensive company intelligence
    including website content, funding data, founders, competitors,
    news coverage, and social media presence.
    
    Based on: https://github.com/exa-labs/company-researcher
    """
    
    def __init__(self, exa_api_key: str | None = None):
        """
        Initialize the Company Researcher.
        
        Args:
            exa_api_key: Exa.ai API key. Falls back to EXA_API_KEY env var.
        """
        api_key = exa_api_key or os.getenv("EXA_API_KEY", "")
        if not api_key:
            raise ValueError("EXA_API_KEY not configured")
        self._client = Exa(api_key=api_key)
    
    def research(
        self,
        company_url: str,
        include_funding: bool = True,
        include_founders: bool = True,
        include_competitors: bool = True,
        include_news: bool = True,
        include_social: bool = True,
        include_wikipedia: bool = True,
        verbose: bool = False,
    ) -> CompanyReport:
        """
        Perform comprehensive research on a company.
        
        Args:
            company_url: The company's website URL (e.g., "exa.ai")
            include_funding: Fetch funding/valuation data
            include_founders: Fetch founder LinkedIn profiles
            include_competitors: Find and analyze competitors
            include_news: Fetch recent news coverage
            include_social: Fetch social media profiles
            include_wikipedia: Fetch Wikipedia info
            verbose: Print progress messages
            
        Returns:
            CompanyReport with all gathered intelligence.
        """
        # Normalize URL
        url = self._normalize_url(company_url)
        domain = urlparse(url).netloc.replace("www.", "")
        
        if verbose:
            print(f"Researching: {domain}")
        
        # 1. Scrape main website content
        if verbose:
            print("  - Fetching website content...")
        company = self._fetch_website_content(url, domain)
        
        # 2. Fetch LinkedIn company profile
        if verbose:
            print("  - Finding LinkedIn profile...")
        linkedin_url = self._fetch_linkedin_profile(domain)
        
        # 3. Fetch funding information
        funding = None
        crunchbase_url = ""
        pitchbook_url = ""
        tracxn_url = ""
        if include_funding:
            if verbose:
                print("  - Fetching funding data...")
            funding = self._fetch_funding(domain)
            crunchbase_url = self._fetch_profile_url(domain, "crunchbase.com")
            pitchbook_url = self._fetch_profile_url(domain, "pitchbook.com")
            tracxn_url = self._fetch_profile_url(domain, "tracxn.com")
        
        # 4. Fetch founders
        founders = []
        if include_founders:
            if verbose:
                print("  - Finding founders...")
            founders = self._fetch_founders(domain)
        
        # 5. Find competitors
        competitors = []
        if include_competitors and company.description:
            if verbose:
                print("  - Analyzing competitors...")
            competitors = self._fetch_competitors(domain, company.description)
        
        # 6. Fetch news
        news = []
        if include_news:
            if verbose:
                print("  - Fetching news coverage...")
            news = self._fetch_news(domain)
        
        # 7. Fetch social profiles
        social_profiles = []
        if include_social:
            if verbose:
                print("  - Finding social profiles...")
            social_profiles = self._fetch_social_profiles(domain)
        
        # 8. Fetch Wikipedia
        wikipedia = None
        if include_wikipedia:
            if verbose:
                print("  - Checking Wikipedia...")
            wikipedia = self._fetch_wikipedia(domain)
        
        if verbose:
            print("Research complete!")
        
        return CompanyReport(
            company=company,
            funding=funding,
            founders=founders,
            competitors=competitors,
            news=news,
            social_profiles=social_profiles,
            wikipedia=wikipedia,
            linkedin_url=linkedin_url,
            crunchbase_url=crunchbase_url,
            pitchbook_url=pitchbook_url,
            tracxn_url=tracxn_url,
        )
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to have https:// prefix."""
        if not url.startswith("http"):
            url = f"https://{url}"
        return url
    
    def _fetch_website_content(self, url: str, domain: str) -> CompanyInfo:
        """Fetch and summarize main website content."""
        try:
            # Get main page content
            result = self._client.get_contents(
                ids=[url],
                text=True,
                summary=True,
            )
            
            main_content = ""
            if result.results:
                main_content = result.results[0].text or ""
            
            # Get subpages (about, pricing, faq, blog)
            subpages_result = self._client.search_and_contents(
                query=f"{domain}",
                type="neural",
                text=True,
                num_results=1,
                livecrawl="always",
                subpages=10,
                subpage_target=["about", "pricing", "faq", "blog"],
                include_domains=[domain],
            )
            
            subpages_content = ""
            if subpages_result.results:
                for r in subpages_result.results:
                    if r.text:
                        subpages_content += f"\n\n{r.url}:\n{r.text[:2000]}"
            
            # Extract company info from content
            description = ""
            if result.results and hasattr(result.results[0], 'summary'):
                description = result.results[0].summary or ""
            
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description=description,
                key_points={"website_content": main_content[:3000]},
            )
            
        except Exception as e:
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description=f"Error fetching content: {e}",
            )
    
    def _fetch_linkedin_profile(self, domain: str) -> str:
        """Find company LinkedIn profile URL."""
        try:
            result = self._client.search(
                query=f"{domain} company linkedin profile:",
                type="keyword",
                num_results=1,
                include_domains=["linkedin.com"],
            )
            
            if result.results:
                return result.results[0].url
            return ""
            
        except Exception:
            return ""
    
    def _fetch_funding(self, domain: str) -> Optional[FundingInfo]:
        """Fetch funding information using Exa summary feature."""
        try:
            result = self._client.search_and_contents(
                query=f"{domain} Funding:",
                type="keyword",
                num_results=1,
                text=True,
                summary={
                    "query": "Tell me all about the funding (and if available, the valuation) "
                             "of this company in detail. Do not tell me about the company, "
                             "just give all the funding information in detail. "
                             "If funding or valuation info is not present, just reply with one word 'NO'."
                },
                livecrawl="always",
                include_text=[domain],
            )
            
            if result.results:
                summary = getattr(result.results[0], 'summary', '') or ''
                if summary and summary.upper() != "NO":
                    return FundingInfo(
                        summary=summary,
                        source_url=result.results[0].url,
                    )
            return None
            
        except Exception:
            return None
    
    def _fetch_founders(self, domain: str) -> list[FounderInfo]:
        """Find founder LinkedIn profiles."""
        try:
            result = self._client.search(
                query=f"{domain} founder's Linkedin page:",
                type="keyword",
                num_results=5,
                include_domains=["linkedin.com"],
            )
            
            founders = []
            for r in result.results:
                # Extract name from LinkedIn URL or title
                name = r.title.split(" - ")[0] if r.title else ""
                if "/in/" in r.url:
                    # Try to extract name from URL path
                    url_name = r.url.split("/in/")[-1].split("/")[0].replace("-", " ").title()
                    if not name:
                        name = url_name
                
                founders.append(FounderInfo(
                    name=name,
                    linkedin_url=r.url,
                ))
            
            return founders
            
        except Exception:
            return []
    
    def _fetch_competitors(self, domain: str, company_description: str) -> list[CompetitorInfo]:
        """Find and analyze competitors."""
        try:
            result = self._client.search_and_contents(
                query=company_description,
                type="auto",
                num_results=5,
                summary={
                    "query": "Explain in one/two lines what does this company do in simple english. "
                             "Don't use any difficult words."
                },
                livecrawl="fallback",
                exclude_text=[domain],
                exclude_domains=[domain, f"*.{domain}"],
            )
            
            competitors = []
            for r in result.results:
                summary = getattr(r, 'summary', '') or ''
                competitors.append(CompetitorInfo(
                    name=urlparse(r.url).netloc.replace("www.", ""),
                    url=r.url,
                    description=summary,
                ))
            
            return competitors
            
        except Exception:
            return []
    
    def _fetch_news(self, domain: str) -> list[NewsArticle]:
        """Fetch recent news coverage."""
        try:
            result = self._client.search_and_contents(
                query=f"{domain} Latest News:",
                category="news",
                type="keyword",
                text=True,
                livecrawl="always",
                include_text=[domain],
                num_results=10,
                exclude_domains=[domain],
            )
            
            news = []
            for r in result.results:
                source = urlparse(r.url).netloc.replace("www.", "")
                news.append(NewsArticle(
                    title=r.title or "",
                    url=r.url,
                    source=source,
                    summary=(r.text or "")[:500],
                ))
            
            return news
            
        except Exception:
            return []
    
    def _fetch_social_profiles(self, domain: str) -> list[SocialProfile]:
        """Find social media profiles."""
        profiles = []
        
        # Twitter/X
        twitter = self._fetch_single_social(
            domain, 
            platform="twitter",
            query=f"{domain} Twitter (X) profile:",
            include_domains=["x.com", "twitter.com"],
        )
        if twitter:
            profiles.append(twitter)
        
        # GitHub
        github = self._fetch_single_social(
            domain,
            platform="github",
            query=f"{domain} Github:",
            include_domains=["github.com"],
        )
        if github:
            profiles.append(github)
        
        # YouTube
        youtube = self._fetch_single_social(
            domain,
            platform="youtube",
            query=f"{domain} YouTube channel:",
            include_domains=["youtube.com"],
        )
        if youtube:
            profiles.append(youtube)
        
        # TikTok
        tiktok = self._fetch_single_social(
            domain,
            platform="tiktok",
            query=f"{domain} Tiktok:",
            include_domains=["tiktok.com"],
        )
        if tiktok:
            profiles.append(tiktok)
        
        return profiles
    
    def _fetch_single_social(
        self, 
        domain: str, 
        platform: str, 
        query: str,
        include_domains: list[str],
    ) -> Optional[SocialProfile]:
        """Fetch a single social media profile."""
        try:
            result = self._client.search(
                query=query,
                type="keyword",
                num_results=1,
                include_domains=include_domains,
            )
            
            if result.results:
                return SocialProfile(
                    platform=platform,
                    url=result.results[0].url,
                    handle=result.results[0].title or "",
                )
            return None
            
        except Exception:
            return None
    
    def _fetch_wikipedia(self, domain: str) -> Optional[WikipediaInfo]:
        """Fetch Wikipedia information if available."""
        try:
            result = self._client.search_and_contents(
                query=f"{domain} company wikipedia page:",
                type="keyword",
                num_results=1,
                include_domains=["wikipedia.org"],
                include_text=[domain],
                text=True,
            )
            
            if result.results:
                return WikipediaInfo(
                    url=result.results[0].url,
                    summary=(result.results[0].text or "")[:1000],
                )
            return None
            
        except Exception:
            return None
    
    def _fetch_profile_url(self, domain: str, profile_domain: str) -> str:
        """Fetch a specific profile URL (crunchbase, pitchbook, tracxn)."""
        try:
            result = self._client.search(
                query=f"{domain} {profile_domain.split('.')[0]} profile:",
                type="keyword",
                num_results=1,
                include_domains=[profile_domain],
                include_text=[domain],
            )
            
            if result.results:
                return result.results[0].url
            return ""
            
        except Exception:
            return ""
