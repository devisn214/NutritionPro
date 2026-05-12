import json
from .bmr import calculate_bmr
from .constants import ACTIVITY_LEVELS
from .biomarker_rules import process_biomarkers
from .gene_rules import process_genes
from .biomarker_interaction import get_biomarker_interactions

from rag import NutritionRAG
from llm import NutritionLLM

from nutrition_engine.meal_optimizer import (optimize_meal_plan)

from llm_evaluator import (LLMMealEvaluator)


def generate_nutrition_plan(user):

    # =====================================================
    # CALORIES
    # =====================================================

    bmr = calculate_bmr(user)

    activity = user.get(
        "activity_level",
        "sedentary"
    )

    if isinstance(activity, (int, float)):
        activity_factor = activity

    else:
        activity_factor = ACTIVITY_LEVELS.get(
            activity,
            1.2
        )

    calories = round(
        bmr * activity_factor
    )

    # =====================================================
    # USER DATA
    # =====================================================

    biomarkers = user.get(
        "biomarkers",
        []
    ) or []

    genes = user.get(
        "genes",
        []
    ) or []

    # =====================================================
    # BIOMARKER RULES
    # =====================================================

    biomarker_recs = process_biomarkers(
        biomarkers,
        user
    )

    biomarker_recs = [

        b for b in biomarker_recs

        if str(
            b.get("status", "")
        ).lower() != "normal"
    ]

    # =====================================================
    # GENE RULES
    # =====================================================

    gene_recs = process_genes(
        genes
    )

    gene_recs = [

        g for g in gene_recs

        if str(
            g.get("variant", "")
        ).lower() != "normal"
    ]

    # =====================================================
    # INTERACTION RULES
    # =====================================================

    interaction = get_biomarker_interactions(
        biomarkers
    )

    interaction_recommendations = []

    for nid in interaction.get(
        "increase",
        []
    ):

        interaction_recommendations.append({

            "name": "Interaction Rule",

            "nutrient_id": nid,

            "direction": "increase"
        })

    for nid in interaction.get(
        "decrease",
        []
    ):

        interaction_recommendations.append({

            "name": "Interaction Rule",

            "nutrient_id": nid,

            "direction": "decrease"
        })

    # =====================================================
    # BUILD FINAL RAG TARGETS
    # =====================================================

    rag_biomarker_recs = (
        biomarker_recs
        + interaction_recommendations
    )

    for g in gene_recs:

        nutrient_ids = str(
            g.get("nutrient_id", "")
        ).split()

        direction = str(
            g.get("direction", "maintain")
        ).lower()

        for nid in nutrient_ids:

            nid = nid.strip()

            if not nid:
                continue

            rag_biomarker_recs.append({

                "name": f"Gene-{g.get('gene')}",

                "nutrient_id": nid,

                "direction": direction
            })

    rag_biomarker_recs = remove_duplicate_recommendations(
        rag_biomarker_recs
    )

    # =====================================================
    # DEBUG
    # =====================================================

    print("\n========== ENGINE DEBUG ==========")

    print("Biomarker Recommendations:")
    print(biomarker_recs)

    print("\nGene Recommendations:")
    print(gene_recs)

    print("==================================\n")

    # =====================================================
    # RAG RETRIEVAL
    # =====================================================

    rag = NutritionRAG()

    rag_context = rag.retrieve_context(

        biomarkers=biomarkers,

        genes=genes,

        biomarker_recs=rag_biomarker_recs,

        gene_recs=gene_recs,

        diet_preference=user.get(
            "diet_preference",
            "vegetarian"
        )
    )

    evidence = rag.last_evidence or []

    rag.close()

    # =====================================================
    # DEBUG
    # =====================================================

    print("\n========== FINAL RAG FOODS ==========")

    for r in rag_context[:10]:

        print(
            r.get("food"),
            "->",
            r.get("reason")
        )

    print("=====================================\n")

    # =====================================================
    # TARGET MACROS
    # =====================================================

    macros = fallback_macros(
        calories
    )

    print("\n========== TARGET MACROS ==========")
    print(macros)
    print("===================================\n")

    # =====================================================
    # MEAL OPTIMIZER
    # =====================================================

    optimized_plan = optimize_meal_plan(

        rag_foods=rag_context,

        target_calories=calories,

        target_protein=macros["protein_g"],

        target_carbs=macros["carbs_g"],

        target_fats=macros["fats_g"]
    )

    # =====================================================
    # LLM MEAL GENERATION
    # =====================================================

    llm = NutritionLLM()

    llm_recommendation = llm.generate_plan(

        user_profile=user,

        rag_context=rag_context,

        optimized_plan=optimized_plan,

        calories=calories,

        macros=macros
    )

    # =====================================================
    # LLM EVALUATION
    # =====================================================

    evaluator = LLMMealEvaluator(
    model="phi3:mini"
)

    llm_evaluation = evaluator.evaluate(
    user_profile=user,
    meal_plan=llm_recommendation,
    calories=calories,
    macros=macros,
    rag_context=rag_context,
    biomarker_recommendations=biomarker_recs,
    gene_recommendations=gene_recs
)


    print("\n========== LLM EVALUATION ==========")
    print(llm_evaluation)
    print("====================================\n")

    # =====================================================
    # CONFIDENCE
    # =====================================================

    score = 0

    score += min(
        len(biomarker_recs) * 12,
        45
    )

    score += min(
        len(gene_recs) * 10,
        20
    )

    score += min(
        len(rag_context) * 2,
        20
    )

    if llm_recommendation and \
       "Service Error" not in llm_recommendation:

        score += 10

    score += 5

    confidence = min(
        round(score),
        100
    )

    # =====================================================
    # FINAL RETURN
    # =====================================================

    return {

        "calories": calories,

        "macros": macros,

        "optimized_plan": optimized_plan,

        "biomarker_recommendations": biomarker_recs,

        "gene_recommendations": gene_recs,

        "interaction_notes": interaction.get(
            "notes",
            []
        ),

        "rag_context": rag_context,

        "llm_recommendation": llm_recommendation,

        "llm_evaluation": llm_evaluation,

        "evidence": evidence,

        "confidence": confidence
    }




def remove_duplicate_recommendations(recs):

    seen = set()

    final = []

    for r in recs:

        key = (

            str(
                r.get("nutrient_id", "")
            ).strip().upper(),

            str(
                r.get("direction", "")
            ).strip().lower()
        )

        if key not in seen:

            seen.add(key)

            final.append(r)

    return final



def fallback_macros(calories):

    return {

        "protein_g":
            round((calories * 0.20) / 4),

        "carbs_g":
            round((calories * 0.55) / 4),

        "fats_g":
            round((calories * 0.25) / 9)
    }