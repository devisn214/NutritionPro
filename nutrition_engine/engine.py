from .bmr import calculate_bmr
from .constants import ACTIVITY_LEVELS
from .biomarker_rules import process_biomarkers
from .gene_rules import process_genes
from rag import NutritionRAG
from llm import NutritionLLM


def generate_nutrition_plan(user):

    # ===== 1. CALORIES =====
    bmr = calculate_bmr(user)
    activity = user.get("activity_level", "sedentary")

    if isinstance(activity, (int, float)):
        activity_factor = activity
    else:
        activity_factor = ACTIVITY_LEVELS.get(activity, 1.2)

    calories = round(bmr * activity_factor)

    # ===== 2. USER DATA =====
    biomarkers = user.get("biomarkers", []) or []
    genes = user.get("genes", []) or []

    biomarker_recs = process_biomarkers(biomarkers, user)
    gene_recs = process_genes(genes)

    # ===== 3. RAG =====
    rag = NutritionRAG()

    rag_context = rag.retrieve_context(
        biomarkers=biomarkers,
        genes=genes,
        biomarker_recs=biomarker_recs,
        gene_recs=gene_recs,
        diet_preference=user.get("diet_preference", "vegetarian")
    )

    evidence = rag.last_evidence or []
    rag.close()

    # ===== 4. MACROS =====
    macros = calculate_macros_from_foods(rag_context)

    if macros["protein_g"] == 0 and macros["carbs_g"] == 0:
        macros = fallback_macros(calories)

    # ===== 5. LLM =====
    llm = NutritionLLM()

    llm_recommendation = llm.generate_plan(
        user_profile=user,
        rag_context=rag_context,
        calories=calories,
        macros=macros
    )

    # ===== 6. NUTRITION EVIDENCE SCORE =====
    score = 0

# Biomarkers (max 45)
    score += min(len(biomarker_recs) * 12, 45)

# Genes (max 20)
    score += min(len(gene_recs) * 10, 20)

# Food Matches (max 20)
    score += min(len(rag_context) * 2, 20)

# LLM Meal Plan Quality
    if llm_recommendation and "Service Error" not in llm_recommendation:
        score += 10

# Macro Available
    if macros["protein_g"] > 0:
        score += 5

    confidence = min(round(score), 100)

    # ===== RETURN =====
    return {
        "calories": calories,
        "macros": macros,
        "biomarker_recommendations": biomarker_recs,
        "gene_recommendations": gene_recs,
        "rag_context": rag_context,
        "llm_recommendation": llm_recommendation,
        "evidence": evidence,
        "confidence": confidence
    }



def calculate_macros_from_foods(rag_context):

    protein = 0
    carbs = 0
    fat = 0

    if not rag_context:
        return {"protein_g": 0, "carbs_g": 0, "fats_g": 0}

    for food in rag_context:

        nutrients = food.get("nutrients", []) or []

        for n in nutrients:
            name = (n.get("name") or "").lower()
            amount = float(n.get("amount", 0) or 0)

            # ===== PROTEIN =====
            if "protein" in name:
                protein += amount

            # ===== CARBS =====
            elif "carbohydrate" in name or "glycemic" in name:
                carbs += amount

            # ===== FAT =====
            elif "fat" in name or "cholesterol" in name:
                fat += amount

    return {
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fats_g": round(fat, 1)
    }



def fallback_macros(calories):
    return {
        "protein_g": round((calories * 0.2) / 4),
        "carbs_g": round((calories * 0.55) / 4),
        "fats_g": round((calories * 0.25) / 9)
    }