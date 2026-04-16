import requests
import json

class NutritionLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    def generate_plan(self, user_profile, rag_context, calories, macros):
        print("\n--- LLM INPUT DEBUG ---")
        print(f"Diet Preference: {user_profile.get('diet_preference')}")
        print(f"RAG Foods: {[c.get('food') for c in rag_context]}")

        if not rag_context:
            return "Error: No suitable ingredients found in the Knowledge Graph matching your dietary profile."

        prompt = self._build_prompt(user_profile, rag_context, calories, macros)
        print("\n--- LLM PROMPT DEBUG ---")
        print(prompt)
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 500,
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json().get("response", "").strip()
            return result
        except Exception as e:
            return f"Service Error: Unable to generate plan ({str(e)})"

    def _build_prompt(self, user, context, calories, macros):
        # Build the structured context from RAG
        context_text = ""
        food_list = []
        
        for c in context:
            food_name = c.get("food", "N/A")
            food_list.append(food_name)
            nutrients = ", ".join([n.get("name", "Unknown") for n in c.get("nutrients", [])[:3]])
            
            context_text += f"""
Food: {food_name}
Nutrients: {nutrients}
Clinical Reason: {c.get('reason', '')}
"""

        allowed_foods = ", ".join(food_list)
        diet = user.get('diet_preference', 'vegetarian').lower()

        return f"""
You are a Clinical Dietitian specialized in Indian Cuisine.
STRICT DIET REQUIREMENT: The user is {diet.upper()}. 
If an ingredient in the allowed list is non-vegetarian and the user is vegetarian, DO NOT USE IT.

HARD CONSTRAINT:
Base Ingredients ONLY: [{allowed_foods}]

CORE RULES:
1. Every dish MUST be primarily based on the allowed ingredients.
2. If an ingredient is a supplement (like Cod Liver Oil), suggest it as a 'Side Supplement' with the meal.
3. Use Indian spices and minor cooking ingredients (oil, salt) as needed.
4. DO NOT repeat the same main food in every meal.
5. JUSTIFICATION: Every dish must have a 1-sentence reason mentioning a nutrient or health goal.

User Profile:
- Age/Sex: {user.get('age')} / {user.get('gender')}
- Diet: {diet}
- Goals: Address deficiencies and respect genetic markers (e.g., {', '.join([g.get('name') for g in user.get('genes', [])])})

Daily Targets:
- Calories: {calories} kcal
- Macros: P:{macros.get('protein_g', 0)}g, C:{macros.get('carbs_g', 0)}g, F:{macros.get('fats_g', 0)}g

Knowledge Graph Evidence:
{context_text}

FORMAT:
Breakfast:
1) Dish Name (Main Ingredients): Reason
Lunch:
1) Dish Name (Main Ingredients): Reason
Dinner:
1) Dish Name (Main Ingredients): Reason

Max 220 words. Focus on realistic Indian preparation.
"""