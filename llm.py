import requests

class NutritionLLM:
    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    # =========================================================
    # MAIN
    # =========================================================

    def generate_plan(
        self,
        user_profile,
        rag_context,
        optimized_plan,
        calories,
        macros,
        biomarker_recommendations,
        gene_recommendations
    ):
        print("\n================= LLM INPUT DEBUG =================")
        print("Diet Preference:", user_profile.get("diet_preference"))
        print("Optimized Breakfast:", [x.get("food") for x in optimized_plan.get("breakfast", [])])
        print("Optimized Lunch:", [x.get("food") for x in optimized_plan.get("lunch", [])])
        print("Optimized Dinner:", [x.get("food") for x in optimized_plan.get("dinner", [])])
        print("===================================================")

        prompt = self._build_prompt(
            user=user_profile,
            optimized_plan=optimized_plan
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 300,
                "temperature": 0.2, # Slightly bumped to 0.2 to allow it to retrieve real dish names creatively
                "top_p": 0.8,
                "repeat_penalty": 1.05,
                "num_ctx": 512,
                "num_thread": 4
            }
        }

        try:
            response = requests.post(
                self.url,
                json=payload,
                timeout=(10, 200)
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
            return "Unable to generate meal description."

    # =========================================================
    # PROMPT
    # =========================================================

    def _build_prompt(
        self,
        user,
        optimized_plan
    ):
        breakfast_foods = [x.get("food") for x in optimized_plan.get("breakfast", []) if x.get("food")]
        lunch_foods = [x.get("food") for x in optimized_plan.get("lunch", []) if x.get("food")]
        dinner_foods = [x.get("food") for x in optimized_plan.get("dinner", []) if x.get("food")]

        diet = str(user.get("diet_preference", "vegetarian")).lower()
        
        return f"""
Generate a realistic Kerala home-style meal plan for breakfast, lunch, and dinner.

Important Rules:
- Identify an ACTUAL, traditional Kerala dish  that utilizes the provided ingredients.
- DO NOT invent new dishes, weird salads, or random mixtures. Name a real, recognizable Kerala dish.
- "Why Recommended" MUST be exactly one simple sentence explaining its nutritional benefit (e.g., "Rich in protein and fiber for sustained energy.").
- "Preparation" MUST be exactly one simple sentence.
- Maximum 3 lines per meal.
- Do not list ingredients separately.
- Do not give macro numbers or percentages.
- No markdown formatting.
- Ensure breakfast, lunch, and dinner are completed.

Diet: {diet}

Breakfast ingredients provided: {", ".join(breakfast_foods)}
Lunch ingredients provided: {", ".join(lunch_foods)}
Dinner ingredients provided: {", ".join(dinner_foods)}

Output Format:

Breakfast:
Dish: 
Why Recommended: 
Preparation: 

Lunch:
Dish: 
Why Recommended: 
Preparation: 

Dinner:
Dish: 
Why Recommended: 
Preparation: 
"""