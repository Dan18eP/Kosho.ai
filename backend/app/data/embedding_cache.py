"""Caché de embeddings pre-generados (`data/embeddings.json`).

Evita re-embedder las ~100 frases del corpus en cada arranque (con bge-m3 en
CPU el fit en vivo tarda ~1 min). `scripts/setup_embeddings.py` genera el
archivo una sola vez; en runtime solo se embedde la pregunta del usuario.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EMBEDDINGS_FILE = PROJECT_ROOT / "data" / "embeddings.json"


def load_embedding_cache(
    path: Path = EMBEDDINGS_FILE, model: str | None = None
) -> dict[str, list[float]]:
    """Carga frase → vector. Devuelve {} si falta el archivo, está corrupto
    o el modelo grabado no coincide con el solicitado."""
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if model is not None and raw.get("model") != model:
        return {}
    return {entry["phrase"]: entry["vector"] for entry in raw.get("entries", [])}


def save_embedding_cache(
    entries: list[dict], model: str | None = None, path: Path = EMBEDDINGS_FILE
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps({"model": model, "entries": entries}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)
