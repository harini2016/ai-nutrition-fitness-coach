from __future__ import annotations

import argparse
from pathlib import Path

from src.agent import NutritionCoachAgent
from src.models import UserProfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a personalized 7-day lifestyle nutrition & fitness plan."
    )
    parser.add_argument("--condition", default="Type 2 Diabetes", help="Health condition (e.g., Type 2 Diabetes, PCOS, Thyroid)")
    parser.add_argument("--calories", type=int, default=14000, help="Weekly calorie budget (kcal)")
    parser.add_argument("--carbs", type=int, default=350, help="Weekly net carbohydrate budget (g)")
    parser.add_argument("--preferences", default="salmon, eggs, avocado, spinach", help="Comma-separated food preferences")
    parser.add_argument("--notes", default="Lifestyle-only nutrition and exercise plan", help="User goals or notes")
    parser.add_argument("--output", default="nutrition_plan.md", help="Output markdown file path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prefs = [p.strip() for p in args.preferences.split(",") if p.strip()]
    profile = UserProfile(
        condition=args.condition,
        weekly_calorie_budget=args.calories,
        weekly_carb_budget=args.carbs,
        preferences=prefs,
        notes=args.notes,
    )

    agent = NutritionCoachAgent()
    report = agent.generate_plan(profile)
    markdown = report.to_markdown()

    output_path = Path(args.output)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Plan generation finished | Status: {report.status} | Mode: {report.mode}")
    print(f"Saved report to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
