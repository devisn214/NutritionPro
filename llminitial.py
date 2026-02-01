import requests

class NutritionLLM:
    def __init__(self, model="llama3.1:8b-instruct-q4_K_M"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"

    def generate_plan(self, user_profile, rag_context):
        prompt = self._build_prompt(user_profile, rag_context)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 300,
                "temperature": 0.4
            }
        }

        response = requests.post(
            self.url,
            json=payload,
            timeout=180
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama error: {response.text}")

        return response.json().get("response", "").strip()

    def _build_prompt(self, user, context):
        context_text = ""

        for c in context[:5]:
            context_text += f"""
Biomarker: {c['biomarker']}
Related Nutrient: {c['nutrient']}
Food Sources: {", ".join(c['foods'][:5])}
Genetic Factors: {", ".join([g['gene'] for g in c['genes']])}
"""

        return f"""
You are a nutrition recommendation assistant.

User Profile:
Age: {user['age']}
Gender: {user['gender']}
Diet Preference: {user['diet_preference']}
Activity Level: {user['activity_level']}

Knowledge Graph Context:
{context_text}

Task:
Generate exactly 3 meals for today (breakfast, lunch, dinner).
- Suggest foods to include
- Briefly explain why based on biomarkers
- Mention gene influence only if relevant
- Avoid medical diagnosis
- Keep total response under 250 words
"""
