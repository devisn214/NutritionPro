from .constants import MACRO_SPLIT, CALORIES_PER_GRAM

def calculate_macros(calories):
    macros = {}

    for macro, ratio in MACRO_SPLIT.items():
        macro_calories = calories * ratio
        macros[f"{macro}_g"] = round(
            macro_calories / CALORIES_PER_GRAM[macro], 1
        )

    return macros
