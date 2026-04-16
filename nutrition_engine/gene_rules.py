import pandas as pd
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def process_genes(user_gene_results):
    df = pd.read_csv(os.path.join(DATA_DIR, "genenutrient.csv"))

    recommendations = []

    for g in user_gene_results:
        gene = g.get("name", "").upper()
        variant = g.get("variant", "Normal")

        match = df[
            (df["gene_symbol"].str.upper() == gene) &
            (df["variant"].str.upper() == variant.upper())
        ]

        if match.empty:
            continue

        row = match.iloc[0]

        # derive direction from action
        action = str(row["action"]).lower()

        if "decrease" in action:
            direction = "decrease"
        elif "increase" in action:
            direction = "increase"
        else:
            direction = "maintain"

        recommendations.append({
            "gene": gene,
            "variant": variant,
            "nutrient_id": row["affected_nutrient"], # Standardized key name
            "impact": row["impact"],
            "direction": direction,
            "reason": row["variant_effect"]
            })

    return recommendations