import hashlib
import math
import re

from app.modules.debate.essay_generator import (
    HONEST_ONE_VOICE,
    HONEST_RESPONSE,
    EssayGenerator,
)
from app.modules.debate.retrieval import (
    EmbeddingRetrievalEngine,
    Quote,
    RetrievedQuote,
)
from app.modules.debate.service import DebateService, _looks_non_english

CORPUS = [
    Quote(phrase="The unexamined life is not worth living.", author="Socrates"),
    Quote(phrase="Knowledge is power.", author="Francis Bacon"),
    Quote(
        phrase="Imagination is more important than knowledge.", author="Albert Einstein"
    ),
    Quote(
        phrase="It is during our darkest moments that we must focus to see the light.",
        author="Aristotle Onassis",
    ),
    Quote(
        phrase="Life is what happens to us while we are making other plans.",
        author="Allen Saunders",
    ),
]


class _FakeLLM:
    """LLM determinista para tests: emite el texto solicitado en `emit`."""

    def __init__(self, emit: str) -> None:
        self.emit = emit
        self.last_prompt = None

    def generate(self, prompt, system=None, max_tokens=None, temperature=None) -> str:
        self.last_prompt = prompt
        return self.emit


class _FakeTranslator:
    def __init__(self, prefix="[ES] ") -> None:
        self.prefix = prefix

    def translate(self, text: str) -> str:
        return f"{self.prefix}{text}"

    def translate_many(self, texts):
        return [self.translate(t) for t in texts]


def _quote(phrase: str, author: str = "X") -> RetrievedQuote:
    return RetrievedQuote(quote=Quote(phrase=phrase, author=author), score=0.5)


def _hash_embedder(texts: list[str]) -> list[list[float]]:
    """Embedder determinista (sin red) basado en hash de tokens.

    Promedia vectores unitarios por token → similitud coseno léxica, útil
    para probar `EmbeddingRetrievalEngine` sin Ollama.
    """
    dim = 64

    def token_vec(tok: str) -> list[float]:
        digest = hashlib.sha256(tok.encode()).digest()
        vec = [(b / 255.0) * 2 - 1 for b in digest[:dim]]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    out: list[list[float]] = []
    for text in texts:
        tokens = re.findall(r"[a-z]+", text.lower())
        if not tokens:
            out.append([0.0] * dim)
            continue
        acc = [0.0] * dim
        for tok in tokens:
            tv = token_vec(tok)
            for i, x in enumerate(tv):
                acc[i] += x
        k = 1.0 / len(tokens)
        out.append([x * k for x in acc])
    return out


def _quotes(n: int) -> list[RetrievedQuote]:
    return [_quote(f"Quote number {i}.", f"Author {i}") for i in range(n)]


class TestTokenize:
    def test_filters_stopwords(self):
        from app.modules.debate.retrieval import tokenize

        assert "is" not in tokenize("Life is what happens", "en")

    def test_handles_empty(self):
        from app.modules.debate.retrieval import tokenize

        assert tokenize("", "en") == []


class TestRetrieval:
    def _engine(self):
        from app.modules.debate.retrieval import RetrievalEngine

        return RetrievalEngine(threshold=0.0, max_quotes=3).fit(CORPUS)

    def test_ranks_by_relevance(self):
        hits = self._engine().retrieve("Is imagination more important than knowledge?")
        scores = [r.score for r in hits]
        assert scores == sorted(scores, reverse=True)
        assert hits[0].quote.author == "Albert Einstein"

    def test_threshold_filters(self):
        from app.modules.debate.retrieval import RetrievalEngine

        engine = RetrievalEngine(threshold=0.99, max_quotes=3).fit(CORPUS)
        assert engine.retrieve("imagination knowledge") == []

    def test_empty_corpus(self):
        from app.modules.debate.retrieval import RetrievalEngine

        engine = RetrievalEngine().fit([])
        assert engine.retrieve("anything") == []

    def test_quote_text_never_altered(self):
        hits = self._engine().retrieve("imagination knowledge")
        assert hits[0].quote.phrase in {q.phrase for q in CORPUS}


class TestEmbeddingRetrieval:
    def _engine(self):
        return EmbeddingRetrievalEngine(
            _hash_embedder, threshold=0.0, max_quotes=3
        ).fit(CORPUS)

    def test_ranks_by_relevance(self):
        hits = self._engine().retrieve("Is imagination more important than knowledge?")
        scores = [r.score for r in hits]
        assert scores == sorted(scores, reverse=True)
        assert hits[0].quote.author == "Albert Einstein"

    def test_threshold_filters(self):
        engine = EmbeddingRetrievalEngine(
            _hash_embedder, threshold=0.99, max_quotes=3
        ).fit(CORPUS)
        assert engine.retrieve("imagination knowledge") == []

    def test_empty_corpus(self):
        engine = EmbeddingRetrievalEngine(_hash_embedder).fit([])
        assert engine.retrieve("anything") == []

    def test_quote_text_never_altered(self):
        hits = self._engine().retrieve("imagination knowledge")
        assert hits[0].quote.phrase in {q.phrase for q in CORPUS}


class TestEssayGenerator:
    def test_two_paragraphs_with_sources(self):
        hits = _quotes(2)
        result = EssayGenerator().generate("Is imagination important?", hits)
        assert result.has_sources is True
        assert result.answer.count("\n\n") == 1

    def test_cites_textually(self):
        result = EssayGenerator().generate("question", _quotes(2))
        assert "Quote number 0." in result.answer
        assert "Author 0" in result.answer

    def test_honest_response_without_sources(self):
        result = EssayGenerator().generate("What is the meaning of the universe?", [])
        assert result.has_sources is False
        assert result.answer == HONEST_RESPONSE

    def test_honest_with_single_voice(self):
        result = EssayGenerator().generate("question", _quotes(1))
        assert result.has_sources is False
        assert result.answer == HONEST_ONE_VOICE

    def test_llm_used_when_it_preserves_quotes(self):
        essay = (
            'As Author 0 puts it: "Quote number 0." Indeed, Author 1 reminds us '
            '"Quote number 1." The debate is enriched.\n\nThis is my conclusion.'
        )
        result = EssayGenerator(llm=_FakeLLM(essay)).generate("question", _quotes(2))
        assert result.has_sources is True
        assert result.answer == essay

    def test_missing_quotes_appended_verbatim(self):
        bad = "The essay talks about other things entirely and none of the quotes."
        generator = EssayGenerator(llm=_FakeLLM(bad), max_tokens=20)
        result = generator.generate("question", _quotes(2))
        assert result.has_sources is True
        assert "Quote number 0." in result.answer  # cita anexada verbatim
        assert "Quote number 1." in result.answer
        assert "Author 0" in result.answer

    def test_spanish_translates_llm_output(self):
        essay = (
            'As Author 0 puts it: "Quote number 0." "Quote number 1." In conclusion.'
        )
        translator = _FakeTranslator()
        result = EssayGenerator(llm=_FakeLLM(essay), translator=translator).generate(
            "question", _quotes(2), language="es"
        )
        assert result.has_sources is True
        assert not result.answer.startswith(essay)  # CT2→fake aportó prefijo
        assert result.answer.startswith("[ES] ")

    def test_spanish_template_uses_translated_quotes(self):
        quotes = _quotes(2)
        translations = ["Frase traducida 0", "Frase traducida 1"]
        result = EssayGenerator().generate(
            "question", quotes, language="es", translations=translations
        )
        assert "Frase traducida 0" in result.answer
        assert "Frase traducida 1" in result.answer


class TestDebateService:
    def _service(self, **kwargs):
        kwargs.setdefault("quotes", CORPUS)
        kwargs.setdefault("llm", _FakeLLM(""))
        kwargs.setdefault("es_translator", _FakeTranslator())
        return DebateService(**kwargs)

    def test_spanish_question_finds_quotes_via_translation(self):
        class QTrans:
            def translate(self, texts):
                assert texts[0] == "¿Es importante la imaginación?"
                return ["imagination knowledge"]

        service = self._service(query_translator=QTrans())
        result = service.debate("¿Es importante la imaginación?", language="es")
        assert result.has_sources is True
        assert result.answer.count("\n\n") == 1

    def test_english_question_without_llm_uses_template(self):
        result = self._service().debate(
            "Is imagination more important than knowledge?", language="en"
        )
        assert result.has_sources is True
        assert result.answer.count("\n\n") == 1

    def test_two_distinct_voices_in_essay(self):
        result = self._service().debate(
            "Is imagination more important than knowledge?", language="en"
        )
        authors = [q.quote.author for q in result.quotes]
        assert len(set(authors)) >= 2
        assert authors[0] in result.answer
        assert authors[1] in result.answer

    def test_honest_when_no_evidence(self):
        result = self._service().debate("Which pet should I adopt?", language="en")
        assert result.has_sources is False

    def test_es_includes_translations_for_citations(self):
        class T(_FakeTranslator):
            def translate(self, text: str) -> str:
                return f"[{text}]"

            def translate_many(self, texts):
                return [f"[{t}]" for t in texts]

        service = self._service(es_translator=T())
        result = service.debate(
            "Is imagination more important than knowledge?", language="es"
        )
        assert result.translations
        assert all(result.translations)

    def test_uses_embedding_engine_when_available(self):
        class EmbedLLM(_FakeLLM):
            def embed(self, texts):
                return _hash_embedder(texts)

        service = self._service(llm=EmbedLLM(""), embed_threshold=0.1)
        result = service.debate(
            "Is imagination more important than knowledge?", language="en"
        )
        assert result.has_sources is True
        assert service._embed_engine is not None
        engine = service._embed_engine
        service.debate("Is imagination more important than knowledge?", language="en")
        assert service._embed_engine is engine  # fit cacheado

    def test_embedding_failure_falls_back_to_tfidf(self):
        class BrokenLLM(_FakeLLM):
            def embed(self, texts):
                raise RuntimeError("embed model not installed")

        service = self._service(llm=BrokenLLM(""))
        result = service.debate(
            "Is imagination more important than knowledge?", language="en"
        )
        assert result.has_sources is True
        assert result.answer.count("\n\n") == 1
        assert service._embed_failed is True


class TestQueryLanguage:
    def test_detects_spanish_accents(self):
        assert _looks_non_english("¿Qué es el amor?")
        assert _looks_non_english("La verdad es más importante que la felicidad")

    def test_plain_english_not_detected(self):
        assert not _looks_non_english("Is imagination more important than knowledge?")
