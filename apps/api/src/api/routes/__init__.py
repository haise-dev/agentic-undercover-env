from fastapi import APIRouter

from src.api.routes import episodes

api_router = APIRouter()
api_router.include_router(episodes.router, prefix="/episodes", tags=["Episodes"])
