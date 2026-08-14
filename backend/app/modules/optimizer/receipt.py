from dataclasses import asdict, dataclass, field

from ...core.provider_spec import ProviderSpec
from .packer import Batch


@dataclass
class BatchReport:
    batch_id: int
    phrase_count: int
    input_tokens: int
    output_tokens: int
    overhead_tokens: int
    total_tokens: int
    utilization: float
    cost: float


@dataclass
class Receipt:
    spec: ProviderSpec
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    currency: str
    batches: list[BatchReport] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "spec": self.spec.to_dict(),
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 6),
            "currency": self.currency,
            "batches": [asdict(b) for b in self.batches],
        }


class ReceiptBuilder:
    """Construye el recibo del Ejercicio 2.

    El recibo reporta unidades (tokens) consumidas y peticiones necesarias.
    Cuando el procesamiento ya ocurrió, se re-cuentan los tokens de salida
    reales con el contador exacto; si no, se reporta la proyección usada para
    empaquetar. El costo usa precios asimétricos entrada/salida de la spec.
    """

    def __init__(self, spec: ProviderSpec) -> None:
        self.spec = spec

    def build(
        self,
        batches: list[Batch],
        actual_output_tokens: list[list[int]] | None = None,
    ) -> Receipt:
        reports: list[BatchReport] = []
        total_in = 0
        total_out = 0
        total_cost = 0.0

        for batch in batches:
            out = (
                actual_output_tokens[batch.batch_id - 1]
                if actual_output_tokens is not None
                else [i.output_tokens_projected for i in batch.items]
            )
            output_tokens = sum(out)
            overhead = self._overhead(batch)
            total_tokens = batch.input_tokens + output_tokens + overhead
            cost = (
                batch.input_tokens * self.spec.price_per_input_token
                + output_tokens * self.spec.price_per_output_token
            )
            utilization = min(1.0, total_tokens / self.spec.max_tokens_per_request)
            reports.append(
                BatchReport(
                    batch_id=batch.batch_id,
                    phrase_count=len(batch.items),
                    input_tokens=batch.input_tokens,
                    output_tokens=output_tokens,
                    overhead_tokens=overhead,
                    total_tokens=total_tokens,
                    utilization=round(utilization, 3),
                    cost=round(cost, 6),
                )
            )
            total_in += batch.input_tokens
            total_out += output_tokens
            total_cost += cost

        return Receipt(
            spec=self.spec,
            total_requests=len(batches),
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_tokens=total_in + total_out,
            total_cost=round(total_cost, 6),
            currency=self.spec.currency,
            batches=reports,
        )

    def _overhead(self, batch: Batch) -> int:
        return self.spec.system_prompt_tokens + self.spec.json_format_overhead
