import requests


class NutritionLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    def generate_plan(self, user_profile, rag_context, calories, macros):
        print("\n================= LLM INPUT DEBUG =================")
        print("Diet Preference:", user_profile.get("diet_preference"))
        print("RAG Foods:", [c.get("food") for c in rag_context])
        print("===================================================")

        if not rag_context:
            return "Error: No suitable ingredients found in the Knowledge Graph matching your dietary profile."

        prompt = self._build_prompt(user_profile, rag_context, calories, macros)

        print("\n================= LLM PROMPT =================")
        print(prompt)
        print("==============================================")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 420,
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=300
            )

            response.raise_for_status()

            result = response.json().get("response", "").strip()

            print("\n================= LLM OUTPUT =================")
            print(result)
            print("==============================================")

            return result

        except Exception as e:
            print("\n================= LLM ERROR =================")
            print(str(e))
            print("=============================================")

            return f"Service Error: Unable to generate plan ({str(e)})"

    def _build_prompt(self, user, context, calories, macros):
        context_text = ""
        food_list = []

        for c in context[:8]:
            food_name = c.get("food", "N/A")
            food_list.append(food_name)

            nutrients = ", ".join(
                [n.get("name", "Unknown") for n in c.get("nutrients", [])[:3]]
            )

            reason = c.get("reason", "")

            context_text += f"""
Food: {food_name}
Nutrients: {nutrients}
Clinical Reason: {reason}
"""

        allowed_foods = ", ".join(food_list)

        diet = user.get("diet_preference", "vegetarian").lower()

        if diet == "vegetarian":
            diet_rule = "User is VEGETARIAN. Use only vegetarian foods."
        else:
            diet_rule = "User is NON-VEGETARIAN. Vegetarian foods and animal foods are allowed."

        genes = ", ".join(
            [g.get("name", "") for g in user.get("genes", [])]
        ).strip()

        if not genes:
            genes = "None reported"

        return f"""
You are a Clinical Dietitian specialized in realistic Indian meal planning.

{diet_rule}

ALLOWED MAIN FOODS:
{allowed_foods}

STRICT RULES:
1. Use mainly the allowed foods listed above.
2. You may use common Indian supporting ingredients: onion, tomato, garlic, ginger, spices, oil, salt.
3. Breakfast should be light Indian breakfast.
4. Lunch should be the main meal.
5. Dinner should be lighter than lunch.
6. Use variety across meals.
7. Do NOT write exclusions like "without X".
8. Do NOT write warnings, notes, brackets, or explanations outside meals.
9. Generate ALL 3 meals completely.

USER PROFILE:
Age: {user.get('age')}
Gender: {user.get('gender')}
Diet: {diet}
Genes: {genes}

DAILY TARGETS:
Calories: {calories} kcal
Protein: {macros.get('protein_g', 0)} g
Carbs: {macros.get('carbs_g', 0)} g
Fat: {macros.get('fats_g', 0)} g

KNOWLEDGE GRAPH EVIDENCE:
{context_text}

OUTPUT FORMAT:

Breakfast:
1) Dish Name (Main Ingredients): short health reason

Lunch:
1) Dish Name (Main Ingredients): short health reason

Dinner:
1) Dish Name (Main Ingredients): short health reason

Keep total output under 260 words.
Use practical Indian dishes only.
"""