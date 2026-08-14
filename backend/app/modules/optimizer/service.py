from dataclasses import dataclass

from ...core.provider_spec import ProviderSpec
from ...core.token_counter import TokenCounter
from ..debate.retrieval import Quote
from .packer import Batch, Packer
from .providers import get_provider
from .providers.base import PhraseRef, ProviderError, TranslatorProvider
from .receipt import Receipt, ReceiptBuilder


@dataclass
class PhraseReport:
    """Conteo y resultado por frase (antes y después de procesarse)."""

    index: int
    phrase: str
    author: str
    input_tokens: int
    output_tokens: int
    translation: str
    context: str


@dataclass
class OptimizeResult:
    receipt: Receipt
    batches: list[Batch]
    items: list[PhraseReport]


class OptimizerService:
    """Orquesta el Ejercicio 2: empaquetar → procesar → recibo.

    Pipeline completo:
      1. Packer calcula lotes óptimos respetando el límite X de la spec.
      2. Provider procesa cada lote (traducción ja + contexto histórico).
      3. TokenCounter re-cuenta los tokens de salida REALES generados.
      4. ReceiptBuilder reporta el recibo con unidades y peticiones.
      5. Se arma el reporte por frase: tokens antes (entrada) y después
         (salida), con su traducción y contexto asociados.
    """

    def __init__(self, counter: TokenCounter | None = None) -> None:
        self.counter = counter or TokenCounter()

    def preview(self, phrases: list[Quote], spec: ProviderSpec) -> Receipt:
        batches = Packer(self.counter).pack(phrases, spec)
        return ReceiptBuilder(spec).build(batches)

    def run(
        self,
        phrases: list[Quote],
        spec: ProviderSpec,
        provider_name: str = "ctranslate2",
        provider: TranslatorProvider | None = None,
    ) -> OptimizeResult:
        batches = Packer(self.counter).pack(phrases, spec)
        engine = provider or get_provider(provider_name)

        actual_output: list[list[int]] = []
        items: list[PhraseReport] = []

        for batch in batches:
            refs = [PhraseRef(phrase=i.phrase, author=i.author) for i in batch.items]
            try:
                result = engine.process_batch(refs)
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError(
                    f"El provider '{engine.name}' falló al procesar el lote {batch.batch_id}: {exc}"
                ) from exc

            output_counts: list[int] = []
            for item, translation, context in zip(
                batch.items, result.translations, result.contexts
            ):
                tokens = self.counter.count(translation) + self.counter.count(context)
                output_counts.append(tokens)
                items.append(
                    PhraseReport(
                        index=item.index,
                        phrase=item.phrase,
                        author=item.author,
                        input_tokens=item.input_tokens,
                        output_tokens=tokens,
                        translation=translation,
                        context=context,
                    )
                )
            actual_output.append(output_counts)

        receipt = ReceiptBuilder(spec).build(batches, actual_output)
        return OptimizeResult(receipt=receipt, batches=batches, items=items)
