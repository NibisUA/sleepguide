from fastapi import APIRouter

from app.api import auth, me, sleep

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(sleep.router)
