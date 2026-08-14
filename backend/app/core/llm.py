"""Cliente HTTP de Ollama para generación local de texto (gratis, sin claves).

Permite generar mini-ensayos y contexto histórico con modelos locales
(por defecto `llama3.2:3b` para ensayos y `llama3.2:1b` para contexto).
El servidor Ollama corre aparte (localhost:11434); este cliente solo habla
HTTP y degrada con elegancia si Ollama no está disponible.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

DEFAULT_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
ESSAY_MODEL = os.getenv("ESSAY_LLM_MODEL", "llama3.2:3b")
CONTEXT_MODEL = os.getenv("CONTEXT_LLM_MODEL", "llama3.2:1b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
_MAX_WORKERS = min(4, os.cpu_count() or 2)


class OllamaClient:
    """Cliente síncrono del API `/api/generate` de Ollama.

    `available()` hace un ping corto a `/api/tags` y cachea el resultado:
    si Ollama no está corriendo o el modelo falta, `generate(*)` no se llama
    y los llamadores deben usar su fallback determinista.
    """

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        max_tokens: int = 260,
        temperature: float = 0.7,
        embed_model: str | None = None,
    ) -> None:
        self.model = model or ESSAY_MODEL
        self.base_url = (base_url or DEFAULT_URL).rstrip("/")
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.embed_model = embed_model or EMBED_MODEL
        self._available: bool | None = None

    def available(self) -> bool:
        if self._available is None:
            try:
                with httpx.Client(timeout=2.0) as client:
                    self._available = (
                        client.get(f"{self.base_url}/api/tags").status_code == 200
                    )
            except (httpx.HTTPError, OSError):
                self._available = False
        return self._available

    def _payload(
        self, prompt: str, system: str | None, max_tokens: int, temperature: float
    ) -> dict:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens or self.max_tokens,
                "temperature": temperature
                if temperature is not None
                else self.temperature,
            },
        }
        if system:
            payload["system"] = system
        return payload

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError(f"Ollama no disponible en {self.base_url}")
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/generate",
                json=self._payload(
                    prompt,
                    system,
                    max_tokens or self.max_tokens,
                    temperature or self.temperature,
                ),
            )
            resp.raise_for_status()
        return resp.json().get("response", "").strip()

    def generate_many(
        self,
        prompts: list[str],
        system: str | None = None,
        workers: int | None = None,
        max_tokens: int | None = None,
    ) -> list[str]:
        """Genera N respuestas en paralelo (I/O-bound → hilos)."""
        if not self.available():
            raise RuntimeError(f"Ollama no disponible en {self.base_url}")
        n = workers or _MAX_WORKERS

        def one(prompt: str) -> str:
            return self.generate(prompt, system=system, max_tokens=max_tokens)

        with ThreadPoolExecutor(max_workers=n) as pool:
            return list(pool.map(one, prompts))

    def embed(self, texts: list[str], timeout: float = 30.0) -> list[list[float]]:
        """Embeddings de oraciones vía `/api/embeddings` (I/O-bound → hilos).

        Se usa para búsqueda semántica del Orador (`EmbeddingRetrievalEngine`).
        Si el modelo no está instalado o Ollama cae, lanza excepción y el
        llamador debe degradar (TF-IDF).
        """
        if not self.available():
            raise RuntimeError(f"Ollama no disponible en {self.base_url}")

        def one(text: str) -> list[float]:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.embed_model, "prompt": text},
                )
                resp.raise_for_status()
                return resp.json()["embedding"]

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            return list(pool.map(one, texts))
