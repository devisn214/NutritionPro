from .derived_macro_estimator import estimate_food_macros
from neo4j import GraphDatabase
import random
import atexit

class NutritionKGQuery:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="neo4jabc"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.food_nutrient_cache = self._load_cache()

    def _load_cache(self):
        query = """
        MATCH (f:Food)-[:CONTAINS]->(n:Nutrient)
        RETURN toLower(f.name) AS food, collect(distinct n.name) AS nutrients
        """
        cache = {}
        try:
            with self.driver.session() as session:
                result = session.run(query)
                for r in result:
                    cache[r["food"]] = set(r["nutrients"])
        except Exception:
            pass
        return cache

    def get_foods_covering_nutrients(self, nutrients):
        query = """
        MATCH (f:Food)-[:CONTAINS]->(n:Nutrient)
        WHERE n.name IN $nutrients
        RETURN
            f.name AS food,
            collect(distinct n.name) AS nutrients,
            count(distinct n) AS coverage
        ORDER BY coverage DESC
        """
        with self.driver.session() as session:
            result = session.run(query, nutrients=list(nutrients))
            return [dict(r) for r in result]
            
    def get_food_nutrients(self, food_name):
        if not food_name:
            return set()
        return self.food_nutrient_cache.get(str(food_name).lower(), set())

    def close(self):
        self.driver.close()

kg = NutritionKGQuery()
atexit.register(kg.close)

MEAL_SPLIT = {
    "breakfast": 0.30,
    "lunch": 0.40,
    "dinner": 0.30
}

def get_dynamic_staples():
    query = """
    MATCH (f:Food)
    WHERE f.category IN [
        'Grain',
        'Tuber',
        'Legume'
    ]
    RETURN
        f.id AS food_id,
        f.name AS food,
        f.category AS category
    """
    staples = []
    with kg.driver.session() as session:
        rows = session.run(query)
        for row in rows:
            est = estimate_food_macros(row["food_id"])
            est["food"] = row["food"]
            est["category"] = row["category"]
            staples.append(est)
    return staples

def get_meal_nutrients(meal):
    nutrients = set()
    for food in meal:
        nutrients.update(food.get("nutrients", set()))
    return nutrients

def add_missing_nutrient_foods(meal, target, foods, missing_nutrients, used_foods_global):
    attempted = set()
    
    while missing_nutrients:
        best_food = None
        best_coverage = 0

        for food in foods:
            name = food["food"].lower()
            if name in used_foods_global or name in attempted:
                continue

            nutrients = food.get("nutrients", set())
            coverage = len(nutrients & missing_nutrients)

            if coverage > best_coverage:
                best_coverage = coverage
                best_food = food

        if not best_food:
            break
            
        attempted.add(best_food["food"].lower())

        multiplier = 1.0
        if best_food.get("calories", 0) < 80:
            multiplier = 2.5
        elif best_food.get("calories", 0) < 150:
            multiplier = 2.0
        elif best_food.get("calories", 0) < 220:
            multiplier = 1.5

        candidate = scale_food(best_food, multiplier)

        if can_add_food(meal, candidate, target):
            meal.append(candidate)
            used_foods_global.add(candidate["food"].lower())
            missing_nutrients -= best_food.get("nutrients", set())

def build_food_objects(rag_foods):
    foods = []
    for food in rag_foods:
        food_id = food["food_id"]
        est = estimate_food_macros(food_id)
        est["food"] = food.get("food", "")
        est["category"] = food.get("category", est.get("category", "Unknown"))
        est["nutrients"] = kg.get_food_nutrients(est["food"])
        est["confidence_score"] = food.get("confidence_score", 0)
        est["semantic_score"] = food.get("semantic_score", 0)
        est["adaptive_score"] = food.get("adaptive_score", 0)
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

def scale_food(food, multiplier):
    scaled = food.copy()
    scaled["portion_multiplier"] = round(multiplier, 2)
    scaled["calories"] = round(food.get("calories", 0) * multiplier, 1)
    scaled["protein_g"] = round(food.get("protein_g", 0) * multiplier, 1)
    scaled["carbs_g"] = round(food.get("carbs_g", 0) * multiplier, 1)
    scaled["fat_g"] = round(food.get("fat_g", 0) * multiplier, 1)
    return scaled

def meal_totals(meal):
    return calculate_totals(meal)

def can_add_food(meal, food, target):
    totals = meal_totals(meal)
    next_cal = totals["calories"] + food.get("calories", 0)
    next_protein = totals["protein_g"] + food.get("protein_g", 0)
    next_carbs = totals["carbs_g"] + food.get("carbs_g", 0)
    next_fat = totals["fat_g"] + food.get("fat_g", 0)

    if next_cal > target["calories"] * 1.15:
        return False
    if next_protein > target["protein_g"] * 1.30:
        return False
    if next_carbs > target["carbs_g"] * 1.25:
        return False
    if next_fat > target["fat_g"] * 1.25:
        return False
    return True

def add_dynamic_staple(meal, target, staples, allowed_categories, used_foods):
    totals = meal_totals(meal)
    if totals["carbs_g"] >= target["carbs_g"] * 0.75:
        return
        
    valid_staples = [
        s for s in staples 
        if s.get("category") in allowed_categories
        and s.get("food", "").lower() not in used_foods
    ]
    
    if valid_staples:
        staple = max(valid_staples, key=lambda x: x.get("carbs_g", 0))
        meal.append(staple.copy())
        used_foods.add(staple.get("food", "").lower())

def optimize_meal_plan(
    rag_foods,
    target_calories,
    target_protein,
    target_carbs,
    target_fats,
    required_nutrients=None,
    adaptive_engine=None,
    user_id=None,
    previous_confidence=0
):
    foods = build_food_objects(rag_foods)
    required_nutrients = (required_nutrients or set())
    recent_foods = set()

    if adaptive_engine and user_id:
        recent = adaptive_engine.get_recent_foods(user_id, limit=15)
        recent_foods = set(x.lower() for x in recent)

    for food in foods:
        food_nutrients = food.get("nutrients", set())
        coverage = len(food_nutrients & required_nutrients)
        food["coverage_score"] = coverage
        
        food_name = str(food.get("food", "")).lower()
        reuse_penalty = -40 if food_name in recent_foods else 0
        
        calories = food.get("calories", 0)
        protein = food.get("protein_g", 0)
        carbs = food.get("carbs_g", 0)
        fats = food.get("fat_g", 0)
        confidence = food.get("confidence_score", 0)
        semantic = food.get("semantic_score", 0)
        adaptive = food.get("adaptive_score", 0)
        
        confidence_boost = -15 if confidence < previous_confidence else 10

        food["optimizer_score"] = (
            calories * 0.28 +
            carbs * 0.32 +
            protein * 0.22 -
            fats * 0.05 +
            confidence * 0.05 +
            semantic * 8 +
            adaptive +
            confidence_boost +
            reuse_penalty
        )

    foods = sorted(
        foods,
        key=lambda x: (
            x.get("coverage_score", 0),
            x.get("optimizer_score", 0)
        ),
        reverse=True
    )

    breakfast_target = {
        "calories": target_calories * MEAL_SPLIT["breakfast"],
        "protein_g": target_protein * MEAL_SPLIT["breakfast"],
        "carbs_g": target_carbs * MEAL_SPLIT["breakfast"],
        "fat_g": target_fats * MEAL_SPLIT["breakfast"]
    }

    lunch_target = {
        "calories": target_calories * MEAL_SPLIT["lunch"],
        "protein_g": target_protein * MEAL_SPLIT["lunch"],
        "carbs_g": target_carbs * MEAL_SPLIT["lunch"],
        "fat_g": target_fats * MEAL_SPLIT["lunch"]
    }

    dinner_target = {
        "calories": target_calories * MEAL_SPLIT["dinner"],
        "protein_g": target_protein * MEAL_SPLIT["dinner"],
        "carbs_g": target_carbs * MEAL_SPLIT["dinner"],
        "fat_g": target_fats * MEAL_SPLIT["dinner"]
    }

    breakfast = []
    lunch = []
    dinner = []
    used_foods = set()

    def fill_meal(meal, target, preferred_count=4):
        attempts = 0
        used_categories = {}
        for f in meal:
            cat = f.get("category")
            if cat:
                used_categories[cat] = used_categories.get(cat, 0) + 1
        
        while len(meal) < preferred_count:
            added = False
            for food in foods:
                food_name = str(food.get("food", "")).lower()
                if food_name in used_foods:
                    continue
                    
                food_cat = food.get("category")
                if food_cat and used_categories.get(food_cat, 0) >= 2:
                    continue

                multiplier = 1.0
                if food.get("calories", 0) < 80:
                    multiplier = 2.5
                elif food.get("calories", 0) < 150:
                    multiplier = 2.0
                elif food.get("calories", 0) < 220:
                    multiplier = 1.5

                scaled_food = scale_food(food, multiplier)
                
                if can_add_food(meal, scaled_food, target):
                    meal.append(scaled_food)
                    used_foods.add(food_name)
                    if food_cat:
                        used_categories[food_cat] = used_categories.get(food_cat, 0) + 1
                    added = True
                    break

            attempts += 1
            if not added or attempts > 60:
                break

    fill_meal(breakfast, breakfast_target)
    fill_meal(lunch, lunch_target)
    fill_meal(dinner, dinner_target)
    
    staples = get_dynamic_staples()
    
    add_dynamic_staple(breakfast, breakfast_target, staples, allowed_categories=['Grain'], used_foods=used_foods)
    add_dynamic_staple(lunch, lunch_target, staples, allowed_categories=['Grain', 'Tuber'], used_foods=used_foods)
    add_dynamic_staple(dinner, dinner_target, staples, allowed_categories=['Grain'], used_foods=used_foods)
    
    if required_nutrients:
        current_nutrients = get_meal_nutrients(breakfast + lunch + dinner)
        missing = set(required_nutrients) - current_nutrients
        
        if missing:
            add_missing_nutrient_foods(breakfast, breakfast_target, foods, missing, used_foods)
        if missing:
            add_missing_nutrient_foods(lunch, lunch_target, foods, missing, used_foods)
        if missing:
            add_missing_nutrient_foods(dinner, dinner_target, foods, missing, used_foods)

    all_foods = breakfast + lunch + dinner
    totals = calculate_totals(all_foods)

    if adaptive_engine and user_id:
        for food in all_foods:
            adaptive_engine.store_recent_food(user_id, food.get("food", ""))

    print("\n========== FINAL OPTIMIZER OUTPUT ==========")
    print("User ID:", user_id)
    print("Breakfast:", [x.get("food") for x in breakfast])
    print("Lunch:", [x.get("food") for x in lunch])
    print("Dinner:", [x.get("food") for x in dinner])
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