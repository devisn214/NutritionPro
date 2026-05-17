import os
import json


class FeedbackManager:

    def __init__(self, feedback_path="user_data/meal_feedback.json"):

        self.feedback_path = feedback_path

        os.makedirs(
            os.path.dirname(self.feedback_path),
            exist_ok=True
        )

        if not os.path.exists(self.feedback_path):

            with open(self.feedback_path, "w") as f:
                json.dump({}, f, indent=4)

    # =====================================================
    # LOAD FEEDBACK
    # =====================================================

    def load_feedback(self):

        with open(self.feedback_path, "r") as f:
            return json.load(f)

    # =====================================================
    # SAVE FEEDBACK
    # =====================================================

    def save_feedback_data(self, data):

        with open(self.feedback_path, "w") as f:
            json.dump(data, f, indent=4)

    # =====================================================
    # ENSURE USER
    # =====================================================

    def ensure_user(self, data, user_id):

        if user_id not in data:

            data[user_id] = {
                "feedback_history": [],
                "food_feedback": {}
            }

    # =====================================================
    # SAVE FEEDBACK
    # =====================================================

    def save_feedback(

        self,

        user_id,

        meal_type,

        foods,

        rating,

        comment=""

    ):

        data = self.load_feedback()

        self.ensure_user(data, user_id)

        feedback_entry = {

            "meal_type": meal_type,

            "foods": foods,

            "rating": rating,

            "comment": comment

        }

        data[user_id]["feedback_history"].append(
            feedback_entry
        )

        for food in foods:

            food_key = food.strip().lower()

            if food_key not in data[user_id]["food_feedback"]:

                data[user_id]["food_feedback"][food_key] = {

                    "total_score": 0,

                    "likes": 0,

                    "dislikes": 0,

                    "history": []

                }

            food_data = data[user_id]["food_feedback"][food_key]

            food_data["total_score"] += rating

            if rating > 0:

                food_data["likes"] += 1

            elif rating < 0:

                food_data["dislikes"] += 1

            food_data["history"].append({

                "rating": rating,

                "comment": comment

            })

        self.save_feedback_data(data)

    # =====================================================
    # GET USER FEEDBACK
    # =====================================================

    def get_user_feedback(self, user_id):

        data = self.load_feedback()

        if user_id not in data:
            return {}

        return data[user_id]

    # =====================================================
    # GET FOOD SCORE
    # =====================================================

    def get_food_score(
        self,
        user_id,
        food_name
    ):

        data = self.load_feedback()

        if user_id not in data:
            return 0

        food_key = food_name.strip().lower()

        if food_key not in data[user_id]["food_feedback"]:
            return 0

        food_data = data[user_id]["food_feedback"][food_key]

        likes = food_data.get("likes", 0)

        dislikes = food_data.get("dislikes", 0)

        total = likes + dislikes

        if total == 0:
            return 0

        score = (likes - dislikes) / total

        return round(score * 10, 2)

    # =====================================================
    # GET TOP LIKED FOODS
    # =====================================================

    def get_top_liked_foods(
        self,
        user_id,
        limit=10
    ):

        data = self.load_feedback()

        if user_id not in data:
            return []

        foods = data[user_id]["food_feedback"]

        ranked = sorted(

            foods.items(),

            key=lambda x: x[1].get("total_score", 0),

            reverse=True

        )

        return ranked[:limit]

    # =====================================================
    # GET MOST DISLIKED FOODS
    # =====================================================

    def get_most_disliked_foods(
        self,
        user_id,
        limit=10
    ):

        data = self.load_feedback()

        if user_id not in data:
            return []

        foods = data[user_id]["food_feedback"]

        ranked = sorted(

            foods.items(),

            key=lambda x: x[1].get("total_score", 0)

        )

        return ranked[:limit]

    # =====================================================
    # RESET USER FEEDBACK
    # =====================================================

    def reset_user_feedback(
        self,
        user_id
    ):

        data = self.load_feedback()

        if user_id in data:

            del data[user_id]

            self.save_feedback_data(data)