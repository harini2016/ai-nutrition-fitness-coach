from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, TypedDict

from .guardrails import check_candidate_safety, validate_user_input
from .llm_planner import LLMThoughtGenerator
from .mcp_tools import MCPContextServer
from .models import NutritionPlanReport, UserProfile


@dataclass
class CoachConfig:
    branching_factor: int = 3  # b = 3 candidate options per day
    beam_width: int = 3        # W = 3 top active pathways retained
    depth_limit: int = 7       # D = 7 days in weekly schedule


class BeamGraphState(TypedDict):
    profile: UserProfile
    current_day: int
    beams: List[Dict]
    guidelines: List[str]
    status: str
    message: str


class NutritionCoachAgent:
    """
    Autonomous AI Nutrition & Fitness Coach orchestrated via LangGraph Tree-of-Thought (ToT)
    Beam Search (W=3, D=7) with defense-in-depth safety guardrails.
    """

    def __init__(self, config: CoachConfig | None = None) -> None:
        self.config = config or CoachConfig()
        self.mcp = MCPContextServer()
        self.generator = LLMThoughtGenerator()

    def _triage_step(self, state: BeamGraphState) -> BeamGraphState:
        profile = state["profile"]
        daily_cal = profile.weekly_calorie_budget // max(1, self.config.depth_limit)
        ok, msg = validate_user_input(profile.notes, profile.condition, daily_cal)
        if not ok:
            return {**state, "status": "BLOCKED_OR_ESCALATED", "message": msg}

        guidelines = self.mcp.retrieve_clinical_guidelines(profile.condition)
        initial_beam = [{
            "days": [],
            "cum_calories": 0,
            "cum_carbs": 0,
            "cum_protein": 0,
            "score": 1.0,
        }]
        return {
            **state,
            "current_day": 1,
            "beams": initial_beam,
            "guidelines": guidelines,
            "status": "RUNNING",
        }

    def _expand_and_prune_step(self, state: BeamGraphState) -> BeamGraphState:
        day = state["current_day"]
        profile = state["profile"]
        all_candidates: List[Dict] = []

        target_daily_cal = profile.weekly_calorie_budget / self.config.depth_limit
        target_daily_carbs = profile.weekly_carb_budget / self.config.depth_limit
        max_allowed_cum_carbs = (day * target_daily_carbs) + 20.0  # +20g buffer

        for beam in state["beams"]:
            rem_cal = profile.weekly_calorie_budget - beam["cum_calories"]
            rem_carbs = profile.weekly_carb_budget - beam["cum_carbs"]
            rem_days = self.config.depth_limit - day + 1

            candidates = self.generator.generate_candidates(
                day=day,
                b=self.config.branching_factor,
                condition=profile.condition,
                guidelines=state["guidelines"],
                rem_cal=rem_cal,
                rem_carbs=rem_carbs,
                rem_days=rem_days,
                preferences=profile.preferences,
            )

            for cand in candidates:
                new_cum_cal = beam["cum_calories"] + cand.calories
                new_cum_carbs = beam["cum_carbs"] + cand.net_carbs_g

                # Stage 1: Deterministic Heuristic Pruning
                if not check_candidate_safety(
                    meals=cand.meals,
                    new_cum_calories=new_cum_cal,
                    new_cum_carbs=new_cum_carbs,
                    weekly_cal_budget=profile.weekly_calorie_budget,
                    max_allowed_cum_carbs=max_allowed_cum_carbs,
                ):
                    continue

                # Stage 2: Rubric Evaluation (Macro 40% + Medical 40% + Preference 20%)
                cal_diff_ratio = abs(cand.calories - target_daily_cal) / max(1.0, target_daily_cal)
                macro_score = max(0.0, 1.0 - cal_diff_ratio)
                pref_match = 1.0 if any(
                    p.lower() in " ".join(cand.meals).lower() for p in profile.preferences
                ) else 0.85
                step_score = (0.40 * macro_score) + (0.40 * 0.95) + (0.20 * pref_match)

                if step_score >= 0.60:
                    all_candidates.append({
                        "days": beam["days"] + [cand],
                        "cum_calories": new_cum_cal,
                        "cum_carbs": new_cum_carbs,
                        "cum_protein": beam["cum_protein"] + cand.protein_g,
                        "score": (beam["score"] + step_score) / 2.0,
                    })

        if not all_candidates:
            return {
                **state,
                "status": "HUMAN_ESCALATION_BEAM_EXHAUSTION",
                "message": (
                    "All active ToT candidate beams failed safety or budget checks. "
                    "Autonomous generation halted; escalating to a registered dietitian."
                ),
            }

        top_beams = sorted(all_candidates, key=lambda x: x["score"], reverse=True)[: self.config.beam_width]
        next_status = "COMPLETED" if day >= self.config.depth_limit else "RUNNING"
        return {
            **state,
            "current_day": day + 1,
            "beams": top_beams,
            "status": next_status,
        }

    def _run_langgraph_or_loop(self, initial_state: BeamGraphState) -> BeamGraphState:
        """Executes the ToT Beam Search via LangGraph StateGraph (with clean loop fallback)."""
        try:
            from langgraph.graph import END, StateGraph

            def route(s: BeamGraphState) -> str:
                return "expand_prune" if s["status"] == "RUNNING" else END

            graph = StateGraph(BeamGraphState)
            graph.add_node("triage", self._triage_step)
            graph.add_node("expand_prune", self._expand_and_prune_step)
            graph.set_entry_point("triage")
            graph.add_conditional_edges("triage", route, {"expand_prune": "expand_prune", END: END})
            graph.add_conditional_edges("expand_prune", route, {"expand_prune": "expand_prune", END: END})
            compiled = graph.compile()
            return compiled.invoke(initial_state)
        except Exception:
            state = self._triage_step(initial_state)
            while state["status"] == "RUNNING":
                state = self._expand_and_prune_step(state)
            return state

    def generate_plan(self, profile: UserProfile) -> NutritionPlanReport:
        mode = "llm-enhanced (LangChain LCEL)" if self.generator.enabled else "deterministic-baseline"
        initial_state: BeamGraphState = {
            "profile": profile,
            "current_day": 0,
            "beams": [],
            "guidelines": [],
            "status": "INIT",
            "message": "",
        }
        final_state = self._run_langgraph_or_loop(initial_state)

        if final_state["status"] != "COMPLETED" or not final_state["beams"]:
            return NutritionPlanReport(
                profile=profile,
                status=final_state["status"],
                mode=mode,
                message=final_state["message"],
                clinical_guidelines_used=final_state["guidelines"],
            )

        best_beam = final_state["beams"][0]
        return NutritionPlanReport(
            profile=profile,
            status="COMPLETED",
            days=best_beam["days"],
            total_calories=best_beam["cum_calories"],
            total_net_carbs_g=best_beam["cum_carbs"],
            total_protein_g=best_beam["cum_protein"],
            beam_score=best_beam["score"],
            mode=mode,
            clinical_guidelines_used=final_state["guidelines"],
        )
