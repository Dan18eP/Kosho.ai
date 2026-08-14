from dataclasses import dataclass, field

from ...core.provider_spec import ProviderSpec
from ...core.token_counter import TokenCounter
from ..debate.retrieval import Quote


@dataclass
class BatchItem:
    index: int
    phrase: str
    author: str
    input_tokens: int
    output_tokens_projected: int

    @property
    def cost(self) -> int:
        return self.input_tokens + self.output_tokens_projected


@dataclass
class Batch:
    batch_id: int
    items: list[BatchItem] = field(default_factory=list)

    @property
    def input_tokens(self) -> int:
        return sum(i.input_tokens for i in self.items)

    @property
    def output_tokens(self) -> int:
        return sum(i.output_tokens_projected for i in self.items)

    @property
    def chars(self) -> int:
        return sum(len(i.phrase) for i in self.items)


class PackingError(ValueError):
    pass


class Packer:
    """Empaqueta frases en lotes que respetan el límite del proveedor.

    Algoritmo: First-Fit Decreasing. Se ordenan las frases por costo
    (entrada + salida proyectada) descendente y se colocan en el primer lote
    con espacio disponible. La verificación es estricta ANTES de añadir cada
    frase:

        system_prompt + json_overhead + Σ(input + output_proyectada) ≤ X

    Nunca se envía un lote que supere el límite. Si una frase ni siquiera
    cabe en un lote vacío, lanza PackingError (el proveedor no puede
    procesarla). El módulo es agnóstico al provider: solo depende de la
    ProviderSpec y del contador de tokens.
    """

    def __init__(self, counter: TokenCounter) -> None:
        self.counter = counter

    def pack(self, phrases: list[Quote], spec: ProviderSpec) -> list[Batch]:
        items = [self._make_item(i, q, spec) for i, q in enumerate(phrases)]
        batches: list[Batch] = []

        for item in sorted(items, key=lambda it: it.cost, reverse=True):
            if not self._fits_empty(item, spec):
                raise PackingError(
                    f"La frase #{item.index} ('{item.phrase[:60]}...') consume "
                    f"{item.cost} tokens y excede el límite de {spec.max_tokens_per_request} "
                    f"incluso en un lote vacío. Reduce 'X' o divide la frase."
                )
            target = next((b for b in batches if self._fits(b, item, spec)), None)
            if target is None:
                target = Batch(batch_id=len(batches) + 1)
                batches.append(target)
            target.items.append(item)

        return batches

    def _make_item(self, index: int, quote: Quote, spec: ProviderSpec) -> BatchItem:
        input_tokens = self.counter.count(quote.phrase)
        output_tokens = self.counter.project_output(
            input_tokens, spec.output_ratio, spec.output_base
        )
        return BatchItem(
            index=index,
            phrase=quote.phrase,
            author=quote.author,
            input_tokens=input_tokens,
            output_tokens_projected=output_tokens,
        )

    def _overhead(self, spec: ProviderSpec) -> int:
        return spec.system_prompt_tokens + spec.json_format_overhead

    def _fits(self, batch: Batch, item: BatchItem, spec: ProviderSpec) -> bool:
        tokens = (
            self._overhead(spec) + batch.input_tokens + batch.output_tokens + item.cost
        )
        if tokens > spec.max_tokens_per_request:
            return False
        return not (
            spec.max_chars_per_request is not None
            and batch.chars + len(item.phrase) > spec.max_chars_per_request
        )

    def _fits_empty(self, item: BatchItem, spec: ProviderSpec) -> bool:
        return self._fits(Batch(batch_id=0), item, spec)
