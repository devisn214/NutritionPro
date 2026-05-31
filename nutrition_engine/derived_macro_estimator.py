import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")

foods_df = pd.read_csv(
    os.path.join(DATA_DIR, "foods.csv")
)

food_map_df = pd.read_csv(
    os.path.join(DATA_DIR, "food_nutrient_map.csv")
)

nutrient_df = pd.read_csv(
    os.path.join(DATA_DIR, "nutrients.csv")
)


# =========================================================
# BUILD CATEGORY MAP
# =========================================================

nutrient_category_map = {}

for _, row in nutrient_df.iterrows():

    nutrient_category_map[
        row["nutrient_id"]
    ] = row["category"]


# =========================================================
# ESTIMATE FOOD MACROS
# =========================================================

def estimate_food_macros(food_id):

    food_rows = food_map_df[
        food_map_df["food_id"] == food_id
    ]

    protein = 0
    carbs = 0
    fats = 0
    fiber = 0

    nutrients_found = []

    for _, row in food_rows.iterrows():

        nutrient_id = row["nutrient_id"]

        amount = float(row["amount"])

        nutrients_found.append(
            row["nutrients"]
        )

        # -----------------------------------------
        # CATEGORY
        # -----------------------------------------

        category = nutrient_category_map.get(
            nutrient_id,
            ""
        )

        nutrient_name = str(
            row["nutrients"]
        ).lower()

        # -----------------------------------------
        # PROTEIN
        # -----------------------------------------

        if nutrient_name == "net protein":
            protein += amount

        # -----------------------------------------
        # CARBS
        # -----------------------------------------

        elif nutrient_name == "total carbohydrates":
            carbs += amount

        elif nutrient_name == "dietary fiber":
            fiber += amount

        elif nutrient_name == "soluble fiber":
            fiber += amount

        # -----------------------------------------
        # FATS
        # -----------------------------------------

        elif category == "lipid":

            if "cholesterol" not in nutrient_name and "omega-3" not in nutrient_name:

                fats += amount

    # =====================================================
    # CALORIES
    # =====================================================

    calories = (
        protein * 4
        + carbs * 4
        + fats * 9
    )

    # =====================================================
    # FOOD INFO
    # =====================================================

    food_info = foods_df[
        foods_df["food_id"] == food_id
    ].iloc[0]

    return {

        "food_id": food_id,

        "food_name": food_info["food_name"],

        "category": food_info["category"],

        "serving_size": food_info["serving_size"],

        "serving_unit": food_info["serving_unit"],

        "protein_g": round(protein, 2),

        "carbs_g": round(carbs, 2),

        "fat_g": round(fats, 2),

        "fiber_g": round(fiber, 2),

        "calories": round(calories, 2),

        "nutrients": nutrients_found
    }