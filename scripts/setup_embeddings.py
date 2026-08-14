"""Pre-genera `data/embeddings.json` (vectores bge-m3 del Orador).

Con bge-m3 en CPU, embedder las 100 frases tarda ~1 min; se hace una vez
aquí para que el runtime del Orador solo embedde la pregunta del usuario.
Reutiliza el modelo configurado con la variable de entorno `EMBED_MODEL`
(default `bge-m3`); requiere Ollama corriendo con ese modelo descargado.

Uso:  python scripts/setup_embeddings.py
"""

import os
import sys

BACKEND = os.path.join(os.path.dirname(__file__), "..", "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, os.path.abspath(BACKEND))

from app.core.llm import OllamaClient
from app.data.embedding_cache import save_embedding_cache
from app.data.quotes_repo import get_quotes


def main() -> None:
    llm = OllamaClient()
    quotes = get_quotes()
    if not llm.available():
        print(f"[setup_embeddings] Ollama no disponible en {llm.base_url}")
        sys.exit(1)
    print(
        f"[setup_embeddings] Embedding {len(quotes)} frases con "
        f"{llm.embed_model} (puede tardar ~1 min)..."
    )
    vectors = llm.embed([q.phrase for q in quotes])
    entries = [
        {"phrase": q.phrase, "author": q.author, "vector": v}
        for q, v in zip(quotes, vectors)
    ]
    save_embedding_cache(entries, model=llm.embed_model)
    print(f"[setup_embeddings] Listo: data/embeddings.json ({len(entries)} frases)")


if __name__ == "__main__":
    main()
