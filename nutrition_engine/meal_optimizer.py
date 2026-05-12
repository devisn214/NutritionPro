from .derived_macro_estimator import (
    estimate_food_macros
)

import random


# =========================================================
# MEAL SPLIT
# =========================================================

MEAL_SPLIT = {

    "breakfast": 0.30,

    "lunch": 0.40,

    "dinner": 0.30
}


# =========================================================
# BUILD FOOD OBJECTS
# =========================================================

def build_food_objects(rag_foods):

    foods = []

    for food in rag_foods:

        food_id = food["food_id"]

        est = estimate_food_macros(
            food_id
        )

        foods.append(est)

    return foods


# =========================================================
# CALCULATE TOTALS
# =========================================================

def calculate_totals(food_list):

    protein = sum(
        x["protein_g"]
        for x in food_list
    )

    carbs = sum(
        x["carbs_g"]
        for x in food_list
    )

    fats = sum(
        x["fat_g"]
        for x in food_list
    )

    calories = sum(
        x["calories"]
        for x in food_list
    )

    return {

        "protein_g": round(protein, 1),

        "carbs_g": round(carbs, 1),

        "fat_g": round(fats, 1),

        "calories": round(calories, 1)
    }


# =========================================================
# MAIN OPTIMIZER
# =========================================================

def optimize_meal_plan(
    rag_foods,
    target_calories,
    target_protein,
    target_carbs,
    target_fats
):

    foods = build_food_objects(
        rag_foods
    )

    # -----------------------------------------------------
    # SORTING
    # -----------------------------------------------------

    protein_foods = sorted(
        foods,
        key=lambda x: x["protein_g"],
        reverse=True
    )

    carb_foods = sorted(
        foods,
        key=lambda x: x["carbs_g"],
        reverse=True
    )

    fat_foods = sorted(
        foods,
        key=lambda x: x["fat_g"],
        reverse=True
    )

    # -----------------------------------------------------
    # BUILD MEALS
    # -----------------------------------------------------

    breakfast = []

    lunch = []

    dinner = []

    # breakfast
    breakfast.extend(
        carb_foods[:2]
    )

    breakfast.extend(
        protein_foods[:1]
    )

    # lunch
    lunch.extend(
        protein_foods[1:4]
    )

    lunch.extend(
        carb_foods[2:4]
    )

    # dinner
    dinner.extend(
        protein_foods[4:6]
    )

    dinner.extend(
        fat_foods[:2]
    )

    # -----------------------------------------------------
    # TOTALS
    # -----------------------------------------------------

    all_foods = (
        breakfast
        + lunch
        + dinner
    )

    totals = calculate_totals(
        all_foods
    )

    return {

        "breakfast": breakfast,

        "lunch": lunch,

        "dinner": dinner,

        "totals": totals,

        "targets": {

            "protein_g": target_protein,

            "carbs_g": target_carbs,

            "fat_g": target_fats,

            "calories": target_calories
        }
    }