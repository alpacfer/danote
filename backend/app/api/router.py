from fastapi import APIRouter

from app.api.routes.analyze import router as analyze_router
from app.api.routes.root import router as root_router
from app.api.routes.tokens import router as tokens_router
from app.api.routes.wordbank import router as wordbank_router

api_router = APIRouter()
api_router.include_router(root_router)
api_router.include_router(analyze_router)
api_router.include_router(tokens_router)
api_router.include_router(wordbank_router)
