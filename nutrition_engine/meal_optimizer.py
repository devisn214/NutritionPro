from .derived_macro_estimator import estimate_food_macros
import random


MEAL_SPLIT = {
    "breakfast": 0.30,
    "lunch": 0.40,
    "dinner": 0.30
}


BRKDIN_STAPLES = [

    {
        "food": "Puttu",
        "calories": 320,
        "protein_g": 8,
        "carbs_g": 68,
        "fat_g": 3
    },

    {
        "food": "Appam",
        "calories": 280,
        "protein_g": 6,
        "carbs_g": 55,
        "fat_g": 4
    },

    {
        "food": "Idli",
        "calories": 240,
        "protein_g": 6,
        "carbs_g": 48,
        "fat_g": 2
    },

    {
        "food": "Dosa",
        "calories": 300,
        "protein_g": 7,
        "carbs_g": 52,
        "fat_g": 5
    },
    {
        "food": "Chapathi",
        "calories": 260,
        "protein_g": 7,
        "carbs_g": 46,
        "fat_g": 4
    },
     {
        "food": "Appam",
        "calories": 280,
        "protein_g": 6,
        "carbs_g": 55,
        "fat_g": 4
    }

]


LUNCH_STAPLES = [

    {
        "food": "Matta Rice",
        "calories": 420,
        "protein_g": 9,
        "carbs_g": 90,
        "fat_g": 2
    },

    {
        "food": "Red Rice",
        "calories": 400,
        "protein_g": 8,
        "carbs_g": 86,
        "fat_g": 2
    },

    {
        "food": "Brown Rice",
        "calories": 390,
        "protein_g": 8,
        "carbs_g": 82,
        "fat_g": 2
    }
]




def build_food_objects(rag_foods):

    foods = []

    for food in rag_foods:

        food_id = food["food_id"]

        est = estimate_food_macros(food_id)

        est["food"] = food.get("food", "")

        est["confidence_score"] = food.get(
            "confidence_score",
            0
        )

        est["semantic_score"] = food.get(
            "semantic_score",
            0
        )

        est["adaptive_score"] = food.get(
            "adaptive_score",
            0
        )

        foods.append(est)

    return foods


def calculate_totals(food_list):

    protein = sum(
        x.get("protein_g", 0)
        for x in food_list
    )

    carbs = sum(
        x.get("carbs_g", 0)
        for x in food_list
    )

    fats = sum(
        x.get("fat_g", 0)
        for x in food_list
    )

    calories = sum(
        x.get("calories", 0)
        for x in food_list
    )

    return {

        "protein_g": round(protein, 1),

        "carbs_g": round(carbs, 1),

        "fat_g": round(fats, 1),

        "calories": round(calories, 1)
    }


def scale_food(food, multiplier):

    scaled = food.copy()

    scaled["portion_multiplier"] = round(
        multiplier,
        2
    )

    scaled["calories"] = round(
        food.get("calories", 0) * multiplier,
        1
    )

    scaled["protein_g"] = round(
        food.get("protein_g", 0) * multiplier,
        1
    )

    scaled["carbs_g"] = round(
        food.get("carbs_g", 0) * multiplier,
        1
    )

    scaled["fat_g"] = round(
        food.get("fat_g", 0) * multiplier,
        1
    )

    return scaled


def meal_totals(meal):

    return calculate_totals(meal)


def can_add_food(meal, food, target):

    totals = meal_totals(meal)

    next_cal = totals["calories"] + food.get(
        "calories",
        0
    )

    next_protein = totals["protein_g"] + food.get(
        "protein_g",
        0
    )

    next_carbs = totals["carbs_g"] + food.get(
        "carbs_g",
        0
    )

    next_fat = totals["fat_g"] + food.get(
        "fat_g",
        0
    )

    if next_cal > target["calories"] * 1.15:
        return False

    if next_protein > target["protein_g"] * 1.30:
        return False

    if next_carbs > target["carbs_g"] * 1.25:
        return False

    if next_fat > target["fat_g"] * 1.25:
        return False

    return True


def add_dynamic_staple(meal, target, staples):

    totals = meal_totals(meal)

    if totals["carbs_g"] >= target["carbs_g"] * 0.75:
        return

    staple = random.choice(staples)

    meal.append(staple.copy())


def optimize_meal_plan(
    rag_foods,
    target_calories,
    target_protein,
    target_carbs,
    target_fats,
    adaptive_engine=None,
    user_id=None
):

    foods = build_food_objects(rag_foods)

    recent_foods = set()

    if adaptive_engine and user_id:

        recent = adaptive_engine.get_recent_foods(
            user_id,
            limit=15
        )

        recent_foods = set(
            x.lower()
            for x in recent
        )

    for food in foods:

        food_name = str(
            food.get("food", "")
        ).lower()

        reuse_penalty = (
            -40
            if food_name in recent_foods
            else 0
        )

        calories = food.get("calories", 0)

        protein = food.get("protein_g", 0)

        carbs = food.get("carbs_g", 0)

        fats = food.get("fat_g", 0)

        confidence = food.get(
            "confidence_score",
            0
        )

        semantic = food.get(
            "semantic_score",
            0
        )

        adaptive = food.get(
            "adaptive_score",
            0
        )

        food["optimizer_score"] = (

            calories * 0.28 +

            carbs * 0.32 +

            protein * 0.22 -

            fats * 0.05 +

            confidence * 0.05 +

            semantic * 8 +

            adaptive +

            reuse_penalty
        )

    foods = sorted(

        foods,

        key=lambda x: x.get(
            "optimizer_score",
            0
        ),

        reverse=True
    )

    breakfast_target = {

        "calories":
            target_calories * MEAL_SPLIT["breakfast"],

        "protein_g":
            target_protein * MEAL_SPLIT["breakfast"],

        "carbs_g":
            target_carbs * MEAL_SPLIT["breakfast"],

        "fat_g":
            target_fats * MEAL_SPLIT["breakfast"]
    }

    lunch_target = {

        "calories":
            target_calories * MEAL_SPLIT["lunch"],

        "protein_g":
            target_protein * MEAL_SPLIT["lunch"],

        "carbs_g":
            target_carbs * MEAL_SPLIT["lunch"],

        "fat_g":
            target_fats * MEAL_SPLIT["lunch"]
    }

    dinner_target = {

        "calories":
            target_calories * MEAL_SPLIT["dinner"],

        "protein_g":
            target_protein * MEAL_SPLIT["dinner"],

        "carbs_g":
            target_carbs * MEAL_SPLIT["dinner"],

        "fat_g":
            target_fats * MEAL_SPLIT["dinner"]
    }

    breakfast = []

    lunch = []

    dinner = []

    used_foods = set()

    def fill_meal(meal, target, preferred_count=4):

        attempts = 0

        while len(meal) < preferred_count:

            added = False

            for food in foods:

                food_name = str(
                    food.get("food", "")
                ).lower()

                if food_name in used_foods:
                    continue

                multiplier = 1.0

                if food.get("calories", 0) < 80:

                    multiplier = 2.5

                elif food.get("calories", 0) < 150:

                    multiplier = 2.0

                elif food.get("calories", 0) < 220:

                    multiplier = 1.5

                scaled_food = scale_food(
                    food,
                    multiplier
                )

                if can_add_food(
                    meal,
                    scaled_food,
                    target
                ):

                    meal.append(scaled_food)

                    used_foods.add(food_name)

                    added = True

                    break

            attempts += 1

            if not added or attempts > 60:
                break

    fill_meal(
        breakfast,
        breakfast_target
    )

    fill_meal(
        lunch,
        lunch_target
    )

    fill_meal(
        dinner,
        dinner_target
    )

    add_dynamic_staple(
        breakfast,
        breakfast_target,
        BRKDIN_STAPLES
    )

    add_dynamic_staple(
        lunch,
        lunch_target,
        LUNCH_STAPLES
    )

    add_dynamic_staple(
        dinner,
        dinner_target,
        BRKDIN_STAPLES
    )

    all_foods = (

        breakfast +

        lunch +

        dinner
    )

    totals = calculate_totals(
        all_foods
    )

    if adaptive_engine and user_id:

        for food in all_foods:

            adaptive_engine.store_recent_food(

                user_id,

                food.get("food", "")
            )

    print("\n========== FINAL OPTIMIZER OUTPUT ==========")
    print("User ID:", user_id)
    print(
        "Breakfast:",
        [x.get("food") for x in breakfast]
    )

    print(
        "Lunch:",
        [x.get("food") for x in lunch]
    )

    print(
        "Dinner:",
        [x.get("food") for x in dinner]
    )

    print("\n========== FINAL MACROS ==========")

    print(totals)

    print("============================================")

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