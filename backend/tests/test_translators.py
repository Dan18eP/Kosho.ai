import json

import pytest
from app.core.translators import EsTranslator, WebTranslator
from app.modules.optimizer.context_service import ContextService


class _FailingCt2:
    def translate(self, texts):
        raise FileNotFoundError("modelo no disponible")


class _FailingWeb:
    def translate(self, texts):
        raise RuntimeError("sin red")


class _EchoWeb:
    def translate(self, texts):
        return [t.upper() for t in texts]


class TestEsTranslator:
    def test_ct2_preferred_when_available(self):
        class Ct2:
            def translate(self, texts):
                return [f"CT2:{t}" for t in texts]

        t = EsTranslator(ct2=Ct2(), web=_EchoWeb())
        assert t.translate_many(["hola"]) == ["CT2:hola"]

    def test_falls_back_to_web(self):
        t = EsTranslator(ct2=_FailingCt2(), web=_EchoWeb())
        assert t.translate_many(["hola"]) == ["HOLA"]

    def test_returns_original_if_all_fail(self):
        t = EsTranslator(ct2=_FailingCt2(), web=_FailingWeb())
        assert t.translate_many(["hola", "adiós"]) == ["hola", "adiós"]

    def test_single_uses_many(self):
        t = EsTranslator(ct2=_FailingCt2(), web=_EchoWeb())
        assert t.translate("hola") == "HOLA"


class TestWebTranslator:
    def test_raises_when_all_backends_fail(self, monkeypatch):
        def boom(self, texts):
            raise RuntimeError("no")

        monkeypatch.setattr(WebTranslator, "translate", boom)
        with pytest.raises(RuntimeError):
            WebTranslator("en", "es").translate(["hola"])


class TestContextService:
    def test_loads_from_file(self, tmp_path):
        path = tmp_path / "contexts.json"
        path.write_text(
            json.dumps({"Albert Einstein": "Contexto de prueba."}), encoding="utf-8"
        )
        service = ContextService(path=path)
        assert service.explain("x", "Albert Einstein") == "Contexto de prueba."

    def test_falls_back_deterministic(self, tmp_path):
        path = tmp_path / "missing.json"
        service = ContextService(path=path)
        out = service.explain("Knowledge is power.", "Francis Bacon")
        assert "Francis Bacon" in out

    def test_update_and_save(self, tmp_path):
        path = tmp_path / "contexts.json"
        service = ContextService(path=path)
        added = service.update({"A": "c1", "B": "c2"})
        assert added == 2
        assert service.explain("x", "A") == "c1"
        service.save()
        reloaded = ContextService(path=path)
        assert reloaded.explain("x", "B") == "c2"
