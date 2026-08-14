import hashlib

from ..context_service import ContextService
from .base import BatchResult, PhraseRef


class MockProvider:
    """Provider determinista para demo y CI (sin red ni modelos).

    Produce salidas predecibles a partir del texto. Nunca debe usarse en
    producción: es un 'stub' para probar el pipeline completo
    (pack → process → receipt) sin dependencias externas. El contexto usa el
    ContextService (pre-generado con LLM, fallback determinista) igual que
    deep_translator/ctranslate2.
    """

    name = "mock"

    def __init__(self, context: ContextService | None = None) -> None:
        self._context = context or ContextService()

    def process_batch(self, refs: list[PhraseRef]) -> BatchResult:
        translations = [f"「{r.phrase}」(traducción simulada ja)" for r in refs]
        contexts = []
        for r in refs:
            seed = hashlib.sha256(r.phrase.encode("utf-8")).hexdigest()[:8]
            contexts.append(
                f"[mock:{seed}] {self._context.explain(r.phrase, r.author)}"
            )
        return BatchResult(translations=translations, contexts=contexts)
