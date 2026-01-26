"""
Company Researcher - Core research logic using Exa.ai with web scraping fallback.

Orchestrates multiple Exa.ai searches to build comprehensive
company intelligence reports. Falls back to direct web scraping
and LLM extraction when Exa.ai returns poor results (common for
new/niche companies not well indexed).

Mirrors the functionality of:
https://github.com/exa-labs/company-researcher but in Python.
"""

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .models import (
    CompanyInfo,
    CompetitorInfo,
    FounderInfo,
    FundingInfo,
    NewsArticle,
    SocialProfile,
    WikipediaInfo,
)

# User agent for direct web requests
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
    Researches companies using Exa.ai semantic search with web scraping fallback.
    
    Provides methods to gather comprehensive company intelligence
    including website content, funding data, founders, competitors,
    news coverage, and social media presence.
    
    When Exa.ai returns poor results (common for new/niche companies),
    falls back to direct web scraping + LLM extraction.
    
    Based on: https://github.com/exa-labs/company-researcher
    """
    
    def __init__(
        self,
        exa_api_key: str | None = None,
        openai_api_key: str | None = None,
    ):
        """
        Initialize the Company Researcher.
        
        Args:
            exa_api_key: Exa.ai API key. Falls back to EXA_API_KEY env var.
            openai_api_key: OpenAI API key for LLM extraction fallback.
                           Falls back to OPENAI_API_KEY env var.
        """
        self._exa_client = None
        self._openai_client = None
        
        # Initialize Exa client (optional - can work without it)
        exa_key = exa_api_key or os.getenv("EXA_API_KEY", "")
        if exa_key:
            try:
                from exa_py import Exa
                self._exa_client = Exa(api_key=exa_key)
            except Exception:
                pass  # Exa not available, will use fallback
        
        # Initialize OpenAI client for LLM extraction
        openai_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=openai_key)
            except Exception:
                pass  # OpenAI not available
    
    def research(
        self,
        company_url: str,
        include_funding: bool = True,
        include_founders: bool = True,
        include_competitors: bool = True,
        include_news: bool = True,
        include_social: bool = True,
        include_wikipedia: bool = True,
        enrich_with_llm: bool = True,
        verbose: bool = False,
    ) -> CompanyReport:
        """
        Perform comprehensive research on a company.
        
        Uses Exa.ai as primary source, with direct web scraping + LLM
        extraction as fallback for companies not well indexed.
        
        Args:
            company_url: The company's website URL (e.g., "exa.ai")
            include_funding: Fetch funding/valuation data
            include_founders: Fetch founder LinkedIn profiles
            include_competitors: Find and analyze competitors
            include_news: Fetch recent news coverage
            include_social: Fetch social media profiles
            include_wikipedia: Fetch Wikipedia info
            enrich_with_llm: Use LLM to clean up and structure results
            verbose: Print progress messages
            
        Returns:
            CompanyReport with all gathered intelligence.
        """
        # Normalize URL
        url = self._normalize_url(company_url)
        domain = urlparse(url).netloc.replace("www.", "")
        
        if verbose:
            print(f"Researching: {domain}")
        
        # 1. Scrape main website content (try Exa first, then direct scraping)
        if verbose:
            print("  - Fetching website content...")
        company = self._fetch_website_content(url, domain, verbose=verbose)
        
        # Check if we got meaningful content - if not, try fallback
        use_fallback = (
            self._is_poor_result(company.description) or
            self._has_html_artifacts(company.description)
        )
        
        if use_fallback:
            if verbose:
                print("  - Exa.ai returned poor/messy results, trying direct scraping + LLM...")
            company = self._fetch_website_content_fallback(url, domain, verbose=verbose)
        elif enrich_with_llm and self._openai_client and self._has_html_artifacts(company.description):
            # Even if Exa worked, clean up the description with LLM
            if verbose:
                print("  - Cleaning up results with LLM...")
            raw_content = company.key_points.get("website_content", company.description)
            enriched = self._extract_company_info_with_llm(
                raw_content, url, domain, company.name, company.description[:200], verbose
            )
            if enriched:
                company = enriched
        
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
        
        # 5. Find competitors (only if we have valid company description)
        competitors = []
        if include_competitors and company.description and not self._is_poor_result(company.description):
            if verbose:
                print("  - Analyzing competitors...")
            competitors = self._fetch_competitors(domain, company.description)
            # Filter out irrelevant results
            competitors = self._filter_relevant_competitors(competitors, domain)
        
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
            # Filter out irrelevant social results
            social_profiles = self._filter_relevant_social(social_profiles, domain)
        
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
    
    def _is_poor_result(self, text: str) -> bool:
        """Check if a result indicates poor/failed Exa.ai response."""
        if not text:
            return True
        
        # Common error indicators
        error_indicators = [
            "error fetching",
            "missing 1 required positional argument",
            "not found",
            "no results",
            "unable to",
            "failed to",
        ]
        
        text_lower = text.lower()
        for indicator in error_indicators:
            if indicator in text_lower:
                return True
        
        # Too short to be meaningful
        if len(text) < 50:
            return True
        
        return False
    
    def _has_html_artifacts(self, text: str) -> bool:
        """Check if text has HTML/markdown artifacts that indicate raw scraping."""
        artifact_patterns = [
            r"\\\_",  # Escaped underscores
            r"&#x?\d+;",  # HTML entities like &#x27;
            r"\!\[.*?\]",  # Markdown image syntax
            r"arrow\_forward",  # Material icons
            r"check\_circle",
            r"mic\n",  # Icon names
        ]
        
        for pattern in artifact_patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def _filter_relevant_competitors(
        self, 
        competitors: list[CompetitorInfo], 
        domain: str
    ) -> list[CompetitorInfo]:
        """Filter out irrelevant competitor results (e.g., StackOverflow links)."""
        # Domains that are never actual competitors
        irrelevant_domains = {
            "stackoverflow.com", "github.com", "dev.to", "medium.com",
            "reddit.com", "quora.com", "youtube.com", "twitter.com",
            "x.com", "linkedin.com", "facebook.com", "instagram.com",
            "readthedocs.io", "docs.python.org", "pypi.org", "npmjs.com",
            "exakat.io", "exakat.readthedocs.io",  # Specific noise seen in results
        }
        
        filtered = []
        for c in competitors:
            comp_domain = urlparse(c.url).netloc.replace("www.", "")
            
            # Skip if it's a known irrelevant domain
            if any(irr in comp_domain for irr in irrelevant_domains):
                continue
            
            # Skip if the description mentions "error" or common programming terms
            desc_lower = c.description.lower()
            if any(term in desc_lower for term in [
                "error", "exception", "python", "javascript", "php",
                "missing argument", "positional argument", "stack trace"
            ]):
                continue
            
            filtered.append(c)
        
        return filtered
    
    def _filter_relevant_social(
        self, 
        profiles: list[SocialProfile], 
        domain: str
    ) -> list[SocialProfile]:
        """Filter out social profiles that aren't actually the company's."""
        company_name = domain.split(".")[0].lower()
        
        filtered = []
        for p in profiles:
            url_lower = p.url.lower()
            handle_lower = p.handle.lower()
            
            # Check if the URL or handle contains the company name
            if company_name in url_lower or company_name in handle_lower:
                filtered.append(p)
                continue
            
            # For platforms like GitHub, be more lenient
            # (the company might have a different username)
            # But filter out obviously unrelated results
            if p.platform == "github":
                # Skip obviously unrelated repos
                if any(term in url_lower for term in [
                    "machine-learning", "algorithms", "tutorial", "example"
                ]):
                    continue
            
            # For Twitter, skip if it's a completely different company
            if p.platform == "twitter":
                if "kyowa" in url_lower or "media-center" in url_lower:
                    continue
        
        return filtered
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL to have https:// prefix."""
        if not url.startswith("http"):
            url = f"https://{url}"
        return url
    
    def _fetch_website_content_fallback(
        self, 
        url: str, 
        domain: str, 
        verbose: bool = False
    ) -> CompanyInfo:
        """
        Fallback: Directly scrape website and use LLM to extract company info.
        
        Used when Exa.ai returns poor results for new/niche companies.
        """
        try:
            # Direct HTTP request to the website
            headers = {"User-Agent": DEFAULT_USER_AGENT}
            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                response.raise_for_status()
                html_content = response.text
            
            # Parse HTML and extract text
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Remove unwanted elements
            for element in soup.select("script, style, nav, footer, header, noscript"):
                element.decompose()
            
            # Get text content
            raw_text = soup.get_text(separator="\n", strip=True)
            
            # Truncate to reasonable size for LLM
            raw_text = raw_text[:15000]
            
            # Extract meta description if available
            meta_desc = ""
            desc_tag = soup.find("meta", {"name": "description"})
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"]
            
            og_desc = soup.find("meta", property="og:description")
            if og_desc and og_desc.get("content"):
                meta_desc = meta_desc or og_desc["content"]
            
            # Extract title
            title = domain.split(".")[0].title()
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip().split("|")[0].split("-")[0].strip()
            
            # Use LLM to extract structured company info
            if self._openai_client:
                company_info = self._extract_company_info_with_llm(
                    raw_text, url, domain, title, meta_desc, verbose
                )
                if company_info:
                    return company_info
            
            # Fallback to basic extraction without LLM
            description = meta_desc if meta_desc else raw_text[:500]
            
            return CompanyInfo(
                name=title,
                url=url,
                description=description,
                key_points={"website_content": raw_text[:3000]},
            )
            
        except Exception as e:
            if verbose:
                print(f"    Warning: Fallback scraping failed: {e}")
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description=f"Could not fetch website content",
            )
    
    def _extract_company_info_with_llm(
        self,
        raw_text: str,
        url: str,
        domain: str,
        title: str,
        meta_desc: str,
        verbose: bool = False,
    ) -> Optional[CompanyInfo]:
        """Use OpenAI to extract structured company info from raw website text."""
        try:
            prompt = f"""Analyze this company website content and extract structured information.

Website URL: {url}
Website Title: {title}
Meta Description: {meta_desc}

Website Content:
{raw_text[:10000]}

Extract the following information in JSON format:
{{
    "name": "Company name (proper casing)",
    "description": "2-3 sentence description of what the company does and its main product",
    "main_product": "Name and brief description of main product/service",
    "target_users": "Who is this product for? Be specific.",
    "pricing": "Pricing info if available, or 'Not specified'",
    "strengths": ["Key strength 1", "Key strength 2", ...],
    "key_points": {{
        "tagline": "Company tagline or main value prop",
        "unique_features": "What makes this product unique",
        "problem_solved": "What problem does it solve"
    }}
}}

Respond ONLY with valid JSON, no markdown formatting."""

            response = self._openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                result_text = re.sub(r"^```(?:json)?\n?", "", result_text)
                result_text = re.sub(r"\n?```$", "", result_text)
            
            data = json.loads(result_text)
            
            return CompanyInfo(
                name=data.get("name", title),
                url=url,
                description=data.get("description", meta_desc),
                main_product=data.get("main_product", ""),
                target_users=data.get("target_users", ""),
                pricing=data.get("pricing", ""),
                strengths=data.get("strengths", []),
                key_points=data.get("key_points", {}),
            )
            
        except Exception as e:
            if verbose:
                print(f"    Warning: LLM extraction failed: {e}")
            return None
    
    def _fetch_website_content(self, url: str, domain: str, verbose: bool = False) -> CompanyInfo:
        """Fetch and summarize main website content using Exa.ai."""
        if not self._exa_client:
            # No Exa client, return empty to trigger fallback
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description="",
            )
        
        try:
            # Get main page content using search_and_contents with the URL
            # This is more reliable than get_contents which has parameter issues
            result = self._exa_client.search_and_contents(
                query=f"site:{domain}",
                type="keyword",
                text=True,
                num_results=1,
                livecrawl="always",
                include_domains=[domain],
            )
            
            main_content = ""
            description = ""
            if result.results:
                main_content = result.results[0].text or ""
                # Use summary if available
                if hasattr(result.results[0], 'summary') and result.results[0].summary:
                    description = result.results[0].summary
                else:
                    # Extract first meaningful paragraph as description
                    description = main_content[:500].strip()
            
            # Get subpages (about, pricing, faq, blog) for more context
            try:
                subpages_result = self._exa_client.search_and_contents(
                    query=f"{domain}",
                    type="neural",
                    text=True,
                    num_results=5,
                    livecrawl="always",
                    include_domains=[domain],
                )
                
                if subpages_result.results:
                    for r in subpages_result.results:
                        if r.text:
                            main_content += f"\n\n{r.url}:\n{r.text[:2000]}"
            except Exception:
                pass  # Subpages are optional
            
            # Check if we got meaningful content
            if not description or len(description) < 50:
                return CompanyInfo(
                    name=domain.split(".")[0].title(),
                    url=url,
                    description="",  # Will trigger fallback
                )
            
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description=description,
                key_points={"website_content": main_content[:3000]},
            )
            
        except Exception as e:
            if verbose:
                print(f"    Warning: Exa.ai failed: {e}")
            return CompanyInfo(
                name=domain.split(".")[0].title(),
                url=url,
                description="",  # Will trigger fallback
            )
    
    def _fetch_linkedin_profile(self, domain: str) -> str:
        """Find company LinkedIn profile URL."""
        if not self._exa_client:
            return ""
        
        try:
            result = self._exa_client.search(
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
        if not self._exa_client:
            return None
        
        try:
            result = self._exa_client.search_and_contents(
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
        if not self._exa_client:
            return []
        
        try:
            result = self._exa_client.search(
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
        if not self._exa_client:
            return []
        
        try:
            # Use a more targeted query to find actual competitors
            # Strip any error messages from description
            clean_desc = company_description[:300] if len(company_description) > 300 else company_description
            
            result = self._exa_client.search_and_contents(
                query=f"companies similar to {clean_desc}",
                type="auto",
                num_results=10,  # Get more results to filter
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
        if not self._exa_client:
            return []
        
        try:
            result = self._exa_client.search_and_contents(
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
        if not self._exa_client:
            return None
        
        try:
            result = self._exa_client.search(
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
        if not self._exa_client:
            return None
        
        try:
            result = self._exa_client.search_and_contents(
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
        if not self._exa_client:
            return ""
        
        try:
            result = self._exa_client.search(
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
