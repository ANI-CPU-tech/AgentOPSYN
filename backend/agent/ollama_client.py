import requests
import json

OLLAMA_BASE_URL = "http://host.docker.internal:11434"
MODEL_NAME = "llama3"


def chat(messages: list, temperature: float = 0.2) -> str:
    """
    Send messages to local Ollama Llama 3 instance.
    messages format: [{"role": "system"|"user"|"assistant", "content": "..."}]
    Returns the assistant's reply as a string.
    Temperature kept low (0.2) for consistent, deterministic answers.
    """
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120,  # Llama 3 can take a moment on first load
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()

    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure it's running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out. Try a shorter query.")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {str(e)}")


def is_ollama_running() -> bool:
    """Health check — used at startup."""
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False
