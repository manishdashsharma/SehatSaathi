from fastapi import APIRouter
from app.api.v1 import auth, users, documents, sessions, agents, webhooks

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(documents.router)
api_router.include_router(sessions.router)
api_router.include_router(agents.router)
api_router.include_router(webhooks.router)
