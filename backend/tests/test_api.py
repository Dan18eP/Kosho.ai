import pytest
from app.main import app
from app.modules.optimizer.providers.ctranslate2_provider import DEFAULT_MODEL_DIR
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(autouse=True)
def _debate_service_without_llm(monkeypatch):
    """Los tests del endpoint de debate no deben depender de Ollama/red."""
    from app.modules.debate.service import DebateService

    class _NoLLM:
        def generate(self, prompt, system=None, max_tokens=None, temperature=None):
            return ""

    class _NoOpTranslator:
        def translate_many(self, texts):
            return list(texts)

        def translate(self, text):
            return text

    service = DebateService(
        llm=_NoLLM(),
        es_translator=_NoOpTranslator(),
        query_translator=_NoOpTranslator(),
    )
    monkeypatch.setattr("app.main._debate_service", service)


class TestQuotes:
    def test_list_quotes(self):
        resp = client.get("/api/quotes")
        assert resp.status_code == 200
        body = resp.json()
        assert body["source"] == "https://quotes.toscrape.com"
        assert body["count"] > 0
        assert "updated_at" in body
        assert len(body["quotes"]) > 0

    def test_quote_contract(self):
        resp = client.get("/api/quotes")
        quote = resp.json()["quotes"][0]
        assert isinstance(quote["phrase"], str) and len(quote["phrase"]) > 0

    def test_refresh_endpoint(self, monkeypatch):
        from app import main as main_module

        def fake_refresh():
            return {
                "source": "https://quotes.toscrape.com",
                "count": 5,
                "added": 2,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }

        monkeypatch.setattr(main_module, "refresh_quotes", fake_refresh)
        resp = client.post("/api/quotes/refresh")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 5
        assert body["added"] == 2

    def test_refresh_endpoint_error(self, monkeypatch):
        from app import main as main_module

        def broken():
            raise ConnectionError("web caída")

        monkeypatch.setattr(main_module, "refresh_quotes", broken)
        resp = client.post("/api/quotes/refresh")
        assert resp.status_code == 502
        assert "No se pudo actualizar" in resp.json()["detail"]


class TestDebate:
    def test_with_sources(self):
        resp = client.post(
            "/api/debate",
            json={
                "question": "Is imagination more important than knowledge?",
                "language": "en",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_sources"] is True
        assert body["answer"].count("\n\n") == 1
        assert len(body["quotes"]) > 0

    def test_honest_response_without_sources(self):
        resp = client.post(
            "/api/debate",
            json={"question": "Which pet should I adopt?", "language": "en"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_sources"] is False
        assert len(body["quotes"]) == 0

    def test_validation_error(self):
        resp = client.post("/api/debate", json={"question": ""})
        assert resp.status_code == 422

    def test_es_serialization_includes_translation(self, monkeypatch):
        from app import main as m
        from app.modules.debate.essay_generator import DebateResult
        from app.modules.debate.retrieval import Quote, RetrievedQuote

        class FakeService:
            def debate(self, question, language, threshold=None):
                return DebateResult(
                    answer="El conocimiento es poder.",
                    has_sources=True,
                    quotes=[
                        RetrievedQuote(
                            quote=Quote(
                                phrase="Knowledge is power.", author="Francis Bacon"
                            ),
                            score=0.5,
                        )
                    ],
                    translations=["El conocimiento es poder."],
                )

        monkeypatch.setattr(m, "_debate_service", FakeService())
        resp = client.post(
            "/api/debate",
            json={"question": "Which question?", "language": "es"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_sources"] is True
        assert body["quotes"][0]["translation"] == "El conocimiento es poder."


class TestOptimizer:
    def test_specs(self):
        resp = client.get("/api/optimizer/specs")
        assert resp.status_code == 200
        assert resp.json()["default_spec"]["max_tokens_per_request"] == 2000
        assert "mock" in resp.json()["providers"]

    def test_preview_respects_limit(self):
        resp = client.post(
            "/api/optimizer/preview",
            json={"spec": {"max_tokens_per_request": 900}, "limit_phrases": 30},
        )
        assert resp.status_code == 200
        receipt = resp.json()["receipt"]
        assert receipt["total_requests"] >= 2
        for b in receipt["batches"]:
            assert b["total_tokens"] <= 900

    def test_run_with_mock(self):
        resp = client.post(
            "/api/optimizer/run",
            json={
                "spec": {"max_tokens_per_request": 300},
                "provider": "mock",
                "limit_phrases": 10,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 10
        first = body["items"][0]
        assert first["input_tokens"] > 0
        assert first["output_tokens"] > 0
        assert first["translation"]
        assert first["context"]
        assert body["receipt"]["total_requests"] >= 1
        assert body["receipt"]["total_output_tokens"] == sum(
            i["output_tokens"] for i in body["items"]
        )

    def test_run_rejects_unfittable_phrase(self):
        resp = client.post(
            "/api/optimizer/run",
            json={
                "spec": {"max_tokens_per_request": 5},
                "provider": "mock",
                "limit_phrases": 5,
            },
        )
        assert resp.status_code == 422

    def test_run_ctranslate2_without_model_returns_503(self, monkeypatch):
        monkeypatch.setattr(
            "app.modules.optimizer.providers.ctranslate2_provider.DEFAULT_MODEL_DIR",
            "C:/no/existe/enja_ct2",
        )
        resp = client.post(
            "/api/optimizer/run",
            json={"provider": "ctranslate2", "limit_phrases": 5},
        )
        assert resp.status_code == 503
        assert "setup_ct2" in resp.json()["detail"]

    @pytest.mark.skipif(
        not (DEFAULT_MODEL_DIR / "model.bin").exists(),
        reason="Modelo CTranslate2 no descargado (scripts/setup_ct2.py)",
    )
    def test_run_ctranslate2_real_end_to_end(self):
        resp = client.post(
            "/api/optimizer/run",
            json={
                "spec": {"max_tokens_per_request": 300},
                "provider": "ctranslate2",
                "limit_phrases": 3,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 3
        for item in body["items"]:
            assert item["input_tokens"] > 0
            assert item["output_tokens"] > 0
            assert item["translation"]
