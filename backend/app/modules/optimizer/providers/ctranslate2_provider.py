import os
import re
from pathlib import Path

import sentencepiece as spm

from ..context_service import ContextService
from .base import BatchResult, PhraseRef, ProviderError

PROJECT_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models" / "enja_ct2"
DEFAULT_SOURCE_SPM = PROJECT_ROOT / "models" / "enja" / "source.spm"
DEFAULT_TARGET_SPM = PROJECT_ROOT / "models" / "enja" / "target.spm"

_CJK = "一-龯ぁ-んァ-ン"
_SPACE_CJK_RE = re.compile(rf"(?<=[{_CJK}])\s+(?=[{_CJK}])")
_SPACE_PUNCT_RE = re.compile(r"\s*([,.;:!?、。！？])\s*")


def clean_japanese(text: str) -> str:
    """Elimina espacios del decode de SentencePiece entre caracteres CJK."""
    text = _SPACE_PUNCT_RE.sub(r"\1", text)
    return _SPACE_CJK_RE.sub("", text).strip()


class CTranslate2Provider:
    """Motor principal: traducción local y gratuita con CTranslate2 (en→ja).

    Usa el modelo Marian OPUS-MT `en-jap/opus-2020-01-08` convertido a
    CTranslate2 (int8). La ruta se resuelve en este orden:
        1. `model_path` explícito
        2. env `CT2_MODEL_PATH`
        3. `models/enja_ct2` (por defecto, creado por `scripts/setup_ct2.py`)

    Tokenización con SentencePiece real (source.spm/target.spm) y
    post-procesado `clean_japanese` para quitar espacios entre morfemas. El
    contexto histórico usa el ContextEngine local (sin claves). Todo es
    gratuito y offline; el costo por token se simula con la ProviderSpec.
    """

    name = "ctranslate2"

    def __init__(
        self,
        model_path: str | None = None,
        source_spm: str | None = None,
        target_spm: str | None = None,
        device: str = "cpu",
        beam_size: int = 4,
        context: ContextService | None = None,
    ) -> None:
        self.model_path = (
            model_path or os.getenv("CT2_MODEL_PATH") or str(DEFAULT_MODEL_DIR)
        )
        self.source_spm = source_spm or str(DEFAULT_SOURCE_SPM)
        self.target_spm = target_spm or str(DEFAULT_TARGET_SPM)
        self.device = device
        self.beam_size = beam_size
        self._translator = None
        self._spm: spm.SentencePieceProcessor | None = None
        self._tspm: spm.SentencePieceProcessor | None = None
        self._context = context or ContextService()

    def _ensure_ready(self) -> None:
        if self._translator is not None:
            return
        if (
            not Path(self.model_path).is_dir()
            or not Path(self.model_path, "model.bin").exists()
        ):
            raise ProviderError(
                "CTranslate2Provider no encuentra el modelo. Ejecuta el setup: "
                "python scripts/setup_ct2.py  (descarga OPUS-MT en→ja y lo convierte "
                "a CTranslate2 int8 en models/enja_ct2). "
                "O define CT2_MODEL_PATH apuntando a un modelo convertido."
            )
        try:
            import ctranslate2
        except ImportError as exc:  # pragma: no cover - depende de instalación
            raise ProviderError(
                "Instala la dependencia con: pip install ctranslate2 sentencepiece"
            ) from exc
        self._translator = ctranslate2.Translator(self.model_path, device=self.device)
        self._spm = spm.SentencePieceProcessor(model_file=self.source_spm)
        self._tspm = spm.SentencePieceProcessor(model_file=self.target_spm)

    def process_batch(self, refs: list[PhraseRef]) -> BatchResult:
        self._ensure_ready()
        source = [self._spm.encode(r.phrase, out_type=str) for r in refs]
        translated = self._translator.translate_batch(
            source, beam_size=self.beam_size, max_batch_size=len(source) or 1
        )
        translations = [
            clean_japanese(self._tspm.decode(r.hypotheses[0])) for r in translated
        ]
        contexts = [self._context.explain(r.phrase, r.author) for r in refs]
        return BatchResult(translations=translations, contexts=contexts)
