"""
Research Summarizer - Extracts ad-ready insights from company research.

Takes raw research.json and produces research-display.json with:
- Key findings summary
- Hook angles for ads
- Testimonial themes
- Unique value propositions
- Target audience details

This is Phase 0.1 in the director workflow, run after research (Phase 0).
"""

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .models import CompanyInfo


@dataclass
class ResearchDisplay:
    """
    Ad-ready summary of company research.
    
    Contains extracted insights, hook angles, and content ready
    for video script generation.
    """
    
    # Core product info
    company_name: str
    product_name: str
    tagline: str
    description: str
    
    # Key findings
    core_differentiator: str
    target_users: str
    key_feature: str
    
    # Ad content
    hook_angles: list[str] = field(default_factory=list)
    testimonial_themes: list[str] = field(default_factory=list)
    unique_value_props: list[str] = field(default_factory=list)
    target_conditions: list[str] = field(default_factory=list)
    
    # Competitor context
    main_competitors: list[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "key_findings": {
                "product": f"{self.product_name} - {self.description}",
                "tagline": self.tagline,
                "core_differentiator": self.core_differentiator,
                "target_users": self.target_users,
                "key_feature": self.key_feature,
            },
            "ad_content": {
                "hook_angles": self.hook_angles,
                "testimonial_themes": self.testimonial_themes,
                "unique_value_props": self.unique_value_props,
            },
            "audience": {
                "target_conditions": self.target_conditions,
                "main_competitors": self.main_competitors,
            },
            "metadata": {
                "company_name": self.company_name,
                "product_name": self.product_name,
            },
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


class ResearchSummarizer:
    """
    Summarizes company research into ad-ready insights using LLM.
    
    Takes research.json as input and produces research-display.json
    with hook angles, testimonial themes, and key findings extracted.
    """
    
    def __init__(self, openai_api_key: str | None = None):
        """
        Initialize the Research Summarizer.
        
        Args:
            openai_api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
        """
        self._openai_client = None
        
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY", "")
        if api_key:
            try:
                import openai
                self._openai_client = openai.OpenAI(api_key=api_key)
            except Exception:
                pass
    
    def summarize(
        self,
        research_data: dict,
        verbose: bool = False,
    ) -> ResearchDisplay:
        """
        Summarize research data into ad-ready insights.
        
        Args:
            research_data: Parsed research.json data
            verbose: Print progress messages
            
        Returns:
            ResearchDisplay with extracted insights.
        """
        company = research_data.get("company", {})
        competitors = research_data.get("competitors", [])
        
        # Extract basic info
        company_name = company.get("name", "Unknown")
        description = company.get("description", "")
        main_product = company.get("main_product", "")
        target_users = company.get("target_users", "")
        key_points = company.get("key_points", {})
        strengths = company.get("strengths", [])
        
        # Try to get tagline from key_points
        tagline = key_points.get("tagline", "")
        
        # Extract product name from main_product or company name
        product_name = company_name
        if main_product and " - " in main_product:
            product_name = main_product.split(" - ")[0].strip()
        elif main_product:
            product_name = main_product.split()[0] if main_product else company_name
        
        # Get competitor names
        main_competitors = [
            c.get("name", "").replace("apps.apple.com", "App Store listing")
            for c in competitors[:5]
            if c.get("name")
        ]
        
        # Use LLM to extract ad-ready insights
        if self._openai_client:
            if verbose:
                print("  - Extracting ad insights with LLM...")
            
            insights = self._extract_insights_with_llm(
                research_data, verbose
            )
            
            if insights:
                return ResearchDisplay(
                    company_name=company_name,
                    product_name=insights.get("product_name", product_name),
                    tagline=insights.get("tagline", tagline),
                    description=insights.get("description", description),
                    core_differentiator=insights.get("core_differentiator", ""),
                    target_users=insights.get("target_users", target_users),
                    key_feature=insights.get("key_feature", ""),
                    hook_angles=insights.get("hook_angles", []),
                    testimonial_themes=insights.get("testimonial_themes", []),
                    unique_value_props=insights.get("unique_value_props", strengths),
                    target_conditions=insights.get("target_conditions", []),
                    main_competitors=main_competitors,
                )
        
        # Fallback: basic extraction without LLM
        return ResearchDisplay(
            company_name=company_name,
            product_name=product_name,
            tagline=tagline,
            description=description[:200] if description else "",
            core_differentiator=key_points.get("unique_features", ""),
            target_users=target_users,
            key_feature=key_points.get("problem_solved", ""),
            hook_angles=[],
            testimonial_themes=[],
            unique_value_props=strengths,
            target_conditions=[],
            main_competitors=main_competitors,
        )
    
    def _extract_insights_with_llm(
        self,
        research_data: dict,
        verbose: bool = False,
    ) -> Optional[dict]:
        """Use LLM to extract ad-ready insights from research."""
        try:
            company = research_data.get("company", {})
            competitors = research_data.get("competitors", [])
            
            # Build context from research
            research_context = f"""
Company: {company.get('name', 'Unknown')}
URL: {company.get('url', '')}
Description: {company.get('description', '')}
Main Product: {company.get('main_product', '')}
Target Users: {company.get('target_users', '')}
Strengths: {', '.join(company.get('strengths', []))}
Key Points: {json.dumps(company.get('key_points', {}), indent=2)}

Competitors:
{chr(10).join([f"- {c.get('name', '')}: {c.get('description', '')[:100]}" for c in competitors[:5]])}
"""

            prompt = f"""Analyze this company research and extract ad-ready insights for a short-form video ad (TikTok/Reels style).

{research_context}

Extract the following in JSON format. These will be used in 15-30 second video ads:

{{
    "product_name": "Main product/app name",
    "tagline": "Core tagline (extract from research, don't make up)",
    "description": "2-3 sentence product description",
    "core_differentiator": "What makes this different in one punchy sentence",
    "target_users": "Specific target audience (be specific about conditions/situations)",
    "key_feature": "The ONE killer feature with memorable phrasing (include specific data if available, like '20 seconds')",
    "hook_angles": [
        "Problem-agitation hook - acknowledge their pain point",
        "Contrast hook - what if X didn't have to be Y?",
        "Specific number hook - include a number/stat",
        "Emotional validation hook - you're not alone/crazy",
        "Curiosity gap hook - hint at solution without revealing"
    ],
    "testimonial_themes": [
        "Before/after transformation with specific detail",
        "Doctor/credibility angle",
        "Comparison to old way of doing things",
        "Emotional relief quote",
        "Specific feature appreciation"
    ],
    "unique_value_props": [
        "Specific feature with benefit",
        "Another specific feature with benefit",
        "Third specific feature with benefit"
    ],
    "target_conditions": [
        "Specific condition 1",
        "Specific condition 2",
        "Specific condition 3",
        "Specific condition 4",
        "Specific condition 5"
    ]
}}

CRITICAL INSTRUCTIONS:
1. Hook angles must sound CONVERSATIONAL, not like marketing copy
2. Use SPECIFIC details from the research (e.g., "20 seconds", "Flare Mode", "spoons")
3. Good hook examples:
   - "Bad days are hard to explain - what if tracking didn't make them worse?"
   - "20 seconds. That's all it takes."
   - "When brain fog hits, the last thing you need is a complex form"
   - "Stop spending spoons on tracking"
4. Testimonials should sound like REAL users, not marketing speak
5. Good testimonial examples:
   - "Used to have a page-long list, now track same detail in 30 seconds"
   - "My doctor actually listens now - the reports gave me credibility"
   - "Brain fog used to mean lost data. Now Clue remembers for me"
6. Extract terminology from the research (spoons, flare, brain fog, etc.)

Respond ONLY with valid JSON, no markdown formatting."""

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",  # Use full model for better creative output
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher for creative output
                max_tokens=1500,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up potential markdown formatting
            if result_text.startswith("```"):
                result_text = re.sub(r"^```(?:json)?\n?", "", result_text)
                result_text = re.sub(r"\n?```$", "", result_text)
            
            return json.loads(result_text)
            
        except Exception as e:
            if verbose:
                print(f"    Warning: LLM insight extraction failed: {e}")
            return None
    
    def summarize_from_file(
        self,
        research_path: Path,
        output_path: Optional[Path] = None,
        verbose: bool = False,
    ) -> ResearchDisplay:
        """
        Load research.json and produce research-display.json.
        
        Args:
            research_path: Path to research.json
            output_path: Path for output (default: research-display.json in same dir)
            verbose: Print progress messages
            
        Returns:
            ResearchDisplay with extracted insights.
        """
        # Load research data
        with open(research_path) as f:
            research_data = json.load(f)
        
        # Summarize
        display = self.summarize(research_data, verbose=verbose)
        
        # Save output
        if output_path is None:
            output_path = research_path.parent / "research-display.json"
        
        with open(output_path, "w") as f:
            f.write(display.to_json(indent=2))
        
        return display
