import sys
from pathlib import Path

import pytest
from app.core.provider_spec import ProviderSpec
from app.core.token_counter import TokenCounter
from app.modules.debate.retrieval import Quote
from app.modules.optimizer.context_engine import ContextEngine
from app.modules.optimizer.providers import UnknownProviderError, get_provider
from app.modules.optimizer.providers.base import PhraseRef, ProviderError
from app.modules.optimizer.providers.ctranslate2_provider import (
    DEFAULT_MODEL_DIR,
    CTranslate2Provider,
    clean_japanese,
)
from app.modules.optimizer.providers.mock import MockProvider
from app.modules.optimizer.service import OptimizerService

PHRASES = [
    Quote(phrase="Knowledge is power.", author="Francis Bacon"),
    Quote(
        phrase="Imagination is more important than knowledge.", author="Albert Einstein"
    ),
    Quote(phrase="The unexamined life is not worth living.", author="Socrates"),
]


def test_mock_provider_processes_batch():
    refs = [PhraseRef(phrase="Knowledge is power.", author="Francis Bacon")]
    result = MockProvider().process_batch(refs)
    assert len(result.translations) == 1
    assert "Knowledge is power." in result.translations[0]
    assert "Francis Bacon" in result.contexts[0]


def test_context_engine_known_author():
    text = ContextEngine().explain("A quote", "Albert Einstein")
    assert "Albert Einstein" in text and "1879-1955" in text


def test_context_engine_unknown_author():
    text = ContextEngine().explain("A quote", "Autor Desconocido")
    assert "Autor Desconocido" in text


def test_get_provider_unknown():
    try:
        get_provider("nope")
        assert False, "debería lanzar UnknownProviderError"
    except UnknownProviderError:
        pass


def test_run_full_pipeline_with_mock():
    spec = ProviderSpec(max_tokens_per_request=200)
    result = OptimizerService().run(PHRASES, spec, provider_name="mock")
    assert result.receipt.total_requests == len(result.batches)
    assert result.receipt.total_requests >= 1
    assert len(result.items) == len(PHRASES)
    assert result.receipt.total_cost >= 0


def test_items_have_per_phrase_tokens_and_output():
    spec = ProviderSpec(max_tokens_per_request=200)
    result = OptimizerService().run(PHRASES, spec, provider_name="mock")
    counter = TokenCounter()
    for item in result.items:
        assert item.input_tokens > 0
        expected = counter.count(item.translation) + counter.count(item.context)
        assert item.output_tokens == expected
        assert item.translation
        assert item.context
    assert result.receipt.total_output_tokens == sum(
        i.output_tokens for i in result.items
    )


def test_receipt_uses_recounted_actual_tokens():
    spec = ProviderSpec(max_tokens_per_request=200)
    result = OptimizerService().run(PHRASES, spec, provider_name="mock")
    assert result.receipt.total_output_tokens == sum(
        i.output_tokens for i in result.items
    )


def test_preview_returns_receipt_without_execution():
    spec = ProviderSpec(max_tokens_per_request=200)
    receipt = OptimizerService().preview(PHRASES, spec)
    assert receipt.total_requests >= 1


def test_ctranslate2_raises_when_model_missing(monkeypatch):
    monkeypatch.setattr(
        "app.modules.optimizer.providers.ctranslate2_provider.DEFAULT_MODEL_DIR",
        Path("C:/no/existe/enja_ct2"),
    )
    provider = get_provider("ctranslate2")
    assert provider.name == "ctranslate2"
    with pytest.raises(ProviderError, match="setup_ct2"):
        provider.process_batch(
            [PhraseRef(phrase="Knowledge is power.", author="Francis Bacon")]
        )


def test_clean_japanese_removes_cjk_spaces():
    assert clean_japanese("知識 が , 力 で あ る") == "知識が,力である"


@pytest.mark.skipif(
    not (DEFAULT_MODEL_DIR / "model.bin").exists(),
    reason="Modelo CTranslate2 no descargado (scripts/setup_ct2.py)",
)
def test_ctranslate2_real_translation():
    provider = CTranslate2Provider()
    refs = [PhraseRef(phrase="Knowledge is power.", author="Francis Bacon")]
    result = provider.process_batch(refs)
    assert result.translations[0]
    assert "Francis Bacon" in result.contexts[0]


def test_deep_translator_missing_lib_raises_provider_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "deep_translator", None)
    provider = get_provider("deep_translator")
    with pytest.raises(ProviderError, match="deep-translator"):
        provider.process_batch(
            [PhraseRef(phrase="Knowledge is power.", author="Francis Bacon")]
        )


def test_service_wraps_sdk_errors_as_provider_error():
    class BrokenProvider:
        name = "broken"

        def process_batch(self, refs: list[PhraseRef]):
            raise ConnectionError("timeout al llamar a la API")

    spec = ProviderSpec(max_tokens_per_request=200)
    with pytest.raises(ProviderError, match="broken"):
        OptimizerService().run(
            PHRASES,
            spec,
            provider=BrokenProvider(),  # type: ignore[arg-type]
        )
