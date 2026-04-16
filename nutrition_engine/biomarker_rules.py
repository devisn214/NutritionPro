import pandas as pd
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR) 
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

df_biomarkers = pd.read_csv(os.path.join(DATA_DIR, "biomarkers.csv"))
df_thresholds = pd.read_csv(os.path.join(DATA_DIR, "biomarkers_maxvalue.csv"))
df_nutrients = pd.read_csv(os.path.join(DATA_DIR, "nutrients.csv"))
df_food_nutrient = pd.read_csv(os.path.join(DATA_DIR, "food_nutrient_map.csv"))
df_foods = pd.read_csv(os.path.join(DATA_DIR, "foods.csv"))

def process_biomarkers(user_test_results, user):
    
    final_recommendations = []

    gender = user.get("gender", "male").lower()

    for test in user_test_results:

    
        b_info = df_biomarkers[ df_biomarkers['name'].str.lower() == test['name'].lower()]

        if b_info.empty:
            continue
        
        b_id = b_info.iloc[0]['biomarker_id']
        n_id = b_info.iloc[0]['nutrient_id']

        
        thresh = df_thresholds[df_thresholds['biomarker_id'] == b_id]

        if thresh.empty:
            continue

        row = thresh.iloc[0]
        try:
            if gender == "male":
                low_v = row['low_male']
                high_v = row['high_male']
            else:
                low_v = row['low_female']
                high_v = row['high_female']
        except KeyError:
            low_v = row.get('low_value', 0)
            high_v = row.get('high_value', 9999)

        val = float(test['value'])

      
        if val < low_v:
            direction = "increase"
            reason = "Low/Deficient"
        elif val > high_v:
            direction = "decrease"
            reason = "High/Excess"
        else:
            continue

        food_map = df_food_nutrient[df_food_nutrient['nutrient_id'] == n_id]

        if food_map.empty:
            continue

        if direction == "increase":
            food_map = food_map.sort_values(by='amount', ascending=False)
        else:
            food_map = food_map.sort_values(by='amount', ascending=True)

        matching_food_ids = food_map['food_id'].head(10)  

        rec_foods = df_foods[df_foods['food_id'].isin(matching_food_ids)]['food_name'].tolist()

       
        n_name_row = df_nutrients[df_nutrients['nutrient_id'] == n_id]

        if n_name_row.empty:
            continue

        n_name = n_name_row.iloc[0]['name']

       
        final_recommendations.append({
            "biomarker": test['name'],
            "current_value": val,
            "low": low_v,
            "high": high_v,
            "status": reason,
            "direction": direction,
            "nutrient_id": n_id,
            "target_nutrient": n_name,
            "recommended_foods": rec_foods
        })

    return final_recommendations