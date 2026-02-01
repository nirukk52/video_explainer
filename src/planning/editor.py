"""Interactive plan editor for user review and refinement."""

import sys
from pathlib import Path

from ..models import VideoPlan
from .generator import PlanGenerator


class PlanEditor:
    """Interactive editor for reviewing and refining video plans."""

    def __init__(
        self,
        generator: PlanGenerator,
        plan_dir: Path,
    ):
        """Initialize the editor.

        Args:
            generator: PlanGenerator for refining plans
            plan_dir: Directory for saving plan files
        """
        self.generator = generator
        self.plan_dir = plan_dir

    def run_interactive_session(self, plan: VideoPlan) -> tuple[VideoPlan, bool]:
        """Run an interactive session for plan review.

        Args:
            plan: The initial video plan to review

        Returns:
            Tuple of (final_plan, was_approved)
        """
        current_plan = plan
        was_approved = False

        while True:
            # Display the plan
            print("\n" + self.generator.format_for_display(current_plan))
            print()

            # Get user input
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nExiting...")
                break

            if not user_input:
                continue

            # Parse command
            command = user_input.lower().split()[0]

            if command in ("a", "approve"):
                current_plan.status = "approved"
                from datetime import datetime
                current_plan.approved_at = datetime.now().isoformat()
                self._save_plan(current_plan)
                was_approved = True
                print("\n✓ Plan approved!")
                print(f"Run 'python -m src.cli script <project>' to generate the script.")
                break

            elif command in ("r", "refine"):
                # Get feedback (everything after the command)
                feedback = user_input[len(command):].strip()
                if not feedback:
                    print("Usage: r <feedback>")
                    print("Example: r Add more emphasis on position embeddings")
                    continue

                print("\nRefining plan...")
                try:
                    current_plan = self.generator.refine(current_plan, feedback)
                    self._save_plan(current_plan)
                    print("✓ Plan updated")
                except Exception as e:
                    print(f"Error refining plan: {e}")

            elif command in ("s", "save"):
                self._save_plan(current_plan)
                print(f"\n✓ Plan saved to {self.plan_dir}")

            elif command in ("q", "quit", "exit"):
                # Save draft before exiting
                self._save_plan(current_plan)
                print(f"\n✓ Draft saved to {self.plan_dir}")
                break

            elif command in ("h", "help", "?"):
                self._print_help()

            else:
                print(f"Unknown command: {command}")
                self._print_help()

        return current_plan, was_approved

    def _save_plan(self, plan: VideoPlan) -> None:
        """Save the current plan."""
        self.generator.save_plan(plan, self.plan_dir)

    def _print_help(self) -> None:
        """Print help information."""
        print("""
Commands:
  a, approve              Approve the plan and proceed
  r, refine <feedback>    Refine the plan with natural language feedback
  s, save                 Save the current draft
  q, quit                 Exit (saves draft automatically)
  h, help, ?              Show this help

Refinement examples:
  r Add arrows showing data flow in scene 2
  r Make the ASCII visual for scene 3 show a side-by-side comparison
  r Scene 4 should have the formula more prominent at the top
  r Add more emphasis on position embeddings
  r Reduce the duration of the hook scene
""")

    def display_plan(self, plan: VideoPlan) -> None:
        """Display a plan without entering interactive mode.

        Args:
            plan: The video plan to display
        """
        print(self.generator.format_for_display(plan))

    def approve_plan(self, plan: VideoPlan) -> VideoPlan:
        """Approve a plan without interactive session.

        Args:
            plan: The video plan to approve

        Returns:
            The approved plan
        """
        from datetime import datetime

        plan.status = "approved"
        plan.approved_at = datetime.now().isoformat()
        self._save_plan(plan)
        return plan
