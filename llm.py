import requests


class NutritionLLM:

    def __init__(self, model="phi3:mini"):

        self.model = model

        self.url = "http://127.0.0.1:11434/api/generate"

    # =========================================================
    # MAIN GENERATION
    # =========================================================

    def generate_plan(self, user_profile, rag_context, optimized_plan, calories, macros, biomarker_recommendations, gene_recommendations):

        print("\n================= LLM INPUT DEBUG =================")

        print(
            "Diet Preference:",
            user_profile.get("diet_preference")
        )

        print(
            "RAG Foods:",
            [c.get("food") for c in rag_context[:8]]
        )

        print("===================================================")

        if not rag_context:

            return "Error: No suitable ingredients found."

        prompt = self._build_prompt(

            user=user_profile,

            context=rag_context,

            optimized_plan=optimized_plan,

            calories=calories,

            macros=macros,

            biomarker_recommendations=biomarker_recommendations,

            gene_recommendations=gene_recommendations
        )

        payload = {

            "model": self.model,

            "prompt": prompt,

            "stream": False,

            "options": {

                "num_predict": 500,

                "temperature": 0.15,

                "top_p": 0.85,

                "repeat_penalty": 1.1,

                "num_ctx": 4096
            }
        }

        try:

            response = requests.post(

                self.url,

                json=payload,

                timeout=(30, 300)
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

    def _build_prompt(self, user, context, optimized_plan, calories, macros, biomarker_recommendations, gene_recommendations):

        context = sorted(

            context,

            key=lambda x: x.get(
                "score",
                0
            ),

            reverse=True
        )

        allowed_foods = []

        for c in context[:20]:

            food = c.get("food")

            if food and food not in allowed_foods:

                allowed_foods.append(food)

        breakfast_foods = [

            x.get("food")

            for x in optimized_plan.get(
                "breakfast",
                []
            )

            if x.get("food")
        ]

        lunch_foods = [

            x.get("food")

            for x in optimized_plan.get(
                "lunch",
                []
            )

            if x.get("food")
        ]

        dinner_foods = [

            x.get("food")

            for x in optimized_plan.get(
                "dinner",
                []
            )

            if x.get("food")
        ]

        diet = str(

            user.get(
                "diet_preference",
                "vegetarian"
            )

        ).lower()

        # =====================================================
        # DIET RULES
        # =====================================================

        if diet == "vegan":

            diet_rule = (

                "Strict vegan diet only. "

                "Do not include milk, curd, paneer, cheese, butter, ghee, egg, meat, fish, or any animal-derived food."
            )

        elif diet == "vegetarian":

            diet_rule = (

                "Vegetarian diet only. "

                "Milk and dairy allowed. "

                "No egg, meat, or fish."
            )

        else:

            diet_rule = (

                "Vegetarian and non-vegetarian foods allowed."
            )

        # =====================================================
        # BIOMARKER SUMMARY
        # =====================================================

        biomarker_summary = []

        for b in biomarker_recommendations:

            biomarker_name = str(
                b.get("biomarker", "")
            )

            status = str(
                b.get("status", "")
            )

            nutrient = str(
                b.get("target_nutrient", "")
            )

            direction = str(
                b.get("direction", "")
            )

            biomarker_summary.append(

                f"{biomarker_name} = {status} → {direction} {nutrient}"
            )

        # =====================================================
        # GENE SUMMARY
        # =====================================================

        gene_summary = []

        for g in gene_recommendations:

            gene_name = str(
                g.get("gene", "")
            )

            genotype = str(
                g.get("genotype", "")
            )

            nutrient = str(
                g.get("nutrient_name", "")
            )

            direction = str(
                g.get("direction", "")
            )

            gene_summary.append(

                f"{gene_name} ({genotype}) → {direction} {nutrient}"
            )

        # =====================================================
        # SEMANTIC FOODS
        # =====================================================

        semantic_foods = []

        for item in context[:15]:

            semantic_foods.append(

                f"{item.get('food')} "

                f"(semantic={item.get('semantic_score',0)}, "

                f"confidence={item.get('confidence_score',0)}, "

                f"adaptive={item.get('adaptive_score',0)})"
            )

        # =====================================================
        # TARGET NUTRIENTS
        # =====================================================

        target_nutrients = []

        for item in context[:10]:

            for n in item.get(
                "nutrients",
                []
            ):

                nutrient_name = n.get("name")

                if nutrient_name and nutrient_name not in target_nutrients:

                    target_nutrients.append(
                        nutrient_name
                    )

        # =====================================================
        # FINAL PROMPT
        # =====================================================

        return f"""

You are an advanced AI Kerala clinical nutrition system.

Generate a highly personalized Kerala meal plan using biomarker analysis, genetic factors, semantic food retrieval, adaptive learning, confidence-aware ranking, and explainable nutritional reasoning.

=====================================================
USER PROFILE
=====================================================

Diet Preference:
{diet}

Age:
{user.get('age')}

Gender:
{user.get('gender')}

Weight:
{user.get('weight_kg')} kg

Height:
{user.get('height_cm')} cm

=====================================================
DIET RULES
=====================================================

{diet_rule}

=====================================================
BIOMARKER ANALYSIS
=====================================================

{chr(10).join(biomarker_summary[:10])}

=====================================================
GENETIC ANALYSIS
=====================================================

{chr(10).join(gene_summary[:10])}

=====================================================
SEMANTICALLY RANKED FOODS
=====================================================

{chr(10).join(semantic_foods)}

=====================================================
ALLOWED FOODS
=====================================================

{", ".join(allowed_foods[:20])}

=====================================================
OPTIMIZED BREAKFAST FOODS
=====================================================

{", ".join(breakfast_foods[:6])}

=====================================================
OPTIMIZED LUNCH FOODS
=====================================================

{", ".join(lunch_foods[:8])}

=====================================================
OPTIMIZED DINNER FOODS
=====================================================

{", ".join(dinner_foods[:6])}

=====================================================
TOP NUTRIENT TARGETS
=====================================================

{", ".join(target_nutrients[:12])}

=====================================================
TARGET DAILY MACROS
=====================================================

Calories:
{calories} kcal

Protein:
{macros.get('protein_g', 0)} g

Carbs:
{macros.get('carbs_g', 0)} g

Fat:
{macros.get('fats_g', 0)} g

IMPORTANT:
These macro targets are PRE-CALCULATED by the nutrition engine.
Your generated meals and serving quantities MUST approximately match these targets.

=====================================================
STRICT CLINICAL CONSTRAINTS
=====================================================

1. Generate COMPLETE breakfast, lunch and dinner.
2. Use realistic Kerala dishes only.
3. Use mainly foods from semantic retrieval.
4. Use foods from optimized meal selections.
5. Keep meals clinically relevant.
6. Mention preparation in ONE short sentence.
7. No markdown tables.
8. No long explanations.
9. No nutrition theory.
10. Keep output under 350 words.
11. Ensure all 3 meals are complete.
12. Avoid excessive ingredient repetition.
13. Ensure meal diversity.
14. Meals must sound medically personalized.
15. Include realistic serving portions in grams or cups.
16. Do not invent unrelated dishes.
17. Prefer foods with stronger semantic and confidence scores.
18. STRICTLY ensure the meal quantities approximately satisfy the target macros.
19. Keep total calories within ±2% of target calories.
20. Keep protein within ±10g of target protein.
21. Keep carbs within ±5g of target carbs.
22. Keep fat within -4g of target fat.
23. Avoid unrealistic quantities.
24. Avoid excessive carbohydrates.
25. Avoid excessive oils and fats.
26. Do not generate impossible nutrition totals.
27. Use clinically realistic portion sizes.
28. Do NOT calculate nutrition totals yourself.
29. Nutrition totals are already calculated separately by the backend.
30. Your role is ONLY to generate meal descriptions and quantities matching the targets.

=====================================================
OUTPUT STYLE
=====================================================

Generate output in professional clinical nutrition recommendation style.
The meal plan should sound medically personalized and AI-assisted.
Briefly explain why each dish is suitable for the biomarkers and genes.

=====================================================
OUTPUT FORMAT
=====================================================

Breakfast:
- Dish name (portion size): short preparation and clinical benefit in two line

Lunch:
- Dish name (portion size): short preparation and clinical benefit in two lines

Dinner:
- Dish name (portion size): short preparation and clinical benefit in two lines


"""