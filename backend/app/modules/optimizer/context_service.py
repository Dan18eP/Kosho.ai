"""Servicio de contexto histórico del Optimizador, pre-generado y cacheado.

El contexto por autor se genera una sola vez (script `setup_contexts.py`:
llama3.2:1b en inglés → traducción en→es) y se persiste en
`data/contexts.json`. En runtime `ContextService` solo lee ese archivo
(0 ms). Si un autor no está en el caché, cae al `ContextEngine` determinista
(curated DB) para nunca bloquear la respuesta.
"""

import json
from pathlib import Path

from .context_engine import ContextEngine

PROJECT_ROOT = Path(__file__).resolve().parents[4]
CONTEXTS_FILE = PROJECT_ROOT / "data" / "contexts.json"


class ContextService:
    """Resuelve el contexto histórico de un autor con caché de archivo.

    Orden de resolución:
        1. `data/contexts.json` (pre-generado con LLM + traducción es).
        2. `ContextEngine` determinista (curated DB) si no existe el autor.

    El archivo se lee una vez y se cachea en memoria; su contenido es opcional:
    su ausencia activa el fallback determinista, por lo que la app nunca falla.
    """

    def __init__(
        self,
        path: Path | None = None,
        fallback: ContextEngine | None = None,
    ) -> None:
        self._path = path or CONTEXTS_FILE
        self._fallback = fallback or ContextEngine()
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._cache = {str(k): str(v) for k, v in data.items()}
            except (OSError, ValueError):
                self._cache = {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def update(self, contexts: dict[str, str]) -> int:
        added = sum(1 for author in contexts if author not in self._cache)
        self._cache.update(contexts)
        return added

    def explain(self, phrase: str, author: str) -> str:
        cached = self._cache.get(author)
        if cached:
            return cached
        return self._fallback.explain(phrase, author)
