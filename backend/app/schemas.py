from pydantic import BaseModel, Field


class QuoteOut(BaseModel):
    phrase: str
    author: str


class QuotesResponse(BaseModel):
    source: str
    count: int
    updated_at: str | None
    quotes: list[QuoteOut]


class RefreshResponse(BaseModel):
    source: str
    count: int
    added: int
    updated_at: str | None


class RetrievedQuoteOut(BaseModel):
    phrase: str
    author: str
    score: float
    translation: str | None = None


class DebateRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    language: str = Field(default="en", pattern="^(en|es)$")


class DebateResponse(BaseModel):
    answer: str
    has_sources: bool
    quotes: list[RetrievedQuoteOut]


class SpecModel(BaseModel):
    name: str = "MiniTranslate"
    tokenizer: str = "o200k_base"
    max_tokens_per_request: int = Field(default=2000, gt=0)
    max_chars_per_request: int | None = Field(default=None, gt=0)
    reserve_output: float = Field(default=0.35, ge=0.0, le=1.0)
    price_per_input_token: float = Field(default=0.00000015, ge=0.0)
    price_per_output_token: float = Field(default=0.00000060, ge=0.0)
    currency: str = "USD"
    requests_per_minute: int = Field(default=60, gt=0)
    system_prompt_tokens: int = Field(default=80, ge=0)
    json_format_overhead: int = Field(default=25, ge=0)
    output_ratio: float = Field(default=2.0, ge=0.0)
    output_base: int = Field(default=40, ge=0)


class OptimizerRequest(BaseModel):
    spec: SpecModel = SpecModel()
    provider: str = Field(
        default="ctranslate2", pattern="^(mock|deep_translator|ctranslate2)$"
    )
    limit_phrases: int | None = Field(default=None, gt=0, le=200)


class PhraseReportOut(BaseModel):
    index: int
    phrase: str
    author: str
    input_tokens: int
    output_tokens: int
    translation: str
    context: str


class OptimizerResponse(BaseModel):
    receipt: dict
    items: list[PhraseReportOut]
