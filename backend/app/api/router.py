from fastapi import APIRouter

from app.accounts.api.routes import router as accounts_router
from app.accounts.api.users import router as users_router
from app.api.routes import health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(accounts_router)
api_router.include_router(users_router)
