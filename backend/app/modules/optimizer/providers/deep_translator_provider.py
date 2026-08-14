import os

from ..context_service import ContextService
from .base import BatchResult, PhraseRef, ProviderError

# Backends de traducción gratuitos (sin API keys) de deep-translator.
# El elegido por defecto es "google" (endpoints gratuitos); ante fallos de red
# o rate-limit se prueba el siguiente en la cadena.
_BACKEND_ORDER = ("google", "libre", "mymemory")


def _build_translator(kind: str, source: str, target: str):
    try:
        if kind == "google":
            from deep_translator import GoogleTranslator

            return GoogleTranslator(source=source, target=target)
        if kind == "libre":
            from deep_translator import LibreTranslator

            return LibreTranslator(source=source, target=target)
        if kind == "mymemory":
            from deep_translator import MyMemoryTranslator

            return MyMemoryTranslator(source=source, target=target)
    except ImportError as exc:  # pragma: no cover - depende de instalación
        raise ProviderError(
            "Instala la dependencia opcional: pip install deep-translator"
        ) from exc
    raise ProviderError(f"Backend de traducción desconocido: {kind!r}")


class DeepTranslatorProvider:
    """Traducción web gratuita (deep-translator) + contexto local (sin claves).

    Traducción al japonés: GoogleTranslator / LibreTranslate / MyMemory, todos
    gratuitos y sin API key (los mirrors públicos tienen rate-limit, por eso se
    reintenta con el siguiente backend). Contexto histórico: ContextEngine
    local y determinista; NO usa OpenAI ni ninguna API key.

    Configuración opcional: env TRANSLATE_BACKEND=google|libre|mymemory.
    MyMemory limita a 500 chars/request → modelar con max_chars_per_request.
    """

    name = "deep_translator"

    def __init__(
        self,
        source: str = "en",
        target: str = "ja",
        context: ContextService | None = None,
    ) -> None:
        self.source = source
        self.target = target
        self._context = context or ContextService()
        primary = os.getenv("TRANSLATE_BACKEND", "google")
        self._order = (primary,) + tuple(k for k in _BACKEND_ORDER if k != primary)
        self._translators: dict[str, object] = {}

    def _translator(self, kind: str):
        if kind not in self._translators:
            self._translators[kind] = _build_translator(kind, self.source, self.target)
        return self._translators[kind]

    def _translate(self, phrases: list[str]) -> list[str]:
        last_error: Exception | None = None
        for kind in self._order:
            try:
                translator = self._translator(kind)
                result = translator.translate_batch(phrases)
                if result and all(isinstance(t, str) and t for t in result):
                    return result
            except Exception as exc:  # noqa: BLE001 - reintenta con otro backend
                last_error = exc
        raise ProviderError(
            "La traducción gratuita falló en todos los backends "
            f"({'/'.join(self._order)}). Detalle: {last_error}"
        )

    def process_batch(self, refs: list[PhraseRef]) -> BatchResult:
        phrases = [r.phrase for r in refs]
        translations = self._translate(phrases)
        contexts = [self._context.explain(r.phrase, r.author) for r in refs]
        return BatchResult(translations=translations, contexts=contexts)
