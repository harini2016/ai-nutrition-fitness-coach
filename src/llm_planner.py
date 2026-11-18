from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field

from .models import DailyPlan


class DailyCandidateSchema(BaseModel):
    meals: List[str] = Field(description="Breakfast, Lunch, Dinner, and Snack")
    workout: str = Field(description="Daily physical activity recommendation")
    calories: int
    net_carbs_g: int
    protein_g: int
    glycemic_notes: str


class CandidateBatchSchema(BaseModel):
    candidates: List[DailyCandidateSchema]


class LLMThoughtGenerator:
    """
    Optional LangChain LCEL Thought Generator (enabled when OPENAI_API_KEY is set).
    Falls back cleanly to deterministic candidate generation when no API key is configured.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self._chain = None

        if self.api_key:
            try:
                from langchain_core.prompts import ChatPromptTemplate
                from langchain_openai import ChatOpenAI

                llm = ChatOpenAI(
                    model=self.model,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    temperature=0.3,
                )
                structured_llm = llm.with_structured_output(CandidateBatchSchema)
                prompt = ChatPromptTemplate.from_messages([
                    (
                        "system",
                        "You are the Thought Generator for a lifestyle-only AI Nutrition & Fitness Coach. "
                        "NEVER recommend medications, weight-loss drugs, or supplements. "
                        "Generate exactly {b} distinct daily meal & workout candidates for Day {day} "
                        "adhering strictly to these clinical guidelines:\n{guidelines}",
                    ),
                    (
                        "human",
                        "Condition: {condition} | Remaining Weekly Budget: {rem_cal} kcal, {rem_carbs}g net carbs "
                        "over {rem_days} remaining days. Preferences: {prefs}",
                    ),
                ])
                self._chain = prompt | structured_llm
            except Exception:
                self._chain = None

    @property
    def enabled(self) -> bool:
        return self._chain is not None

    def generate_candidates(
        self,
        day: int,
        b: int,
        condition: str,
        guidelines: List[str],
        rem_cal: int,
        rem_carbs: int,
        rem_days: int,
        preferences: List[str],
    ) -> List[DailyPlan]:
        if self._chain is not None:
            batch = self._chain.invoke({
                "b": b,
                "day": day,
                "guidelines": "\n".join(guidelines),
                "condition": condition,
                "rem_cal": rem_cal,
                "rem_carbs": rem_carbs,
                "rem_days": rem_days,
                "prefs": ", ".join(preferences) if preferences else "Balanced whole foods",
            })
            return [
                DailyPlan(
                    day=day,
                    meals=c.meals,
                    workout=c.workout,
                    calories=c.calories,
                    net_carbs_g=c.net_carbs_g,
                    protein_g=c.protein_g,
                    glycemic_notes=c.glycemic_notes,
                )
                for c in batch.candidates
            ]

        return self._deterministic_candidates(day, b, rem_cal, rem_carbs, rem_days)

    def _deterministic_candidates(
        self, day: int, b: int, rem_cal: int, rem_carbs: int, rem_days: int
    ) -> List[DailyPlan]:
        """Zero-key deterministic candidate generator for local verification and unit tests."""
        avg_cal = max(1250, min(2200, rem_cal // max(1, rem_days)))
        avg_carb = max(25, min(60, rem_carbs // max(1, rem_days)))

        templates = [
            DailyPlan(
                day=day,
                meals=[
                    "Breakfast: Spinach & mushroom egg scramble with sliced avocado",
                    "Lunch: Grilled wild salmon over mixed greens with olive oil vinaigrette",
                    "Dinner: Herb-roasted chicken breast, steamed broccoli, and quinoa",
                    "Snack: Unsweetened Greek yogurt with chia seeds and walnuts",
                ],
                workout="35-minute brisk incline walk + 15-minute core mobility",
                calories=avg_cal,
                net_carbs_g=max(20, avg_carb - 5),
                protein_g=145,
                glycemic_notes="Low-glycemic load (<10); high protein & healthy fats",
            ),
            DailyPlan(
                day=day,
                meals=[
                    "Breakfast: Chia pudding with unsweetened almond milk and pumpkin seeds",
                    "Lunch: Turkey & avocado lettuce wraps with cucumber salad",
                    "Dinner: Baked cod with roasted asparagus and cauliflower mash",
                    "Snack: Celery sticks with natural almond butter",
                ],
                workout="30-minute full-body resistance circuit",
                calories=max(1250, avg_cal - 120),
                net_carbs_g=max(20, avg_carb - 10),
                protein_g=138,
                glycemic_notes="Insulin-friendly low net-carb profile",
            ),
            DailyPlan(
                day=day,
                meals=[
                    "Breakfast: Plain Greek yogurt parfait with flaxseeds and berries",
                    "Lunch: Lentil and grilled chicken Mediterranean bowl",
                    "Dinner: Stir-fried tofu and bok choy with sesame ginger glaze",
                    "Snack: Handful of raw almonds and boiled egg",
                ],
                workout="40-minute moderate cycling + post-meal 10-minute walk",
                calories=avg_cal + 50,
                net_carbs_g=avg_carb,
                protein_g=132,
                glycemic_notes="High-fiber complex carbs paired with lean protein",
            ),
        ]
        return templates[:b]
