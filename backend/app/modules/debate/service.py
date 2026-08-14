"""Orquestación del Orador: recuperación robusta + generación del ensayo.

Resuelve los problemas reales del corpus (100 frases en inglés):
- Preguntas en español ya no devuelven 0 citas: se detecta el idioma de la
  consulta y, si hace falta, se traduce a inglés (best-effort) para poder
  compararla contra el corpus.
- Recuperación híbrida: por defecto, embeddings semánticos (Ollama `bge-m3`)
  que capturan sinónimos y reformulaciones; si Ollama/el modelo falla, se
  degrada automáticamente a TF-IDF + coseno (determinista y sin red).
- Si una sola pasada no basta, se reintenta con umbral relajado.
- El ensayo exige 2 citas DISTINTAS: nunca repite la misma voz en el párrafo 2.
"""

import re
from collections.abc import Callable

from ...core.llm import ESSAY_MODEL, OllamaClient
from ...core.translators import EsTranslator, WebTranslator
from ...data.embedding_cache import load_embedding_cache
from ...data.quotes_repo import get_quotes
from .essay_generator import DebateResult, EssayGenerator
from .retrieval import (
    EmbeddingRetrievalEngine,
    Quote,
    RetrievalEngine,
    RetrievedQuote,
)

_NON_ENGLISH_RE = re.compile(r"[áéíóúüñÁÉÍÓÚÜÑ¿¡]")


def _looks_non_english(text: str) -> bool:
    """Heurística: tildes/ñ/¿/¡ delatan consultas en español (corpus EN)."""
    return bool(_NON_ENGLISH_RE.search(text))


class DebateService:
    """Orquesta pregunta → (traducción) → recuperación → ensayo."""

    def __init__(
        self,
        quotes: list[Quote] | None = None,
        threshold: float = 0.15,
        relaxed_factor: float = 0.6,
        embed_threshold: float = 0.50,
        llm: OllamaClient | None = None,
        es_translator: EsTranslator | None = None,
        query_translator: WebTranslator | None = None,
        quotes_loader: Callable[[], list[Quote]] | None = None,
    ) -> None:
        self._quotes = list(quotes) if quotes is not None else None
        self._quotes_loader = quotes_loader or get_quotes
        self.threshold = threshold
        self.relaxed_factor = relaxed_factor
        self.embed_threshold = embed_threshold
        self._llm = llm if llm is not None else OllamaClient(model=ESSAY_MODEL)
        self._es_translator = (
            es_translator if es_translator is not None else EsTranslator()
        )
        self._query_translator = (
            query_translator
            if query_translator is not None
            else WebTranslator("auto", "en")
        )
        self._embed_engine: EmbeddingRetrievalEngine | None = None
        self._embed_quotes: list[Quote] | None = None
        self._embed_failed = False

    def debate(
        self,
        question: str,
        language: str = "en",
        threshold: float | None = None,
    ) -> DebateResult:
        quotes = self._quotes if self._quotes is not None else self._quotes_loader()

        hits = self._search(quotes, question, threshold)
        if not hits:
            translated = self._translate_query(question, language)
            if translated:
                hits = self._search(quotes, translated, threshold)
            if not hits:
                hits = self._search(quotes, question, threshold, relaxed=True)
                if not hits and translated:
                    hits = self._search(quotes, translated, threshold, relaxed=True)

        distinct = self._distinct(hits)
        translations = None
        if language == "es" and self._es_translator is not None and len(distinct) >= 2:
            translations = self._es_translator.translate_many(
                [r.quote.phrase for r in distinct]
            )

        generator = EssayGenerator(llm=self._llm, translator=self._es_translator)
        return generator.generate(
            question, distinct, language=language, translations=translations
        )

    def _search(
        self,
        quotes: list[Quote],
        question: str,
        threshold: float | None,
        relaxed: bool = False,
    ) -> list[RetrievedQuote]:
        """Busca con el motor disponible: embeddings (Ollama) o TF-IDF.

        El motor de embeddings se construye una sola vez (cachea el fit); si
        Ollama cae o el modelo no está, se marca el fallo y se usa TF-IDF.
        """
        engine = self._ensure_embedding_engine(quotes)
        if engine is not None:
            # Los embeddings ya capturan sinónimos y reformulaciones (y son
            # multilingües), así que la pasada "relajada" no baja el umbral:
            # evita que ruido semántico convierta preguntas sin evidencia en
            # "fuentes" inventadas.
            thr = self.embed_threshold if threshold is None else threshold
            return engine.retrieve(question, threshold=thr)

        thr = self.threshold if threshold is None else threshold
        if relaxed:
            thr *= self.relaxed_factor
        return (
            RetrievalEngine(threshold=thr, max_quotes=6, language="en")
            .fit(quotes)
            .retrieve(question)
        )

    def _ensure_embedding_engine(
        self, quotes: list[Quote]
    ) -> EmbeddingRetrievalEngine | None:
        embedder = getattr(self._llm, "embed", None)
        if embedder is None or self._embed_failed:
            return None
        if self._embed_engine is None or self._embed_quotes is not quotes:
            # Solo el OllamaClient real usa la caché de vectores; los fakes de
            # test embeden en vivo (determinista) para no mezclar dimensiones.
            cache: dict[str, list[float]] = {}
            if isinstance(self._llm, OllamaClient):
                cache = load_embedding_cache(model=self._llm.embed_model)
            vectors = [cache[q.phrase] for q in quotes if q.phrase in cache]
            try:
                if len(vectors) == len(quotes):
                    engine = EmbeddingRetrievalEngine(embedder).fit(
                        quotes, vectors=vectors
                    )
                else:
                    engine = EmbeddingRetrievalEngine(embedder).fit(quotes)
            except Exception:  # noqa: BLE001 - degrada a TF-IDF
                self._embed_failed = True
                return None
            self._embed_engine = engine
            self._embed_quotes = quotes
        return self._embed_engine

    def _translate_query(self, question: str, language: str) -> str | None:
        if not (_looks_non_english(question) or language == "es"):
            return None
        try:
            return self._query_translator.translate([question])[0]
        except Exception:  # noqa: BLE001 - best-effort: recupera sin traducir
            return None

    @staticmethod
    def _distinct(hits: list[RetrievedQuote]) -> list[RetrievedQuote]:
        seen: set[str] = set()
        out: list[RetrievedQuote] = []
        for hit in hits:
            key = hit.quote.phrase.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(hit)
        return out[:3]
