import os
import json
import pandas as pd

from sentence_transformers import SentenceTransformer


class FoodEmbeddingBuilder:

    def __init__(

        self,

        foods_csv="data/foods.csv",

        nutrients_csv="data/nutrients.csv",

        food_nutrient_csv="data/food_nutrient_map.csv",

        output_path="data/food_embeddings.json"

    ):

        self.foods_csv = foods_csv

        self.nutrients_csv = nutrients_csv

        self.food_nutrient_csv = food_nutrient_csv

        self.output_path = output_path

        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    # =====================================================
    # BUILD FOOD TEXT
    # =====================================================

    def build_food_descriptions(self):

        foods_df = pd.read_csv(
            self.foods_csv
        )

        nutrients_df = pd.read_csv(
            self.nutrients_csv
        )

        food_nutrient_df = pd.read_csv(
            self.food_nutrient_csv
        )

        nutrient_map = {}

        for _, row in nutrients_df.iterrows():

            nutrient_map[
                str(row["nutrient_id"]).strip()
            ] = str(row["name"]).strip()

        food_descriptions = []

        for _, food in foods_df.iterrows():

            food_id = str(
                food["food_id"]
            ).strip()

            food_name = str(
                food["food_name"]
            ).strip()

            category = str(
                food.get("category", "")
            ).strip()

            diet_type = str(
                food.get("diet_type", "")
            ).strip()

            nutrient_rows = food_nutrient_df[
                food_nutrient_df["food_id"].astype(str).str.strip() == food_id
            ]

            nutrient_names = []

            for _, n in nutrient_rows.iterrows():

                nutrient_id = str(
                    n["nutrient_id"]
                ).strip()

                if nutrient_id in nutrient_map:

                    nutrient_names.append(
                        nutrient_map[nutrient_id]
                    )

            nutrient_text = ", ".join(
                list(set(nutrient_names))
            )

            description = f"""

            Food: {food_name}

            Category: {category}

            Diet Type: {diet_type}

            Nutrients: {nutrient_text}

            """

            food_descriptions.append({

                "food_id": food_id,

                "food_name": food_name,

                "description": description.strip()

            })

        return food_descriptions

    # =====================================================
    # GENERATE EMBEDDINGS
    # =====================================================

    def generate_embeddings(self):

        food_descriptions = self.build_food_descriptions()

        texts = [

            item["description"]

            for item in food_descriptions
        ]

        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)


        final_data = []

        for item, emb in zip(
            food_descriptions,
            embeddings
        ):

            final_data.append({

                "food_id": item["food_id"],

                "food_name": item["food_name"],

                "description": item["description"],

                "embedding": emb.tolist()

            })

        os.makedirs(
            os.path.dirname(self.output_path),
            exist_ok=True
        )

        with open(self.output_path, "w") as f:

            json.dump(
                final_data,
                f
            )

        print("\n========== EMBEDDING BUILD COMPLETE ==========")

        print(f"Saved embeddings to: {self.output_path}")

        print(f"Total foods embedded: {len(final_data)}")

        print("==============================================")
        

if __name__ == "__main__":

    builder = FoodEmbeddingBuilder()

    builder.generate_embeddings()