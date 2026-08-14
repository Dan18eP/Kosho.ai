"""Traducciones auxiliares gratuitas (sin API keys) para Kosho.ai.

- `EsTranslator`: en→es. Intenta el modelo local CTranslate2 OPUS-MT en→es
  (`models/enes_ct2`); si no responde usa `deep-translator` (Google/Libre/
  MyMemory); si tampoco, devuelve el texto original (best-effort).
- `WebTranslator`: caja fina sobre los backends gratuitos de `deep-translator`
  con reintentos, usada también para traducir la consulta es→en del orador.

Todo es gratuito y sin claves; los fallos de red degradan con elegancia.
"""

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENES_CT2 = PROJECT_ROOT / "models" / "enes_ct2"
DEFAULT_ENES_SRC = PROJECT_ROOT / "models" / "enes" / "source.spm"
DEFAULT_ENES_TGT = PROJECT_ROOT / "models" / "enes" / "target.spm"

# Backends de deep-translator gratuitos; por defecto "google" (endpoints
# públicos). Ante fallos de red o rate-limit se prueba el siguiente.
_BACKEND_ORDER = ("google", "libre", "mymemory")


def _build_translator(kind: str, source: str, target: str):
    from deep_translator import (  # import tardío: dependencia opcional
        GoogleTranslator,
        LibreTranslator,
        MyMemoryTranslator,
    )

    if kind == "google":
        return GoogleTranslator(source=source, target=target)
    if kind == "libre":
        return LibreTranslator(source=source, target=target)
    if kind == "mymemory":
        return MyMemoryTranslator(source=source, target=target)
    raise ValueError(f"backend de traducción desconocido: {kind!r}")


class WebTranslator:
    """Traduce lotes con deep-translator, reintentando entre backends.

    `source='auto'` permite que Google detecte el idioma de origen (útil para
    consultas es→en). Sin claves ni setup; si todos los backends fallan lanza
    `RuntimeError`, que los llamadores deben degradar.
    """

    def __init__(self, source: str = "en", target: str = "es") -> None:
        self.source = source
        self.target = target
        primary = os.getenv("TRANSLATE_BACKEND", "google")
        self._order = (primary,) + tuple(
            kind for kind in _BACKEND_ORDER if kind != primary
        )

    def translate(self, texts: list[str]) -> list[str]:
        last_error: Exception | None = None
        for kind in self._order:
            try:
                translator = _build_translator(kind, self.source, self.target)
                result = translator.translate_batch(list(texts))
                if result and all(isinstance(t, str) and t for t in result):
                    return result
            except Exception as exc:  # noqa: BLE001 - se reintenta con otro backend
                last_error = exc
        raise RuntimeError(
            "deep-translator falló en todos los backends "
            f"({'/'.join(self._order)}): {last_error}"
        )


def _clean_es(text: str) -> str:
    """Limpieza ligera del decode de SentencePiece para texto en español."""
    text = re.sub(r"\s+([,.;:!?¡¿])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


class _Ct2EnEs:
    """Traducción local OPUS-MT en→es con CTranslate2 (gratis, offline)."""

    def __init__(
        self,
        model_path: str | None = None,
        source_spm: str | None = None,
        target_spm: str | None = None,
    ) -> None:
        self.model_path = Path(
            model_path or os.getenv("ENES_CT2_MODEL_PATH") or DEFAULT_ENES_CT2
        )
        self.source_spm = Path(source_spm or DEFAULT_ENES_SRC)
        self.target_spm = Path(target_spm or DEFAULT_ENES_TGT)
        self._translator = None
        self._spm = None
        self._tspm = None

    def _ready(self) -> None:
        if not (self.model_path / "model.bin").exists():
            raise FileNotFoundError(
                f"Modelo en→es no disponible en {self.model_path} "
                "(ejecuta scripts/setup_ct2.py --pair en-es)"
            )
        import ctranslate2
        import sentencepiece as spm

        self._translator = ctranslate2.Translator(str(self.model_path), device="cpu")
        self._spm = spm.SentencePieceProcessor(model_file=str(self.source_spm))
        self._tspm = spm.SentencePieceProcessor(model_file=str(self.target_spm))

    def translate(self, texts: list[str]) -> list[str]:
        self._ready()
        source = [self._spm.encode(t, out_type=str) for t in texts]
        translated = self._translator.translate_batch(
            source, beam_size=4, max_batch_size=len(source) or 1
        )
        return [_clean_es(self._tspm.decode(r.hypotheses[0])) for r in translated]


class EsTranslator:
    """Cadena en→es: CTranslate2 local → deep-translator → texto original.

    Es la pieza que garantiza el ensayo/contexto monolingüe en español. Los
    fallos no lanzan: siempre se devuelve algo utilizable (best-effort).
    """

    def __init__(
        self,
        ct2: _Ct2EnEs | None = None,
        web: WebTranslator | None = None,
    ) -> None:
        self._ct2 = ct2 if ct2 is not None else _Ct2EnEs()
        self._web = web if web is not None else WebTranslator("en", "es")

    def translate_many(self, texts: list[str]) -> list[str]:
        try:
            return self._ct2.translate(list(texts))
        except Exception:  # noqa: BLE001 - degrada a web
            try:
                return self._web.translate(list(texts))
            except Exception:  # noqa: BLE001 - best-effort: original
                return [t for t in texts]

    def translate(self, text: str) -> str:
        return self.translate_many([text])[0]
