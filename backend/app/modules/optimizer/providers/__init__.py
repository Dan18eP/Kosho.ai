from .base import TranslatorProvider
from .ctranslate2_provider import CTranslate2Provider
from .deep_translator_provider import DeepTranslatorProvider
from .mock import MockProvider


class UnknownProviderError(ValueError):
    pass


def get_provider(name: str) -> TranslatorProvider:
    """Fabrica un provider por nombre. 'ctranslate2' es el motor principal (local, gratis)."""
    registry = {
        "ctranslate2": CTranslate2Provider,
        "deep_translator": DeepTranslatorProvider,
        "mock": MockProvider,
    }
    try:
        cls = registry[name]
    except KeyError:
        raise UnknownProviderError(
            f"Provider desconocido: {name!r}. Válidos: {', '.join(registry)}"
        ) from None
    return cls()


def available_providers() -> list[str]:
    return ["ctranslate2", "deep_translator", "mock"]
