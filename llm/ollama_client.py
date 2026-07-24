"""
Ollama Client

Integration with local Ollama server for LLM inference.
"""

import requests

from core.config import get_config
from utils.logger import log


class OllamaClient:
    """Client for Ollama local LLM server"""

    def __init__(self):
        config = get_config()
        self.base_url = config.llm.base_url
        self.model = config.llm.model
        self.temperature = config.llm.temperature
        self.max_tokens = config.llm.max_tokens
        self.context_window = config.llm.context_window
        self.timeout = config.llm.timeout
        self.keep_alive = config.llm.keep_alive
        self.session = requests.Session()

        log.info(f"Ollama client initialized: {self.model} @ {self.base_url}")

    def generate(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Generate completion from Ollama.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text

        Raises:
            ConnectionError: If Ollama is not running
            TimeoutError: If request times out
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
                "num_ctx": self.context_window,
            },
            "keep_alive": self.keep_alive,
        }

        try:
            log.debug(f"Sending request to Ollama: {self.model}")
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()

            result = response.json()
            generated_text = result.get("response", "")

            log.debug(f"Received response ({len(generated_text)} chars)")
            return generated_text.strip()

        except requests.exceptions.ConnectionError:
            log.error("Cannot connect to Ollama. Is it running?")
            raise ConnectionError(
                "Ollama server not reachable. Please start Ollama with: ollama serve"
            )

        except requests.exceptions.Timeout:
            log.error("Ollama request timed out")
            raise TimeoutError(f"Request exceeded {self.timeout}s timeout")

        except Exception as e:
            log.error(f"Ollama generation failed: {e}")
            raise

    def check_health(self) -> bool:
        """
        Check if Ollama server is running.

        Returns:
            True if server is reachable
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def list_models(self) -> list[str]:
        """
        List available models.

        Returns:
            List of model names
        """
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception as e:
            log.error(f"Failed to list models: {e}")
            return []

    def close(self) -> None:
        """Release pooled HTTP connections."""
        self.session.close()
