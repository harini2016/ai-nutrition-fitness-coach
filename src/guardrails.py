from __future__ import annotations

import re
from typing import Tuple

MEDICATION_PATTERNS = [
    r"\bozempic\b", r"\bwegovy\b", r"\bmounjaro\b", r"\bzepbound\b",
    r"\bglp-1\b", r"\bmetformin\b", r"\binsulin\b", r"\blevothyroxine\b",
    r"\bmedication\b", r"\bprescription\b", r"\bweight[- ]loss drug\b",
    r"\bappetite suppressant\b", r"\bdosage\b", r"\bpill\b", r"\bdiagnos(e|is)\b",
]

RED_FLAG_PATTERNS = [
    r"\bpregnan(t|cy)\b", r"\beating disorder\b", r"\banorexia\b", r"\bbulimia\b",
    r"\bchest pain\b", r"\bhypoglycemi(a|c) shock\b", r"\bketoacidosis\b",
]

CONTRAINDICATED_TERMS = [
    "white rice", "soda", "candy", "sugary", "medication", "ozempic", "pill"
]


def validate_user_input(notes: str, condition: str, daily_calories: int) -> Tuple[bool, str]:
    """Input triage guardrail blocking medications, medical red flags, and crash diets."""
    combined = f"{notes} {condition}".lower()
    for pattern in MEDICATION_PATTERNS:
        if re.search(pattern, combined):
            return False, (
                "ESCALATION [Pharmacological / Clinical Scope]: This assistant focuses exclusively on "
                "sustainable lifestyle, nutrition, and exercise modifications. It cannot recommend, "
                "evaluate, or adjust medications or weight-loss drugs. Please consult a licensed physician."
            )

    for pattern in RED_FLAG_PATTERNS:
        if re.search(pattern, combined):
            return False, (
                "ESCALATION [High-Risk Medical Red Flag]: Your profile indicates a clinical condition or "
                "acute symptom requiring direct supervision by a healthcare professional or registered dietitian."
            )

    if daily_calories < 1200:
        return False, (
            "GUARDRAIL BLOCK [Unsafe Caloric Target]: Daily targets below 1,200 kcal/day pose severe "
            "nutritional risks and are blocked by safety policy. Please specify >= 1,200 kcal/day."
        )

    return True, "OK"


def check_candidate_safety(
    meals: list[str],
    new_cum_calories: int,
    new_cum_carbs: int,
    weekly_cal_budget: int,
    max_allowed_cum_carbs: float,
) -> bool:
    """Stage-1 deterministic heuristic check pruning unsafe or over-budget branches."""
    if new_cum_calories > weekly_cal_budget:
        return False
    if new_cum_carbs > max_allowed_cum_carbs:
        return False
    joined = " ".join(meals).lower()
    if any(term in joined for term in CONTRAINDICATED_TERMS):
        return False
    return True
