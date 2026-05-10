import pandas as pd
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def process_genes(user_gene_results):

    df = pd.read_csv(os.path.join(DATA_DIR, "genenutrient.csv"))
    df_nutrients = pd.read_csv(os.path.join(DATA_DIR, "nutrients.csv"))

    recommendations = []

    for g in user_gene_results:

        gene = str(g.get("name", "")).upper().strip()
        variant = str(g.get("variant", "Normal")).strip()

        match = df[
            (df["gene_symbol"].str.upper() == gene) &
            (df["variant"].str.upper() == variant.upper())
        ]

        if match.empty:
            continue

        row = match.iloc[0]

        # ===== direction =====
        action = str(row.get("action", "")).lower()

        if "decrease" in action:
            direction = "decrease"
        elif "increase" in action:
            direction = "increase"
        else:
            direction = "maintain"

        # ===== SAFE nutrient name lookup (FIX) =====
        n_id = row.get("affected_nutrient", "")

        n_name_row = df_nutrients[
            df_nutrients["nutrient_id"] == n_id
        ]

        if not n_name_row.empty:
            nutrient_name = n_name_row.iloc[0]["name"]
        else:
            nutrient_name = n_id  # fallback (never crash)

        recommendations.append({
            "gene": gene,
            "variant": variant,
            "nutrient_id": n_id,
            "nutrient_name": nutrient_name,
            "impact": row.get("impact", ""),
            "direction": direction,
            "reason": row.get("variant_effect", "")
        })

    return recommendations