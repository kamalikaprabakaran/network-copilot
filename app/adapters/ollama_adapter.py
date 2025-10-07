import os
import requests
from .base import BaseAdapter

class OllamaAdapter(BaseAdapter):
    def __init__(self):
        # Default model if none provided
        self.default_model = os.getenv("OLLAMA_MODEL", "llama3")
        # Ensure the URL points to your running Ollama API
        self.api_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

    def generate(self, prompt: str, model: str = None, max_tokens: int = 1200, temperature: float = 0.0) -> str:
        """
        Calls the Ollama API to generate a response for a given prompt.
        """
        payload = {
            "model": model or self.default_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=180)
            response.raise_for_status()
            data = response.json()
            # Ollama API returns response in 'response' key
            return data.get("response", "").strip()
        except Exception as e:
            return f"[OllamaAdapter ERROR] {e}"

# Utility function for direct queries (optional)
def query_model(model: str, prompt: str):
    """
    Standalone function to call Ollama API directly if needed.
    """
    try:
        url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
        payload = {"model": model, "prompt": prompt, "stream": False}
        response = requests.post(url, json=payload, timeout=180)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}
