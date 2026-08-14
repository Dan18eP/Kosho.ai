import asyncio
import inspect
import json
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from ..modules.debate.retrieval import Quote

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
QUOTES_FILE = DATA_DIR / "quotes.json"
SOURCE_URL = "https://quotes.toscrape.com"


def _ensure_scraper_on_path() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))


def load_quotes(path: Path | None = None) -> list[Quote]:
    src = path or QUOTES_FILE
    raw = json.loads(src.read_text(encoding="utf-8"))
    return [Quote(phrase=item["phrase"], author=item["author"]) for item in raw]


@lru_cache(maxsize=1)
def get_quotes() -> list[Quote]:
    return load_quotes()


def _file_mtime() -> str | None:
    if QUOTES_FILE.exists():
        ts = datetime.fromtimestamp(QUOTES_FILE.stat().st_mtime, tz=timezone.utc)
        return ts.isoformat()
    return None


def quotes_meta() -> dict:
    quotes = get_quotes()
    return {
        "source": SOURCE_URL,
        "count": len(quotes),
        "updated_at": _file_mtime(),
        "quotes": [{"phrase": q.phrase, "author": q.author} for q in quotes],
    }


def _write_atomic(quotes: list[Quote]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = QUOTES_FILE.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(
            [{"phrase": q.phrase, "author": q.author} for q in quotes],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    os.replace(tmp, QUOTES_FILE)


def _default_scraper() -> Callable[[], list[dict]]:
    _ensure_scraper_on_path()
    from scraper import extract_phrases

    return extract_phrases


def refresh_quotes(
    scraper: Callable[[], list[dict]] | None = None,
) -> dict:
    """Re-scrapea la web y actualiza data/quotes.json de forma atómica.

    Compara con el dataset actual por (phrase, author) para reportar cuántas
    frases nuevas se añadieron. Invalida la caché para que GET /api/quotes y
    los módulos lean los datos recién scrapeados.
    """
    runner = scraper or _default_scraper()
    if inspect.iscoroutinefunction(runner):
        raw = asyncio.run(runner())
    else:
        raw = runner()

    fresh = [
        Quote(phrase=item["phrase"], author=item["author"])
        for item in raw
        if item.get("phrase") and item.get("author")
    ]

    previous = load_quotes() if QUOTES_FILE.exists() else []
    existing = {(q.phrase, q.author) for q in previous}
    added = [q for q in fresh if (q.phrase, q.author) not in existing]

    _write_atomic(fresh)
    get_quotes.cache_clear()

    return {
        "source": SOURCE_URL,
        "count": len(fresh),
        "added": len(added),
        "updated_at": _file_mtime(),
    }
