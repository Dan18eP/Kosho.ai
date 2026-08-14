from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .core.provider_spec import ProviderSpec
from .data.quotes_repo import get_quotes, quotes_meta, refresh_quotes
from .modules.debate.service import DebateService
from .modules.optimizer.packer import PackingError
from .modules.optimizer.providers import available_providers
from .modules.optimizer.providers.base import ProviderError
from .modules.optimizer.service import OptimizerService
from .schemas import (
    DebateRequest,
    DebateResponse,
    OptimizerRequest,
    OptimizerResponse,
    PhraseReportOut,
    QuotesResponse,
    RefreshResponse,
    RetrievedQuoteOut,
)

app = FastAPI(
    title="Orador de Debates + Optimizador",
    description="Ejercicio 1 (debate respaldado) y Ejercicio 2 (empaquetado y recibo).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_service = OptimizerService()
_debate_service = DebateService()


@app.get("/api/quotes", response_model=QuotesResponse)
def list_quotes() -> QuotesResponse:
    return QuotesResponse(**quotes_meta())


@app.post("/api/quotes/refresh", response_model=RefreshResponse)
def refresh_quotes_endpoint() -> RefreshResponse:
    try:
        result = refresh_quotes()
    except Exception as exc:  # noqa: BLE001 - la web puede fallar
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo actualizar las citas desde {quotes_meta()['source']}: {exc}",
        )
    return RefreshResponse(**result)


@app.post("/api/debate", response_model=DebateResponse)
def debate(req: DebateRequest) -> DebateResponse:
    result = _debate_service.debate(
        req.question, language=req.language, threshold=req.threshold
    )
    translations = result.translations or []
    return DebateResponse(
        answer=result.answer,
        has_sources=result.has_sources,
        quotes=[
            RetrievedQuoteOut(
                phrase=r.quote.phrase,
                author=r.quote.author,
                score=round(r.score, 4),
                translation=translations[i] if i < len(translations) else None,
            )
            for i, r in enumerate(result.quotes)
        ],
    )


@app.get("/api/optimizer/specs")
def optimizer_specs() -> dict:
    return {
        "default_spec": ProviderSpec().to_dict(),
        "providers": available_providers(),
    }


def _build_spec(req: OptimizerRequest) -> ProviderSpec:
    s = req.spec
    return ProviderSpec(
        name=s.name,
        tokenizer=s.tokenizer,
        max_tokens_per_request=s.max_tokens_per_request,
        max_chars_per_request=s.max_chars_per_request,
        reserve_output=s.reserve_output,
        price_per_input_token=s.price_per_input_token,
        price_per_output_token=s.price_per_output_token,
        currency=s.currency,
        requests_per_minute=s.requests_per_minute,
        system_prompt_tokens=s.system_prompt_tokens,
        json_format_overhead=s.json_format_overhead,
        output_ratio=s.output_ratio,
        output_base=s.output_base,
    )


def _phrases(req: OptimizerRequest):
    quotes = get_quotes()
    if req.limit_phrases:
        quotes = quotes[: req.limit_phrases]
    return quotes


@app.post("/api/optimizer/preview", response_model=OptimizerResponse)
def optimizer_preview(req: OptimizerRequest) -> OptimizerResponse:
    try:
        receipt = _service.preview(_phrases(req), _build_spec(req))
    except PackingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return OptimizerResponse(receipt=receipt.to_dict(), items=[])


@app.post("/api/optimizer/run", response_model=OptimizerResponse)
def optimizer_run(req: OptimizerRequest) -> OptimizerResponse:
    try:
        result = _service.run(
            _phrases(req), _build_spec(req), provider_name=req.provider
        )
    except PackingError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except ProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    return OptimizerResponse(
        receipt=result.receipt.to_dict(),
        items=[
            PhraseReportOut(
                index=i.index,
                phrase=i.phrase,
                author=i.author,
                input_tokens=i.input_tokens,
                output_tokens=i.output_tokens,
                translation=i.translation,
                context=i.context,
            )
            for i in result.items
        ],
    )
