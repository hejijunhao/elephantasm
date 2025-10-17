"""API v1 router aggregation."""

from fastapi import APIRouter

from backend.app.api.v1.endpoints import events

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(events.router)
