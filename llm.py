import requests


class NutritionLLM:

    def __init__(self, model="phi3:mini"):
        self.model = model
        self.url = "http://127.0.0.1:11434/api/generate"

    # =========================================================
    # MAIN GENERATION
    # =========================================================
    def generate_plan(self, user_profile, rag_context, calories, macros):

        print("\n================= LLM INPUT DEBUG =================")
        print("Diet Preference:", user_profile.get("diet_preference"))
        print("RAG Foods:", [c.get("food") for c in rag_context[:8]])
        print("===================================================")

        if not rag_context:
            return "Error: No suitable ingredients found for the current clinical profile."

        prompt = self._build_prompt(user_profile, rag_context, calories, macros)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 250,
                "temperature": 0.1,
                "top_p": 0.8,
                "repeat_penalty": 1.1
            }
        }

        try:
            response = requests.post(self.url, json=payload, timeout=120)
            response.raise_for_status()

            result = response.json().get("response", "").strip()

            print("\n================= LLM OUTPUT =================")
            print(result)
            print("==============================================")

            return result

        except Exception as e:
            return f"Service Error: Unable to generate plan ({str(e)})"

    # =========================================================
    # BUILD PROMPT (FIXED ALIGNMENT)
    # =========================================================
    def _build_prompt(self, user, context, calories, macros):

        # =====================================================
        # SORT BY SCORE (IMPORTANT FIX)
        # =====================================================
        context = sorted(context, key=lambda x: x.get("score", 0), reverse=True)

        # =====================================================
        # FOOD EVIDENCE (NOW STRICTLY RANKED)
        # =====================================================
        food_lines = []
        allowed_foods = []

        for c in context[:8]:

            food = c.get("food", "N/A")
            score = c.get("score", 0)

            allowed_foods.append(food)

            nutrients = ", ".join([
                f"{n.get('name')} ({n.get('amount')})"
                for n in c.get("nutrients", [])[:4]
            ])

            reason = c.get("reason", "")

            food_lines.append(
                f"{food} (score: {score}): {reason}. Nutrients: {nutrients}"
            )

        context_text = "\n".join(food_lines)
        allowed_foods_text = ", ".join(allowed_foods)

        # =====================================================
        # DIET RULE
        # =====================================================
        diet = str(user.get("diet_preference", "vegetarian")).lower()

        diet_rule = (
            "Vegetarian only."
            if diet == "vegetarian"
            else "Vegetarian and non-vegetarian foods allowed."
        )

        # =====================================================
        # BIOMARKERS
        # =====================================================
        biomarker_lines = []

        for b in user.get("biomarkers", []):
            status = str(b.get("status", "")).strip().lower()

            if status and status != "normal":
                biomarker_lines.append(f"{b.get('name')}={status}")

        biomarker_summary = ", ".join(biomarker_lines) or "No major abnormal biomarkers"

        # =====================================================
        # GENES
        # =====================================================
        gene_lines = []

        for g in user.get("genes", []):
            variant = str(g.get("variant", "")).strip()

            if variant and variant.lower() != "normal":
                gene_lines.append(f"{g.get('name')} ({variant})")

        gene_summary = ", ".join(gene_lines) or "No major gene variants"

        # =====================================================
        # MACROS
        # =====================================================
        protein = macros.get("protein_g", 0)
        carbs = macros.get("carbs_g", 0)
        fats = macros.get("fats_g", 0)

        # =====================================================
        # FINAL PROMPT (STRENGTHENED CONSTRAINTS)
        # =====================================================
        return f"""
You are a Clinical Dietitian specialized in realistic Kerala style meal planning.

{diet_rule}

ALLOWED MAIN FOODS:
{allowed_foods}

STRICT RULES:
1. Use mainly the allowed foods listed above.
2. You may use common Kerala supporting ingredients: onion, tomato, garlic, ginger, spices, oil, salt.
3. Breakfast should be light Kerala breakfast with more protein .
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
Genes: {gene_summary}

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

total calories: X kcal
Use practical Kerala dishes only
total details should be complete and strictly follow the allowed foods and targets.
"""