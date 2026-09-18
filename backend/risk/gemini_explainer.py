import os

from google import genai


class GeminiRiskExplainer:

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set."
            )

        self.client = genai.Client(
            api_key=api_key
        )

        self.model = "gemini-3.6-flash"

    def explain(
        self,
        function_name,
        file_name,
        risk_score,
        risk_level,
        top_features,
        source_code="",
        graph_context=None,
    ):

        feature_text = "\n".join(
            [
                f"- {item['label']}: "
                f"{item['value']} "
                f"(model importance: "
                f"{item['importance']:.2%})"
                for item in top_features
            ]
        )

        graph_text = graph_context or "No additional graph context."

        prompt = f"""
You are the explanation engine for CodeAtlas,
an AI-powered Python codebase intelligence platform.

Explain why the machine-learning model flagged a
Python function as risky.

IMPORTANT:
- Do not change or recalculate the risk score.
- Do not invent metrics.
- Do not claim that a feature causes bugs.
- Clearly distinguish model signals from certainty.
- Keep the explanation concise and developer-friendly.

Function: {function_name}
File: {file_name}

Risk score: {risk_score}%
Risk level: {risk_level}

Top model signals:
{feature_text}

Graph context:
{graph_text}

Source code:
{source_code}

Give the response in this format:

Summary:
<2-3 sentence explanation>

Key factors:
- <factor>
- <factor>
- <factor>

Developer takeaway:
<one practical sentence>
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        return response.text