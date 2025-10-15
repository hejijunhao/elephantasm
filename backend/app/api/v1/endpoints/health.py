from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns the health status of the API.
    """
    return {
        "status": "healthy",
        "message": "API is running"
    }
