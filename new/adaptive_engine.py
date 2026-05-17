import os
import json


class AdaptiveEngine:

    def __init__(self, memory_path="user_data/adaptive_memory.json"):

        self.memory_path = memory_path

        if not os.path.exists(self.memory_path):

            with open(self.memory_path, "w") as f:
                json.dump({}, f, indent=4)

    # =========================================================
    # LOAD MEMORY
    # =========================================================

    def load_memory(self):

        with open(self.memory_path, "r") as f:
            return json.load(f)

    # =========================================================
    # SAVE MEMORY
    # =========================================================

    def save_memory(self, data):

        with open(self.memory_path, "w") as f:
            json.dump(data, f, indent=4)

    # =========================================================
    # CREATE USER
    # =========================================================

    def ensure_user(self, data, user_id):

        if not user_id:
            return

        if user_id not in data:

            data[user_id] = {
                "foods": {},
                "total_feedback": 0
            }

    # =========================================================
    # UPDATE FEEDBACK
    # =========================================================

    def update_feedback(self, user_id, food_name, feedback):

        data = self.load_memory()

        self.ensure_user(data, user_id)

        if not user_id:
            return

        food_key = str(food_name).strip().lower()

        if food_key not in data[user_id]["foods"]:

            data[user_id]["foods"][food_key] = {
                "score": 0,
                "likes": 0,
                "dislikes": 0,
                "history": []
            }

        food_data = data[user_id]["foods"][food_key]

        learning_rate = 2

        if feedback > 0:

            food_data["score"] += learning_rate
            food_data["likes"] += 1

        elif feedback < 0:

            food_data["score"] -= learning_rate
            food_data["dislikes"] += 1

        else:

            food_data["score"] += 0.2

        food_data["score"] = max(
            -20,
            min(20, food_data["score"])
        )

        food_data["history"].append({
            "feedback": feedback
        })

        data[user_id]["total_feedback"] += 1

        self.save_memory(data)

    # =========================================================
    # GET SCORE
    # =========================================================

    def get_score(self, user_id, food_name):

        if not user_id:
            return 0

        data = self.load_memory()

        if user_id not in data:
            return 0

        food_key = str(food_name).strip().lower()

        if food_key not in data[user_id]["foods"]:
            return 0

        food_data = data[user_id]["foods"][food_key]

        return float(
            food_data.get("score", 0)
        )

    # =========================================================
    # GET ADAPTIVE SCORE
    # =========================================================

    def get_adaptive_score(self, user_id, food_name):

        return self.get_score(
            user_id,
            food_name
        )

    # =========================================================
    # GLOBAL ADAPTIVE SCORE
    # =========================================================

    def global_adaptive_score(self, rag_context):

        if not rag_context:
            return 0

        total = 0

        for item in rag_context:

            total += float(
                item.get(
                    "adaptive_score",
                    0
                )
            )

        return round(
            total / len(rag_context),
            2
        )

    # =========================================================
    # GET USER PREFERENCES
    # =========================================================

    def get_top_preferences(self, user_id, limit=10):

        if not user_id:
            return []

        data = self.load_memory()

        if user_id not in data:
            return []

        foods = data[user_id]["foods"]

        ranked = sorted(

            foods.items(),

            key=lambda x: x[1].get("score", 0),

            reverse=True
        )

        return ranked[:limit]

    # =========================================================
    # GET USER AVOID FOODS
    # =========================================================

    def get_avoid_foods(self, user_id, limit=10):

        if not user_id:
            return []

        data = self.load_memory()

        if user_id not in data:
            return []

        foods = data[user_id]["foods"]

        ranked = sorted(

            foods.items(),

            key=lambda x: x[1].get("score", 0)
        )

        return ranked[:limit]

    # =========================================================
    # RESET USER
    # =========================================================

    def reset_user(self, user_id):

        data = self.load_memory()

        if user_id in data:

            del data[user_id]

            self.save_memory(data)

    # =========================================================
    # DEBUG
    # =========================================================

    def print_user_memory(self, user_id):

        data = self.load_memory()

        if user_id not in data:

            print("No adaptive memory found")

            return

        print("\n========== USER ADAPTIVE MEMORY ==========")

        for food, info in data[user_id]["foods"].items():

            print(

                f"{food} | "
                f"score={info['score']} | "
                f"likes={info['likes']} | "
                f"dislikes={info['dislikes']}"

            )

        print("==========================================")