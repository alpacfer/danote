from fastapi import APIRouter

from app.api.routes.account import router as account_router
from app.api.routes.analyze import router as analyze_router
from app.api.routes.developer import router as developer_router
from app.api.routes.guest import router as guest_router
from app.api.routes.root import router as root_router
from app.api.routes.sentencebank import router as sentencebank_router
from app.api.routes.wordbank import router as wordbank_router

api_router = APIRouter()
api_router.include_router(root_router)
api_router.include_router(account_router)
api_router.include_router(guest_router)
api_router.include_router(developer_router)
api_router.include_router(analyze_router)
api_router.include_router(wordbank_router)
api_router.include_router(sentencebank_router)
