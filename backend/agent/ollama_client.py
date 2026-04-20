import requests
import json
from django.conf import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.1-8b-instant"


def chat(messages: list, temperature: float = 0.2) -> str:
    """
    Send messages to Groq's LPU-accelerated Llama 3 instance.
    """
    api_key = getattr(settings, "GROQ_API_KEY", None)
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing from Django settings or .env.")

    # ✨ FIX 1: Groq rejects exactly 0.0. This forces a safe minimum.
    safe_temperature = max(temperature, 1e-4)

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": safe_temperature,
    }

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        response = requests.post(
            GROQ_API_URL,
            json=payload,
            headers=headers,
            timeout=15,
        )

        # ✨ FIX 2: Read the actual error string from Groq before crashing!
        if response.status_code != 200:
            error_data = response.text
            raise RuntimeError(f"Groq rejected the request: {error_data}")

        data = response.json()
        return data["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        raise RuntimeError("Groq API request timed out.")
    except Exception as e:
        raise RuntimeError(str(e))


def is_ollama_running() -> bool:
    """Health check — Groq is cloud-hosted, so we just verify the key exists."""
    return getattr(settings, "GROQ_API_KEY", None) is not None
