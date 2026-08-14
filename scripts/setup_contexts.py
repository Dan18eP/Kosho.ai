"""Pre-genera `data/contexts.json` con contexto histórico por autor.

Cada autor único recibe 1–2 oraciones de contexto en inglés (llama3.2:1b vía
Ollama, en paralelo) que luego se traducen a español con `EsTranslator`.
El resultado se persiste para que el Optimizador lea en runtime sin esperas.

Idempotente: solo genera los autores que faltan (o todos con `--force`).
Si Ollama no está disponible, termina sin tocar el archivo (el runtime
degradará al ContextEngine determinista).

Uso:
    python scripts/setup_contexts.py [--force] [--workers N]
"""

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.llm import CONTEXT_MODEL, OllamaClient
from app.core.translators import EsTranslator
from app.data.quotes_repo import load_quotes
from app.modules.optimizer.context_engine import AUTHORS
from app.modules.optimizer.context_service import CONTEXTS_FILE

_SYSTEM = (
    "You write concise historical context in English. For each author, write "
    "1-2 sentences about their lifetime, era, and why their words matter. "
    "Do not invent facts; if you are unsure, stay generic."
)

_REFUSAL_RE = re.compile(
    r"(cannot|can'?t|unable|not (able|allowed)|no puedo|no puedo cumplir|"
    r"refus|inappropriate|no voy a|lamento|sorry|lo siento)",
    re.IGNORECASE,
)


def _is_refusal(text: str) -> bool:
    return _REFUSAL_RE.search(text) and len(text) < 400


def _prompt(author: str, phrase: str) -> str:
    years, _ = AUTHORS.get(author, ("", ""))
    meta = f" ({years})" if years else ""
    return (
        f"Author: {author}{meta}\n"
        f'Representative quote: "{phrase}"\n\n'
        "Write the historical context in English now."
    )


def _chunks(seq: list[str], size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _representative_phrase(quotes, author: str) -> str:
    for q in quotes:
        if q.author == author:
            return q.phrase
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force", action="store_true", help="Regenerar todos los autores."
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)

    quotes = load_quotes()
    authors = sorted({q.author for q in quotes})
    existing = {}
    if CONTEXTS_FILE.exists():
        existing = json.loads(CONTEXTS_FILE.read_text(encoding="utf-8"))
    todo = authors if args.force else [a for a in authors if a not in existing]

    if not todo:
        print(f"[setup_contexts] Todo cubierto ({len(authors)} autores).")
        return 0

    llm = OllamaClient(model=CONTEXT_MODEL, max_tokens=120, temperature=0.5)
    if not llm.available():
        print("[setup_contexts] Ollama no disponible; no se generó nada.")
        return 1

    translator = EsTranslator()
    prompts = [_prompt(a, _representative_phrase(quotes, a)) for a in todo]

    print(
        f"[setup_contexts] Generando {len(todo)} contextos con {llm.model} "
        f"({args.workers} workers)..."
    )
    english: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(llm.generate, p): a for p, a in zip(prompts, todo)}
        for future in as_completed(futures):
            author = futures[future]
            try:
                text = future.result()
                if text and not _is_refusal(text):
                    english[author] = text
                else:
                    print(f"[setup_contexts] respuesta vacía/rechazo para {author}; se omite")
            except Exception as exc:  # noqa: BLE001 - ese autor cae al fallback
                print(f"[setup_contexts] fallo para {author}: {exc}")

    ordered = [a for a in todo if a in english]
    # Traducción por lotes cortos: un texto largo que falle en el modelo en→es
    # no debe tumbar la traducción de todos los autores (fallback a original).
    for chunk in _chunks(ordered, 8):
        translations = translator.translate_many([english[a] for a in chunk])
        for author, text in zip(chunk, translations):
            existing[author] = text

    CONTEXTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONTEXTS_FILE.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[setup_contexts] Guardados {len(ordered)} contextos en {CONTEXTS_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
