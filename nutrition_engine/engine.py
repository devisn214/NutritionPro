from .bmr import calculate_bmr
from .constants import ACTIVITY_LEVELS
from .biomarker_rules import process_biomarkers
from .gene_rules import process_genes
from .biomarker_interaction import get_biomarker_interactions
from rag import NutritionRAG
from llm import NutritionLLM


def generate_nutrition_plan(user):

    bmr = calculate_bmr(user)

    activity = user.get("activity_level", "sedentary")

    if isinstance(activity, (int, float)):
        activity_factor = activity
    else:
        activity_factor = ACTIVITY_LEVELS.get(activity, 1.2)

    calories = round(bmr * activity_factor)

    biomarkers = user.get("biomarkers", []) or []
    genes = user.get("genes", []) or []

    biomarker_recs = process_biomarkers(biomarkers, user)

    biomarker_recs = [
        b for b in biomarker_recs
        if str(b.get("status", "")).lower() != "normal"
    ]

    gene_recs = process_genes(genes)

    gene_recs = [
        g for g in gene_recs
        if str(g.get("variant", "")).lower() != "normal"
    ]

    interaction = get_biomarker_interactions(biomarkers)

    interaction_recommendations = []

    for nid in interaction.get("increase", []):

        interaction_recommendations.append({
            "name": "Interaction Rule",
            "nutrient_id": nid,
            "direction": "increase"
        })

    for nid in interaction.get("decrease", []):

        interaction_recommendations.append({
            "name": "Interaction Rule",
            "nutrient_id": nid,
            "direction": "decrease"
        })

    rag_biomarker_recs = biomarker_recs + interaction_recommendations

    for g in gene_recs:

        nutrient_ids = str(g.get("nutrient_id", "")).split()

        direction = str(g.get("direction", "maintain")).lower()

        for nid in nutrient_ids:

            nid = nid.strip()

            if not nid:
                continue

            rag_biomarker_recs.append({
                "name": f"Gene-{g.get('gene')}",
                "nutrient_id": nid,
                "direction": direction
            })

    rag_biomarker_recs = remove_duplicate_recommendations(rag_biomarker_recs)

    print("\n========== ENGINE DEBUG ==========")
    print("Biomarker Recommendations:")
    print(biomarker_recs)

    print("\nGene Recommendations:")
    print(gene_recs)
    print("==================================\n")

    rag = NutritionRAG()

    rag_context = rag.retrieve_context(
        biomarkers=biomarkers,
        genes=genes,
        biomarker_recs=rag_biomarker_recs,
        gene_recs=gene_recs,
        diet_preference=user.get("diet_preference", "vegetarian")
    )

    evidence = rag.last_evidence or []

    rag.close()

    print("\n========== FINAL RAG FOODS ==========")

    for r in rag_context[:10]:
        print(r.get("food"), "->", r.get("reason"))

    print("=====================================\n")

    macros = calculate_macros_from_foods(rag_context)

    if macros["protein_g"] < 25:

        fallback = fallback_macros(calories)

        macros["protein_g"] = max(macros["protein_g"], fallback["protein_g"])
        macros["carbs_g"] = max(macros["carbs_g"], fallback["carbs_g"])
        macros["fats_g"] = max(macros["fats_g"], fallback["fats_g"])

    print("\n========== MACROS ==========")
    print(macros)
    print("============================\n")

    llm = NutritionLLM()

    llm_recommendation = llm.generate_plan(
        user_profile=user,
        rag_context=rag_context,
        calories=calories,
        macros=macros
    )

    score = 0

    score += min(len(biomarker_recs) * 12, 45)

    score += min(len(gene_recs) * 10, 20)

    score += min(len(rag_context) * 2, 20)

    if llm_recommendation and "Service Error" not in llm_recommendation:
        score += 10

    if macros["protein_g"] > 0:
        score += 5

    confidence = min(round(score), 100)

    return {
        "calories": calories,
        "macros": macros,
        "biomarker_recommendations": biomarker_recs,
        "gene_recommendations": gene_recs,
        "interaction_notes": interaction.get("notes", []),
        "rag_context": rag_context,
        "llm_recommendation": llm_recommendation,
        "evidence": evidence,
        "confidence": confidence
    }


def remove_duplicate_recommendations(recs):

    seen = set()
    final = []

    for r in recs:

        key = (
            str(r.get("nutrient_id", "")).strip().upper(),
            str(r.get("direction", "")).strip().lower()
        )

        if key not in seen:
            seen.add(key)
            final.append(r)

    return final


def calculate_macros_from_foods(rag_context):

    protein = 0
    carbs = 0
    fat = 0

    if not rag_context:
        return {
            "protein_g": 0,
            "carbs_g": 0,
            "fats_g": 0
        }

    for food in rag_context:

        nutrients = food.get("nutrients", []) or []

        for n in nutrients:

            name = str(n.get("name", "")).lower()

            amount = float(n.get("amount", 0) or 0)

            if "protein" in name:
                protein += amount

            elif "carbohydrate" in name or "glycemic" in name:
                carbs += amount

            elif "fat" in name or "cholesterol" in name:
                fat += amount

    return {
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fats_g": round(fat, 1)
    }


def fallback_macros(calories):

    return {
        "protein_g": round((calories * 0.20) / 4),
        "carbs_g": round((calories * 0.55) / 4),
        "fats_g": round((calories * 0.25) / 9)
    }