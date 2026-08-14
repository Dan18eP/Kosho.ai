from dataclasses import dataclass
from typing import Protocol


class ProviderError(RuntimeError):
    """Error de configuración o ejecución de un provider, con mensaje de usuario."""


@dataclass(frozen=True)
class PhraseRef:
    phrase: str
    author: str


@dataclass
class BatchResult:
    translations: list[str]
    contexts: list[str]


class TranslatorProvider(Protocol):
    """Contrato común para todos los providers del Ejercicio 2.

    El Packer y el ReceiptBuilder no dependen del provider concreto: solo de
    la ProviderSpec y del TokenCounter. Cada provider declara su `name` y
    cómo traducir al japonés + explicar el contexto histórico de un lote.

    `process_batch` recibe referencias (frase + autor) y devuelve, por cada
    una, la traducción y el contexto. Los errores de configuración o red
    deben lanzarse como `ProviderError` (mensaje orientado al usuario).
    """

    name: str

    def process_batch(self, refs: list[PhraseRef]) -> BatchResult: ...
