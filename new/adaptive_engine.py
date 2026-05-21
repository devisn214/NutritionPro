import os
import json
from datetime import datetime


class AdaptiveEngine:

    def __init__(self, memory_path="user_data/adaptive_memory.json"):

        self.memory_path = memory_path

        if not os.path.exists(self.memory_path):

            with open(self.memory_path, "w") as f:
                json.dump({}, f, indent=4)

    def load_memory(self):

        if not os.path.exists(self.memory_path):

            with open(self.memory_path, "w") as f:
                json.dump({}, f, indent=4)

        try:

            with open(self.memory_path, "r") as f:

                content = f.read().strip()

                if not content:
                    return {}

                return json.loads(content)

        except Exception as e:

            print("ADAPTIVE MEMORY LOAD ERROR:", e)

            return {}

    def save_memory(self, data):

        try:

            with open(self.memory_path, "w") as f:

                json.dump(data, f, indent=4)

        except Exception as e:

            print("ADAPTIVE MEMORY SAVE ERROR:", e)

    def ensure_user(self, data, user_id):

        if not user_id:
            return

        if user_id not in data:

            data[user_id] = {

                "foods": {},

                "total_feedback": 0,

                "recent_foods": [],

                "best_confidence": 0,

                "recommendation_attempts": 0
            }

    def apply_decay(self, score, last_updated):

        try:

            old_time = float(last_updated)

        except:

            return score

        current_time = datetime.now().timestamp()

        gap_seconds = current_time - old_time

        days_gap = gap_seconds / 86400

        decay_factor = max(
            0.75,
            1 - (days_gap * 0.01)
        )

        return score * decay_factor

    def update_feedback(self, user_id, food_name, feedback):

        data = self.load_memory()

        self.ensure_user(data, user_id)

        if not user_id:
            return

        food_key = str(food_name).strip().lower()

        if not food_key:
            return

        if food_key not in data[user_id]["foods"]:

            data[user_id]["foods"][food_key] = {

                "score": 0,

                "likes": 0,

                "dislikes": 0,

                "history": [],

                "last_updated":
                datetime.now().timestamp()
            }

        food_data = data[user_id]["foods"][food_key]

        current_score = float(
            food_data.get("score", 0)
        )

        current_score = self.apply_decay(

            current_score,

            food_data.get(
                "last_updated",
                datetime.now().timestamp()
            )
        )

        learning_rate = 2

        if feedback > 0:

            current_score += learning_rate

            food_data["likes"] += 1

        elif feedback < 0:

            current_score -= learning_rate

            food_data["dislikes"] += 1

        else:

            current_score += 0.2

        current_score = max(
            -20,
            min(20, current_score)
        )

        food_data["score"] = round(
            current_score,
            2
        )

        food_data["last_updated"] = (
            datetime.now().timestamp()
        )

        food_data["history"].append({

            "feedback": feedback,

            "timestamp":
            datetime.now().isoformat()
        })

        food_data["history"] = (
            food_data["history"][-50:]
        )

        data[user_id]["total_feedback"] += 1

        self.save_memory(data)

    def update_meal_feedback(self, user_id, foods, feedback):

        if not foods:
            return

        for food in foods:

            self.update_feedback(
                user_id,
                food,
                feedback
            )

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

        score = float(
            food_data.get("score", 0)
        )

        score = self.apply_decay(

            score,

            food_data.get(
                "last_updated",
                datetime.now().timestamp()
            )
        )

        return round(score, 2)

    def get_adaptive_score(self, user_id, food_name):

        return self.get_score(
            user_id,
            food_name
        )

    def store_recent_food(self, user_id, food_name):

        if not user_id:
            return

        data = self.load_memory()

        self.ensure_user(data, user_id)

        recent = data[user_id].get(
            "recent_foods",
            []
        )

        recent.append(food_name)

        recent = recent[-30:]

        data[user_id]["recent_foods"] = recent

        self.save_memory(data)

    def get_recent_foods(self, user_id, limit=15):

        if not user_id:
            return []

        data = self.load_memory()

        if user_id not in data:
            return []

        recent = data[user_id].get(
            "recent_foods",
            []
        )

        return recent[-limit:]

    def global_adaptive_score(self, rag_context):

        if not rag_context:
            return 0

        total = 0

        count = 0

        for item in rag_context:

            score = float(

                item.get(
                    "adaptive_score",
                    0
                )
            )

            total += score

            count += 1

        if count == 0:
            return 0

        return round(total / count, 2)

    def get_top_preferences(self, user_id, limit=10):

        if not user_id:
            return []

        data = self.load_memory()

        if user_id not in data:
            return []

        foods = data[user_id]["foods"]

        ranked = sorted(

            foods.items(),

            key=lambda x:
            x[1].get("score", 0),

            reverse=True
        )

        return ranked[:limit]

    def get_avoid_foods(self, user_id, limit=10):

        if not user_id:
            return []

        data = self.load_memory()

        if user_id not in data:
            return []

        foods = data[user_id]["foods"]

        ranked = sorted(

            foods.items(),

            key=lambda x:
            x[1].get("score", 0)
        )

        return ranked[:limit]

    def get_best_confidence(self, user_id):

        if not user_id:
            return 0

        data = self.load_memory()

        if user_id not in data:
            return 0

        return float(

            data[user_id].get(
                "best_confidence",
                0
            )
        )

    def update_best_confidence(
        self,
        user_id,
        confidence_score
    ):

        if not user_id:
            return

        data = self.load_memory()

        self.ensure_user(data, user_id)

        current_best = float(

            data[user_id].get(
                "best_confidence",
                0
            )
        )

        if confidence_score > current_best:

            data[user_id][
                "best_confidence"
            ] = confidence_score

        self.save_memory(data)

    def increment_attempts(self, user_id):

        if not user_id:
            return

        data = self.load_memory()

        self.ensure_user(data, user_id)

        current = int(

            data[user_id].get(
                "recommendation_attempts",
                0
            )
        )

        data[user_id][
            "recommendation_attempts"
        ] = current + 1

        self.save_memory(data)

    def reset_user(self, user_id):

        data = self.load_memory()

        if user_id in data:

            del data[user_id]

            self.save_memory(data)

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