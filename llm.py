import requests
import json

class NutritionLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    def generate_plan(self, user_profile, rag_context,calories,macros):
        print("\n LLM INPUT DEBUG ")
        print("User Profile:")
        print(json.dumps(user_profile, indent=2))

        print("\RAG Context (first 3):")
        print(json.dumps(rag_context[:3], indent=2))
        print("\n")

        prompt = self._build_prompt(user_profile, rag_context,calories,macros)

  
        print("\n FINAL PROMPT ")
        print(prompt)
        print("\n")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 500,
                "temperature": 0.4
            }
        }

        response = requests.post(
            self.url,
            json=payload,
            timeout=1000
        )

        if response.status_code != 200:
            print("Ollama raw response:", response.text)
            raise RuntimeError(f"Ollama error: {response.text}")

        result = response.json().get("response", "").strip()

        print("\n LLM OUTPUT ")
        print(result)
        print("\n")

        return result

    def _build_prompt(self, user, context,calories,macros):
        context_text = ""

        for c in context[:3]:
            foods = ", ".join(c.get("foods", [])[:3]) or "None"
            genes = ", ".join(g.get("gene", "N/A") for g in c.get("genes", [])[:2]) or "None"

            context_text += f"""
                    Biomarker: {c.get('biomarker', 'N/A')}
                    Nutrient: {c.get('nutrient', 'N/A')}
                    Food Sources: {foods}
                    Genes: {genes}"""

        return f"""
You are a nutrition assistant.

User Profile:
Age: {user.get('age')}
Gender: {user.get('gender')}
Diet: {user.get('diet_preference')}
Activity Level: {user.get('activity_level')}

Daily Nutrition Targets:
- Total Calories: {calories} kcal
- Protein: {macros.get('protein_g')} g
- Carbohydrates: {macros.get('carbs_g')} g
- Fats: {macros.get('fats_g')} g

Meal Split Guidance:
- Breakfast: ~30% of total calories
- Lunch: ~40% of total calories
- Dinner: ~30% of total calories

Macronutrient Distribution Rules:
- Protein: distribute evenly across all meals.
- Carbohydrates: higher at lunch, moderate at breakfast, lighter at dinner.
- Fats: moderate and balanced across meals; avoid very high-fat meals.


Knowledge Graph Context:
{context_text}

Task:
Generate a 1-day Indian meal plan with Breakfast, Lunch, and Dinner.

Rules:
- Meals MUST approximately respect calorie and protein targets.
- Prefer high-protein Indian foods when protein is high.
- Ignore foods that conflict with biomarkers or gene rules.
- Be concise.
- Use exactly this format:

Breakfast: [Meal name] - [Short description]
Lunch: [Meal name] - [Short description]
Dinner: [Meal name] - [Short description]

Total response under 300 words.
"""