"""
Anchor picker prompt for the Witness agent's reconnaissance step.

Used to pick best text anchors from REAL page content (no hallucination).
"""

ANCHOR_PICKER_PROMPT = """You are given a list of ACTUAL text snippets found on a web page.
Your job is to pick the 2-4 best ones that would help locate this element:

Target element description: "{description}"

Available text snippets from the page:
{text_candidates}

Rules:
- Pick ONLY from the provided list (copy exactly, including newlines)
- Prefer specific text: prices, model names, unique labels
- Avoid generic text like "Learn more", "Contact", navigation items
- Pick texts that would be INSIDE or NEAR the target element

Return JSON:
{{"selected_anchors": ["exact text 1", "exact text 2"], "reasoning": "brief explanation"}}"""
