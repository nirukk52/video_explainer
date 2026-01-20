"""
Universal storytelling principles for video narration.

These principles apply to any educational/explainer video and help create
engaging, memorable content in the style of 3Blue1Brown, Veritasium, etc.

These are separate from the visual principles in principles.py, which focus
on visual design and animation. Narration principles focus on the written
script and storytelling structure.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class NarrationPrinciple:
    """A principle for good video narration."""

    id: int
    name: str
    description: str
    good_example: str
    bad_example: str
    check_question: str  # Question to ask when evaluating narration

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "good_example": self.good_example,
            "bad_example": self.bad_example,
            "check_question": self.check_question,
        }


# =============================================================================
# The 10 Universal Narration Principles
# =============================================================================

NARRATION_PRINCIPLES: list[NarrationPrinciple] = [
    NarrationPrinciple(
        id=1,
        name="Hook in the first sentence",
        description=(
            "Every scene should start with something that grabs attention - "
            "a surprising statistic, a provocative question, a bold claim, or a "
            "counter-intuitive insight. The hook creates immediate curiosity."
        ),
        good_example=(
            "'83.3% versus 13.4%. That's the difference between...' - "
            "Opens with dramatic contrast that demands explanation"
        ),
        bad_example=(
            "'In this section, we will discuss how AI models work.' - "
            "Generic, forgettable, doesn't create curiosity"
        ),
        check_question="Does the first sentence make viewers want to hear what's next?",
    ),
    NarrationPrinciple(
        id=2,
        name="Build tension before resolution",
        description=(
            "Don't give away the answer immediately. Present the problem, build "
            "anticipation, maybe hint at dead ends or challenges, THEN reveal the "
            "insight. The delay between question and answer is where learning happens."
        ),
        good_example=(
            "'The obvious solution seemed simple... but this hit a fundamental wall.' - "
            "Sets up expectation, then subverts it, creating tension"
        ),
        bad_example=(
            "'The solution is X. Here's why X works.' - "
            "No buildup, no tension, no payoff"
        ),
        check_question="Is there a moment of suspense or anticipation before the key insight?",
    ),
    NarrationPrinciple(
        id=3,
        name="Smooth transitions between scenes",
        description=(
            "Each scene should flow naturally into the next. End scenes with a bridge: "
            "'But there's a problem...', 'This leads to...', 'The question is...'. "
            "The transition creates momentum and narrative continuity."
        ),
        good_example=(
            "'The trade-off? Multiple model calls per reasoning step. Thinking takes time and compute.' - "
            "Ends with a natural lead-in to discussing limitations"
        ),
        bad_example=(
            "'That's how tree-of-thought works. Next, we'll look at fine-tuning.' - "
            "Abrupt topic change, no narrative connection"
        ),
        check_question="Does this scene end in a way that makes the next scene feel inevitable?",
    ),
    NarrationPrinciple(
        id=4,
        name="One key insight per scene",
        description=(
            "Don't overload viewers. Each scene should leave them with ONE clear "
            "takeaway - one 'aha' moment, one memorable fact, one new understanding. "
            "If you have multiple insights, split into multiple scenes."
        ),
        good_example=(
            "Scene focuses entirely on 'reasoning ability was already locked inside - "
            "it just needed to be unlocked' as the single insight"
        ),
        bad_example=(
            "Scene tries to explain chain-of-thought, self-consistency, and tree-of-thought "
            "all at once - too much to absorb"
        ),
        check_question="Can you state the ONE thing viewers should remember from this scene?",
    ),
    NarrationPrinciple(
        id=5,
        name="Use concrete analogies",
        description=(
            "Abstract concepts need concrete parallels. Connect new ideas to familiar "
            "experiences: 'Like learning chess by only knowing if you won or lost'. "
            "Good analogies make complex ideas instantly graspable."
        ),
        good_example=(
            "'Not by building smarter models - by giving them scratch paper.' - "
            "Chain-of-thought as 'scratch paper' is instantly understandable"
        ),
        bad_example=(
            "'The model outputs a probability distribution over the vocabulary space.' - "
            "Technically accurate but abstract and hard to visualize"
        ),
        check_question="Is there a real-world analogy that makes this concept intuitive?",
    ),
    NarrationPrinciple(
        id=6,
        name="Include emotional beats",
        description=(
            "Narration should evoke emotions: surprise ('Wait, that works?'), "
            "curiosity ('But why?'), satisfaction ('Aha!'), wonder ('That's remarkable'). "
            "Emotions make content memorable. Quote real moments when possible."
        ),
        good_example=(
            "'The training team documented an extraordinary moment: the model learned to write "
            "\"Wait, wait. That's an aha moment I can flag here.\"' - "
            "Real quote creates genuine wonder"
        ),
        bad_example=(
            "'The model improved its performance metrics.' - "
            "Dry, emotionless, forgettable"
        ),
        check_question="Will viewers feel something (curiosity, surprise, wonder) during this scene?",
    ),
    NarrationPrinciple(
        id=7,
        name="Match length to visual duration",
        description=(
            "Narration pace should match scene duration. Target ~150 words per minute "
            "(2.5 words/second). Too fast overwhelms; too slow loses attention. "
            "Leave room for visual breathing - not every second needs narration."
        ),
        good_example=(
            "25-second scene with ~60 words - comfortable pace with room for visuals"
        ),
        bad_example=(
            "25-second scene with 150 words - too rushed, viewers can't process"
        ),
        check_question="Does the word count match the target for this duration?",
    ),
    NarrationPrinciple(
        id=8,
        name="Ask rhetorical questions",
        description=(
            "Questions engage viewers actively. 'But how did they solve this?' "
            "'What if we tried something different?' Questions create mental gaps "
            "that viewers want to fill - they lean in waiting for the answer."
        ),
        good_example=(
            "'Here's the core problem. Your model generates a five-hundred-token reasoning chain "
            "that leads to the wrong answer. Which tokens caused the failure?' - "
            "Poses the puzzle viewers will learn to solve"
        ),
        bad_example=(
            "'Credit assignment is the problem of determining which decisions in a sequence "
            "deserve credit or blame.' - Declarative, doesn't engage viewer"
        ),
        check_question="Is there at least one question that makes viewers think?",
    ),
    NarrationPrinciple(
        id=9,
        name="Show progression and stakes",
        description=(
            "Help viewers understand why each step matters. What problem does this solve? "
            "What happens if we don't do this? What did we gain? Progress markers "
            "('But this hit a wall...', 'The breakthrough came when...') maintain engagement."
        ),
        good_example=(
            "'Models learned to copy the style... without understanding the underlying process. "
            "They memorized patterns, not principles.' - Shows what went wrong and why it matters"
        ),
        bad_example=(
            "'Next we used reinforcement learning instead.' - "
            "No explanation of why the change was needed"
        ),
        check_question="Will viewers understand why we're discussing this and what's at stake?",
    ),
    NarrationPrinciple(
        id=10,
        name="End with impact",
        description=(
            "Final scene should leave viewers with something memorable - a powerful "
            "conclusion, a thought-provoking question, or a glimpse of implications. "
            "The ending determines what viewers remember and share."
        ),
        good_example=(
            "'AI learned to think not by copying humans, but by discovering what works.' - "
            "Powerful conclusion that reframes everything"
        ),
        bad_example=(
            "'That concludes our overview of reasoning models.' - "
            "Forgettable, no lasting impression"
        ),
        check_question="Will this ending stick with viewers after the video ends?",
    ),
]


def get_principle_by_id(principle_id: int) -> Optional[NarrationPrinciple]:
    """Get a narration principle by its ID."""
    for principle in NARRATION_PRINCIPLES:
        if principle.id == principle_id:
            return principle
    return None


def get_principle_by_name(name: str) -> Optional[NarrationPrinciple]:
    """Get a narration principle by name (case-insensitive partial match)."""
    name_lower = name.lower()
    for principle in NARRATION_PRINCIPLES:
        if name_lower in principle.name.lower():
            return principle
    return None


def format_principles_for_prompt() -> str:
    """Format all narration principles for inclusion in an LLM prompt."""
    lines = ["## The 10 Narration Principles for Engaging Educational Videos\n"]

    for p in NARRATION_PRINCIPLES:
        lines.append(f"### {p.id}. {p.name}")
        lines.append(f"{p.description}\n")
        lines.append(f"**Good example:** {p.good_example}")
        lines.append(f"**Bad example:** {p.bad_example}")
        lines.append(f"**Check:** {p.check_question}\n")

    return "\n".join(lines)


def format_checklist_for_prompt() -> str:
    """Format narration principles as a checklist for evaluation."""
    lines = ["## Narration Quality Checklist\n"]
    lines.append("For each scene, evaluate against these criteria:\n")

    for p in NARRATION_PRINCIPLES:
        lines.append(f"[ ] {p.id}. **{p.name}**: {p.check_question}")

    return "\n".join(lines)
