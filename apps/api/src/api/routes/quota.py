from fastapi import APIRouter
from pydantic import BaseModel

from src.core.quota import QuotaManager

router = APIRouter()


class QuotaUsageResponse(BaseModel):
    api_key_index: int
    total_tokens: int


@router.get(
    "",
    response_model=list[QuotaUsageResponse],
    summary="Get current token usage for all isolated API keys",
)
async def get_quota_usage() -> list[QuotaUsageResponse]:
    """
    Returns the accumulated token usage for each of the 4 isolated API key indices.
    """
    usages = await QuotaManager.get_usage()
    return [
        QuotaUsageResponse(api_key_index=idx, total_tokens=usages.get(idx, 0))
        for idx in range(1, 5)
    ]
