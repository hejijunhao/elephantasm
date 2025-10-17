"""Main API router aggregation."""

from fastapi import APIRouter

from backend.app.api.routes import events, health

api_router = APIRouter()

# Include route modules
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, tags=["events"])
