import requests


class NutritionLLM:

    def __init__(self, model="phi3:mini"):

        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    # =========================================================
    # MAIN GENERATION
    # =========================================================

    def generate_plan(
        self,
        user_profile,
        rag_context,
        optimized_plan,
        calories,
        macros
    ):

        print("\n================= LLM INPUT DEBUG =================")
        print("Diet Preference:", user_profile.get("diet_preference"))
        print("RAG Foods:", [c.get("food") for c in rag_context[:8]])
        print("===================================================")

        if not rag_context:
            return "Error: No suitable ingredients found."

        prompt = self._build_prompt(
            user_profile,
            rag_context,
            optimized_plan,
            calories,
            macros
        )

        payload = {

            "model": self.model,

            "prompt": prompt,

            "stream": False,

            "options": {

                "num_predict": 300,

                "temperature": 0.1,

                "top_p": 0.8,

                "repeat_penalty": 1.1,

                "num_ctx": 2048
            }
        }

        try:

            response = requests.post(
                self.url,
                json=payload,
                timeout=120
            )

            response.raise_for_status()

            result = response.json().get(
                "response",
                ""
            ).strip()

            print("\n================= LLM OUTPUT =================")
            print(result)
            print("==============================================")

            return result

        except Exception as e:

            print("\n================= LLM ERROR =================")
            print(str(e))
            print("=============================================")

            return f"Service Error: Unable to generate plan ({str(e)})"

    # =========================================================
    # BUILD PROMPT
    # =========================================================

    def _build_prompt(
        self,
        user,
        context,
        optimized_plan,
        calories,
        macros
    ):

        context = sorted(
            context,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        allowed_foods = []

        for c in context[:15]:

            food = c.get("food")

            if food and food not in allowed_foods:
                allowed_foods.append(food)

        breakfast_foods = [
            x.get("food")
            for x in optimized_plan.get("breakfast", [])
            if x.get("food")
        ]

        lunch_foods = [
            x.get("food")
            for x in optimized_plan.get("lunch", [])
            if x.get("food")
        ]

        dinner_foods = [
            x.get("food")
            for x in optimized_plan.get("dinner", [])
            if x.get("food")
        ]

        diet = str(
            user.get(
                "diet_preference",
                "vegetarian"
            )
        ).lower()

        diet_rule = (
            "Vegetarian only."
            if diet == "vegetarian"
            else "Vegetarian and non-vegetarian foods allowed."
        )

        biomarker_summary = []

        for b in user.get("biomarkers", []):

            status = str(
                b.get("status", "")
            ).lower()

            if status and status != "normal":

                biomarker_summary.append(
                    f"{b.get('name')}={status}"
                )

        gene_summary = []

        for g in user.get("genes", []):

            variant = str(
                g.get("variant", "")
            ).strip()

            if variant and variant.lower() != "normal":

                gene_summary.append(
                    f"{g.get('name')} ({variant})"
                )

        return f"""
You are a Kerala clinical dietitian.

{diet_rule}

IMPORTANT BIOMARKERS:
{", ".join(biomarker_summary[:5])}

GENETIC FACTORS:
{", ".join(gene_summary[:5])}

ALLOWED FOODS:
{", ".join(allowed_foods[:15])}

BREAKFAST FOODS:
{", ".join(breakfast_foods[:4])}

LUNCH FOODS:
{", ".join(lunch_foods[:6])}

DINNER FOODS:
{", ".join(dinner_foods[:4])}

TARGETS:
Calories: {calories} kcal
Protein: {macros.get('protein_g', 0)} g
Carbs: {macros.get('carbs_g', 0)} g
Fat: {macros.get('fats_g', 0)} g

STRICT RULES:
1. Generate COMPLETE breakfast lunch and dinner.
2. Use realistic Kerala dishes only.
3. Keep response concise.
4. Use mainly recommended foods.
5. Mention simple preparation briefly.
6. No long explanations.
7. No nutrition theory.
8. No markdown tables.
9. Generate ALL 3 meals completely.not cut off in between
10. Ensure meals approximately match macro targets.

OUTPUT FORMAT:

Breakfast:
- Dish name:Simple preparation mentioning the ingredients in 1 line

Lunch:
- Dish name:Simple preparation mentioning the ingredients in 1 line

Dinner:
- Dish name:Simple preparation mentioning the ingredients in 1 line
Daily Total:
Calories:
Protein:
Carbs:
Fat:

IMPORTANT:
1. Maximum 2 dishes per meal.
2. Maximum 1 sentence preparation.
3. Keep total output under 300 words.
4. No nutrition explanations.
5. No calorie explanation for each dish.
6. No long text.


"""