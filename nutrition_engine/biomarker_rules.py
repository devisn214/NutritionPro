import pandas as pd
import os

from .unit_convertor import convert_value

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

df_biomarkers = pd.read_csv(os.path.join(DATA_DIR, "biomarkers.csv"))
df_thresholds = pd.read_csv(os.path.join(DATA_DIR, "biomarkers_maxvalue.csv"))
df_nutrients = pd.read_csv(os.path.join(DATA_DIR, "nutrients.csv"))
df_food_nutrient = pd.read_csv(os.path.join(DATA_DIR, "food_nutrient_map.csv"))
df_foods = pd.read_csv(os.path.join(DATA_DIR, "foods.csv"))

BIOMARKER_UNIT_MAP = {
    str(row["name"]).strip().lower(): str(row.get("unit", "")).strip().lower()
    for _, row in df_thresholds.iterrows()
}


def process_biomarkers(user_test_results, user):
    final_recommendations = []
    gender = user.get("gender", "male").lower()

    for test in user_test_results:
        biomarker_name = str(test.get("name", "")).strip().lower()

        b_info = df_biomarkers[
            df_biomarkers['name'].str.strip().str.lower() == biomarker_name
        ]

        if b_info.empty:
            continue

        b_id = b_info.iloc[0]['biomarker_id']

        # Indentation fixed from here downward
        thresh = df_thresholds[
            df_thresholds['biomarker_id'] == b_id
        ]

        if thresh.empty:
            continue

        row = thresh.iloc[0]

        if gender == "male":
            low_v = float(row['low_male'])
            high_v = float(row['high_male'])
        else:
            low_v = float(row['low_female'])
            high_v = float(row['high_female'])

        try:
            raw_val = float(test.get('value', 0))
        except:
            continue

        input_unit = str(test.get("unit", "")).strip().lower()

        if not input_unit:
            input_unit = BIOMARKER_UNIT_MAP.get(
                biomarker_name,
                ""
            )

        target_unit = BIOMARKER_UNIT_MAP.get(
            biomarker_name,
            input_unit
        )

        try:
            val = convert_value(
                raw_val,
                input_unit,
                target_unit
            )
        except:
            val = raw_val

        if val < 0 or val > 10000:
            continue

        if val < (low_v * 0.1) or val > (high_v * 10):
            continue

        if val < low_v:
            biomarker_status = "Low"
        elif val > high_v:
            biomarker_status = "High"
        else:
            biomarker_status = "Normal"

        if biomarker_status == "Normal":
            continue
            

        matching_rules = b_info[
            b_info["status"].str.strip().str.lower()
            ==
            biomarker_status.lower()
        ]

        for _, rule in matching_rules.iterrows():
            if pd.isna(rule["nutrient_id"]):
                continue

            n_id = str(rule["nutrient_id"]).strip()
            if not n_id:
                continue

            direction = str(rule.get("action", "maintain")).strip().lower()

            nutrient_row = df_nutrients[
                df_nutrients["nutrient_id"] == n_id
            ]

            if nutrient_row.empty:
                continue

            nutrient_name = nutrient_row.iloc[0]["name"]
            rec_foods = []

            food_map = df_food_nutrient[
                df_food_nutrient["nutrient_id"] == n_id
            ]

            if not food_map.empty:
                if direction in ["increase", "support"]:
                    food_map = food_map.sort_values(
                        by="amount",
                        ascending=False
                    )
                elif direction == "decrease":
                    food_map = food_map.sort_values(
                        by="amount",
                        ascending=True
                    )
                else:
                    food_map = food_map.sort_values(
                        by="amount",
                        ascending=False
                    )

                food_ids = food_map["food_id"].head(10)

                rec_foods = df_foods[
                    df_foods["food_id"].isin(food_ids)
                ]["food_name"].tolist()

            # Space and indentation error resolved below
            final_recommendations.append({
                "biomarker": test["name"],
                "current_value": val,
                "unit": target_unit,
                "low": low_v,
                "high": high_v,
                "status": biomarker_status.lower(),
                "direction": direction,
                "nutrient_id": n_id,
                "target_nutrient": nutrient_name,
                "recommended_foods": rec_foods
            })

    # Printed and returned outside the for-loop, completing the function
    print("Final Recommendations:", final_recommendations)
    return final_recommendations