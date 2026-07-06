from fastapi import APIRouter

from src.api.ws import game_stream

ws_router = APIRouter()
ws_router.include_router(game_stream.router)
