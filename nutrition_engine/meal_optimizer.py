from .derived_macro_estimator import estimate_food_macros
import random


MEAL_SPLIT = {"breakfast": 0.30, "lunch": 0.40, "dinner": 0.30}


def build_food_objects(rag_foods):

    foods = []

    for food in rag_foods:

        food_id = food["food_id"]

        est = estimate_food_macros(food_id)

        est["food"] = food.get("food", "")

        est["confidence_score"] = food.get("confidence_score", 0)

        foods.append(est)

    return foods


def calculate_totals(food_list):

    protein = sum(x.get("protein_g", 0) for x in food_list)

    carbs = sum(x.get("carbs_g", 0) for x in food_list)

    fats = sum(x.get("fat_g", 0) for x in food_list)

    calories = sum(x.get("calories", 0) for x in food_list)

    return {
        "protein_g": round(protein, 1),
        "carbs_g": round(carbs, 1),
        "fat_g": round(fats, 1),
        "calories": round(calories, 1)
    }


def optimize_meal_plan(rag_foods, target_calories, target_protein, target_carbs, target_fats, adaptive_engine=None, user_id=None):

    foods = build_food_objects(rag_foods)

    recent_foods = set()

    if adaptive_engine and user_id:

        recent = adaptive_engine.get_recent_foods(user_id, limit=15)

        recent_foods = set(x.lower() for x in recent)

    for food in foods:

        food_name = str(food.get("food", "")).lower()

        if food_name in recent_foods:

            food["reuse_penalty"] = -40

        else:

            food["reuse_penalty"] = 0

    foods = sorted(
        foods,
        key=lambda x: (
            x.get("protein_g", 0) 
            +
            x.get("carbs_g", 0)
            -
            x.get("fat_g", 0)
            +
            x.get("confidence_score", 0)
            +
            x.get("reuse_penalty", 0)
        ),
        reverse=True
    )

    breakfast = []

    lunch = []

    dinner = []

    used_foods = set()

    current = {
        "calories": 0,
        "protein_g": 0,
        "carbs_g": 0,
        "fat_g": 0
    }

    def can_add(food):

        next_cal = current["calories"] + food.get("calories", 0)

        next_protein = current["protein_g"] + food.get("protein_g", 0)

        next_carbs = current["carbs_g"] + food.get("carbs_g", 0)

        next_fat = current["fat_g"] + food.get("fat_g", 0)

        if next_cal > target_calories * 1.05:
            return False

        if next_carbs > target_carbs * 1.10:
            return False

        if next_fat > target_fats * 1.10:
            return False
        
        if next_protein > target_protein * 1.2:
            return False

        return True

    def add_food(meal, food):

        meal.append(food)

        current["calories"] += food.get("calories", 0)

        current["protein_g"] += food.get("protein_g", 0)

        current["carbs_g"] += food.get("carbs_g", 0)

        current["fat_g"] += food.get("fat_g", 0)

        used_foods.add(food.get("food", "").lower())

    for food in foods:

        food_name = food.get("food", "").lower()

        if food_name in used_foods:
            continue

        if not can_add(food):
            continue

        if len(breakfast) < 3:

            add_food(breakfast, food)

            continue

        if len(lunch) < 4:

            add_food(lunch, food)

            continue

        if len(dinner) < 3:

            add_food(dinner, food)

            continue

        if current["calories"] >= target_calories * 0.95 and current["protein_g"] >= target_protein * 0.90:
            break

    all_foods = breakfast + lunch + dinner

    totals = calculate_totals(all_foods)

    if adaptive_engine and user_id:

        for food in all_foods:

            adaptive_engine.store_recent_food(user_id, food.get("food", ""))

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