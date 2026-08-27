from fastapi import APIRouter

from .chat.controller import ChatRouter
from .kb.controller import KbRouter

ai_router = APIRouter(prefix="/ai")

ai_router.include_router(ChatRouter)
ai_router.include_router(KbRouter)
