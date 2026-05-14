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

        gene = str(g.get("gene", "")).upper().strip()
        rsid = str(g.get("rsid", "")).strip()
        genotype = str(g.get("genotype", "")).strip().upper()

        if not rsid or not genotype:
            continue

        match = df[
            (df["gene_symbol"].str.upper() == gene) &
            (df["rsid"].astype(str).str.upper() == rsid.upper()) &
            (df["genotype"].astype(str).str.upper() == genotype.upper())
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

        elif "monitor" in action:
            direction = "monitor"

        elif "moderate" in action:
            direction = "moderate"

        else:
            direction = "support"

        # ===== nutrient lookup =====

        n_ids = str(row.get("affected_nutrient", "")).split()

        nutrient_names = []

        for nid in n_ids:

            n_name_row = df_nutrients[
                df_nutrients["nutrient_id"] == nid
            ]

            if not n_name_row.empty:
                nutrient_names.append(
                    n_name_row.iloc[0]["name"]
                )

            else:
                nutrient_names.append(nid)

        recommendations.append({

            "gene": gene,
            "rsid": rsid,
            "genotype": genotype,

            "nutrient_id": " ".join(n_ids),
            "nutrient_name": ", ".join(nutrient_names),

            "impact": row.get("impact", ""),
            "direction": direction,

            "reason": row.get("variant_effect", ""),
            "description": row.get("description", ""),
            "interaction_type": row.get("interaction_type", ""),
            "action": row.get("action", "")
        })

    return recommendations