# nutrition_engine/bmr.py

def calculate_bmr(user):
    weight = user["weight_kg"]
    height = user["height_cm"]
    age = user["age"]
    gender = user["gender"].lower()

    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:
        return 10 * weight + 6.25 * height - 5 * age - 161
