import json

from .bmr import calculate_bmr
from .constants import ACTIVITY_LEVELS

from .biomarker_rules import process_biomarkers
from .gene_rules import process_genes
from .biomarker_interaction import get_biomarker_interactions

from rag import NutritionRAG
from llm import NutritionLLM

from nutrition_engine.meal_optimizer import optimize_meal_plan

from llm_evaluator import LLMMealEvaluator

from new.confidence import ConfidenceEngine
from new.adaptive_engine import AdaptiveEngine


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
            g.get("direction", "")
        ).strip().lower() != "normal"
    ]

    # =====================================================
    # INTERACTION ENGINE
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

            "biomarker": "Interaction Rule",

            "target_nutrient": nid,

            "nutrient_id": nid,

            "direction": "increase",

            "status": "combined"
        })

    for nid in interaction.get(
        "decrease",
        []
    ):

        interaction_recommendations.append({

            "biomarker": "Interaction Rule",

            "target_nutrient": nid,

            "nutrient_id": nid,

            "direction": "decrease",

            "status": "combined"
        })

    # =====================================================
    # BUILD RAG TARGETS
    # =====================================================

    rag_biomarker_recs = biomarker_recs + interaction_recommendations

    for g in gene_recs:

        nutrient_ids = str(
            g.get("nutrient_id", "")
        ).split()

        direction = str(
            g.get("direction", "support")
        ).lower()

        for nid in nutrient_ids:

            nid = nid.strip()

            if not nid:
                continue

            rag_biomarker_recs.append({

                "biomarker": f"Gene-{g.get('gene')}",

                "target_nutrient": g.get(
                    "nutrient_name",
                    nid
                ),

                "nutrient_id": nid,

                "direction": direction,

                "status": "genetic"
            })

    rag_biomarker_recs = remove_duplicate_recommendations(
        rag_biomarker_recs
    )

    # =====================================================
    # TARGET NUTRIENTS
    # =====================================================

    increase_ids = []
    decrease_ids = []

    for rec in rag_biomarker_recs:

        nutrient_ids = str(
            rec.get("nutrient_id", "")
        ).split()

        direction = str(
            rec.get("direction", "")
        ).lower()

        for nid in nutrient_ids:

            nid = nid.strip()

            if not nid:
                continue

            if direction in [
                "increase",
                "support",
                "maintain",
                "monitor"
            ]:

                increase_ids.append(nid)

            elif direction == "decrease":

                decrease_ids.append(nid)

    increase_ids = list(set(increase_ids))
    decrease_ids = list(set(decrease_ids))

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
        ),
         user_id=user.get("user_id")
    )

    evidence = rag.last_evidence or []

    rag.close()

    # =====================================================
    # ADAPTIVE + CONFIDENCE
    # =====================================================

    confidence_engine = ConfidenceEngine()

    adaptive_engine = AdaptiveEngine()

    for item in rag_context:

        matched_nutrients = [

            n.get("id")

            for n in item.get(
                "nutrients",
                []
            )
        ]

        adaptive_score = adaptive_engine.get_adaptive_score(
            user_id=user.get("user_id"),
            food_name=item.get("food", "")
        )

        semantic_score = item.get(
            "semantic_score",
            0
        )

        item["adaptive_score"] = adaptive_score

        item["confidence_score"] = confidence_engine.calculate_food_confidence(

            matched_nutrients=matched_nutrients,

            increase_ids=increase_ids,

            decrease_ids=decrease_ids,

            semantic_score=semantic_score,

            adaptive_score=adaptive_score
        )

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
    def calculate_actual_macros(optimized_plan):

        total_calories = 0
        total_protein = 0
        total_carbs = 0
        total_fats = 0

        for meal_type, foods in optimized_plan.items():

            for food in foods:

                nutrients = food.get("nutrients", [])

                for n in nutrients:

                    name = str(n.get("name", "")).lower()

                    amount = float(n.get("amount", 0))

                    if "energy" in name or "calories" in name:
                        total_calories += amount

                    elif "protein" in name:
                        total_protein += amount

                    elif "carbohydrate" in name or "carbs" in name:
                        total_carbs += amount

                    elif "fat" in name:
                        total_fats += amount

        return {

        "calories": round(total_calories),
        "protein": round(total_protein),
        "carbs": round(total_carbs),
        "fat": round(total_fats)
        }

    # =====================================================
    # LLM GENERATION
    # =====================================================

    llm = NutritionLLM()

    llm_recommendation = llm.generate_plan(

        user_profile=user,

        rag_context=rag_context,

        optimized_plan=optimized_plan,

        calories=calories,

        macros=macros,
        biomarker_recommendations=biomarker_recs,

        gene_recommendations=gene_recs
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
    # GLOBAL CONFIDENCE
    # =====================================================

    global_confidence = confidence_engine.calculate_global_confidence(

        rag_context=rag_context,

        biomarker_recommendations=biomarker_recs,

        gene_recommendations=gene_recs
    )

    confidence_breakdown = {

        "biomarker_support": len(
            biomarker_recs
        ),

        "gene_support": len(
            gene_recs
        ),

        "food_overlap": len(
            rag_context
        ),

        "semantic_support": round(

            sum(

                x.get(
                    "semantic_score",
                    0
                )

                for x in rag_context[:10]

            ) / max(
                len(rag_context[:10]),
                1
            ),

            3
        )
    }

    adaptive_global = adaptive_engine.global_adaptive_score(
        rag_context
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

        "confidence": global_confidence,

        "confidence_breakdown": confidence_breakdown,

        "adaptive_score": adaptive_global
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