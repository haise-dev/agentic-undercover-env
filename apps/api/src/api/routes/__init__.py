from fastapi import APIRouter

from src.api.routes import episodes, providers, quota

api_router = APIRouter()
api_router.include_router(episodes.router, prefix="/episodes", tags=["Episodes"])
api_router.include_router(providers.router, prefix="/providers", tags=["Providers"])
api_router.include_router(quota.router, prefix="/quota", tags=["Quota"])
