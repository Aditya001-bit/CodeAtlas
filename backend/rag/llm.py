import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"


class GeminiLLM:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set.")

        self.client = genai.Client(api_key=api_key)
        self.model = MODEL_NAME

    def generate(self, prompt):
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        return response.text


def get_llm():
    return GeminiLLM()