import os
import time

from dotenv import load_dotenv
from google import genai


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# GEMINI CONFIGURATION
# ============================================================

MODEL_NAME = "gemini-3.6-flash"


# ============================================================
# RISK EXPLANATION
# ============================================================

def explain_risk_with_gemini(
    function_name,
    file_name,
    risk_level,
    risk_probability,
    reasons,
    top_features,
):
    """
    Generate a short, developer-friendly explanation
    for a Random Forest risk prediction.

    Random Forest:
        Decides the risk.

    Gemini:
        Explains the risk.

    Gemini does NOT calculate or modify the risk score.
    """

    # --------------------------------------------------------
    # Check API key
    # --------------------------------------------------------

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "explanation": (
                "Gemini explanation is unavailable because "
                "GEMINI_API_KEY is not configured."
            ),
            "gemini_available": False,
            "error": "GEMINI_API_KEY is not configured.",
        }

    # --------------------------------------------------------
    # Create Gemini client
    # --------------------------------------------------------

    client = genai.Client(
        api_key=api_key
    )

    # --------------------------------------------------------
    # Prepare model signals
    # --------------------------------------------------------

    if reasons:
        reason_text = "\n".join(
            f"- {reason}"
            for reason in reasons[:4]
        )
    else:
        reason_text = "- No strong model signals."

    if top_features:
        feature_text = "\n".join(
            [
                f"- {item.get('label', item.get('feature'))}: "
                f"{item.get('value')}"
                for item in top_features[:4]
            ]
        )
    else:
        feature_text = "- No additional feature information."

    # --------------------------------------------------------
    # Gemini prompt
    # --------------------------------------------------------

    prompt = f"""
You are CodeAtlas, a codebase intelligence platform.

Explain the Random Forest risk prediction for this
Python function using ONLY the supplied information.

IMPORTANT RULES:

- Random Forest already decided the risk level.
- Do NOT calculate a new risk score.
- Do NOT change the risk level.
- Gemini only explains the prediction.
- Do NOT claim that the function definitely contains a bug.
- Keep the explanation concise and useful to a developer.
- Write EXACTLY 2 short sentences.
- Keep the total response UNDER 45 WORDS.
- Sentence 1: explain why the model assigned this risk level.
- Sentence 2: explain the most important thing a developer
  should watch when modifying this function.
- Avoid generic advice.
- Do not repeat the probability unless it helps explain
  the result.
- Start directly with the explanation.
- Do not use headings.
- Do not use bullet points.

FUNCTION:
{function_name}

FILE:
{file_name}

RISK LEVEL:
{risk_level}

RISK PROBABILITY:
{risk_probability:.2%}

MODEL REASONS:
{reason_text}

IMPORTANT FEATURES:
{feature_text}
"""

    # --------------------------------------------------------
    # Retry transient Gemini errors
    # --------------------------------------------------------

    max_attempts = 4

    for attempt in range(max_attempts):

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )

            # ------------------------------------------------
            # Extract response
            # ------------------------------------------------

            text = getattr(
                response,
                "text",
                None,
            )

            if text and text.strip():

                explanation = text.strip()

                return {
                    "explanation": explanation,
                    "gemini_available": True,
                    "error": None,
                }

            # ------------------------------------------------
            # Empty Gemini response
            # ------------------------------------------------

            return {
                "explanation": (
                    "Gemini returned an empty explanation."
                ),
                "gemini_available": False,
                "error": "Gemini returned an empty response.",
            }

        except Exception as error:

            error_text = str(error)

            # ------------------------------------------------
            # PRINT ACTUAL GEMINI ERROR
            # ------------------------------------------------

            print(
                "\n========== GEMINI ERROR =========="
            )
            print(error_text)
            print(
                "=================================="
            )

            # ------------------------------------------------
            # Retry temporary API errors
            # ------------------------------------------------

            transient_error = (
                "503" in error_text
                or "UNAVAILABLE" in error_text
                or "429" in error_text
                or "RESOURCE_EXHAUSTED" in error_text
                or "500" in error_text
                or "INTERNAL" in error_text
            )

            if (
                transient_error
                and attempt < max_attempts - 1
            ):

                wait_time = 2 ** attempt

                print(
                    f"Retrying in {wait_time}s..."
                )

                time.sleep(
                    wait_time
                )

                continue

            # ------------------------------------------------
            # Permanent / final error
            # ------------------------------------------------

            return {
                "explanation": (
                    "Gemini explanation is temporarily "
                    "unavailable. The Random Forest "
                    "prediction is still available."
                ),
                "gemini_available": False,
                "error": error_text,
            }

    # ========================================================
    # Final fallback
    # ========================================================

    return {
        "explanation": (
            "Gemini explanation is temporarily unavailable. "
            "The Random Forest prediction is still available."
        ),
        "gemini_available": False,
        "error": "Gemini request failed after retries.",
    }