from fastapi import APIRouter

from app.api.routes import health
from app.identity.api.routes import router as identity_router
from app.identity.api.users import router as identity_users_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(identity_router)
api_router.include_router(identity_users_router)
