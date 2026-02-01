import pandas as pd
import os


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
DATA_DIR = os.path.join(PROJECT_ROOT, "data")


def load_gene_data():
    return {
        "genes": pd.read_csv(os.path.join(DATA_DIR, "genes.csv")),
        "nutrients": pd.read_csv(os.path.join(DATA_DIR, "nutrients.csv")),
        "food_map": pd.read_csv(os.path.join(DATA_DIR, "food_nutrient_map.csv")),
        "foods": pd.read_csv(os.path.join(DATA_DIR, "foods.csv"))
    }

def get_foods_for_nutrient(nutrient_name, data, limit=5):
    # Find nutrient ID
    nutrient_row = data["nutrients"][data["nutrients"]['name'].str.contains(nutrient_name, case=False, na=False)]
    if nutrient_row.empty:
        return []
    
    n_id = nutrient_row.iloc[0]['nutrient_id']
    
    # getting foods rich in this nutrient
    matching_map = data["food_map"][data["food_map"]['nutrient_id'] == n_id].sort_values(by='amount', ascending=False)
    top_food_ids = matching_map.head(limit)['food_id']

    # Getting actual names of these foods
    recommended_foods = data["foods"][data["foods"]['food_id'].isin(top_food_ids)]['food_name'].tolist()
    
    return recommended_foods

def process_genes(user_gene_results):
   
    data = load_gene_data()
    recommendations = []

    for user_gene in user_gene_results:
        symbol = user_gene.get("name", "").upper()
        efficiency = user_gene.get("efficiency")

        gene_info = data["genes"][data["genes"]['gene_symbol'] == symbol]
        
        if not gene_info.empty and efficiency is not None:
            threshold = gene_info.iloc[0]['threshold']
            
            if efficiency < threshold:
              
                nutrient_needed = gene_info.iloc[0]['affected_nutrients']
                
                all_foods = []
                for nut in nutrient_needed.split(): 
                    all_foods.extend(get_foods_for_nutrient(nut, data))

                recommendations.append({
                    "gene": symbol,
                    "reason": f"Reduced efficiency ({efficiency}%) below threshold ({threshold}%)",
                    "nutrient": nutrient_needed,
                    "foods": list(set(all_foods))[:10] 
                })
                

    return recommendations
