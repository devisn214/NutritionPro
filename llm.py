import requests
import json

class NutritionLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    def generate_plan(self, user_profile, rag_context, calories, macros):
        print("\n LLM INPUT DEBUG ")
        print("User Profile:")
        print(json.dumps(user_profile, indent=2))

        print("\RAG Context (first 3):")
        print(json.dumps(rag_context[:6], indent=2))
        print("\n")

        prompt = self._build_prompt(user_profile, rag_context, calories, macros)

        print("\n FINAL PROMPT ")
        print(prompt)
        print("\n")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 600,
                "temperature": 0.35
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

    def _build_prompt(self, user, context, calories, macros):
        context_text = ""

        for c in context[:4]:
            foods = ", ".join(c.get("foods", [])[:4]) or "None"
            genes = ", ".join(g.get("gene", "N/A") for g in c.get("genes", [])[:3]) or "None"

            context_text += f"""
                    Biomarker: {c.get('biomarker', 'N/A')}
                    Nutrient: {c.get('nutrient', 'N/A')}
                    Food Sources: {foods}
                    Genes: {genes}"""

        return f"""
You are a clinical-grade personalized nutrition planning system.

User Profile:
Age: {user.get('age')}
Gender: {user.get('gender')}
Diet: {user.get('diet_preference')}
Activity Level: {user.get('activity_level')}

Health Logic:
- Some biomarkers may show deficiency or excess.
- Some gene variants alter absorption, metabolism, or sensitivity.
- Food selection MUST balance multiple objectives simultaneously.

Core Objectives:
1. Correct nutrient deficiencies.
2. Avoid nutrient excess.
3. Respect gene–nutrient interactions.
4. Maintain calorie & macronutrient balance.
5. Optimize overall metabolic health.

Daily Targets:
Calories: {calories} kcal
Protein: {macros.get('protein_g')} g
Carbs: {macros.get('carbs_g')} g
Fats: {macros.get('fats_g')} g

Meal Distribution:
Breakfast 30%, Lunch 40%, Dinner 30%

Macronutrient Distribution:
Protein: evenly across meals
Carbs: lunch > breakfast > dinner
Fats: balanced, avoid overload

Knowledge Graph Context:
{context_text}

Task:
Generate a 1-day Indian meal plan.

For EACH meal:
- Provide a short clinical justification for EACH food item explaining:
    • Which biomarker it helps
    • Which nutrient it provides
    • Which gene interaction it supports or avoids
    • If not directly biomarker-driven, explain which metabolic or health constraint it satisfies
- Exactly 2 food items.
- Each explanation must be ONE short sentence only (≤15 words).
- Do NOT exceed 30 words per meal.

Output Format:

Breakfast:
1) Food: Reason
2) Food: Reason

Lunch:
1) Food: Reason
2) Food: Reason

Dinner:
1) Food: Reason
2) Food: Reason
Rules:
- Justifications MUST be biologically meaningful.
- Multiple conditions may justify a single food.
- Do not list foods without reasons.
- Avoid contraindicated foods.

Max 300 words.
"""