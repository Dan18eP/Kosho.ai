import unicodedata

_EMBEDDING = None


def _load_encoding(encoding_name: str):
    global _EMBEDDING
    if _EMBEDDING is None:
        import tiktoken

        _EMBEDDING = tiktoken.get_encoding(encoding_name)
    return _EMBEDDING


def _is_cjk(text: str) -> bool:
    for ch in text:
        name = unicodedata.name(ch, "")
        if name.startswith(("CJK ", "HIRAGANA", "KATAKANA")):
            return True
    return False


class TokenCounter:
    """Contador exacto de tokens con tiktoken y fallback heurístico.

    Exactitud: tiktoken `o200k_base` cuenta de forma determinista y reversible,
    igual que factura la mayoría de proveedores de LLM. Si tiktoken no está
    disponible (ej. sin descarga de encoding offline), cae a una heurística
    por caracteres: ~1 token / 3.5 chars (latino) y ~1 token / 2 chars (CJK).
    """

    def __init__(self, encoding_name: str = "o200k_base") -> None:
        self.encoding_name = encoding_name
        self._enc = None
        self._fallback = False

    def _ensure(self) -> None:
        if self._enc is not None or self._fallback:
            return
        try:
            self._enc = _load_encoding(self.encoding_name)
        except Exception:  # noqa: BLE001 - cualquier fallo de tiktoken activa el fallback
            self._fallback = True

    def count(self, text: str) -> int:
        """Tokens exactos de un texto (contado contra el tokenizador definido)."""
        self._ensure()
        text = text or ""
        if self._enc is not None:
            return len(self._enc.encode(text))
        return self.estimate(text)

    def estimate(self, text: str) -> int:
        """Proyección heurística de tokens (usada para salida y fallback)."""
        n = len(text or "")
        divisor = 2.0 if _is_cjk(text) else 3.5
        return max(1, round(n / divisor))

    def project_output(self, input_tokens: int, ratio: float, base: int) -> int:
        return max(1, round(input_tokens * ratio) + base)
