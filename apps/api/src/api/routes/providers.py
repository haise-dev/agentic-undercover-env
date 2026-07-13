from fastapi import APIRouter
from pydantic import BaseModel

from src.core.quota import QuotaTracker
from src.models.enums import LLMProvider

router = APIRouter()


class ProviderModelInfo(BaseModel):
    provider: str
    models: list[str]
    is_exhausted: bool


# Static definition of supported models per provider
AVAILABLE_PROVIDERS = {
    LLMProvider.OPENAI.value: ["gpt-4o", "gpt-4o-mini"],
    LLMProvider.GEMINI.value: ["gemini-3.5-flash", "gemini-2.0-flash"],
    LLMProvider.GROQ.value: [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ],
    LLMProvider.DEEPSEEK.value: ["deepseek-chat", "deepseek-coder"],
}


@router.get(
    "",
    response_model=list[ProviderModelInfo],
    summary="Get list of LLM providers and their model options",
)
async def get_providers() -> list[ProviderModelInfo]:
    """
    Returns supported LLM providers and their models, along with their quota exhaust status.
    """
    results = []
    for provider, models in AVAILABLE_PROVIDERS.items():
        is_ex = await QuotaTracker.is_exhausted(provider)
        results.append(
            ProviderModelInfo(
                provider=provider,
                models=models,
                is_exhausted=is_ex,
            )
        )
    return results
