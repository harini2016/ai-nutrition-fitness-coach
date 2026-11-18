import unittest
from src.agent import NutritionCoachAgent
from src.models import UserProfile


def test_medication_request_escalates():
    agent = NutritionCoachAgent()
    profile = UserProfile(
        condition="Type 2 Diabetes",
        weekly_calorie_budget=14000,
        weekly_carb_budget=350,
        notes="Can you prescribe Ozempic or recommend a weight-loss drug?",
    )
    report = agent.generate_plan(profile)
    assert report.status == "BLOCKED_OR_ESCALATED"
    assert "Pharmacological" in report.message
    assert "This is not medical advice; AI can make mistakes." in report.to_markdown()


def test_crash_diet_blocked():
    agent = NutritionCoachAgent()
    profile = UserProfile(
        condition="PCOS",
        weekly_calorie_budget=6300,  # 900 kcal/day (< 1,200 kcal/day threshold)
        weekly_carb_budget=250,
        notes="Rapid weight loss plan",
    )
    report = agent.generate_plan(profile)
    assert report.status == "BLOCKED_OR_ESCALATED"
    assert "1,200 kcal/day" in report.message


def test_valid_7day_tot_plan_completion():
    agent = NutritionCoachAgent()
    profile = UserProfile(
        condition="Type 2 Diabetes",
        weekly_calorie_budget=14000,
        weekly_carb_budget=350,
        preferences=["salmon", "avocado", "spinach"],
        notes="Sustainable blood sugar management through diet and exercise",
    )
    report = agent.generate_plan(profile)
    assert report.status == "COMPLETED"
    assert len(report.days) == 7
    assert report.total_calories <= 14000
    assert report.total_net_carbs_g <= 350
    md = report.to_markdown()
    assert "This is not medical advice; AI can make mistakes." in md


class TestNutritionCoachAgent(unittest.TestCase):
    def test_medication_escalation(self):
        test_medication_request_escalates()

    def test_crash_diet(self):
        test_crash_diet_blocked()

    def test_valid_plan(self):
        test_valid_7day_tot_plan_completion()


if __name__ == "__main__":
    unittest.main()
