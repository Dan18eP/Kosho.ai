import re
from dataclasses import dataclass, field

from ...core.llm import OllamaClient
from ...core.translators import EsTranslator
from .retrieval import RetrievedQuote

HONEST_RESPONSE = (
    "No tengo frases en mi base de datos que respalden un debate sobre esta "
    "pregunta. Para responder con evidencia textual necesitaría citas "
    "relacionadas y no las encontré. / "
    "I don't have phrases in my database that support a debate on this "
    "question. I would need related citations to answer with textual "
    "evidence, and I found none."
)

HONEST_ONE_VOICE = (
    "Solo encontré una cita distinta relacionada con la pregunta. Para "
    "argumentar con honestidad necesito al menos dos voces; reformula la "
    "pregunta para ver si aparece más evidencia. / "
    "I found only one distinct citation related to the question. To argue "
    "honestly I need at least two voices; rephrase the question to surface "
    "more evidence."
)

_SYSTEM_ESSAY = (
    "You are a philosophical orator grounding every claim in textual evidence. "
    "Write a mini-essay of exactly two paragraphs separated by one blank line. "
    "Argue about the question using ONLY the quotes provided, inserting each "
    "one verbatim inside quotation marks and attributing it to its author. "
    "Do NOT invent quotes, authors, facts, or other sources. Keep the whole "
    "essay under 170 words."
)


@dataclass
class DebateResult:
    answer: str
    has_sources: bool
    quotes: list[RetrievedQuote] = field(default_factory=list)
    translations: list[str | None] = field(default_factory=list)


class EssayGenerator:
    """Genera un mini-ensayo de 2 párrafos que solo usa las citas dadas.

    Estrategia por prioridad de tiempo y honestidad:
        1. llama3.2:3b (Ollama) escribe el ensayo en inglés con reglas
           estrictas; se verifica que las 2 citas aparezcan verbatim. Si el
           LLM no está disponible, falla o no cumple → degradación a plantilla.
        2. Si el idioma elegido es español, el ensayo ENTERO se traduce con
           `EsTranslator` (CTranslate2 en→es → deep-translator), quedando
           monolingüe. Las citas conservan su traducción para la vista.
        3. Plantilla determinista (sin LLM) con ambas citas; jamás se inventa
           contenido. Con menos de 2 citas distintas se responde con honestidad.
    """

    def __init__(
        self,
        llm: OllamaClient | None = None,
        translator: EsTranslator | None = None,
        max_tokens: int = 260,
    ) -> None:
        self._llm = llm
        self._translator = translator
        self._max_tokens = max_tokens

    def generate(
        self,
        question: str,
        retrieved: list[RetrievedQuote],
        language: str = "en",
        translations: list[str | None] | None = None,
    ) -> DebateResult:
        if not retrieved:
            return DebateResult(answer=HONEST_RESPONSE, has_sources=False)
        if len(retrieved) < 2:
            return DebateResult(answer=HONEST_ONE_VOICE, has_sources=False)

        translations = translations or [None] * len(retrieved)
        answer = self._try_llm(question, retrieved)
        if answer is not None:
            answer = EssayGenerator._ensure_verbatim_quotes(answer, retrieved)
            if language == "es" and self._translator is not None:
                answer = self._translator.translate(answer)
        else:
            answer = self._template(question, retrieved, language, translations)

        return DebateResult(
            answer=answer,
            has_sources=True,
            quotes=retrieved,
            translations=translations,
        )

    def _try_llm(self, question: str, retrieved: list[RetrievedQuote]) -> str | None:
        if self._llm is None:
            return None
        first, second = retrieved[0], retrieved[1]
        prompt = (
            f'Question: "{question}"\n\n'
            "Provided quotes:\n"
            f'1. "{first.quote.phrase}" — {first.quote.author}\n'
            f'2. "{second.quote.phrase}" — {second.quote.author}\n\n'
            "Write the essay now."
        )
        try:
            essay = self._llm.generate(
                prompt, system=_SYSTEM_ESSAY, max_tokens=self._max_tokens
            )
        except Exception:  # noqa: BLE001 - degrada a plantilla
            return None
        if not essay or not self._contains_quotes(essay, retrieved):
            return None
        return essay

    @staticmethod
    def _ensure_verbatim_quotes(essay: str, retrieved: list[RetrievedQuote]) -> str:
        """Fuerza que ambas citas estén verbatim (parafraseos del LLM no valen).

        Si una cita falta, se añade con su autor para que el texto siga siendo
        honesto y verificable, sin descartar el ensayo generado. El apéndice
        se traduce junto con el resto cuando language == 'es'.
        """
        for r in retrieved[:2]:
            if not EssayGenerator._contains_quotes(essay, [r]):
                essay = (
                    f"{essay}\n\n{r.quote.author} also framed it memorably: "
                    f"'{r.quote.phrase}'"
                )
        return essay

    @staticmethod
    def _contains_quotes(essay: str, retrieved: list[RetrievedQuote]) -> bool:
        def norm(text: str) -> str:
            return re.sub(r"[^a-z0-9]+", "", text.lower())

        body = norm(essay)
        return all(norm(r.quote.phrase) in body for r in retrieved[:2])

    @staticmethod
    def _template(
        question: str,
        retrieved: list[RetrievedQuote],
        language: str,
        translations: list[str | None],
    ) -> str:
        first, second = retrieved[0], retrieved[1]
        phrase_one = translations[0] or first.quote.phrase
        phrase_two = translations[1] or second.quote.phrase
        topic = EssayGenerator._normalize_topic(question)

        if language == "es":
            paragraph_one = (
                f"Sobre {topic}, la evidencia disponible respalda una postura clara. "
                f"Como señala {first.quote.author}: "
                f"“{phrase_one}” "
                f"Esta idea muestra que la cuestión tiene raíces profundas en la "
                f"experiencia humana y no admite una respuesta trivial."
            )
            paragraph_two = (
                f"La discusión gana matices al considerar una segunda perspectiva. "
                f"{second.quote.author} lo expresa de forma contundente: "
                f"“{phrase_two}” "
                f"Entre ambas voces, el debate queda enriquecido: cada postura aporta "
                f"evidencia textual propia y deja al lector la tarea de sopesar las razones."
            )
        else:
            paragraph_one = (
                f"On {topic}, the available evidence supports a clear position. "
                f"As {first.quote.author} puts it: "
                f"“{first.quote.phrase}” "
                f"This shows the question has deep roots in human experience and "
                f"admits no trivial answer."
            )
            paragraph_two = (
                f"The discussion gains nuance when we consider a second perspective. "
                f"{second.quote.author} puts it forcefully: "
                f"“{second.quote.phrase}” "
                f"Between these voices, the debate is enriched: each position brings "
                f"its own textual evidence and leaves the reader weighing the reasons."
            )

        return f"{paragraph_one}\n\n{paragraph_two}"

    @staticmethod
    def _normalize_topic(question: str) -> str:
        q = question.strip().rstrip("?¿")
        for prefix in (
            "is ",
            "are ",
            "should ",
            "can ",
            "does ",
            "do ",
            "what is ",
            "es ",
            "son ",
            "puede ",
            "debería ",
            "qué es ",
        ):
            if q.lower().startswith(prefix):
                q = q[len(prefix) :].strip()
        return q or question.strip()
