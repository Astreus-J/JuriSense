from fastapi import APIRouter

from app.api.routes import health
from app.identity.api.routes import router as identity_router
from app.identity.api.users import router as identity_users_router
from app.integrations.api.routes import router as integrations_router
from app.suppliers.api.routes import router as suppliers_router

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router)
api_router.include_router(identity_router)
api_router.include_router(identity_users_router)
api_router.include_router(integrations_router)
api_router.include_router(suppliers_router)
