import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

MODEL_NAME = "gemini-3.6-flash"


class GeminiLLM:

    def __init__(self):

        api_key = os.getenv(
            "GEMINI_API_KEY"
        )

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = MODEL_NAME


    def generate(self, prompt):

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        # ====================================================
        # NORMAL RESPONSE
        # ====================================================

        if getattr(response, "text", None):

            text = response.text.strip()

            if text:
                return text


        # ====================================================
        # FALLBACK: READ CANDIDATE PARTS
        # ====================================================

        candidates = getattr(
            response,
            "candidates",
            None
        )

        if candidates:

            parts_text = []

            for candidate in candidates:

                content = getattr(
                    candidate,
                    "content",
                    None
                )

                if not content:
                    continue

                parts = getattr(
                    content,
                    "parts",
                    None
                )

                if not parts:
                    continue

                for part in parts:

                    text = getattr(
                        part,
                        "text",
                        None
                    )

                    if text:

                        parts_text.append(
                            text.strip()
                        )

            if parts_text:

                return "\n".join(
                    parts_text
                )


        # ====================================================
        # NO TEXT RESPONSE
        # ====================================================

        finish_reason = None

        if candidates:

            first_candidate = candidates[0]

            finish_reason = getattr(
                first_candidate,
                "finish_reason",
                None
            )


        raise RuntimeError(
            "Gemini returned no text. "
            f"Finish reason: {finish_reason}"
        )


def get_llm():

    return GeminiLLM()