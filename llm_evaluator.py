import requests
import json


class LLMMealEvaluator:

    def __init__(self, model="llama3.1:8b-instruct-q4_K_M"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    def evaluate(
        self,
        user_profile,
        meal_plan,
        calories,
        macros,
        rag_context,
        biomarker_recommendations,
        gene_recommendations
    ):

        foods = [
            r.get("food", "")
            for r in rag_context[:15]
        ]

        biomarker_text = []

        for b in biomarker_recommendations:

            biomarker_text.append(
                f"{b.get('biomarker')}={b.get('status')}"
            )

        gene_text = []

        for g in gene_recommendations:

            gene_text.append(
                f"{g.get('gene')} ({g.get('variant')})"
            )

        prompt = f"""
You are an expert clinical nutrition evaluator.

Evaluate whether this meal plan is clinically appropriate.

USER:
Age: {user_profile.get('age')}
Gender: {user_profile.get('gender')}
Diet: {user_profile.get('diet_preference')}

TARGETS:
Calories: {calories}
Protein: {macros.get('protein_g')}
Carbs: {macros.get('carbs_g')}
Fat: {macros.get('fats_g')}

BIOMARKERS:
{", ".join(biomarker_text)}

GENES:
{", ".join(gene_text)}

ALLOWED FOODS:
{", ".join(foods)}

MEAL PLAN:
{meal_plan}

Evaluate:
1. Clinical correctness
2. Macro balance
3. Food suitability
4. Meal diversity
5. Safety

Return short evaluation only.
"""

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 200
            }
        }

        try:

            response = requests.post(
                self.url,
                json=payload,
                timeout=180
            )

            print("EVALUATOR STATUS:", response.status_code)

            if response.status_code != 200:

                return {
                    "evaluation_error": response.text
                }

            data = response.json()

            return {
                "evaluation": data.get(
                    "response",
                    "No evaluation returned"
                ).strip()
            }

        except Exception as e:

            return {
                "evaluation_error": str(e)
            }