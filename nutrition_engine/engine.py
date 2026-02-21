from .bmr import calculate_bmr
from .macros import calculate_macros
from .constants import ACTIVITY_LEVELS
from .biomarker_rules import process_biomarkers
from .gene_rules import process_genes
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
    macros = calculate_macros(calories)
    biomarker_recs = process_biomarkers(user.get("biomarkers", []))
    gene_recs = process_genes(user.get("genes", []))

    rag = NutritionRAG(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="neo4jabc"
    )
    rag_context = rag.retrieve_context(
        biomarkers=user.get("biomarkers", []),
        genes=user.get("genes", []),
        biomarker_recs=biomarker_recs,
        gene_recs=gene_recs
    )
    rag.close()

    llm = NutritionLLM(model="phi3:mini")
    llm_recommendation = llm.generate_plan(
        user_profile=user,
        rag_context=rag_context,
        calories=calories,
        macros=macros
    )

    return {
        "calories": calories,
        "macros": macros,
        "biomarker_recommendations": biomarker_recs,
        "gene_recommendations": gene_recs,
        "llm_recommendation": llm_recommendation,
        "rag_context": rag_context
    }