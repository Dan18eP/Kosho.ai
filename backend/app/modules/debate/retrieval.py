import math
import re
from collections.abc import Callable
from dataclasses import dataclass

EN_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "has",
        "he",
        "her",
        "his",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "our",
        "over",
        "so",
        "that",
        "the",
        "their",
        "there",
        "they",
        "this",
        "to",
        "was",
        "we",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "with",
        "you",
        "your",
        "not",
        "do",
        "does",
        "did",
        "just",
        "can",
        "dont",
        "more",
        "than",
        "would",
        "should",
        "could",
        "about",
        "up",
        "out",
        "all",
        "also",
        "each",
        "many",
        "only",
        "some",
        "those",
        "them",
        "because",
        "into",
    ]
)

ES_STOPWORDS = frozenset(
    [
        "a",
        "al",
        "ante",
        "como",
        "con",
        "contra",
        "de",
        "del",
        "desde",
        "durante",
        "e",
        "el",
        "ella",
        "ellas",
        "ellos",
        "en",
        "entre",
        "es",
        "esa",
        "esas",
        "ese",
        "esos",
        "esta",
        "estas",
        "este",
        "estos",
        "fue",
        "fueron",
        "ha",
        "han",
        "he",
        "hizo",
        "la",
        "las",
        "le",
        "les",
        "lo",
        "los",
        "más",
        "me",
        "mi",
        "mis",
        "mucho",
        "muchos",
        "muy",
        "nada",
        "no",
        "nos",
        "nuestro",
        "nuestros",
        "o",
        "para",
        "pero",
        "por",
        "porque",
        "que",
        "quien",
        "se",
        "sea",
        "según",
        "sin",
        "so",
        "sobre",
        "sus",
        "su",
        "tus",
        "un",
        "una",
        "uno",
        "unos",
        "una",
        "vez",
        "y",
        "ya",
    ]
)

_TOKEN_RE = re.compile(r"[a-záéíóúüñ']+", re.IGNORECASE)


def tokenize(text: str, language: str = "en") -> list[str]:
    words = [w.lower() for w in _TOKEN_RE.findall(text or "")]
    stop = ES_STOPWORDS if language == "es" else EN_STOPWORDS
    return [w for w in words if w not in stop]


@dataclass
class Quote:
    phrase: str
    author: str


@dataclass
class RetrievedQuote:
    quote: Quote
    score: float


class RetrievalEngine:
    """TF-IDF + cosine similarity sobre un corpus de frases scrapeadas.

    El umbral de relevancia decide si una frase pasa a ser evidencia. Es
    determinista y no requiere red. La elección de TF-IDF sobre embeddings
    mantiene el módulo ligero y reproducible para el ejercicio.
    """

    def __init__(
        self,
        threshold: float = 0.15,
        max_quotes: int = 3,
        language: str = "en",
    ) -> None:
        self.threshold = threshold
        self.max_quotes = max_quotes
        self.language = language
        self._quotes: list[Quote] = []
        self._idf: dict[str, float] = {}
        self._doc_vectors: list[dict[str, float]] = []

    def fit(self, quotes: list[Quote]) -> "RetrievalEngine":
        self._quotes = list(quotes)
        tokenized = [tokenize(q.phrase, self.language) for q in self._quotes]

        df: dict[str, int] = {}
        for tokens in tokenized:
            for w in set(tokens):
                df[w] = df.get(w, 0) + 1

        n = len(tokenized)
        # Smooth idf: log((N+1)/(df+1)) + 1 evita división por cero y df=0.
        self._idf = {w: math.log((n + 1) / (d + 1)) + 1 for w, d in df.items()}

        self._doc_vectors = []
        for tokens in tokenized:
            counts: dict[str, int] = {}
            for w in tokens:
                counts[w] = counts.get(w, 0) + 1
            total = len(tokens) or 1
            self._doc_vectors.append(
                {w: (c / total) * self._idf[w] for w, c in counts.items()}
            )
        return self

    def _vectorize(self, text: str) -> dict[str, float]:
        tokens = tokenize(text, self.language)
        counts: dict[str, int] = {}
        for w in tokens:
            counts[w] = counts.get(w, 0) + 1
        total = len(tokens) or 1
        return {w: (c / total) * self._idf.get(w, 0.0) for w, c in counts.items()}

    @staticmethod
    def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
        dot = sum(v * b.get(w, 0.0) for w, v in a.items())
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve(self, question: str) -> list[RetrievedQuote]:
        if not self._quotes:
            return []
        q_vec = self._vectorize(question)
        scored = [
            RetrievedQuote(quote=q, score=self._cosine(q_vec, v))
            for q, v in zip(self._quotes, self._doc_vectors)
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return [r for r in scored if r.score >= self.threshold][: self.max_quotes]


class EmbeddingRetrievalEngine:
    """Búsqueda semántica con embeddings (Ollama) + similitud coseno.

    Complementa (no reemplaza) a `RetrievalEngine`: captura sinónimos y
    reformulaciones que el TF-IDF exacto no ve (p. ej. preguntas en español
    contra citas en inglés). El `embedder` es una función que mapea una lista
    de textos a una lista de vectores; ante cualquier fallo del embedder,
    `DebateService` degrada al TF-IDF (híbrido).
    """

    def __init__(
        self,
        embedder: Callable[[list[str]], list[list[float]]],
        threshold: float = 0.40,
        max_quotes: int = 6,
    ) -> None:
        self._embedder = embedder
        self.threshold = threshold
        self.max_quotes = max_quotes
        self._quotes: list[Quote] = []
        self._vectors: list[list[float]] = []
        self._norms: list[float] = []

    def fit(
        self,
        quotes: list[Quote],
        vectors: list[list[float]] | None = None,
    ) -> "EmbeddingRetrievalEngine":
        self._quotes = list(quotes)
        if self._quotes:
            if vectors is None:
                vectors = self._embedder([q.phrase for q in self._quotes])
            self._vectors = list(vectors)
            self._norms = [self._norm(v) for v in self._vectors]
        return self

    def retrieve(
        self, question: str, threshold: float | None = None
    ) -> list[RetrievedQuote]:
        if not self._quotes:
            return []
        q_vec = self._embedder([question])[0]
        q_norm = self._norm(q_vec)
        thr = self.threshold if threshold is None else threshold
        scored: list[RetrievedQuote] = []
        for quote, vec, norm in zip(self._quotes, self._vectors, self._norms):
            if q_norm == 0.0 or norm == 0.0:
                score = 0.0
            else:
                dot = sum(a * b for a, b in zip(q_vec, vec))
                score = dot / (q_norm * norm)
            if score >= thr:
                scored.append(RetrievedQuote(quote=quote, score=score))
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[: self.max_quotes]

    @staticmethod
    def _norm(v: list[float]) -> float:
        return math.sqrt(sum(x * x for x in v))
