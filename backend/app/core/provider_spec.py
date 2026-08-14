from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderSpec:
    """Spec del proveedor ficticio (unidad de facturación = tokens).

    Definición central del Ejercicio 2: el proveedor cobra por cada fragmento
    enviado y recibido, y limita el envío a `max_tokens_per_request` por
    petición. Todos los valores son configurables desde el frontend para
    simular distintos proveedores (estilo GPT-mini, DeepL char-based, etc.).
    """

    name: str = "MiniTranslate"
    tokenizer: str = "o200k_base"
    max_tokens_per_request: int = 2000
    max_chars_per_request: int | None = None
    reserve_output: float = 0.35
    price_per_input_token: float = 0.00000015
    price_per_output_token: float = 0.00000060
    currency: str = "USD"
    requests_per_minute: int = 60
    system_prompt_tokens: int = 80
    json_format_overhead: int = 25
    # Proyección de salida: completion ≈ input * output_ratio + output_base.
    output_ratio: float = 2.0
    output_base: int = 40

    def to_dict(self) -> dict:
        return asdict(self)
