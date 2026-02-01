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

def process_biomarkers(user_test_results):
    
    final_recommendations = []

    for test in user_test_results:

        b_info = df_biomarkers[df_biomarkers['name'].str.lower() == test['name'].lower()]
        if b_info.empty: continue
        
        b_id = b_info.iloc[0]['biomarker_id']
        n_id = b_info.iloc[0]['nutrient_id']
    
        thresh = df_thresholds[df_thresholds['biomarker_id'] == b_id]
        if thresh.empty: continue
        
        low_v = thresh.iloc[0]['low_value']
        high_v = thresh.iloc[0]['high_value']
        val = test['value']


        is_abnormal = False
        reason = ""

        if val < low_v:
            is_abnormal = True
            reason = "Low/Deficient"
        
        '''elif val > high_v:
            is_abnormal = True
            reason = "High/Excess"'''

        if is_abnormal:
          
            matching_food_ids = df_food_nutrient[df_food_nutrient['nutrient_id'] == n_id]['food_id']

            rec_foods = df_foods[df_foods['food_id'].isin(matching_food_ids)]['food_name'].tolist()
            
     
            n_name = df_nutrients[df_nutrients['nutrient_id'] == n_id]['name'].iloc[0]

            final_recommendations.append({
                "biomarker": test['name'],
                "current_value": val,
                "range": f"{low_v} - {high_v}",
                "status": reason,
                "target_nutrient": n_name,
                "recommended_foods": rec_foods
            })

    return final_recommendations