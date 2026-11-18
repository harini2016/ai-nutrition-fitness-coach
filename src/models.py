from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List


@dataclass
class UserProfile:
    condition: str
    weekly_calorie_budget: int = 14000
    weekly_carb_budget: int = 350
    preferences: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class DailyPlan:
    day: int
    meals: List[str]
    workout: str
    calories: int
    net_carbs_g: int
    protein_g: int
    glycemic_notes: str = ""


@dataclass
class NutritionPlanReport:
    profile: UserProfile
    status: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    days: List[DailyPlan] = field(default_factory=list)
    total_calories: int = 0
    total_net_carbs_g: int = 0
    total_protein_g: int = 0
    beam_score: float = 0.0
    mode: str = "deterministic-baseline"
    message: str = ""
    clinical_guidelines_used: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines: List[str] = [
            f"# 7-Day Personalized Nutrition & Fitness Plan ({self.profile.condition})",
            "",
            f"- **Generated on:** {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Execution Mode:** {self.mode}",
            f"- **Status:** {self.status}",
            f"- **Weekly Target:** {self.profile.weekly_calorie_budget} kcal | {self.profile.weekly_carb_budget}g net carbs",
            "",
        ]

        if self.status != "COMPLETED":
            lines.extend([
                "## Safety Guardrail & Human Escalation Notice",
                "",
                f"> {self.message}",
                "",
            ])
        else:
            lines.extend([
                "## Executive Weekly Summary",
                f"- **Planned Total Calories:** {self.total_calories} / {self.profile.weekly_calorie_budget} kcal",
                f"- **Planned Total Net Carbs:** {self.total_net_carbs_g}g / {self.profile.weekly_carb_budget}g",
                f"- **Planned Total Protein:** {self.total_protein_g}g",
                f"- **ToT Beam Confidence Score:** {self.beam_score:.3f} (Beam Width W=3, Depth D=7)",
                "",
                "## Daily Schedule (Days 1–7)",
                "",
            ])
            for d in self.days:
                lines.append(f"### Day {d.day} ({d.calories} kcal | {d.net_carbs_g}g net carbs | {d.protein_g}g protein)")
                for m in d.meals:
                    lines.append(f"- {m}")
                lines.append(f"- **Workout:** {d.workout}")
                if d.glycemic_notes:
                    lines.append(f"- **Clinical Note:** {d.glycemic_notes}")
                lines.append("")

        lines.extend([
            "---",
            "## Mandatory Safety & Non-Medical Disclaimer",
            "**IMPORTANT NOTICE:** This is not medical advice; AI can make mistakes. "
            "This system provides lifestyle and nutritional education only and does not diagnose conditions "
            "or recommend medications. Always consult a licensed healthcare provider or registered dietitian.",
        ])
        return "\n".join(lines)
