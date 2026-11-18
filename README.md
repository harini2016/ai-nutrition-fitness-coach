# Autonomous AI Nutrition & Fitness Coach

## Overview

This repository contains the capstone implementation of the **Autonomous AI Nutrition & Fitness Coach**—a stateful, safety-first personal assistant agent designed to generate customized 7-day meal and exercise plans for individuals managing chronic health conditions (such as Type 2 Diabetes, PCOS, and Thyroid disorders) exclusively through sustainable lifestyle modifications.

The agent can:

- Triage user profiles to enforce a strict lifestyle-only operational boundary (blocking medication or weight-loss drug inquiries, medical red flags, and crash diets)
- Retrieve condition-specific clinical nutrition guidelines via an MCP Context Server backed by LlamaIndex (`BAAI/bge-small-en-v1.5`)
- Query verified macronutrient data from the public USDA FoodData Central API
- Optimize 7-day meal and workout schedules using a **Tree-of-Thought (ToT) Beam Search** ($b=3, W=3, D=7$) orchestrated via LangGraph
- Prune unsafe or over-budget branches deterministically before scoring candidates
- Generate structured Markdown plans with mandatory non-medical safety disclaimers

The agent works in two modes:
- **Default mode:** Deterministic baseline planner (runs immediately with zero API keys required).
- **LLM-enhanced mode:** Dynamic LangChain LCEL structured thought generation if `OPENAI_API_KEY` is configured.

## Project Structure

```text
ai-nutrition-fitness-coach/
├── src/
│   ├── __init__.py           # Package exports (NutritionCoachAgent, CoachConfig)
│   ├── agent.py              # LangGraph Tree-of-Thought (W=3, D=7) orchestration
│   ├── cli.py                # Command-line interface for generating 7-day plans
│   ├── guardrails.py         # Input triage, anti-medication filters, and heuristic pruning
│   ├── llm_planner.py        # LangChain LCEL Thought Generator (with deterministic fallback)
│   ├── mcp_tools.py          # MCP Context Server (LlamaIndex RAG + USDA API)
│   └── models.py             # Data models and Markdown report renderer
├── data/
│   └── clinical_rules/
│       └── lifestyle_guidelines.md  # Curated public nutrition rules for RAG
├── tests/
│   └── test_agent.py         # Test suite verifying guardrails, escalation, and 7-day ToT plans
├── nutrition_plan.md         # Sample generated 7-day plan output artifact
├── README.md                 # Setup, usage, architecture, and safety documentation
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variable template
```

## Setup

1. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```powershell
   python -m pip install -r requirements.txt
   ```

3. **Configure Environment Variables (Optional for LLM mode):**
   Copy `.env.example` to `.env`:
   ```env
   OPENAI_API_KEY=
   OPENAI_MODEL=gpt-4o-mini
   OPENAI_BASE_URL=https://api.openai.com/v1
   USDA_API_KEY=DEMO_KEY
   ```
   *(Do not commit `.env` or API keys to source control.)*

## Run

Generate a personalized 7-day nutrition and fitness plan directly from the command line:

```powershell
python -m src.cli --condition "Type 2 Diabetes" --calories 14000 --carbs 350 --output nutrition_plan.md
```

## Output Format

The generated Markdown plan includes:
- **Executive Weekly Summary:** Planned Total Calories, Net Carbs, Protein, and ToT Beam Confidence Score
- **Daily Schedule (Days 1–7):** Meals, Workouts, and Clinical Glycemic Notes
- **Mandatory Safety & Non-Medical Disclaimer:** *"This is not medical advice; AI can make mistakes."*

## Tests

Run the test suite using `unittest` or `pytest`:

```powershell
python -m unittest discover -s tests -v
```

## Safety & Non-Medical Notes

- **This is not medical advice; AI can make mistakes.**
- The agent operates strictly within a lifestyle-only boundary and refuses requests for weight-loss medications, prescriptions, or clinical diagnoses.
- All clinical reference files in `data/` use publicly available, non-proprietary educational guidelines.
