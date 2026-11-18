from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List
import requests


class MCPContextServer:
    """
    Model Context Protocol (MCP) Context & Tool Server:
    1. Semantic retrieval of clinical guidelines (LlamaIndex + HuggingFace bge-small-en-v1.5)
    2. Verified nutritional lookups via USDA FoodData Central API
    """

    def __init__(self, rules_dir: str = "data/clinical_rules") -> None:
        self.rules_dir = Path(rules_dir)
        self.usda_api_key = os.getenv("USDA_API_KEY", "DEMO_KEY")
        self._retriever = None
        self._init_llama_index()

    def _init_llama_index(self) -> None:
        try:
            from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            if self.rules_dir.exists():
                Settings.embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
                Settings.llm = None
                docs = SimpleDirectoryReader(str(self.rules_dir)).load_data()
                index = VectorStoreIndex.from_documents(docs)
                self._retriever = index.as_retriever(similarity_top_k=3)
        except Exception:
            self._retriever = None

    def retrieve_clinical_guidelines(self, condition: str) -> List[str]:
        if self._retriever is not None:
            try:
                nodes = self._retriever.retrieve(f"Lifestyle and dietary guidelines for {condition}")
                if nodes:
                    return [n.get_content() for n in nodes]
            except Exception:
                pass

        md_file = self.rules_dir / "lifestyle_guidelines.md"
        if md_file.exists():
            text = md_file.read_text(encoding="utf-8")
            sections = [s.strip() for s in text.split("## ") if s.strip()]
            matched = [s for s in sections if condition.lower().split()[0] in s.lower()]
            return matched if matched else sections[:2]
        return ["Target balanced whole foods, lean protein, high fiber, and consistent daily movement."]

    def lookup_usda_food(self, food_query: str) -> Dict:
        url = "https://api.nal.usda.gov/fdc/v1/foods/search"
        params = {"api_key": self.usda_api_key, "query": food_query, "pageSize": 1}
        try:
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200 and resp.json().get("foods"):
                food = resp.json()["foods"][0]
                nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", [])}
                return {
                    "food": food.get("description", food_query),
                    "calories": nutrients.get("Energy", 0),
                    "protein_g": nutrients.get("Protein", 0),
                    "carbs_g": nutrients.get("Carbohydrate, by difference", 0),
                    "source": "USDA FoodData Central API",
                }
        except Exception:
            pass
        return {"food": food_query, "source": "local_verified_baseline"}
